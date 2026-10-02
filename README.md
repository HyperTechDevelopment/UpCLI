# AGENTS — Centro de Atualizações

Menu de terminal (TUI) para **atualizar, em um lugar só, várias ferramentas de linha de comando** — Claude, Cline, OpenCode, Hermes, CMDC, pacotes npm, Winget e o que você quiser adicionar. Em vez de lembrar o comando de update de cada uma, você roda um menu e dispara tudo (ou só o que escolher), inclusive de forma automatizada.

- **Interativo:** um menu com lista, seleção, cadastro e gerenciamento de ferramentas.
- **Automatizável:** flags de linha de comando para rodar sem interação (ideal para o Agendador de Tarefas do Windows).
- **Extensível:** a lista de ferramentas vive num arquivo de texto (`AGENTS_CUSTOM.cfg`) que você edita pelo menu ou à mão.

## Para que serve

O objetivo é **reduzir o trabalho manual de manter o ambiente em dia**. De uma vez só, o AGENTS:

- atualiza os **agentes e ferramentas de CLI usados no pipeline de desenvolvimento** (Claude, Cline, OpenCode, Hermes, CMDC, Skills, etc.);
- atualiza os **programas do Windows**, via Winget.

A rotina é executá-lo **diariamente, logo no início do expediente**, para começar o dia com tudo atualizado. Para não depender de lembrar, o agendamento pode ser feito pela própria ferramenta (menu → **[6] Automação**), que registra uma tarefa diária no Agendador de Tarefas do Windows.

## Requisitos

- **Windows 10+** para o comportamento completo. A espera "de verdade" pelo fim do processo usa um *Job Object* do Windows; em outros sistemas o script funciona, mas cai no modo simples (espera só o processo direto).
- **Python 3.8+** (testado no 3.14).

## Como executar

Sempre a partir da pasta do projeto (é de lá que o pacote `agents/` é encontrado):

```bat
cd /d "C:\Users\Marcos\Downloads\PROJETOS\Automação"
python AGENTS.py
```

Sem nenhum argumento, abre o **menu interativo**.

## Menu interativo

| Opção | O que faz |
|------|-----------|
| **1** | Atualiza **todas** as ferramentas, uma por vez. |
| **2** | Seleciona ferramentas específicas por número/intervalo (ex.: `1,3-5`). |
| **3** | Lista as ferramentas cadastradas (nome e comando). |
| **4** | Adiciona uma nova ferramenta (nome + comando de update). |
| **5** | Gerencia a lista: **editar**, **remover** ou **restaurar os padrões**. |
| **6** | **Automação**: mostra o comando pronto e cria/remove/consulta a tarefa agendada (Windows). |
| **0** | Sai. |

A interface é responsiva: em terminais largos mostra a tabela com colunas; em terminais estreitos empilha nome e comando. Redimensione a janela e a próxima tela se adapta.

## Automação (linha de comando)

Roda sem menu, sem pausas, escrevendo um log simples — pensado para agendadores e pipelines.

```bat
python AGENTS.py --update-all             :: atualiza todas as ferramentas
python AGENTS.py --update Claude,CMDC     :: atualiza por nome
python AGENTS.py --update 1,3-5           :: atualiza por número/intervalo
python AGENTS.py --list                   :: lista e sai
python AGENTS.py --update-all --no-color  :: sem cores (bom para arquivo de log)
```

Seleção aceita números (`1,3`), intervalos (`1-5`), nomes (`Claude,CMDC`) e mistura. Nome pode ser parcial desde que case com um único item.

**Códigos de saída** (úteis para saber se deu certo):

| Código | Significado |
|--------|-------------|
| `0` | Tudo atualizado com sucesso. |
| `1` | Rodou, mas alguma ferramenta falhou. |
| `2` | A seleção informada não casou com nenhuma ferramenta. |
| `130` | Interrompido com Ctrl+C. |

## Agendando no Windows (Agendador de Tarefas)

Você pode criar/remover a tarefa pela própria TUI: **menu → [6] Automação**. Ela monta o comando com os caminhos absolutos e registra a tarefa para rodar diariamente, semanalmente ou no logon.

Ou faça na mão com `schtasks`. Exemplo criando uma tarefa diária às 09:00 (ajuste o caminho):

```bat
schtasks /Create /TN "AGENTS - Atualizar tudo" /SC DAILY /ST 09:00 ^
  /TR "python \"C:\Users\Marcos\Downloads\PROJETOS\Automação\AGENTS.py\" --update-all --no-color" /F
```

Na interface gráfica do Agendador, use `python` como programa, o caminho do `AGENTS.py` + `--update-all --no-color` como argumentos, e a pasta do projeto em **Iniciar em**.

## Cadastro de ferramentas — `AGENTS_CUSTOM.cfg`

Este arquivo é a **fonte única** da lista. Formato: uma linha `Nome|Comando` por ferramenta; linhas começando com `#` são ignoradas.

```
# AGENTS — lista de ferramentas (Nome|Comando). Edite livremente.
Claude|claude upgrade
OpenCode|opencode upgrade
Meu script|meu-script --self-update
```

- Na primeira execução (ou em "restaurar padrões" no menu), o arquivo é criado com as ferramentas predefinidas do script.
- Você pode editar pelo menu (opção **5**) ou diretamente no arquivo.
- Se existir um arquivo no formato antigo (só as customizadas, sem cabeçalho), o script **migra** automaticamente: junta com os padrões para não perder nada.

## Estrutura do projeto

```
AGENTS.py              # ponto de entrada (chama agents/cli.py)
AGENTS_CUSTOM.cfg      # lista de ferramentas (fonte da verdade)
agents/
  tema.py              # cores, tamanho do terminal e layout responsivo
  componentes.py       # widgets reutilizáveis (caixas, tabelas, mensagens, prompts)
  gerenciador.py       # modelo e persistência da lista de ferramentas
  execucao.py          # execução de comandos com contenção de árvore (Job Object)
  agendador.py         # agendamento da atualização automática (schtasks)
  telas.py             # telas do modo interativo
  automacao.py         # seleção/execução por linha de comando
  cli.py               # despacho (menu ou automação)
```

## Notas técnicas

- **Espera real pelo fim do update.** Algumas ferramentas (ex.: `hermes update` no Windows) retornam antes de terminar, desanexando o trabalho num processo filho. O script segura a execução até a **árvore de processos** acabar (Job Object do Windows), então nunca começa a próxima ferramenta com a anterior ainda rodando. Daemons legítimos (como o gateway do Hermes) podem escapar do job de propósito e sobreviver ao update.
- **Comandos não interativos.** O comando padrão do Winget já inclui `--accept-package-agreements --accept-source-agreements` para não travar esperando confirmação em modo automático. Se você adicionar ferramentas que pedem confirmação, inclua a flag equivalente (ex.: `-y`).
- **Saída em UTF-8.** A saída é forçada em UTF-8 com `replace`, então acentos e caracteres de caixa não quebram quando o resultado é redirecionado para um arquivo de log.

## Aviso

As ferramentas são executadas com os **seus** privilégios de usuário. Revise os comandos em `AGENTS_CUSTOM.cfg` antes de rodar `--update-all`.
