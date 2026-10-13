#!/usr/bin/env bash
#
# Publica manualmente uma nova versão das imagens Docker do OpenHFTA no
# servidor de produção, seguindo o fluxo descrito em docker/DEPLOY_SERVER.md.
#
# Uso:
#   docs/deployProducao.sh [api|web|all]
#
# Variáveis de ambiente opcionais:
#   DEPLOY_HOST   usuário@host do servidor (padrão: root@217.216.67.119)
#   DEPLOY_DIR    diretório remoto do projeto (padrão: /opt/openhfta)
#   HEALTH_PORT   porta local do container web no servidor (padrão: 8001)
#
# Exemplos:
#   docs/deployProducao.sh            # builda e publica api + web
#   docs/deployProducao.sh web        # publica só o frontend
#   DEPLOY_HOST=root@1.2.3.4 docs/deployProducao.sh api

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

SERVICES="${1:-all}"
DEPLOY_HOST="${DEPLOY_HOST:-root@217.216.67.119}"
DEPLOY_DIR="${DEPLOY_DIR:-/opt/openhfta}"
HEALTH_PORT="${HEALTH_PORT:-8001}"
TAR_NAME="openhfta-images.tar"
LOCAL_TAR="/tmp/${TAR_NAME}"

case "$SERVICES" in
  api)   BUILD_SERVICES="api";      IMAGES="openhfta-api:latest" ;;
  web)   BUILD_SERVICES="web";      IMAGES="openhfta-web:latest" ;;
  all)   BUILD_SERVICES="api web";  IMAGES="openhfta-api:latest openhfta-web:latest" ;;
  *) echo "Uso: $0 [api|web|all]" >&2; exit 1 ;;
esac

echo "==> Build local: ${BUILD_SERVICES}"
docker compose build ${BUILD_SERVICES}

echo "==> Empacotando imagens em ${LOCAL_TAR}"
docker save -o "${LOCAL_TAR}" ${IMAGES}
LOCAL_SHA=$(sha256sum "${LOCAL_TAR}" | awk '{print $1}')
echo "    sha256 local: ${LOCAL_SHA}"

echo "==> Transferindo para ${DEPLOY_HOST}:${DEPLOY_DIR}/"
if ! scp "${LOCAL_TAR}" docker-compose.prod.yml "${DEPLOY_HOST}:${DEPLOY_DIR}/"; then
  echo "    scp falhou, tentando rsync --partial"
  rsync -av --partial --progress "${LOCAL_TAR}" "${DEPLOY_HOST}:${DEPLOY_DIR}/${TAR_NAME}"
  scp docker-compose.prod.yml "${DEPLOY_HOST}:${DEPLOY_DIR}/"
fi

echo "==> Conferindo integridade no servidor"
REMOTE_SHA=$(ssh "${DEPLOY_HOST}" "sha256sum ${DEPLOY_DIR}/${TAR_NAME}" | awk '{print $1}')
echo "    sha256 remoto: ${REMOTE_SHA}"
if [ "${LOCAL_SHA}" != "${REMOTE_SHA}" ]; then
  echo "ERRO: hash do arquivo transferido não confere. Aborte e tente novamente." >&2
  exit 1
fi

echo "==> Carregando imagens e recriando containers (${SERVICES})"
if [ "$SERVICES" = "all" ]; then
  RECREATE_ARGS="--force-recreate"
else
  RECREATE_ARGS="--no-deps --force-recreate ${SERVICES}"
fi
ssh "${DEPLOY_HOST}" "cd ${DEPLOY_DIR} && \
  docker load -i ${TAR_NAME} && \
  docker compose -f docker-compose.prod.yml up -d ${RECREATE_ARGS} && \
  docker compose -f docker-compose.prod.yml ps"

echo "==> Verificando saúde da aplicação"
ssh "${DEPLOY_HOST}" "curl -fsS http://127.0.0.1:${HEALTH_PORT}/health && echo && curl -fsSI http://127.0.0.1:${HEALTH_PORT}/ | head -5"

echo "==> Deploy concluído em ${DEPLOY_HOST}:${DEPLOY_DIR} (serviços: ${SERVICES})"
