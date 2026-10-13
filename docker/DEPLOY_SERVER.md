# Implantação no servidor usando somente Docker

O servidor precisa apenas de Docker Engine e do plugin Docker Compose. Ele não
precisa instalar Python, Node, npm, gfortran ou executar a aplicação fora dos
containers.

## 1. Gerar as imagens na máquina de build

Na raiz do projeto:

```bash
docker compose build api web
docker save -o openhfta-images.tar openhfta-api:latest openhfta-web:latest
```

Transfira para o servidor somente:

- `docker-compose.prod.yml`;
- `openhfta-images.tar`;
- `.env` de produção, criado no servidor e mantido fora do repositório.

## 2. Carregar e iniciar no servidor

```bash
docker load -i openhfta-images.tar
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
```

A aplicação ficará disponível em `http://SERVIDOR:8000`.

## 3. Operação

```bash
docker compose -f docker-compose.prod.yml logs -f
docker compose -f docker-compose.prod.yml restart
docker compose -f docker-compose.prod.yml down
```

Para usar outra porta externa:

```bash
WEB_PORT=8080 docker compose -f docker-compose.prod.yml up -d
```

O arquivo `.env` deve conter os segredos de produção, como a configuração da
IA. Não coloque chaves no compose, no arquivo de imagens ou no repositório.
