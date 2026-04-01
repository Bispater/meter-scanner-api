#!/bin/bash

# Script de despliegue automático para HydroScan API
# Uso: ./start.sh [servidor] [directorio-remoto]

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuración por defecto
REMOTE_SERVER="${1:-root@srv702740}"
REMOTE_DIR="${2:-/opt/meter-scanner-api}"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "${GREEN}=== HydroScan API - Despliegue Automático ===${NC}"
echo -e "${YELLOW}Servidor:${NC} $REMOTE_SERVER"
echo -e "${YELLOW}Directorio remoto:${NC} $REMOTE_DIR"
echo ""

# Verificar que existe el archivo .env.prod
if [ ! -f "$LOCAL_DIR/.env.prod" ]; then
    echo -e "${RED}Error: No se encuentra el archivo .env.prod${NC}"
    echo -e "${YELLOW}Copia .env.prod.example a .env.prod y configúralo:${NC}"
    echo "cp .env.prod.example .env.prod"
    exit 1
fi

# Confirmar despliegue
read -p "¿Continuar con el despliegue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Despliegue cancelado${NC}"
    exit 0
fi

echo -e "${GREEN}[1/6] Creando directorio remoto...${NC}"
ssh $REMOTE_SERVER "mkdir -p $REMOTE_DIR"

echo -e "${GREEN}[2/6] Sincronizando archivos...${NC}"
rsync -avz --progress \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='db.sqlite3' \
    --exclude='media/' \
    --exclude='staticfiles/' \
    --exclude='venv/' \
    --exclude='.DS_Store' \
    $LOCAL_DIR/ $REMOTE_SERVER:$REMOTE_DIR/

echo -e "${GREEN}[3/6] Copiando archivo de configuración de producción...${NC}"
scp $LOCAL_DIR/.env.prod $REMOTE_SERVER:$REMOTE_DIR/.env

echo -e "${GREEN}[4/6] Deteniendo contenedores existentes...${NC}"
ssh $REMOTE_SERVER "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml down || true"

echo -e "${GREEN}[5/6] Construyendo y levantando contenedores...${NC}"
ssh $REMOTE_SERVER "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml build --no-cache"
ssh $REMOTE_SERVER "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml up -d"

echo -e "${GREEN}[6/6] Verificando estado de los servicios...${NC}"
sleep 5
ssh $REMOTE_SERVER "cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml ps"

echo ""
echo -e "${GREEN}=== Despliegue completado ===${NC}"
echo -e "${YELLOW}Ver logs:${NC} ssh $REMOTE_SERVER 'cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml logs -f'"
echo -e "${YELLOW}Estado:${NC} ssh $REMOTE_SERVER 'cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml ps'"
echo ""
