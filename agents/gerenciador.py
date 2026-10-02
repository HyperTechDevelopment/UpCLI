"""Modelo e persistência da lista de ferramentas.

O arquivo AGENTS_CUSTOM.cfg é a fonte única da lista: nasce com as ferramentas
padrão e, a partir daí, é ele que manda — por isso qualquer comando, predefinido
ou adicionado, pode ser editado ou removido.
"""

from pathlib import Path

from .tema import Cores

# O config fica na raiz do projeto (um nível acima do pacote).
BASE_DIR = Path(__file__).resolve().parent.parent
CUSTOM_CONFIG = BASE_DIR / "AGENTS_CUSTOM.cfg"

# A presença deste cabeçalho marca o formato atual (lista completa). A ausência
# indica um arquivo antigo, que guardava só as customizadas e precisa migrar.
CONFIG_HEADER = "# AGENTS — lista de ferramentas (Nome|Comando). Edite livremente."


class GerenciadorFerramentas:
    """Gerencia a lista de ferramentas e suas atualizações."""

    # Ferramentas predefinidas. Servem para popular o arquivo na primeira
    # execução e para "restaurar padrões"; o arquivo tem precedência.
    FERRAMENTAS_PADRAO = [
        ("Claude", "claude upgrade"),
        ("Mimo", "mimo upgrade"),
        ("Cline", "cline update"),
        ("OpenCode", "opencode upgrade"),
        ("Hermes", "hermes update --force -y"),
        ("Oh My Pi", "omp update"),
        ("CMDC", "cmdc update"),
        ("Grok", "grok update"),
        ("Skills", "npx skills update -y"),
        ("Open Code Review", "npm install -g @alibaba-group/open-code-review"),
        ("DeepSeek Harness", "npm install -g @deepseek-ai/dsh"),
        ("npm", "npm install -g npm@latest"),
        ("Pacotes globais npm", "npm update -g"),
        ("Pacotes via Winget", "winget upgrade --all --accept-package-agreements --accept-source-agreements"),
    ]

    def __init__(self):
        self.ferramentas = []
        self._carregar()

    def _carregar(self):
        """Carrega a lista do arquivo de configuração.

        Dois formatos são aceitos:
          - atual: cabeçalho CONFIG_HEADER e uma linha "Nome|Comando" por item;
          - antigo: apenas as customizadas, sem cabeçalho. Nesse caso mesclamos
            com os padrões, senão as ferramentas predefinidas desapareceriam.
        """
        if not CUSTOM_CONFIG.exists():
            self.ferramentas = list(self.FERRAMENTAS_PADRAO)
            self.salvar()
            return

        try:
            with open(CUSTOM_CONFIG, "r", encoding="utf-8") as f:
                linhas = f.readlines()
        except Exception as e:
            print(f"{Cores.ALERTA}   Aviso: erro ao ler config: {e}{Cores.RESET}")
            self.ferramentas = list(self.FERRAMENTAS_PADRAO)
            return

        tem_cabecalho = any(ln.lstrip().startswith("#") for ln in linhas)

        itens = []
        for ln in linhas:
            ln = ln.strip()
            if not ln or ln.startswith("#") or "|" not in ln:
                continue
            nome, cmd = ln.split("|", 1)
            nome, cmd = nome.strip(), cmd.strip()
            if nome and cmd:
                itens.append((nome, cmd))

        if itens and not tem_cabecalho:
            # Formato antigo (só customizadas): mescla com os padrões e migra.
            self.ferramentas = list(self.FERRAMENTAS_PADRAO)
            nomes = {n.lower() for n, _ in self.ferramentas}
            for nome, cmd in itens:
                if nome.lower() not in nomes:
                    self.ferramentas.append((nome, cmd))
                    nomes.add(nome.lower())
            self.salvar()
            return

        self.ferramentas = itens if itens else list(self.FERRAMENTAS_PADRAO)
        if not itens:
            self.salvar()

    def salvar(self):
        """Salva a lista completa no arquivo de configuração."""
        try:
            with open(CUSTOM_CONFIG, "w", encoding="utf-8") as f:
                f.write(CONFIG_HEADER + "\n")
                for nome, cmd in self.ferramentas:
                    f.write(f"{nome}|{cmd}\n")
        except Exception as e:
            print(f"{Cores.ERRO}   Erro ao salvar config: {e}{Cores.RESET}")

    def listar_ferramentas(self):
        """Retorna a lista de ferramentas."""
        return self.ferramentas

    def obter_ferramenta(self, indice):
        """Obtém uma ferramenta pelo índice (1-based)."""
        if 1 <= indice <= len(self.ferramentas):
            return self.ferramentas[indice - 1]
        return None

    def eh_personalizada(self, indice):
        """True se a ferramenta difere das predefinidas (nova ou editada)."""
        item = self.obter_ferramenta(indice)
        return item is not None and item not in self.FERRAMENTAS_PADRAO

    def adicionar_ferramenta(self, nome, cmd):
        """Adiciona uma nova ferramenta."""
        for n, _ in self.ferramentas:
            if n.lower() == nome.lower():
                return False, "Já existe uma ferramenta com este nome"

        self.ferramentas.append((nome, cmd))
        self.salvar()
        return True, "Ferramenta adicionada com sucesso"

    def editar_ferramenta(self, indice, nome=None, cmd=None):
        """Edita nome e/ou comando; campo vazio mantém o valor atual."""
        atual = self.obter_ferramenta(indice)
        if atual is None:
            return False, "Índice inválido"

        nome_atual, cmd_atual = atual
        novo_nome = (nome or "").strip() or nome_atual
        novo_cmd = (cmd or "").strip() or cmd_atual

        for j, (n, _) in enumerate(self.ferramentas, 1):
            if j != indice and n.lower() == novo_nome.lower():
                return False, "Já existe uma ferramenta com este nome"

        self.ferramentas[indice - 1] = (novo_nome, novo_cmd)
        self.salvar()
        return True, "Ferramenta atualizada com sucesso"

    def remover_ferramenta(self, indice):
        """Remove UMA ferramenta pelo índice (1-based)."""
        if 1 <= indice <= len(self.ferramentas):
            item = self.ferramentas.pop(indice - 1)
            self.salvar()
            return True, item[0]
        return False, "Índice inválido"

    def restaurar_padroes(self):
        """Restaura a lista às ferramentas predefinidas."""
        self.ferramentas = list(self.FERRAMENTAS_PADRAO)
        self.salvar()
        return True
