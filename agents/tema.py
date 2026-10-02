"""Cores, detecção de terminal e layout responsivo.

Concentra tudo que é "aparência base": paleta ANSI, tamanho do terminal e o
cálculo de largura útil. É o único módulo que fala com o sistema operacional
por questões de terminal.
"""

import os
import shutil
import sys

# Largura máxima do conteúdo. Em telas largas evita linhas esticadas demais,
# que ficam difíceis de ler.
LARGURA_MAX = 76

# Piso absoluto. Abaixo disso o conteúdo degradaria a ponto de não caber nada.
LARGURA_MIN = 16

# Abaixo deste valor as telas entram em modo compacto (empilham informação em
# vez de usar colunas lado a lado).
LIMITE_COMPACTO = 58


class Cores:
    """Suporte a cores ANSI com fallback para terminais sem suporte."""

    HABILITADA = True

    # Reset e estilos
    RESET = "\033[0m"
    NEGRITO = "\033[1m"
    ITALICO = "\033[3m"
    SUBLINHADO = "\033[4m"
    ESCURECER = "\033[2m"
    CLARO = "\033[22m"

    # Cores de texto
    PRETO = "\033[30m"
    CINZA_ESCURO = "\033[90m"
    VERMELHO = "\033[31m"
    VERMELHO_CLARO = "\033[91m"
    VERDE = "\033[32m"
    VERDE_CLARO = "\033[92m"
    AMARELO = "\033[33m"
    AMARELO_CLARO = "\033[93m"
    AZUL = "\033[34m"
    AZUL_CLARO = "\033[94m"
    MAGENTA = "\033[35m"
    MAGENTA_CLARA = "\033[95m"
    CIANO = "\033[36m"
    CIANO_CLARO = "\033[96m"
    BRANCO = "\033[37m"
    BRANCO_BRILHANTE = "\033[97m"

    # Cores de fundo
    FUNDO_PRETO = "\033[40m"
    FUNDO_CINZA_ESCURO = "\033[100m"
    FUNDO_VERMELHO = "\033[41m"
    FUNDO_VERDE = "\033[42m"
    FUNDO_AMARELO = "\033[43m"
    FUNDO_AZUL = "\033[44m"
    FUNDO_MAGENTA = "\033[45m"
    FUNDO_CIANO = "\033[46m"
    FUNDO_BRANCO = "\033[47m"
    FUNDO_BRANCO_BRILHANTE = "\033[107m"

    # Destaques semânticos
    DESTACAR = "\033[1;96m"      # Ciano brilhante negrito
    SUCESSO = "\033[1;92m"       # Verde brilhante negrito
    ALERTA = "\033[1;93m"        # Amarelo brilhante negrito
    ERRO = "\033[1;91m"          # Vermelho brilhante negrito
    INFO = "\033[1;94m"          # Azul brilhante negrito

    @classmethod
    def desabilitar(cls):
        """Desabilita cores para terminais que não suportam."""
        for attr in dir(cls):
            if attr.isupper() and isinstance(getattr(cls, attr), str):
                setattr(cls, attr, "")
        cls.HABILITADA = False


def obter_tamanho_terminal():
    """Obtém o tamanho do terminal de forma segura."""
    try:
        tamanho = shutil.get_terminal_size((80, 24))
        return tamanho.columns, tamanho.lines
    except Exception:
        return 80, 24


def largura_util():
    """Largura do conteúdo, responsiva.

    Acompanha o terminal, mas com teto (LARGURA_MAX) para não esticar em telas
    largas e com piso (LARGURA_MIN) para não colapsar. É recalculada a cada
    chamada, então redimensionar a janela é refletido na próxima tela.
    """
    colunas, _ = obter_tamanho_terminal()
    return max(LARGURA_MIN, min(colunas - 2, LARGURA_MAX))


def modo_compacto(limite=LIMITE_COMPACTO):
    """True quando a largura é pequena demais para layouts de várias colunas."""
    return largura_util() < limite


def inicializar_cores():
    """Inicializa suporte a cores baseado no sistema operacional."""
    if sys.platform == "win32":
        try:
            # Tenta habilitar VT100 no Windows 10+
            os.system("")
        except Exception:
            Cores.desabilitar()

    # Verifica se o terminal suporta cores
    if not os.environ.get("FORCE_COLOR") and not sys.stdout.isatty():
        Cores.desabilitar()


def configurar_saida_utf8():
    """Força UTF-8 na saída para não quebrar com acentos e caracteres de caixa
    quando a saída é redirecionada (ex: log de tarefa agendada). `replace`
    garante que nenhum caractere derrube o script."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
