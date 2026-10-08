# Corte para produção — ContaView

Este procedimento aplica o Django ao PostgreSQL existente sem remover o Reflex antes do aceite do ciclo real.

## Pré-requisitos

1. O commit a implantar passou pela ação `Validar e implantar ContaView`.
2. O Railway possui um serviço web com Dockerfile, domínio público e as variáveis abaixo, mantidas somente no painel:
   - `DATABASE_URL`: pool de sessão IPv4 do Supabase com SSL; a conexão direta é usada apenas pelo backup e por operações nativas de banco.
   - `DJANGO_SECRET_KEY`: segredo aleatório exclusivo da produção.
   - `DJANGO_ALLOWED_HOSTS`: domínio público atribuído ao serviço.
   - Em Railway, a aplica??o tamb?m permite `healthcheck.railway.app` internamente para a sonda de deploy.
   - `DJANGO_CSRF_TRUSTED_ORIGINS`: `https://` seguido do domínio público.
   - `DJANGO_SETTINGS_MODULE=configuracao.settings.producao`.
   - `DJANGO_SECURE_SSL_REDIRECT=true`.
   - `OPENAI_API_KEY`, somente se o Assistente for habilitado.
3. O serviço usa o Dockerfile do repositório, health check `/saude/aplicacao/`, porta `8000` e pré-deploy `python web/manage.py migrate --noinput`. A rota `/saude/` permanece como verificação pública de aplicação e banco.
4. Antes de habilitar deploy automatizado, cadastrar no GitHub o segredo `RAILWAY_TOKEN` e a variável `RAILWAY_DEPLOY_ENABLED=true`; validar o workflow em um push controlado.

## Backup antes da migração

1. Use a conexão direta do Supabase, nunca a porta de pool transacional, somente para o backup.
2. Configure `PG_DUMP` se o executável não estiver no `PATH`.
3. Execute `python scripts/backup_pre_corte.py --executar`.
4. Guarde o arquivo `.dump` e o manifesto SHA-256 fora do repositório.
5. Confirme a presença e o tamanho do dump antes de liberar a migração.

## Implantação e smoke tests

1. Configure no Railway o builder Dockerfile, o pré-deploy e as variáveis sem revelar valores no terminal.
2. Faça o primeiro deploy manual e aguarde o estado `SUCCESS`.
3. Confirme `GET /saude/` com `banco: disponivel`.
4. Acesse `/acesso/`, crie o primeiro usuário pelo comando seguro e selecione uma empresa e competência.
5. Execute o ciclo CAP em ambiente de aceitação: entrada, conferência, aprovação, conciliação, auditoria, relatório e exportação.
6. Somente depois do aceite da contadora, mantenha o Django como aplicação principal e desative o Reflex.

## Rollback

1. Remova o deploy mais recente do serviço web ou redeploye a versão anterior no Railway.
2. Mantenha o Reflex disponível até o ciclo real ser aceito.
3. Não restaure o banco em produção para desfazer uma falha de aplicação. Restauração exige analisar a migração, selecionar o dump correto e executar um procedimento específico de recuperação.
4. Registre o commit, horário, identificador do deploy e motivo do rollback em `faltando.md`.
