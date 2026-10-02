"""Execução de comandos com contenção de árvore de processos (Job Object).

Uma ferramenta pode retornar antes de realmente terminar. O caso conhecido é o
`hermes update`: no Windows ele desanexa o resto do trabalho (uv sync, builds,
restart do gateway) num processo filho e retorna 0 na hora — o próprio updater
diz "this shell returns right away" (hermes_cli/update_handoff.py,
continue_update_in_fresh_interpreter).

Sem contenção o script dava o Hermes como concluído e seguia para a próxima
ferramenta enquanto o update anterior ainda mexia no mesmo install: atualização
em cima de atualização, sem saber onde está.

Um Job Object resolve de forma genérica — não só para o Hermes. Processos
filhos herdam a participação no job, então "job sem processos ativos" é prova
real de que a ferramenta terminou, mesmo que o processo direto tenha mentido.

Exceção deliberada, e importante: o job permite breakaway, porque o gateway do
Hermes é spawnado com CREATE_BREAKAWAY_FROM_JOB justamente para sobreviver como
daemon. Ele escapa — e deve escapar. Nesse caso a espera termina quando o
processo direto morre, em vez de ficar presa num daemon eterno.
"""

import ctypes
import subprocess
import sys
import time

from .tema import Cores

_TIMEOUT_COMANDO = 30 * 60       # segundos; acima do teto de lock do Hermes (20 min)
_INTERVALO_ESPERA_JOB = 0.5      # segundos entre consultas ao job

# Flags do Job Object. BREAKAWAY_OK é essencial: daemons legítimos (o gateway do
# Hermes, spawnado com CREATE_BREAKAWAY_FROM_JOB) precisam poder escapar, senão
# ficariam presos no job e a espera nunca terminaria. Quem NÃO pede breakaway —
# o processo de handoff do update — permanece contido e é o que esperamos.
_JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x00000800
_JobObjectExtendedLimitInformation = 9
_JobObjectBasicAccountingInformation = 1


class _IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]


class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", ctypes.c_uint32),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", ctypes.c_uint32),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", ctypes.c_uint32),
        ("SchedulingClass", ctypes.c_uint32),
    ]


class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", _IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _JOBOBJECT_BASIC_ACCOUNTING_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("TotalUserTime", ctypes.c_int64),
        ("TotalKernelTime", ctypes.c_int64),
        ("ThisPeriodTotalUserTime", ctypes.c_int64),
        ("ThisPeriodTotalKernelTime", ctypes.c_int64),
        ("TotalPageFaultCount", ctypes.c_uint32),
        ("TotalProcesses", ctypes.c_uint32),
        ("ActiveProcesses", ctypes.c_uint32),
        ("TotalTerminatedProcesses", ctypes.c_uint32),
    ]


class JobObject:
    """Job Object do Windows: contém a árvore de processos de um comando e diz
    quando ela terminou de verdade.

    Só existe em Windows; em outros sistemas `disponivel` é False e o chamador
    cai no comportamento antigo (esperar apenas o processo direto).

    Criado com JOB_OBJECT_LIMIT_BREAKAWAY_OK de propósito: daemons legítimos — o
    gateway do Hermes, spawnado com CREATE_BREAKAWAY_FROM_JOB
    (hermes_cli/_subprocess_compat.py) — precisam poder escapar. Eles devem
    sobreviver ao update, e esperá-los deixaria o script preso para sempre. Já o
    processo de handoff do update é um Popen comum, sem breakaway: esse fica
    contido, e é exatamente ele que fazemos o script esperar.

    KILL_ON_JOB_CLOSE é deliberadamente omitido: fechar o handle não pode matar
    um processo que ainda esteja trabalhando.
    """

    def __init__(self):
        self.handle = None
        self.disponivel = False
        # Só vira True quando um processo entra de fato no job. Um job disponível
        # mas VAZIO responderia "0 ativos" na hora, e o script concluiria que o
        # comando terminou com ele ainda rodando.
        self.contido = False
        self._kernel32 = None
        if sys.platform != "win32":
            return
        # Qualquer falha aqui degrada para "sem job", nunca derruba o script:
        # sem contenção ainda dá para atualizar, quebrando no meio não.
        try:
            self._kernel32 = self._carregar_kernel32()
            if self._kernel32 is None:
                return
            self.handle = self._criar()
            self.disponivel = self.handle is not None
        except Exception:
            self.handle = None
            self.disponivel = False

    @staticmethod
    def _carregar_kernel32():
        """Carrega kernel32 com assinaturas corretas; None se indisponível."""
        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        except (OSError, AttributeError):
            return None

        kernel32.CreateJobObjectW.restype = ctypes.c_void_p
        kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]
        kernel32.SetInformationJobObject.restype = ctypes.c_int
        kernel32.SetInformationJobObject.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32
        ]
        kernel32.AssignProcessToJobObject.restype = ctypes.c_int
        kernel32.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        kernel32.QueryInformationJobObject.restype = ctypes.c_int
        kernel32.QueryInformationJobObject.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p
        ]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        kernel32.TerminateJobObject.restype = ctypes.c_int
        kernel32.TerminateJobObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel32.CloseHandle.restype = ctypes.c_int
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        return kernel32

    def _criar(self):
        """Cria o job e liga BREAKAWAY_OK; None em qualquer falha."""
        handle = self._kernel32.CreateJobObjectW(None, None)
        if not handle:
            return None
        info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_BREAKAWAY_OK
        ok = self._kernel32.SetInformationJobObject(
            handle, _JobObjectExtendedLimitInformation, ctypes.byref(info), ctypes.sizeof(info)
        )
        if not ok:
            self._kernel32.CloseHandle(handle)
            return None
        return handle

    def conter(self, pid):
        """Coloca um processo (e tudo que ele criar depois) dentro do job.

        Lida logo após o Popen: o filho direto é o `cmd.exe` do shell, que ainda
        está inicializando, então nenhum descendente tem como escapar antes disto.
        """
        if not self.disponivel:
            return False
        # PROCESS_SET_QUOTA | PROCESS_TERMINATE, o mínimo que AssignProcessToJobObject exige.
        PROCESS_SET_QUOTA_E_TERMINATE = 0x0100 | 0x0001
        kernel32 = self._kernel32
        processo = kernel32.OpenProcess(PROCESS_SET_QUOTA_E_TERMINATE, False, int(pid))
        if not processo:
            return False
        try:
            ok = bool(kernel32.AssignProcessToJobObject(self.handle, processo))
            self.contido = ok
            return ok
        except Exception:
            return False
        finally:
            try:
                kernel32.CloseHandle(processo)
            except Exception:
                pass

    def ativos(self):
        """Quantos processos ainda estão vivos dentro do job."""
        if not self.contido:
            return 0
        info = _JOBOBJECT_BASIC_ACCOUNTING_INFORMATION()
        ok = self._kernel32.QueryInformationJobObject(
            self.handle, _JobObjectBasicAccountingInformation, ctypes.byref(info),
            ctypes.sizeof(info), None
        )
        return info.ActiveProcesses if ok else 0

    def matar_tudo(self):
        """Encerra o job inteiro (inclusive descendentes); nunca levanta.

        Usado só no timeout. Matar apenas o processo direto deixaria os filhos
        trabalhando no mesmo install — que é justamente a sobreposição que esta
        contenção existe para impedir.
        """
        if not self.contido or self._kernel32 is None:
            return
        try:
            self._kernel32.TerminateJobObject(self.handle, 1)
        except Exception:
            pass

    def fechar(self):
        """Fecha o handle; não mata nada que ainda esteja rodando."""
        if self.handle and self._kernel32 is not None:
            self._kernel32.CloseHandle(self.handle)
        self.handle = None
        self.disponivel = False
        self.contido = False


def _aguardar_arvore(job, processo):
    """Espera a árvore de processos terminar; devolve 'fim' ou 'timeout'.

    A condição é uma só: `job.ativos() == 0`. É a prova real de que a ferramenta
    terminou, e é justamente o que o processo direto não consegue provar —
    `hermes update` devolve 0 com o trabalho ainda rodando num filho desanexado.

    Deliberadamente NÃO se olha o processo direto aqui. Na cadeia do Hermes
    (cmd.exe -> hermes.cmd -> hermes.exe -> python) o cmd.exe sai cedo
    justamente porque o handoff é desanexado; tratá-lo como "terminou" daria o
    update por concluído na hora, que é o bug que esta correção elimina.

    Daemons legítimos como o gateway do Hermes não seguram esta espera: eles são
    spawnados com CREATE_BREAKAWAY_FROM_JOB, então saem do job e não contam em
    `ativos()`. Quem permanece no job é o trabalho real do update, e é ele que
    esperamos.

    Sem job contendo o processo, resta esperar o processo direto — o mesmo
    comportamento de antes desta correção.
    """
    if not job.contido:
        try:
            processo.wait(timeout=_TIMEOUT_COMANDO)
            return "fim"
        except subprocess.TimeoutExpired:
            return "timeout"

    inicio = time.monotonic()
    while True:
        if job.ativos() == 0:
            return "fim"
        if time.monotonic() - inicio > _TIMEOUT_COMANDO:
            return "timeout"
        time.sleep(_INTERVALO_ESPERA_JOB)


def executar_comando(comando):
    """Executa um comando e só retorna quando a ÁRVORE de processos terminar.

    A saída aparece em tempo real e prompts interativos (ex: confirmar com Y)
    funcionam, pois stdin/stdout/stderr são os do próprio terminal.

    Não basta esperar o processo direto: `hermes update` no Windows imprime
    "this shell returns right away" e devolve 0 enquanto o resto do trabalho
    (uv sync, builds, restart do gateway) continua num filho desanexado
    (hermes_cli/update_handoff.py). Esperar só o processo direto fazia o script
    iniciar a próxima ferramenta com o update anterior ainda rodando — updates
    sobrepostos, sem saber onde cada um está. Por isso o comando roda dentro de
    um Job Object e esperamos o job esvaziar.

    Os flushes garantem que cabeçalhos/rodapés do script não se misturem com a
    saída da ferramenta (que pode usar \\r / barras de progresso ANSI).
    """
    job = JobObject()
    try:
        sys.stdout.flush()
        sys.stderr.flush()
        # shell=True preserva o comportamento anterior; como é o filho direto do
        # Popen, o cmd.exe entra no job e seus descendentes herdam a participação.
        processo = subprocess.Popen(comando, shell=True)
        job.conter(processo.pid)
        resultado = _aguardar_arvore(job, processo)
        if resultado == "timeout":
            # Encerra o job INTEIRO, não só o processo direto: os filhos
            # continuariam mexendo no mesmo install, que é exatamente a
            # sobreposição que esta contenção existe para impedir. Precisa
            # acontecer antes do fechar() abaixo, que só libera o handle.
            job.matar_tudo()
        # Drena o status: `returncode` continua None até o processo ser
        # coletado, e ler antes disso daria falso negativo em todo comando.
        # O wait é instantâneo aqui (só o processo direto, que já terminou).
        processo.wait()
    except Exception:
        print()
        sys.stdout.flush()
        return False
    finally:
        job.fechar()

    # Ferramentas com barra de progresso terminam com \r sem \n:
    # força quebra de linha e libera o buffer antes do próximo cabeçalho.
    print()
    sys.stdout.flush()
    sys.stderr.flush()

    if resultado == "fim":
        return processo.returncode == 0

    # Timeout (o job já foi encerrado acima).
    print(f"{Cores.ERRO}   ⏱ Comando excedeu {_TIMEOUT_COMANDO // 60} minutos e foi interrompido.{Cores.RESET}")
    return False
