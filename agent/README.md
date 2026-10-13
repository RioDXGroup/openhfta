# OpenHFTA Agent TUI

Agente de terminal em TypeScript usando `@openrouter/agent`. Ele interpreta
resultados do OpenHFTA e pode executar a análise determinística pela API local.

## Executar

Na raiz do projeto, com `OPENROUTER_API_KEY` configurada no `.env`:

```bash
cd agent
set -a; source ../.env; set +a
npm start
```

Comandos disponíveis: `/help`, `/model`, `/new`, `/session`, `/sessions`,
`/export` e `/quit`.

O agente não possui ferramentas de escrita de arquivos nem shell. A ferramenta
`openhfta_analyze` somente envia o perfil escolhido para a API local e retorna
as métricas calculadas pelo núcleo original.
