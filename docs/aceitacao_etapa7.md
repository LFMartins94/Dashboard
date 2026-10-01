# Aceitação da Etapa 7 — Assistente controlado

## Entregue

- Conversas e mensagens são gravadas no banco legado existente.
- A sessão autenticada controla quais conversas podem ser abertas ou excluídas.
- A tela `/assistente/` permite criar, retomar, enviar e excluir conversas.
- O contexto atual de empresa e competência é enviado como limite para as ferramentas.
- Consultas para outra empresa ou competência são recusadas antes da ferramenta.
- CPFs, CNPJs, nomes e registros nominais de ferramentas não são enviados ao modelo.
- O assistente nunca aprova lote, grava lançamento ou altera conciliação.
- Ausência da chave OpenAI e falhas de rede retornam mensagem operacional sem interromper a aplicação.

## Verificações

- 50 testes Django aprovados.
- 30 testes legados aprovados anteriormente.
- Testes específicos validam isolamento da sessão e persistência de mensagem de usuário e assistente.
- Nenhuma migração ou escrita foi executada no Supabase de produção.

## Limite conhecido

O vínculo das conversas é mantido na sessão porque as tabelas legadas não têm coluna de usuário. A migração de produção e o vínculo permanente ficam para a etapa de banco prevista no plano.
