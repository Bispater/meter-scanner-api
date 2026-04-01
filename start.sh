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

# Configurar SSH ControlMaster para reutilizar conexión
SSH_CONTROL_PATH="/tmp/ssh-hydroscan-%r@%h:%p"
SSH_OPTS="-o ControlMaster=auto -o ControlPath=$SSH_CONTROL_PATH -o ControlPersist=10m"

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

# Función para limpiar la conexión SSH al salir
cleanup() {
    ssh $SSH_OPTS -O exit $REMOTE_SERVER 2>/dev/null || true
}
trap cleanup EXIT

echo -e "${GREEN}[1/6] Estableciendo conexión SSH...${NC}"
ssh $SSH_OPTS -N -f $REMOTE_SERVER

echo -e "${GREEN}[2/6] Creando directorio remoto y sincronizando archivos...${NC}"
ssh $SSH_OPTS $REMOTE_SERVER "mkdir -p $REMOTE_DIR"

rsync -avz --progress \
    -e "ssh $SSH_OPTS" \
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
scp $SSH_OPTS $LOCAL_DIR/.env.prod $REMOTE_SERVER:$REMOTE_DIR/.env

echo -e "${GREEN}[4/6] Ejecutando despliegue en el servidor...${NC}"
ssh $SSH_OPTS $REMOTE_SERVER bash << EOF
    set -e
    cd $REMOTE_DIR
    
    echo "Deteniendo contenedores existentes..."
    docker-compose -f docker-compose.prod.yml down || true
    
    echo "Construyendo imágenes..."
    docker-compose -f docker-compose.prod.yml build --no-cache
    
    echo "Levantando servicios..."
    docker-compose -f docker-compose.prod.yml up -d
    
    echo "Esperando que los servicios inicien..."
    sleep 5
    
    echo "Estado de los servicios:"
    docker-compose -f docker-compose.prod.yml ps
EOF

echo ""
echo -e "${GREEN}=== Despliegue completado ===${NC}"
echo -e "${YELLOW}Ver logs:${NC} ssh $REMOTE_SERVER 'cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml logs -f'"
echo -e "${YELLOW}Estado:${NC} ssh $REMOTE_SERVER 'cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml ps'"
echo ""
