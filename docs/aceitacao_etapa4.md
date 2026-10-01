# Aceitação da Etapa 4 — tela Trabalho

Data da verificação: 01/10/2026.

## Entrega

A página inicial da nova aplicação deixou de ser um painel estático e passou a funcionar como fila operacional da empresa e competência selecionadas. A contadora vê o próximo trabalho, o checklist do período, as exceções abertas e as demais competências em andamento na mesma tela.

As migrações foram preparadas e testadas em banco isolado. Nenhuma tabela, linha ou permissão do PostgreSQL de produção foi alterada.

## Fluxo implementado

1. A contadora seleciona empresa e competência no contexto seguro da sessão.
2. Se o período ainda não possui rotina, a tela oferece a ação explícita `Iniciar competência`.
3. Essa ação cria, em uma transação idempotente, a competência operacional e quatro itens recorrentes: documentos, conferência, divergências e entrega.
4. A tela reúne os totais determinísticos das tabelas existentes e os estados persistidos do checklist.
5. A próxima ação prioriza lote pendente, divergência e depois o primeiro item não entregue.
6. Cada alerta abre a área e o registro responsável.
7. Alterações de estado recalculam o estado geral da competência.
8. Competências abertas de outras empresas podem substituir o contexto por `POST`, depois de nova validação no servidor.

## Dados apresentados

- Arquivos não cancelados recebidos na competência.
- Lotes em revisão e quantidade de linhas pendentes.
- Divergências da conciliação mais recente.
- Ocorrências de auditoria não resolvidas e vinculadas a lançamentos do período.
- Documentos recorrentes ainda aguardados.
- Entregas revisadas e entregues.
- Estado geral da competência gravado no banco.

## Persistência e proteção

As novas tabelas são:

- `django_competencias_trabalho`;
- `django_itens_checklist_trabalho`.

Elas possuem índices por empresa, período e estado; chave estrangeira para `empresas`; unicidade por empresa e competência; unicidade dos itens dentro da competência; e constraints para empresa, período, estado, categoria e rota permitida.

No PostgreSQL, a migração habilita RLS e revoga das roles `anon` e `authenticated` todos os privilégios sobre as tabelas e sequências. O acesso ocorre somente pela conexão privada do servidor Django.

## Critérios de aceite

| Critério | Resultado |
|---|---|
| Identificar o próximo trabalho sem navegar por vários módulos | Aprovado |
| Mostrar documentos, lotes, divergências e entregas | Aprovado |
| Cada alerta apontar para sua área e registro | Aprovado |
| Estado exibido vir do banco | Aprovado |
| Checklist ser criado uma única vez por competência | Aprovado |
| Uma empresa não atualizar item de outro contexto | Aprovado |
| Requisições `GET` não criarem nem alterarem a rotina | Aprovado |
| Falha de banco não expor detalhes internos nem oferecer gravação | Aprovado |

## Verificações executadas

| Verificação | Resultado |
|---|---|
| Testes Django do app `nucleo` | 35 aprovados |
| Testes legados com `unittest` | 30 aprovados |
| Consulta SQL representativa em SQLite | Métricas e alertas filtrados corretamente |
| Consultas agregadas no PostgreSQL real | Aprovadas em modo somente leitura |
| `manage.py check` em teste e produção | Aprovado, sem problemas |
| `makemigrations --check --dry-run` | Nenhuma mudança pendente |
| Compilação Python | Aprovada |
| Tailwind e HTMX locais | Compilados com sucesso |
| `collectstatic` com manifesto | 3 arquivos coletados e 9 pós-processados |
| `pip check` | Nenhuma dependência quebrada |
| `npm audit --omit=dev` | 0 vulnerabilidades |

## Pendência de produção

As tabelas novas ainda não existem no Supabase de produção. A aplicação das migrações continua reservada para a Etapa 13, com backup confirmado, criação do usuário inicial, smoke test e procedimento de reversão no mesmo corte.
