# Sistema de Gestion de Citas (FastAPI + HTML + PostgreSQL + GCS)

Sistema academico de citas medicas con:
- Backend REST en FastAPI
- Frontend HTML/CSS/JS (single page)
- Base de datos PostgreSQL
- Despliegue en VM de Google Cloud con Docker Compose
- Adjuntos por cita en Google Cloud Storage (controlado por IAM)

## Funcionalidades principales

- CRUD de `citas`, `pacientes`, `medicos`, `especialidades` y `consultorios`.
- Validaciones de negocio:
  - No se repiten especialidades por descripcion.
  - No se repiten consultorios para el mismo medico + especialidad.
  - No se permiten dos citas en el mismo consultorio con misma fecha y hora.
  - Una cita valida que paciente, medico y consultorio existan.
  - El medico de la cita debe coincidir con el del consultorio.
- Seed de catalogo al iniciar (medicos y consultorios base).
- Carga de documentos al agendar cita:
  - Endpoint multipart `POST /citas/{id_cita}/documentos`
  - Metadatos guardados en tabla `cita_documento`
  - Archivos almacenados en Cloud Storage (`gs://bucket/...`)

## Estructura del proyecto

```text
sistema_citas/
|-- app/
|   |-- database/
|   |-- models/
|   |-- routes/
|   |-- schemas/
|   |-- services/storage.py
|   |-- static/index.html
|   `-- main.py
|-- infra/nginx/default.conf
|-- Dockerfile.backend
|-- Dockerfile.frontend
|-- docker-compose.yml
|-- docker-compose.cloud.yml
|-- requirements.txt
|-- .env.example
`-- .env.cloud.example
```

## Variables de entorno

Base:
- `DATABASE_URL`
- `ENABLE_STARTUP_SEED=true|false`

Cloud Storage:
- `ENABLE_GCS_UPLOAD=true|false`
- `GCS_BUCKET_NAME=<nombre_bucket>`
- `GCS_OBJECT_PREFIX=citas`
- `MAX_FILES_PER_UPLOAD=3`
- `MAX_FILES_PER_CITA=5`
- `MAX_UPLOAD_FILE_SIZE_MB=5`

Si ejecutas fuera de GCE y sin Workload Identity, define:
- `GOOGLE_APPLICATION_CREDENTIALS=/ruta/sa-key.json`

## Ejecutar local con Docker

```bash
docker compose up -d --build
```

Servicios:
- Frontend: `http://localhost:8080`
- Backend: `http://localhost:8000`
- Health: `http://localhost:8000/health`
- PostgreSQL: `localhost:5432`

Detener:

```bash
docker compose down
```

Detener y limpiar DB:

```bash
docker compose down -v
```

## Publicar imagenes en Docker Hub

PowerShell:

```powershell
$env:DOCKERHUB_USER="TU_USUARIO"
$env:APP_TAG="v1"

docker build -f Dockerfile.backend -t "$env:DOCKERHUB_USER/sistema-citas-backend:$env:APP_TAG" .
docker build -f Dockerfile.frontend -t "$env:DOCKERHUB_USER/sistema-citas-frontend:$env:APP_TAG" .

docker push "$env:DOCKERHUB_USER/sistema-citas-backend:$env:APP_TAG"
docker push "$env:DOCKERHUB_USER/sistema-citas-frontend:$env:APP_TAG"
```

## Despliegue en VM de Google Cloud

1. Copiar `docker-compose.cloud.yml` y `.env.cloud.example` a la VM.
2. Crear `.env`:

```bash
cp .env.cloud.example .env
```

3. Editar valores:

```bash
DOCKERHUB_USER=tu_usuario
APP_TAG=v1
POSTGRES_PASSWORD=postgres
ENABLE_STARTUP_SEED=true
ENABLE_GCS_UPLOAD=true
GCS_BUCKET_NAME=tu_bucket_gcs
GCS_OBJECT_PREFIX=citas
```

4. Levantar por pull:

```bash
docker compose --env-file .env -f docker-compose.cloud.yml pull
docker compose --env-file .env -f docker-compose.cloud.yml up -d
docker compose --env-file .env -f docker-compose.cloud.yml ps
```

5. Verificar:
- Frontend: `http://IP_PUBLICA_VM`
- API docs: `http://IP_PUBLICA_VM:8000/docs`
- Health: `http://IP_PUBLICA_VM:8000/health`

## IAM + Cloud Storage (minimo recomendado)

1. Crear bucket:

```bash
gcloud storage buckets create gs://NOMBRE_BUCKET --location=us-central1
```

2. Obtener Service Account de la VM:

```bash
gcloud compute instances describe NOMBRE_VM --zone=ZONA --format="value(serviceAccounts.email)"
```

3. Otorgar permisos de objetos sobre el bucket:

```bash
gcloud storage buckets add-iam-policy-binding gs://NOMBRE_BUCKET \
  --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
  --role="roles/storage.objectAdmin"
```

Rol mas estricto opcional:
- `roles/storage.objectCreator`
- `roles/storage.objectViewer`

## Evidencia de logs

Logs de contenedores en VM:

```bash
docker compose --env-file .env -f docker-compose.cloud.yml logs backend --tail=200
```

Eventos esperados:
- `event=cita_creada`
- `event=cita_actualizada`
- `event=documentos_cargados`
- `event=cita_eliminada`
- `Startup seed summary`
- `Cloud storage config`

## Endpoints principales

- `GET /medicos/`
- `GET /pacientes/`
- `GET /especialidades/`
- `GET /consultorios/`
- `GET /citas/`
- `POST /citas/`
- `POST /citas/{id_cita}/documentos`
- `GET /citas/{id_cita}/documentos`
