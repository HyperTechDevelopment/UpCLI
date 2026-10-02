"""Pacote do AGENTS — Centro de Atualizações.

Organização em módulos:

  tema         cores, tamanho do terminal e layout responsivo
  componentes  widgets reutilizáveis (caixas, tabelas, mensagens, prompts)
  gerenciador  modelo e persistência da lista de ferramentas
  execucao     execução de comandos com contenção de árvore (Job Object)
  telas        telas do modo interativo
  automacao    seleção e execução não interativas (linha de comando)
  cli          ponto de entrada
"""

__version__ = "3.1"

__all__ = [
    "tema",
    "componentes",
    "gerenciador",
    "execucao",
    "telas",
    "automacao",
    "cli",
]
