# Aceitação da Etapa 2 — esqueleto Django

Data da verificação: 30/09/2026.

## Entrega

A nova aplicação web foi criada em `web/` sem remover ou alterar o legado Reflex. A aplicação usa Django 5.2 LTS, templates renderizados no servidor, Tailwind CSS compilado, HTMX local e PostgreSQL configurado por `DATABASE_URL`.

Esta etapa não executou migrações, DDL ou escrita no PostgreSQL de produção. A única consulta feita ao banco durante o teste HTTP foi `SELECT 1` pelo diagnóstico `/saude/`.

## Estrutura criada

- Configurações separadas em `desenvolvimento.py`, `producao.py`, `teste.py` e `compilacao.py`.
- Segredo de sessão obrigatório em produção, sem valor real no repositório.
- Conexão PostgreSQL com SSL, verificação de conexão e persistência configurável.
- Interface responsiva com sidebar de 252 px, cabeçalho, mensagens, dark mode e páginas de módulo.
- CSS compilado pelo Tailwind 4.3.0 e HTMX 2.0.11 servido pelo próprio projeto.
- Páginas de erro em português com identificador de referência.
- Diagnósticos separados para processo web e banco.
- Logs JSON com identificador, método, caminho, status e duração da requisição.
- Dockerfile em duas fases: compilação da interface e execução por Gunicorn.

## Verificações executadas

| Verificação | Resultado |
|---|---|
| `python web/manage.py check` com configurações de teste | Aprovada, sem problemas |
| `python web/manage.py check` com configurações de produção | Aprovada, sem problemas |
| `python web/manage.py makemigrations --check --dry-run` | Nenhuma mudança detectada |
| Testes Django do app `nucleo` | 10 testes aprovados |
| Testes legados com `unittest` | 30 testes aprovados |
| Compilação Tailwind e cópia local do HTMX | Aprovadas |
| `collectstatic` com manifesto WhiteNoise | 3 arquivos coletados e 9 pós-processados |
| Auditoria npm | 0 vulnerabilidades |
| Verificação de espaços e conflitos com `git diff --check` | Aprovada |

## Teste HTTP real

O servidor de desenvolvimento foi iniciado em `127.0.0.1:8010` e consultado por HTTP:

| Rota | HTTP | Resultado |
|---|---:|---|
| `/` | 200 | Tela inicial renderizada |
| `/entradas/` | 200 | Acesso direto ao módulo |
| `/saude/aplicacao/` | 200 | Processo disponível |
| `/saude/` | 200 | Aplicação e PostgreSQL disponíveis |
| `/rota-inexistente/` | 404 | Página de erro do ContaView |
| `/static/css/contaview.css` | 200 | CSS compilado servido |
| `/static/vendor/htmx.min.js` | 200 | HTMX local servido |
| `/static/js/contaview.js` | 200 | JavaScript local servido |

Os testes automatizados também simularam o banco indisponível. Nesse caso, `/saude/` retornou HTTP 503 com `aplicacao: disponivel` e `banco: indisponivel`, sem expor a exceção ao cliente.

## Segurança verificada

- Nenhuma chave real foi adicionada aos arquivos versionados.
- O HTML não contém `DJANGO_SECRET_KEY`, `DATABASE_URL` ou chave da OpenAI.
- Produção exige `DJANGO_SECRET_KEY`, `DATABASE_URL` e `DJANGO_ALLOWED_HOSTS`.
- Os cabeçalhos de segurança, CSRF, cookies seguros e proteção contra frames estão configurados.
- O navegador recebe apenas um identificador de requisição; erros internos ficam no log.

## Limitação do ambiente

O Docker não está instalado neste computador, portanto a imagem não pôde ser construída localmente. A coleta de estáticos usada pela imagem foi executada com sucesso e o Dockerfile foi mantido como artefato da etapa. A construção completa da imagem deverá ser repetida em um ambiente com Docker ou no serviço de integração antes do primeiro deploy.

O aviso `security.W021` do `check --deploy` permanece intencional: o preload de HSTS só deve ser habilitado depois que o domínio final e o HTTPS estiverem confirmados.
