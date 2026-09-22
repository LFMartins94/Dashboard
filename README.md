# ContaView

Ferramenta de preparação e conferência de dados contábeis para uma contadora que trabalha com várias empresas. O ContaView recebe planilhas de origens diferentes, preserva o arquivo original, permite corrigir os dados, cruza fontes e exporta um conjunto limpo em CSV ou XLSX. A exportação é genérica, sem vínculo com Domínio, Alterdata ou outro sistema oficial.

O projeto usa Reflex no navegador, PostgreSQL do Supabase para persistência e OpenAI GPT-4o-mini para sugerir o mapeamento de colunas e responder no Assistente. Cálculos, validação, conciliação e exportação são determinísticos. A contadora confirma empresa, tipo do documento, aba, cabeçalho e colunas antes da gravação.

## Fluxo de trabalho

1. **Importar:** selecionar a empresa e enviar XLSX, CSV ou XLS. A prévia mostra as abas, os títulos e as primeiras linhas. É possível trocar a linha de cabeçalho; o valor `0` significa que não há cabeçalho.
2. **Dados preparados:** conferir linhas, corrigir datas, valores e classificações e resolver pendências. O arquivo original, a linha e os valores brutos ficam vinculados ao lote.
3. **Conciliação:** escolher dois lotes da mesma empresa. Pares únicos com data, valor e descrição iguais são identificados automaticamente. Candidatos ambíguos, diferenças de valor e itens sem correspondência exigem revisão humana.
4. **Exportar:** baixar CSV ou XLSX depois que todas as linhas do lote estiverem validadas. Colunas internas não são exportadas.
5. **Painel e Assistente:** acompanhar totais e pendências e consultar resumos. O Assistente não recebe linhas brutas, CPF ou CNPJ das ferramentas de consulta.

Os lançamentos contábeis e as páginas antigas de auditoria e relatórios continuam disponíveis como legado. A navegação principal prioriza a preparação de arquivos e a conciliação entre fontes. O ContaView não emite ECD/ECF e não substitui o sistema contábil oficial.

## Leitura de arquivos

- XLSX: todas as abas, inclusive células com campos separados por ponto e vírgula.
- XLS: Excel binário via `xlrd` e XML SpreadsheetML legado.
- CSV: separadores `;`, `,`, tabulação ou `|`; codificações UTF-8 e Windows usuais.
- Limites atuais: 20 MB por arquivo e 30.000 linhas por aba. Arquivos protegidos por senha e formatos fora desses três tipos precisam ser convertidos antes do envio.

O mapeamento sugerido usa regras locais. Quando data ou valor não são reconhecidos e `OPENAI_API_KEY` está configurada, uma chamada estruturada à OpenAI recebe apenas os nomes das colunas. O tipo do documento e o destino são sempre escolhidos pela contadora.

## Banco de dados

As tabelas existentes são preservadas. A área de preparação acrescenta `lotes_importacao`, `linhas_preparadas` e `historico_alteracoes`. Um trigger PostgreSQL registra inserções, edições e exclusões das linhas preparadas e dos lançamentos. O arquivo original é armazenado no lote. As consultas e alterações da preparação sempre usam `empresa_id`.

O Reflex acessa o banco pelo servidor com `DATABASE_URL`; o navegador não usa Supabase Auth nem a Data API. Por isso, a configuração de segurança habilita RLS nas tabelas do ContaView, inclusive na tabela legada `gastos`, e revoga o acesso direto dos papéis `anon`, `authenticated` e `service_role` às tabelas e sequências. Não há políticas de liberação para esses papéis. A conexão PostgreSQL do servidor continua responsável por autorizar as operações após o login no aplicativo. A função de auditoria usa os privilégios da própria conexão e não pode ser executada pelos papéis da Data API.

A migração é explícita e **não é executada durante o início do app**. Antes de aplicá-la em um banco com dados reais, faça backup e confira a `DATABASE_URL`:

```powershell
python -c "from contaview.logic.database import inicializar_banco; inicializar_banco()"
python -c "from contaview.logic.database import migrar_preparacao; migrar_preparacao()"
```

Os dois comandos aplicam a configuração de RLS na mesma transação das respectivas alterações. Para configurar novamente um banco já migrado, execute `python -c "from contaview.logic.database import configurar_seguranca_banco; configurar_seguranca_banco()"`. O usuário da conexão deve ter permissão para criar tabelas, índices, função e triggers, além de alterar privilégios dos objetos do ContaView. Antes de usar um papel de banco diferente para a aplicação, revise as políticas e os privilégios concedidos a ele.

## Execução local

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Preencha `.env` com `DATABASE_URL`, `APP_USUARIO`, `APP_SENHA` e, opcionalmente, `OPENAI_API_KEY`. Depois inicialize o banco conforme acima e execute:

```powershell
.venv\Scripts\reflex init
.venv\Scripts\reflex run
```

Para validar a lógica sem conexão de banco:

```powershell
.venv\Scripts\python -m unittest tests.test_importacao_dataframe -v
```

Em produção, configure as mesmas variáveis no Reflex Cloud e aplique a migração no PostgreSQL antes do deploy.

## Organização

- `contaview/logic/`: leitura, mapeamento, importação, validação, conciliação, persistência e exportação.
- `contaview/state/`: estado Reflex, filtros e eventos de interface.
- `contaview/pages/`: páginas.
- `contaview/components/`: componentes visuais.
- `docs/DESIGN_SYSTEM.md`: regras visuais do projeto.
- `AGENTS.md`: regras de arquitetura e manutenção.
