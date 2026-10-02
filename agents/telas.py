"""Telas do modo interativo.

Cada tela apenas orquestra componentes e regras de negócio: calcular a largura,
desenhar com os componentes e ler a entrada. Nada de formatação crua aqui — se
falta um estilo, ele vira componente, não código solto na tela.
"""

import sys
import time

from . import __version__
from . import agendador
from .componentes import (
    Coluna,
    barra_progresso,
    cabecalho,
    caixa_campos,
    dica,
    interativo,
    item_menu,
    limpar_tela,
    mensagem,
    pausar,
    preencher,
    prompt,
    rotulo,
    separador,
    tabela,
    tecla,
    titulo_app,
    truncar,
)
from .execucao import executar_comando
from .tema import Cores, largura_util


def _render_lista(gerenciador, largura):
    """Imprime a lista de ferramentas.

    Em terminal largo usa uma tabela alinhada; em terminal estreito empilha
    nome e comando em duas linhas, em vez de espremer colunas ilegíveis.
    """
    ferramentas = gerenciador.listar_ferramentas()

    if largura < 58:
        for i, (nome, cmd) in enumerate(ferramentas, 1):
            marcador = f"{Cores.MAGENTA_CLARA}★{Cores.RESET}" if gerenciador.eh_personalizada(i) else " "
            print(f"  {marcador} {Cores.NEGRITO}{i:>2}{Cores.RESET}  "
                  f"{Cores.BRANCO_BRILHANTE}{truncar(nome, largura - 8)}{Cores.RESET}")
            print(f"        {Cores.ESCURECER}$ {truncar(cmd, largura - 10)}{Cores.RESET}")
        return

    colunas = [
        Coluna("", peso=0, minimo=1, maximo=1, alinhamento="^"),
        Coluna("#", peso=0, minimo=3, maximo=4, alinhamento=">"),
        Coluna("Ferramenta", peso=3, minimo=12, maximo=32),
        Coluna("Comando", peso=6, minimo=14, maximo=200),
    ]
    linhas = []
    for i, (nome, cmd) in enumerate(ferramentas, 1):
        estrela = ("★", Cores.MAGENTA_CLARA) if gerenciador.eh_personalizada(i) else ""
        linhas.append([estrela, str(i), (nome, Cores.BRANCO_BRILHANTE), (cmd, Cores.ESCURECER)])
    tabela(colunas, linhas, largura)


def _pausa_curta(segundos=1):
    if interativo():
        time.sleep(segundos)


# =============================================
#  MENU
# =============================================
def exibir_menu():
    """Exibe o menu principal e retorna a opção do usuário."""
    limpar_tela()
    largura = largura_util()
    titulo_app("AGENTS — Centro de Atualizações", f"Ferramentas CLI  ·  v{__version__}", largura)
    print()
    print(f"  {Cores.ESCURECER}Selecione uma opção{Cores.RESET}")
    print()

    opcoes = [
        ("1", "Atualizar TODAS as ferramentas", "roda a lista inteira", Cores.VERDE_CLARO),
        ("2", "Selecionar ferramentas específicas", "por número ou intervalo", Cores.CIANO_CLARO),
        ("3", "Listar ferramentas cadastradas", "ver nome e comando", Cores.AMARELO_CLARO),
        ("4", "Adicionar nova atualização", "nome + comando", Cores.MAGENTA_CLARA),
        ("5", "Gerenciar ferramentas", "editar / remover", Cores.BRANCO_BRILHANTE),
        ("6", "Automação", "agendar atualização", Cores.AZUL_CLARO),
    ]
    for num, texto, hint, cor in opcoes:
        item_menu(num, texto, cor, hint, largura)

    print()
    item_menu("0", "Sair", Cores.ESCURECER, None, largura)
    print()
    separador(largura)
    return prompt("Opção: ", Cores.AMARELO_CLARO)


# =============================================
#  LISTAR
# =============================================
def listar_ferramentas_interface(gerenciador):
    """Interface para listar todas as ferramentas."""
    limpar_tela()
    largura = largura_util()
    cabecalho("FERRAMENTAS CADASTRADAS", largura)
    print()

    _render_lista(gerenciador, largura)

    ferramentas = gerenciador.listar_ferramentas()
    tem_personalizada = any(gerenciador.eh_personalizada(i) for i in range(1, len(ferramentas) + 1))

    print()
    if tem_personalizada:
        print(f"  {Cores.MAGENTA_CLARA}★{Cores.RESET} "
              f"{Cores.ESCURECER}personalizada (adicionada ou editada){Cores.RESET}")
    rotulo(f"Total: {len(ferramentas)} ferramentas")

    pausar()


# =============================================
#  EXECUÇÃO
# =============================================
def executar_atualizacao(gerenciador, indices=None):
    """Executa atualização das ferramentas (todas ou selecionadas).

    Retorna (sucesso, falha). No modo interativo desenha a tela e pausa no fim;
    no modo automático (CLI) escreve linhas simples e não pausa, para que a
    saída sirva de log para um agendador de tarefas.
    """
    limpar_tela()
    largura = largura_util()
    ferramentas = gerenciador.listar_ferramentas()

    if indices is None:
        indices = list(range(1, len(ferramentas) + 1))

    total = len(indices)
    sucesso = 0
    falha = 0

    titulo = "ATUALIZANDO TODAS AS FERRAMENTAS" if total == len(ferramentas) else "ATUALIZANDO FERRAMENTAS SELECIONADAS"
    if interativo():
        cabecalho(titulo, largura)
        print()
    else:
        print(f"{titulo} ({total})")
        print("-" * 40)
    sys.stdout.flush()

    for i, idx in enumerate(indices, 1):
        ferramenta = gerenciador.obter_ferramenta(idx)
        if ferramenta is None:
            continue

        nome, cmd = ferramenta

        if interativo():
            porcentagem = int(i * 100 / total) if total else 0
            print(f"  {Cores.NEGRITO}[{i}/{total}]{Cores.RESET}  {porcentagem:>3}%  "
                  f"{barra_progresso(porcentagem, 22)}")
            print(f"    {Cores.CIANO_CLARO}▶ {truncar(nome, largura - 6)}{Cores.RESET}")
            print(f"      {Cores.ESCURECER}$ {truncar(cmd, largura - 8)}{Cores.RESET}")
            separador(largura)
        else:
            print(f"[{i}/{total}] {nome}: $ {cmd}")
        sys.stdout.flush()

        # Executa o comando de forma bloqueante: só retorna após a
        # ferramenta finalizar, então a próxima nunca se mistura com esta.
        sucesso_cmd = executar_comando(cmd)

        if interativo():
            separador(largura)

        if sucesso_cmd:
            if interativo():
                mensagem("sucesso", f"{nome}: atualizado com sucesso!")
            else:
                print(f"    OK    {nome}")
            sucesso += 1
        else:
            if interativo():
                mensagem("erro", f"{nome}: falha na atualização")
            else:
                print(f"    FALHA {nome}")
            falha += 1

        print()
        sys.stdout.flush()
        if interativo():
            time.sleep(0.3)  # Pausa para visualização antes da próxima ferramenta

    if interativo():
        separador(largura)
        print()
        rotulo("RESUMO DA EXECUÇÃO")
    else:
        print("-" * 40)
        print("RESUMO DA EXECUÇÃO")
    print()
    print(f"  {Cores.SUCESSO}Sucesso: {sucesso}{Cores.RESET}    "
          f"{Cores.ERRO}Falhas: {falha}{Cores.RESET}    "
          f"{Cores.NEGRITO}Total: {total}{Cores.RESET}")
    print()

    pausar()
    return sucesso, falha


def _item_selecao(gerenciador, numero, nome, largura):
    """Item numerado colorido para a tela de seleção."""
    cor = Cores.MAGENTA_CLARA if gerenciador.eh_personalizada(numero) else Cores.CIANO_CLARO
    return f"{cor}{truncar(f'{numero:>2}. {nome}', largura - 1)}{Cores.RESET}"


def selecionar_ferramentas(gerenciador):
    """Interface para selecionar ferramentas específicas."""
    limpar_tela()
    largura = largura_util()
    cabecalho("SELECIONAR FERRAMENTAS", largura)
    print()

    ferramentas = gerenciador.listar_ferramentas()
    rotulo("Ferramentas disponíveis:")
    print()

    if largura < 58:
        for i, (nome, _) in enumerate(ferramentas, 1):
            print(f"  {_item_selecao(gerenciador, i, nome, largura - 2)}")
    else:
        # Duas colunas para aproveitar a largura em terminais largos.
        metade = (len(ferramentas) + 1) // 2
        largura_col = (largura - 2) // 2
        for i in range(metade):
            esquerda = _item_selecao(gerenciador, i + 1, ferramentas[i][0], largura_col)
            j = i + metade
            direita = (_item_selecao(gerenciador, j + 1, ferramentas[j][0], largura_col)
                       if j < len(ferramentas) else "")
            print(f"  {preencher(esquerda, largura_col)}{preencher(direita, largura_col)}")

    print()
    separador(largura)
    print()
    rotulo("Como selecionar:")
    print()
    dica("• Números separados por vírgula:  1,3,5")
    dica("• Intervalo com hífen:            1-5")
    dica("• Misto (vírgula + hífen):        1,3-6,8")
    print()

    selecao = prompt("Sua seleção: ", Cores.AMARELO_CLARO)

    if not selecao:
        mensagem("alerta", "Nenhuma ferramenta selecionada!")
        _pausa_curta()
        return

    indices = parsear_selecao(selecao, len(ferramentas))
    if not indices:
        mensagem("erro", "Nenhuma ferramenta válida selecionada!")
        _pausa_curta()
        return

    executar_atualizacao(gerenciador, indices)


def parsear_selecao(selecao, maximo):
    """Analisa a entrada do usuário e retorna lista de índices válidos."""
    indices = set()
    for parte in selecao.replace(" ", ",").split(","):
        parte = parte.strip()
        if not parte:
            continue
        if "-" in parte:
            try:
                inicio, fim = (int(x.strip()) for x in parte.split("-", 1))
                for i in range(inicio, fim + 1):
                    if 1 <= i <= maximo:
                        indices.add(i)
            except ValueError:
                continue
        else:
            try:
                num = int(parte)
                if 1 <= num <= maximo:
                    indices.add(num)
            except ValueError:
                continue
    return sorted(indices)


# =============================================
#  ADICIONAR
# =============================================
def adicionar_ferramenta_interface(gerenciador):
    """Interface para adicionar uma nova ferramenta."""
    limpar_tela()
    largura = largura_util()
    cabecalho("ADICIONAR NOVA ATUALIZAÇÃO", largura)
    print()

    rotulo("Informe os dados da nova ferramenta:")
    print()

    nome = prompt("Nome da ferramenta: ", Cores.BRANCO_BRILHANTE)
    if not nome:
        mensagem("alerta", "Operação cancelada!")
        _pausa_curta()
        return

    cmd = prompt("Comando de atualização: ", Cores.BRANCO_BRILHANTE)
    if not cmd:
        mensagem("alerta", "Operação cancelada!")
        _pausa_curta()
        return

    print()
    caixa_campos("CONFIRMAR ADICIONAMENTO", [
        ("Nome", nome, Cores.CIANO_CLARO),
        ("Comando", cmd, Cores.ESCURECER),
    ], largura)
    print()

    confirmar = prompt("Confirmar? (S/N): ", Cores.AMARELO_CLARO)
    if confirmar.upper() != "S":
        mensagem("alerta", "Operação cancelada!")
        _pausa_curta()
        return

    sucesso, msg = gerenciador.adicionar_ferramenta(nome, cmd)

    print()
    if sucesso:
        mensagem("sucesso", f'Ferramenta "{nome}" adicionada.')
        dica("Disponível em [2] Selecionar e [3] Listar.")
    else:
        mensagem("erro", msg)

    pausar()


# =============================================
#  GERENCIAR
# =============================================
def gerenciar_ferramentas_interface(gerenciador):
    """Interface para gerenciar as ferramentas: editar, remover ou restaurar."""
    limpar_tela()
    largura = largura_util()
    cabecalho("GERENCIAR FERRAMENTAS", largura)
    print()

    ferramentas = gerenciador.listar_ferramentas()

    if not ferramentas:
        mensagem("alerta", "A lista está vazia.")
        dica("Use [4] para adicionar ou R para restaurar os padrões.")
        print()
        acao = prompt("Digite 4, R ou Enter para voltar: ", Cores.BRANCO_BRILHANTE)
        if acao == "4":
            adicionar_ferramenta_interface(gerenciador)
            return
        if acao.upper() == "R":
            gerenciador.restaurar_padroes()
            print()
            mensagem("sucesso", "Ferramentas padrão restauradas!")
            pausar()
        return

    _render_lista(gerenciador, largura)

    print()
    separador(largura)
    print()
    rotulo("Digite o número da ferramenta para editar ou remover.")
    print(f"  {Cores.NEGRITO}Digite {tecla('R')} para restaurar as ferramentas padrão.{Cores.RESET}")
    dica("Enter volta ao menu sem alterar nada.")
    print()

    acao = prompt("Ação: ", Cores.BRANCO_BRILHANTE)

    if not acao:
        return

    if acao.upper() in ("R", "RESTAURAR"):
        print()
        rotulo("Isso descarta suas personalizações e volta à lista padrão.")
        confirmar = prompt("Confirmar? (S/N): ", Cores.ALERTA)
        print()
        if confirmar.upper() == "S":
            gerenciador.restaurar_padroes()
            mensagem("sucesso", "Ferramentas padrão restauradas!")
        else:
            mensagem("alerta", "Operação cancelada.")
        pausar()
        return

    if not acao.isdigit() or not (1 <= int(acao) <= len(ferramentas)):
        print()
        mensagem("erro", f"Número inválido! Escolha de 1 a {len(ferramentas)}.")
        pausar()
        return

    indice = int(acao)
    nome, cmd = ferramentas[indice - 1]

    print()
    caixa_campos("EDITAR / REMOVER", [
        ("Ferramenta", nome, Cores.MAGENTA_CLARA),
        ("Comando", cmd, Cores.ESCURECER),
    ], largura)
    print()
    print(f"  {tecla('E')} Editar    {tecla('R')} Remover    "
          f"{Cores.ESCURECER}Enter cancela{Cores.RESET}")
    print()

    sub = prompt("Ação: ", Cores.BRANCO_BRILHANTE).upper()
    print()

    if sub == "E":
        novo_nome = prompt(f"Novo nome [{truncar(nome, max(4, largura - 20))}]: ", Cores.BRANCO_BRILHANTE)
        novo_cmd = prompt(f"Novo comando [{truncar(cmd, max(4, largura - 24))}]: ", Cores.BRANCO_BRILHANTE)
        ok, msg = gerenciador.editar_ferramenta(indice, novo_nome, novo_cmd)
        mensagem("sucesso", f"{msg}.") if ok else mensagem("erro", msg)
    elif sub == "R":
        confirmar = prompt(f'Remover "{truncar(nome, max(4, largura - 16))}"? (S/N): ', Cores.ERRO)
        if confirmar.upper() == "S":
            ok, resultado = gerenciador.remover_ferramenta(indice)
            mensagem("sucesso", f'"{resultado}" removida.') if ok else mensagem("erro", resultado)
        else:
            mensagem("alerta", "Operação cancelada.")
    else:
        mensagem("alerta", "Operação ignorada.")

    pausar()


# =============================================
#  AUTOMAÇÃO
# =============================================
def _mostrar_saida(saida, largura, limite=14):
    """Mostra linhas de saída de comando, truncadas à largura."""
    for linha in saida.splitlines()[:limite]:
        print(f"    {Cores.ESCURECER}{truncar(linha.rstrip(), largura - 4)}{Cores.RESET}")


def _criar_tarefa(largura):
    """Fluxo de criação da tarefa agendada."""
    print()
    rotulo("Frequência:")
    item_menu("1", "Diária", Cores.VERDE_CLARO, "todo dia no horário", largura)
    item_menu("2", "Semanal", Cores.VERDE_CLARO, "toda segunda-feira", largura)
    item_menu("3", "Ao entrar", Cores.VERDE_CLARO, "no logon", largura)
    print()

    escolha = prompt("Frequência: ", Cores.BRANCO_BRILHANTE)
    mapa = {"1": "diaria", "2": "semanal", "3": "logon"}
    if escolha not in mapa:
        mensagem("alerta", "Operação cancelada.")
        return

    frequencia = mapa[escolha]
    hora = "09:00"
    if frequencia in ("diaria", "semanal"):
        informada = prompt(f"Horário [{hora}]: ", Cores.BRANCO_BRILHANTE)
        if informada:
            hora = informada

    quando = agendador.FREQUENCIAS[frequencia] + ("" if frequencia == "logon" else f" às {hora}")

    print()
    caixa_campos("CRIAR TAREFA AGENDADA", [
        ("Nome", agendador.NOME_TAREFA, Cores.CIANO_CLARO),
        ("Quando", quando, Cores.VERDE_CLARO),
        ("Comando", agendador.comando_automatico(), Cores.ESCURECER),
    ], largura)
    print()

    if prompt("Confirmar? (S/N): ", Cores.ALERTA).upper() != "S":
        mensagem("alerta", "Operação cancelada.")
        return

    ok, saida = agendador.criar(frequencia, hora)
    print()
    if ok:
        mensagem("sucesso", f'Tarefa "{agendador.NOME_TAREFA}" criada ({quando}).')
    else:
        mensagem("erro", "Não foi possível criar a tarefa.")
        if saida:
            _mostrar_saida(saida, largura)


def _remover_tarefa(largura):
    """Fluxo de remoção da tarefa agendada."""
    print()
    if prompt(f'Remover a tarefa "{agendador.NOME_TAREFA}"? (S/N): ', Cores.ERRO).upper() != "S":
        mensagem("alerta", "Operação cancelada.")
        return

    ok, saida = agendador.remover()
    print()
    if ok:
        mensagem("sucesso", "Tarefa agendada removida.")
    else:
        mensagem("alerta", "Não foi possível remover (talvez não exista).")
        if saida:
            _mostrar_saida(saida, largura, limite=6)


def _ver_tarefa(largura):
    """Mostra o status da tarefa agendada."""
    ok, saida = agendador.consultar()
    print()
    if ok:
        rotulo("Tarefa agendada:")
        _mostrar_saida(saida, largura, limite=12)
    else:
        mensagem("info", "Nenhuma tarefa agendada com esse nome.")


def automacao_interface(gerenciador):
    """Tela de automação: comando pronto e agendamento da atualização."""
    limpar_tela()
    largura = largura_util()
    cabecalho("AUTOMAÇÃO", largura)
    print()

    print(f"  {Cores.ESCURECER}A automação roda sem abrir este menu — pelo comando abaixo.{Cores.RESET}")
    print()
    rotulo("Comando (rode no Prompt/PowerShell, ou agende):")
    print(f"    {Cores.CIANO_CLARO}{truncar(agendador.comando_automatico(), largura - 4)}{Cores.RESET}")
    print()

    if not agendador.suportado():
        mensagem("info", "Agendamento automático disponível apenas no Windows.")
        dica("Use o comando acima no agendador do sistema (cron, systemd, etc.).")
        pausar()
        return

    item_menu("1", "Criar tarefa agendada", Cores.VERDE_CLARO, "diária/semanal/logon", largura)
    item_menu("2", "Remover tarefa agendada", Cores.VERMELHO_CLARO, None, largura)
    item_menu("3", "Ver tarefa agendada", Cores.CIANO_CLARO, None, largura)
    print()
    separador(largura)

    opcao = prompt("Opção (Enter volta): ", Cores.AMARELO_CLARO)

    if opcao == "1":
        _criar_tarefa(largura)
    elif opcao == "2":
        _remover_tarefa(largura)
    elif opcao == "3":
        _ver_tarefa(largura)
    else:
        return

    pausar()


# =============================================
#  SAÍDA
# =============================================
def exibir_saida():
    """Exibe tela de saída."""
    limpar_tela()
    largura = largura_util()
    titulo_app("Até a próxima!", "AGENTS CLI", largura)
    print()
    _pausa_curta()
