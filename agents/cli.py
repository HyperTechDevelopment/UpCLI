"""Ponto de entrada: despacha entre o menu interativo e o modo automático."""

import sys
import time

from . import telas
from .automacao import criar_parser, modo_automatico
from .gerenciador import GerenciadorFerramentas
from .tema import Cores, configurar_saida_utf8, inicializar_cores


def main():
    """Função principal do programa."""
    configurar_saida_utf8()
    args = criar_parser().parse_args()

    if args.update_all or args.update or args.list:
        try:
            sys.exit(modo_automatico(args))
        except KeyboardInterrupt:
            print(f"\n{Cores.ALERTA}Interrompido pelo usuário.{Cores.RESET}", file=sys.stderr)
            sys.exit(130)

    inicializar_cores()
    if args.no_color:
        Cores.desabilitar()

    gerenciador = GerenciadorFerramentas()

    try:
        while True:
            opcao = telas.exibir_menu()

            if opcao == "1":
                telas.executar_atualizacao(gerenciador)
            elif opcao == "2":
                telas.selecionar_ferramentas(gerenciador)
            elif opcao == "3":
                telas.listar_ferramentas_interface(gerenciador)
            elif opcao == "4":
                telas.adicionar_ferramenta_interface(gerenciador)
            elif opcao == "5":
                telas.gerenciar_ferramentas_interface(gerenciador)
            elif opcao == "6":
                telas.automacao_interface(gerenciador)
            elif opcao == "0":
                telas.exibir_saida()
                break
            else:
                # Opção inválida - volta ao menu
                time.sleep(0.5)

    except KeyboardInterrupt:
        print(f"\n\n{Cores.ALERTA}   Interrompido pelo usuário. Saindo...{Cores.RESET}")
        time.sleep(1)
    except EOFError:
        print(f"\n\n{Cores.ALERTA}   Entrada encerrada. Saindo...{Cores.RESET}")
        time.sleep(1)

    sys.exit(0)
