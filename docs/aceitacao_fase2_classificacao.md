# Aceitacao - Fase 2: classificacao contabil assistida

## Entrega

A aplicacao Django possui a rota autenticada `/classificacoes/`. Ela obtem empresa e competencia por `exigir_contexto(request)` antes de consultar ou alterar regras. Toda escrita usa formulario Django, CSRF e transacao.

A regra confirmada e isolada por empresa e pode restringir conta bancaria, descricao, favorecido, documento, tipo de operacao, D/C, faixa de valor e vigencia. Ela sugere conta contabil, historico, centro de custo e D/C para uma fonte transacional. A sugestao e somente leitura: nao atualiza `linhas_preparadas`, nao grava lancamentos e nao aprova lote.

## Regras de seguranca e qualidade

- Um criterio textual precisa ter ao menos tres caracteres.
- Uma regra baseada apenas em `PIX` e recusada.
- Prioridade, valor, vigencia, tipo e campos de destino sao validados no servidor.
- Criterios iguais em regras ativas com mesma empresa, conta bancaria e prioridade sao recusados.
- Duas regras na melhor prioridade produzem conflito; o servico nao escolhe uma delas.
- Regra em revisao ou desativada nao produz sugestao.
- Criacao, alteracao, desativacao e reativacao geram historico com responsavel e estados antes e depois.
- Editar uma regra desativada nao a reativa implicitamente.
- A origem `contabil_estruturado` nao entra em classificacao; o XLSX CAP continua em validacao e rastreabilidade.

## Banco de dados

A migracao `0011_regras_classificacao_contabil` cria `django_regras_classificacao_contabil` e `django_historicos_regras_classificacao`, com constraints, indices e operacao PostgreSQL que habilita RLS e revoga os papeis `anon` e `authenticated` nas tabelas e sequencias novas.

Ela foi exercitada apenas em SQLite isolado e analisada com `migrate --plan`. Nao foi aplicada no Supabase nem houve deploy Railway. Producao exige backup novo confirmado, testes isolados, deploy controlado e verificacao de RLS por consulta somente leitura.

## Testes executados em 14/10/2026

- `npm run build`
- `python web/manage.py test nucleo nucleo.test_classificacao --settings=configuracao.settings.teste` - 85 testes aprovados.
- `python -m unittest discover -s tests -p "test_*.py"` - 31 testes aprovados.
- `python web/manage.py check --settings=configuracao.settings.teste`
- `python web/manage.py makemigrations --check --dry-run --settings=configuracao.settings.teste`
- `python web/manage.py migrate --plan --settings=configuracao.settings.teste`
- `git diff --check`

## Proxima fase

A Fase 3 vai aplicar sugestoes as linhas transacionais somente apos revisao explicita, apresentar conflitos e pendencias, registrar amostragem e impedir aprovacao de lote com excecoes abertas.
