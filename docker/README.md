# Produção com Docker

Na raiz do projeto:

```bash
docker compose build
docker compose up -d
```

A aplicação ficará disponível em `http://localhost:8000`. O container `web`
serve o bundle React pelo Nginx e encaminha `/api` e `/health` para o
container `api`.

Para acompanhar os logs:

```bash
docker compose logs -f
```

Para parar:

```bash
docker compose down
```

Se a porta 8000 já estiver ocupada, use outra porta externa:

```bash
WEB_PORT=8080 docker compose up -d --build
```

As variáveis de IA podem ser colocadas no `.env` da raiz. Segredos não devem
ser gravados no `docker-compose.yml` nem enviados ao repositório.
