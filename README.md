# HydroScan API — Backend Django

Backend REST API para el sistema de gestión de mediciones de agua HydroScan.

## Stack

- **Django 5.1** + **Django REST Framework 3.15**
- **JWT** (SimpleJWT) para autenticación
- **PostgreSQL** (Docker) / **SQLite** (desarrollo local)
- **Docker + Docker Compose** para despliegue
- **Swagger UI** en `/api/docs/`

## Endpoints principales

| Recurso | URL | Métodos |
|---------|-----|---------|
| Login (JWT) | `POST /api/auth/login/` | Obtener access + refresh token |
| Refresh token | `POST /api/auth/refresh/` | Renovar access token |
| Mi perfil | `GET /api/accounts/users/me/` | Datos del usuario autenticado |
| Usuarios | `/api/accounts/users/` | CRUD (solo admin) |
| Asignar dptos | `POST /api/accounts/users/{id}/assign-apartments/` | `{"apartment_ids": [1,2]}` |
| Edificios | `/api/buildings/buildings/` | CRUD |
| Torres | `/api/buildings/towers/` | CRUD |
| Departamentos | `/api/buildings/apartments/` | CRUD |
| Mediciones | `/api/measurements/` | CRUD |
| Swagger docs | `/api/docs/` | Documentación interactiva |

---

## Opción 1: Desarrollo local (sin Docker)

### Requisitos
- Python 3.11+

### Pasos

```bash
# 1. Ir al directorio del proyecto
cd /ruta/a/hydroscan-api

# 2. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Aplicar migraciones (SQLite por defecto)
python manage.py migrate

# 5. Cargar datos de ejemplo
python manage.py seed_data

# 6. Levantar servidor
python manage.py runserver 8001
```

### Acceder
- API: http://localhost:8001/api/
- Swagger: http://localhost:8001/api/docs/
- Admin Django: http://localhost:8001/admin/

### Credenciales de prueba
| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| `admin` | `admin` | Administrador |
| `jperez` | `1234` | Operador |
| `mlopez` | `1234` | Operador |

---

## Opción 2: Docker Compose (recomendado para producción/servidor)

### Requisitos
- Docker y Docker Compose instalados

### Pasos

```bash
# 1. Ir al directorio del proyecto
cd /ruta/a/hydroscan-api

# 2. Levantar todo (PostgreSQL + Django)
docker compose up --build -d

# 3. (Opcional) Ver logs
docker compose logs -f web
```

El `docker-compose.yml` ejecuta automáticamente:
1. Inicia PostgreSQL
2. Aplica migraciones
3. Carga datos de ejemplo (seed_data)
4. Inicia Gunicorn en el puerto 8001

### Acceder
- API: http://localhost:8001/api/
- Swagger: http://localhost:8001/api/docs/
- Admin: http://localhost:8001/admin/

### Detener
```bash
docker compose down         # Detener contenedores
docker compose down -v      # Detener Y borrar datos de BD
```

---

## Subir a un servidor (VPS / DigitalOcean / AWS EC2)

```bash
# 1. En el servidor, clonar/subir el proyecto
scp -r hydroscan-api/ usuario@servidor:/home/usuario/

# 2. SSH al servidor
ssh usuario@servidor

# 3. Instalar Docker si no está
curl -fsSL https://get.docker.com | sh

# 4. Ir al proyecto y levantar
cd /home/usuario/hydroscan-api

# 5. Editar `.env.prod` (o variables en compose)
#    - SECRET_KEY, DB_PASSWORD
#    - `CORS_ALLOWED_ORIGINS`: todos los orígenes desde los que cargará el admin (HTTPS de producción).
#      Si pruebas el Angular en `http://localhost:4200` contra esta API, añade también
#      `http://localhost:4200,http://127.0.0.1:4200` o el navegador bloqueará las peticiones (CORS).
#    - `CSRF_TRUSTED_ORIGINS` si usas formularios Django; la API JWT suele ir solo con CORS bien configurado.

# 6. Levantar (producción usa `docker-compose.prod.yml`)
docker compose -f docker-compose.prod.yml up --build -d

# 7. Datos demo (opcional, una sola vez): el arranque en prod **no** ejecuta `seed_data`.
#    docker compose -f docker-compose.prod.yml exec web python manage.py seed_data
#    Crear superusuario alternativo: `exec web python manage.py createsuperuser`
```

### Generar SECRET_KEY seguro
```bash
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Probar la API con curl

```bash
# Login
curl -X POST http://localhost:8001/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'

# Usar el token obtenido
TOKEN="<access_token_del_login>"

# Ver edificios
curl http://localhost:8001/api/buildings/buildings/ \
  -H "Authorization: Bearer $TOKEN"

# Ver mediciones
curl http://localhost:8001/api/measurements/ \
  -H "Authorization: Bearer $TOKEN"

# Crear usuario
curl -X POST http://localhost:8001/api/accounts/users/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"nuevo","password":"1234","first_name":"Nuevo","last_name":"Operador","role":"operator"}'
```
