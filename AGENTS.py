#!/usr/bin/env python3
"""
AGENTS - Centro de Atualizações

Ponto de entrada enxuto. A implementação vive no pacote `agents/`:

    agents/tema.py         cores, terminal e layout responsivo
    agents/componentes.py  widgets reutilizáveis (caixas, tabelas, mensagens)
    agents/gerenciador.py  lista de ferramentas e persistência
    agents/execucao.py     execução de comandos (Job Object)
    agents/telas.py        telas do modo interativo
    agents/automacao.py    seleção/execução por linha de comando
    agents/cli.py          despacho (menu ou automação)
"""

from agents.cli import main

if __name__ == "__main__":
    main()
