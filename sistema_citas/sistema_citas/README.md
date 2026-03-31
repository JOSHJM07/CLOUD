# Sistema de Gestion de Citas (FastAPI + HTML + PostgreSQL)

Proyecto con CRUD basico de:
- Citas
- Pacientes
- Medicos
- Especialidades
- Consultorios

Reglas basicas incluidas para consistencia:
- No se repiten especialidades por descripcion.
- No se repiten consultorios para el mismo medico + especialidad.
- No se permiten dos citas en el mismo consultorio, misma fecha y hora.
- Una cita valida que paciente, medico y consultorio existan.
- El medico de la cita debe coincidir con el medico del consultorio.

Seed catalogo al iniciar:
- En cada arranque del backend se valida y precarga un catalogo base de medicos y consultorios.
- Es idempotente: no duplica registros ya existentes.
- Se controla con `ENABLE_STARTUP_SEED=true|false`.
- Incluye 4 especialidades base: `Medicina General`, `Pediatria`, `Cardiologia`, `Dermatologia`.
- Incluye 4 medicos catalogo con correo `catalogo.*@medicitas.com`.

El frontend ya esta conectado al backend y puede correr:
- Directo desde FastAPI (`http://localhost:8000`)
- O en contenedor Nginx con proxy `/api` (`http://localhost:8080`)

## Estructura

```text
sistema_citas/
|-- app/
|   |-- database/
|   |-- models/
|   |-- routes/
|   |-- schemas/
|   |-- static/index.html
|   `-- main.py
|-- Dockerfile.backend
|-- Dockerfile.frontend
|-- docker-compose.yml
|-- docker-compose.cloud.yml
|-- infra/nginx/default.conf
|-- requirements.txt
`-- .env.example
```

## Ejecutar en local (sin Docker)

1. Crear y activar entorno virtual.
2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

3. Crear `.env` desde `.env.example` y ajustar credenciales.
4. Levantar API:

```bash
uvicorn app.main:app --reload
```

5. Abrir:
- Frontend + API: `http://localhost:8000`
- Docs API: `http://localhost:8000/docs`

## Ejecutar con Docker Compose (local)

```bash
docker compose up -d --build
```

Servicios:
- Frontend: `http://localhost:8080`
- Backend API: `http://localhost:8000`
- Health backend: `http://localhost:8000/health`
- PostgreSQL: `localhost:5432`

Para bajar:

```bash
docker compose down
```

Para bajar y borrar volumen de DB:

```bash
docker compose down -v
```

Si vienes de una version anterior del proyecto, se recomienda ejecutar ese comando
(`down -v`) una vez para recrear la base con las nuevas validaciones.

## Subir imagenes a Docker Hub

1. Login:

```bash
docker login
```

2. Definir usuario y tag (PowerShell):

```powershell
$env:DOCKERHUB_USER="TU_USUARIO"
$env:APP_TAG="v1"
```

3. Build y tag:

```bash
docker build -f Dockerfile.backend -t %DOCKERHUB_USER%/sistema-citas-backend:%APP_TAG% .
docker build -f Dockerfile.frontend -t %DOCKERHUB_USER%/sistema-citas-frontend:%APP_TAG% .
```

En PowerShell usa:

```powershell
docker build -f Dockerfile.backend -t "$env:DOCKERHUB_USER/sistema-citas-backend:$env:APP_TAG" .
docker build -f Dockerfile.frontend -t "$env:DOCKERHUB_USER/sistema-citas-frontend:$env:APP_TAG" .
```

4. Push:

```powershell
docker push "$env:DOCKERHUB_USER/sistema-citas-backend:$env:APP_TAG"
docker push "$env:DOCKERHUB_USER/sistema-citas-frontend:$env:APP_TAG"
```

## Desplegar en instancia de GCP con pull

1. Copiar `docker-compose.cloud.yml` y `.env.cloud.example` a la VM.
2. Crear archivo `.env` en la VM:

```bash
cp .env.cloud.example .env
```

3. Editar `.env` con tus valores:

```bash
DOCKERHUB_USER=TU_USUARIO
APP_TAG=v1
POSTGRES_PASSWORD=postgres
ENABLE_STARTUP_SEED=true
```

Si no quieres cargar catalogo automaticamente:

```bash
ENABLE_STARTUP_SEED=false
```

4. Levantar por pull:

```bash
docker compose --env-file .env -f docker-compose.cloud.yml pull
docker compose --env-file .env -f docker-compose.cloud.yml up -d
```

5. Verificar:
- Frontend: `http://IP_PUBLICA_VM`
- API docs: `http://IP_PUBLICA_VM:8000/docs`
- Health: `http://IP_PUBLICA_VM:8000/health`

## Flujo recomendado para cargar datos

1. Crear especialidades.
2. Crear medicos.
3. Crear pacientes.
4. Crear consultorios.
5. Crear citas.

## Endpoints principales

- `GET /medicos/`
- `GET /pacientes/`
- `GET /especialidades/`
- `GET /consultorios/`
- `GET /citas/`
