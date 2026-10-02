"""Agendamento da atualização automática (Windows, via schtasks).

Dá suporte à tela de Automação: monta a linha de comando que roda o script sem
interação e cria/remove/consulta a tarefa no Agendador de Tarefas do Windows.

O comando usa caminhos absolutos (python e o AGENTS.py), e o próprio script
descobre a pasta do projeto por `__file__` — então a tarefa funciona
independente do diretório de trabalho que o agendador usar.
"""

import subprocess
import sys

from .gerenciador import BASE_DIR

NOME_TAREFA = "AGENTS - Atualizar tudo"

# Rótulos amigáveis para cada frequência suportada.
FREQUENCIAS = {
    "diaria": "Diária",
    "semanal": "Semanal (segunda-feira)",
    "logon": "Ao entrar (logon)",
}


def suportado():
    """True quando o agendamento automático está disponível (Windows)."""
    return sys.platform == "win32"


def comando_automatico():
    """Linha de comando pronta para rodar a atualização sem interação."""
    script = BASE_DIR / "AGENTS.py"
    return f'"{sys.executable}" "{script}" --update-all --no-color'


def criar(frequencia="diaria", hora="09:00"):
    """Cria (ou substitui) a tarefa agendada. Retorna (ok, saída)."""
    if not suportado():
        return False, "Agendamento disponível apenas no Windows."

    args = [
        "schtasks", "/Create",
        "/TN", NOME_TAREFA,
        "/TR", comando_automatico(),
        "/F",
    ]
    if frequencia == "diaria":
        args += ["/SC", "DAILY", "/ST", hora]
    elif frequencia == "semanal":
        args += ["/SC", "WEEKLY", "/D", "MON", "/ST", hora]
    elif frequencia == "logon":
        args += ["/SC", "ONLOGON"]
    else:
        return False, f"Frequência inválida: {frequencia}"

    return _executar(args)


def remover():
    """Remove a tarefa agendada. Retorna (ok, saída)."""
    if not suportado():
        return False, "Agendamento disponível apenas no Windows."
    return _executar(["schtasks", "/Delete", "/TN", NOME_TAREFA, "/F"])


def consultar():
    """Consulta a tarefa agendada. Retorna (ok, saída)."""
    if not suportado():
        return False, "Agendamento disponível apenas no Windows."
    return _executar(["schtasks", "/Query", "/TN", NOME_TAREFA])


def _executar(args):
    """Roda o schtasks e devolve (sucesso, saída combinada)."""
    try:
        resultado = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
        return resultado.returncode == 0, resultado.stdout.strip()
    except FileNotFoundError:
        return False, "schtasks não encontrado no sistema."
    except Exception as e:
        return False, str(e)
