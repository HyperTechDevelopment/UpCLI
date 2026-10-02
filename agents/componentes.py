"""Componentes reutilizáveis de interface.

Aqui ficam os "tijolos" de UI: caixas, tabelas, mensagens, prompts e barra de
progresso. Todos recebem (ou calculam) a largura disponível e degradam de forma
previsível em terminais estreitos — a responsividade mora aqui, não nas telas.

Regra de ouro: o texto das células NUNCA carrega código ANSI. A cor é aplicada
depois de calcular a largura, senão a contagem de caracteres sai errada.
"""

import os
import re
import sys
from dataclasses import dataclass

from .tema import Cores, largura_util

_ANSI = re.compile(r"\033\[[0-9;]*m")

# Modo interativo: quando desligado (execução por linha de comando), nada de
# limpar tela, pausar ou pedir input.
_INTERATIVO = True


def definir_interativo(valor):
    """Liga/desliga o modo interativo (usado pela automação)."""
    global _INTERATIVO
    _INTERATIVO = bool(valor)


def interativo():
    """True quando a UI pode desenhar telas e pedir input."""
    return _INTERATIVO


# =============================================
#  TEXTO E LARGURA (consciente de ANSI)
# =============================================
def sem_ansi(texto):
    """Remove sequências de cor para medir o texto visível."""
    return _ANSI.sub("", texto)


def largura_visivel(texto):
    """Largura de exibição, ignorando códigos ANSI."""
    return len(sem_ansi(texto))


def truncar(texto, limite):
    """Corta o texto ao limite, terminando com reticências quando preciso."""
    texto = str(texto)
    if limite <= 0:
        return ""
    if len(texto) <= limite:
        return texto
    if limite == 1:
        return "…"
    return texto[: limite - 1] + "…"


def preencher(texto, largura, alinhamento="<"):
    """Preenche o texto até a largura, respeitando códigos ANSI."""
    espaco = max(0, largura - largura_visivel(texto))
    if alinhamento == ">":
        return " " * espaco + texto
    if alinhamento == "^":
        esquerda = espaco // 2
        return " " * esquerda + texto + " " * (espaco - esquerda)
    return texto + " " * espaco


# =============================================
#  TELA E INPUT
# =============================================
def limpar_tela():
    """Limpa a tela do terminal de forma cross-platform."""
    if not _INTERATIVO:
        return
    os.system("cls" if sys.platform == "win32" else "clear")


def pausar(mensagem="Pressione Enter para voltar ao menu..."):
    """Pausa até o usuário pressionar Enter."""
    if not _INTERATIVO:
        return
    try:
        input(f"\n   {Cores.ESCURECER}{mensagem}{Cores.RESET}")
    except (EOFError, KeyboardInterrupt):
        pass


def prompt(rotulo, cor=None):
    """Lê uma linha com o rótulo colorido.

    EOF (Ctrl+Z/Ctrl+D) e Ctrl+C propagam até o main, que encerra de forma
    limpa. Engolir essas exceções aqui causava laço infinito com `cls`.
    """
    cor = cor or Cores.BRANCO_BRILHANTE
    return input(f"   {cor}{rotulo}{Cores.RESET}").strip()


# =============================================
#  ESTRUTURA (caixas, separadores, menu)
# =============================================
def _linha_caixa(conteudo, largura, alinhamento="<"):
    """Linha com bordas verticais e conteúdo alinhado dentro da caixa."""
    interior = preencher(conteudo, largura - 2, alinhamento)
    return f"  {Cores.AZUL}║{Cores.RESET}{interior}{Cores.AZUL}║{Cores.RESET}"


def titulo_app(titulo, subtitulo=None, largura=None):
    """Bloco de título do programa, com borda e subtítulo opcional."""
    largura = largura or largura_util()
    borda = "═" * largura
    print()
    print(f"  {Cores.AZUL}{borda}{Cores.RESET}")
    print(_linha_caixa(" " * (largura - 2), largura))
    print(_linha_caixa(f"  {Cores.NEGRITO}{Cores.CIANO_CLARO}{truncar(titulo, largura - 6)}{Cores.RESET}", largura))
    if subtitulo:
        print(_linha_caixa(f"  {Cores.ESCURECER}{truncar(subtitulo, largura - 6)}{Cores.RESET}", largura))
    print(_linha_caixa(" " * (largura - 2), largura))
    print(f"  {Cores.AZUL}{borda}{Cores.RESET}")


def cabecalho(texto, largura=None):
    """Cabeçalho de seção, centralizado."""
    largura = largura or largura_util()
    print()
    print(f"  {Cores.AZUL}{'═' * largura}{Cores.RESET}")
    conteudo = f"{Cores.NEGRITO}{Cores.BRANCO_BRILHANTE}{truncar(texto, largura - 4)}{Cores.RESET}"
    print(_linha_caixa(preencher(conteudo, largura - 2, "^"), largura))
    print(f"  {Cores.AZUL}{'═' * largura}{Cores.RESET}")


def caixa_campos(titulo, campos, largura=None):
    """Caixa com título e pares (rótulo, valor, cor) — para confirmar/editar."""
    largura = largura or largura_util()
    borda = "═" * largura
    print(f"  {Cores.AZUL}{borda}{Cores.RESET}")
    cab = preencher(f"{Cores.NEGRITO}{truncar(titulo, largura - 4)}{Cores.RESET}", largura - 2, "^")
    print(_linha_caixa(cab, largura))
    print(f"  {Cores.AZUL}{'─' * largura}{Cores.RESET}")
    for rot, valor, cor in campos:
        rot = truncar(rot, max(6, largura // 3))
        valor = truncar(valor, max(4, largura - len(rot) - 6))
        conteudo = f" {Cores.ESCURECER}{rot}:{Cores.RESET} {cor}{valor}{Cores.RESET}"
        print(_linha_caixa(conteudo, largura))
    print(f"  {Cores.AZUL}{borda}{Cores.RESET}")


def separador(largura=None, char="─", cor=None):
    """Linha divisória horizontal."""
    largura = largura or largura_util()
    cor = cor if cor is not None else Cores.AZUL
    print(f"  {cor}{char * largura}{Cores.RESET}")


def item_menu(numero, texto, cor=None, dica=None, largura=None):
    """Item de menu: tecla entre colchetes, rótulo e dica alinhada à direita.

    A dica só aparece quando há largura de sobra; em terminal estreito o item
    vira uma linha simples.
    """
    cor = cor or Cores.BRANCO_BRILHANTE
    prefixo = f"  {Cores.NEGRITO}{cor}[{numero}]{Cores.RESET}  "
    if dica and largura:
        disponivel = largura - largura_visivel(prefixo) - largura_visivel(dica) - 2
        if disponivel >= len(texto) + 2:
            espaco = largura - largura_visivel(prefixo) - largura_visivel(texto) - largura_visivel(dica)
            print(f"{prefixo}{cor}{texto}{Cores.RESET}{' ' * espaco}{Cores.ESCURECER}{dica}{Cores.RESET}")
            return
    print(f"{prefixo}{cor}{truncar(texto, largura - 8) if largura else texto}{Cores.RESET}")


def rotulo(texto):
    """Linha de rótulo em negrito."""
    print(f"  {Cores.NEGRITO}{texto}{Cores.RESET}")


def dica(texto):
    """Linha de texto secundária (apagada)."""
    print(f"  {Cores.ESCURECER}{texto}{Cores.RESET}")


def tecla(simbolo):
    """Fragmento de tecla para compor instruções, ex: [E]."""
    return f"{Cores.AMARELO_CLARO}[{simbolo}]{Cores.RESET}"


# =============================================
#  MENSAGENS E FEEDBACK
# =============================================
_ICONES = {
    "sucesso": "✓",
    "erro": "✗",
    "alerta": "!",
    "info": "ℹ",
}

# Nome do atributo de cor por tipo. Resolvido em tempo de chamada (getattr),
# e não copiado no import: `Cores.desabilitar()` troca os atributos por "", e um
# dict congelado no import continuaria emitindo códigos ANSI mesmo com --no-color.
_ATRIBUTO_COR = {
    "sucesso": "SUCESSO",
    "erro": "ERRO",
    "alerta": "ALERTA",
    "info": "INFO",
}


def mensagem(tipo, texto):
    """Mensagem de feedback com ícone e cor semântica."""
    cor = getattr(Cores, _ATRIBUTO_COR.get(tipo, ""), "")
    icone = _ICONES.get(tipo, "·")
    print(f"   {cor}{icone} {texto}{Cores.RESET}")


def barra_progresso(porcentagem, largura=22):
    """Barra de progresso colorida conforme a porcentagem."""
    if porcentagem < 30:
        cor = Cores.ERRO
    elif porcentagem < 70:
        cor = Cores.ALERTA
    else:
        cor = Cores.SUCESSO
    preenchidos = int(porcentagem * largura / 100)
    vazios = largura - preenchidos
    return f"{cor}{'█' * preenchidos}{Cores.ESCURECER}{'░' * vazios}{Cores.RESET}"


# =============================================
#  TABELA RESPONSIVA
# =============================================
@dataclass
class Coluna:
    """Definição de uma coluna: peso para o cálculo e limites de largura.

    peso 0 com minimo == maximo cria uma coluna de largura fixa (ex: o ★).
    """

    titulo: str
    peso: int = 1
    minimo: int = 3
    maximo: int = 200
    alinhamento: str = "<"


def distribuir_largura(total, colunas):
    """Divide `total` entre as colunas proporcionalmente ao peso.

    Respeita mínimo e máximo de cada coluna e sempre converge para somar
    exatamente `total`. Se `total` for menor que a soma dos mínimos, encolhe
    proporcionalmente (com piso 1) para nunca estourar a largura do terminal —
    degradar é melhor que quebrar o layout.
    """
    n = len(colunas)
    if n == 0:
        return []

    minimos = [max(1, c.minimo) for c in colunas]
    soma_min = sum(minimos)

    if total <= soma_min:
        # Não cabe nem o mínimo: encolhe proporcionalmente, piso 1.
        pisos = [1] * n
        tetos = [max(1, total)] * n
        larguras = [max(1, total * m // soma_min) for m in minimos]
    else:
        pisos = minimos
        tetos = [max(p, c.maximo) for p, c in zip(pisos, colunas)]
        soma_pesos = sum(max(0, c.peso) for c in colunas) or n
        larguras = [
            max(p, min(c.maximo, int(total * max(0, c.peso) / soma_pesos)))
            for p, c in zip(pisos, colunas)
        ]

    # Ajusta a diferença restante, tirando de quem tem mais folga.
    for _ in range(20000):
        diferenca = total - sum(larguras)
        if diferenca == 0:
            break
        if diferenca > 0:
            candidatos = [k for k in range(n) if larguras[k] < tetos[k]]
            if not candidatos:
                break
            j = max(candidatos, key=lambda k: tetos[k] - larguras[k])
            larguras[j] += 1
        else:
            candidatos = [k for k in range(n) if larguras[k] > pisos[k]]
            if not candidatos:
                break
            j = max(candidatos, key=lambda k: larguras[k] - pisos[k])
            larguras[j] -= 1

    return larguras


def _partes_celula(celula):
    """Aceita `str` ou `(texto, cor)` e devolve os dois separados."""
    if isinstance(celula, tuple):
        return celula[0], celula[1]
    return celula, ""


def tabela(colunas, linhas, largura=None, cor_cabecalho=None, cor_borda=None):
    """Renderiza uma tabela alinhada que se ajusta à largura disponível."""
    largura = largura or largura_util()
    cor_cabecalho = cor_cabecalho if cor_cabecalho is not None else Cores.NEGRITO
    cor_borda = cor_borda if cor_borda is not None else Cores.AZUL

    gaps = 2 * (len(colunas) - 1)
    disponivel = max(len(colunas), largura - gaps)
    larguras = distribuir_largura(disponivel, colunas)

    def render(celulas):
        partes = []
        for coluna, largura_col, celula in zip(colunas, larguras, celulas):
            texto, cor = _partes_celula(celula)
            conteudo = preencher(truncar(texto, largura_col), largura_col, coluna.alinhamento)
            partes.append(f"{cor}{conteudo}{Cores.RESET}" if cor else conteudo)
        return "  " + "  ".join(partes)

    print(render([(c.titulo, cor_cabecalho) for c in colunas]))
    print(f"  {cor_borda}{'  '.join('─' * w for w in larguras)}{Cores.RESET}")
    for linha in linhas:
        print(render(linha))
