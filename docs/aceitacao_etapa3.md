# Aceitação da Etapa 3 — autenticação e contexto de trabalho

Data da verificação: 01/10/2026.

## Entrega

A nova aplicação Django passou a proteger todas as rotas operacionais por padrão. Depois do login, a contadora escolhe uma empresa ativa e uma competência no formato `AAAA-MM`; esse contexto fica associado à sessão no servidor e é exigido novamente por cada serviço operacional.

Esta etapa criou as migrações necessárias, mas não as executou no PostgreSQL de produção. A aplicação do schema e a criação do primeiro usuário pertencem ao corte controlado da Etapa 13, depois de novo backup confirmado.

## Controles implementados

- Autenticação pelo sistema nativo do Django, com senhas armazenadas por hash.
- Criação do primeiro usuário por comando que não aceita senha na linha de comando.
- Proteção global das rotas, com exceção explícita somente para login e diagnósticos.
- Logout somente por `POST`, seguido de invalidação completa da sessão.
- Sessão de oito horas, renovada durante o uso e encerrada ao fechar o navegador.
- Cookies de sessão e CSRF com `HttpOnly` e `SameSite=Lax`; em produção, ambos exigem HTTPS.
- Formulários com token CSRF e página de erro própria para requisições recusadas.
- Limite persistente de tentativas de login por combinação de endereço e usuário.
- Chave do limitador armazenada como HMAC SHA-256, sem guardar endereço ou nome de usuário brutos.
- Mensagem de credencial inválida igual para usuário existente e desconhecido.
- Destinos de redirecionamento validados para impedir encaminhamento a domínio externo.
- Empresa validada novamente no servidor com consulta parametrizada antes de salvar o contexto.
- Contextos independentes para sessões simultâneas.

## Banco e RLS

As migrações criam a tabela `django_tentativas_login` e as tabelas nativas de autenticação e sessão do Django. No PostgreSQL, a migração de proteção:

1. habilita RLS nas tabelas internas do Django;
2. revoga os privilégios diretos dos papéis `anon` e `authenticated` quando eles existirem;
3. mantém o acesso apenas pela conexão privada do servidor.

Não há política de leitura para o navegador, pois o navegador não consulta essas tabelas diretamente. A migração é neutra no SQLite usado nos testes.

## Verificações automatizadas

Os testes da aplicação usam SQLite em memória e não acessam o banco de produção. Eles cobrem:

- redirecionamento de visitante para login;
- presença e validação do token CSRF;
- login válido e inválido;
- resposta genérica para usuário existente e desconhecido;
- bloqueio depois do limite configurado;
- armazenamento somente da chave protegida do limitador;
- rejeição de redirecionamento externo;
- logout, limpeza da sessão e rejeição de logout por `GET`;
- atributos do cookie de sessão;
- seleção, validação e persistência do contexto;
- isolamento entre dois clientes simultâneos;
- comando de criação do usuário inicial;
- páginas de erro, diagnósticos e logs estruturados.

| Verificação final | Resultado |
|---|---|
| Testes Django do app `nucleo` | 24 aprovados |
| Testes legados com `unittest` | 30 aprovados |
| `manage.py check` em teste e produção | Aprovado, sem problemas |
| `makemigrations --check --dry-run` | Nenhuma mudança pendente |
| Compilação Python | Aprovada |
| `pip check` | Nenhuma dependência quebrada |
| Tailwind e HTMX locais | Compilados com sucesso |
| `collectstatic` com manifesto | 3 arquivos coletados e 9 pós-processados |
| `npm audit --omit=dev` | 0 vulnerabilidades |
| `git diff --check` | Aprovado |
| Consulta somente leitura das empresas ativas no Supabase | Aprovada |

## Critérios de aceite

| Critério | Resultado |
|---|---|
| Acesso sem login redireciona para `/acesso/` | Aprovado |
| Sessões mantêm contextos independentes | Aprovado |
| Logout invalida sessão e contexto | Aprovado |
| Erro não revela se o usuário existe | Aprovado |
| Empresa e competência são validadas no servidor | Aprovado |
| Banco de produção permanece sem alteração | Aprovado |

## Pendência deliberada para produção

O login da nova aplicação só poderá ser usado no endereço público depois que as migrações forem executadas e o usuário inicial for criado. Essa ação foi reservada para a Etapa 13 para que o corte tenha backup, verificação do alvo, smoke test e procedimento de reversão no mesmo ciclo.
