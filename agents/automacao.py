"""Seleção e execução não interativas (linha de comando).

Dá ao script o que um agendador de tarefas precisa: rodar sem menu, sem pausas
e devolver um código de saída que diz se deu tudo certo (0), se algo falhou (1)
ou se a seleção era inválida (2).
"""

import argparse
import re
import sys

from . import componentes
from .gerenciador import GerenciadorFerramentas
from .telas import executar_atualizacao
from .tema import Cores, inicializar_cores


def resolver_selecao(gerenciador, texto):
    """Converte uma seleção textual em índices (1-based).

    Aceita números ("1,3"), intervalos ("1-5"), nomes ("Claude,CMDC") e
    combinações. Nomes podem ser parciais desde que casem com um único item.
    """
    ferramentas = gerenciador.listar_ferramentas()
    indices = set()
    desconhecidos = []

    for parte in re.split(r"[,\s]+", texto.strip()):
        if not parte:
            continue

        if parte.isdigit():
            num = int(parte)
            if 1 <= num <= len(ferramentas):
                indices.add(num)
            else:
                desconhecidos.append(parte)
            continue

        if re.fullmatch(r"\d+-\d+", parte):
            inicio, fim = (int(x) for x in parte.split("-", 1))
            for num in range(inicio, fim + 1):
                if 1 <= num <= len(ferramentas):
                    indices.add(num)
            continue

        # Nome: primeiro exato, depois parcial (só se casar com um único item)
        alvo = parte.lower()
        exatos = [i for i, (n, _) in enumerate(ferramentas, 1) if n.lower() == alvo]
        parciais = [i for i, (n, _) in enumerate(ferramentas, 1) if alvo in n.lower()]
        if exatos:
            indices.update(exatos)
        elif len(parciais) == 1:
            indices.update(parciais)
        else:
            desconhecidos.append(parte)

    if desconhecidos:
        print(f"{Cores.ALERTA}Ignorados (sem correspondência): {', '.join(desconhecidos)}{Cores.RESET}",
              file=sys.stderr)

    return sorted(indices)


def listar_em_texto(gerenciador):
    """Lista as ferramentas em texto simples (para automação/pipelines)."""
    ferramentas = gerenciador.listar_ferramentas()
    for i, (nome, cmd) in enumerate(ferramentas, 1):
        print(f"{i:>3}  {nome}  —  {cmd}")
    print(f"\nTotal: {len(ferramentas)} ferramentas")
    return 0


def criar_parser():
    """Monta o parser de argumentos do modo automático."""
    parser = argparse.ArgumentParser(
        prog="AGENTS.py",
        description="AGENTS — Centro de Atualizações: menu interativo ou execução automatizada.",
        epilog=(
            "exemplos:\n"
            "  AGENTS.py                       menu interativo\n"
            "  AGENTS.py --update-all          atualiza todas as ferramentas\n"
            "  AGENTS.py --update Claude,CMDC  atualiza por nome\n"
            "  AGENTS.py --update 1,3-5        atualiza por índice/intervalo\n"
            "  AGENTS.py --list                lista as ferramentas"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("-a", "--update-all", action="store_true",
                       help="atualiza todas as ferramentas sem interação")
    grupo.add_argument("-u", "--update", metavar="SELEÇÃO",
                       help="atualiza por número, intervalo ou nome (ex: 1,3-5,Claude)")
    grupo.add_argument("-l", "--list", action="store_true",
                       help="lista as ferramentas e sai")
    parser.add_argument("--no-color", action="store_true",
                        help="desativa cores na saída")
    return parser


def modo_automatico(args):
    """Executa os modos não interativos. Retorna o código de saída."""
    componentes.definir_interativo(False)

    inicializar_cores()
    if args.no_color:
        Cores.desabilitar()

    gerenciador = GerenciadorFerramentas()

    if args.list:
        return listar_em_texto(gerenciador)

    if args.update_all:
        indices = None
    else:
        indices = resolver_selecao(gerenciador, args.update)
        if not indices:
            print(f"{Cores.ERRO}Nenhuma ferramenta válida em '{args.update}'.{Cores.RESET}",
                  file=sys.stderr)
            return 2

    _, falha = executar_atualizacao(gerenciador, indices)
    return 1 if falha else 0
