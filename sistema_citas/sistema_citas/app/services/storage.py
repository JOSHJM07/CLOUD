import logging
import os
import re
from datetime import datetime, timezone
from uuid import uuid4

from google.api_core.exceptions import GoogleAPIError, NotFound
from google.cloud import storage

logger = logging.getLogger("uvicorn.error")


def _is_true(raw: str | None, default: bool = False) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


GCS_BUCKET_NAME = (os.getenv("GCS_BUCKET_NAME") or "").strip()
GCS_OBJECT_PREFIX = (os.getenv("GCS_OBJECT_PREFIX") or "citas").strip().strip("/")
ENABLE_GCS_UPLOAD = _is_true(os.getenv("ENABLE_GCS_UPLOAD"), default=False)

_gcs_client: storage.Client | None = None
_gcs_bucket: storage.Bucket | None = None


def storage_status() -> dict[str, str | bool]:
    return {
        "enabled": bool(ENABLE_GCS_UPLOAD and GCS_BUCKET_NAME),
        "bucket": GCS_BUCKET_NAME,
        "prefix": GCS_OBJECT_PREFIX,
    }


def is_storage_enabled() -> bool:
    return bool(storage_status()["enabled"])


def _get_bucket() -> storage.Bucket:
    if not GCS_BUCKET_NAME:
        raise RuntimeError("No se configuro GCS_BUCKET_NAME para Cloud Storage")

    global _gcs_client, _gcs_bucket
    if _gcs_bucket is not None:
        return _gcs_bucket

    _gcs_client = storage.Client()
    _gcs_bucket = _gcs_client.bucket(GCS_BUCKET_NAME)
    return _gcs_bucket


def _sanitize_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", filename or "archivo")
    cleaned = re.sub(r"_+", "_", cleaned).strip("._")
    return cleaned or "archivo"


def build_object_name(id_cita: int, filename: str) -> str:
    safe_name = _sanitize_filename(filename)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    unique = uuid4().hex
    return f"{GCS_OBJECT_PREFIX}/cita_{id_cita}/{timestamp}_{unique}_{safe_name}"


def upload_bytes(id_cita: int, filename: str, content: bytes, content_type: str | None) -> tuple[str, str]:
    if not is_storage_enabled():
        raise RuntimeError("Cloud Storage no esta habilitado para este entorno")

    object_name = build_object_name(id_cita=id_cita, filename=filename)
    bucket = _get_bucket()
    blob = bucket.blob(object_name)
    blob.upload_from_string(content, content_type=content_type or "application/octet-stream")
    return object_name, f"gs://{bucket.name}/{object_name}"


def delete_object(object_name: str) -> bool:
    if not object_name or not is_storage_enabled():
        return False
    try:
        bucket = _get_bucket()
        bucket.blob(object_name).delete()
        return True
    except NotFound:
        logger.warning("event=gcs_objeto_no_encontrado object_name=%s", object_name)
        return False
    except GoogleAPIError as exc:
        logger.warning("event=gcs_error_eliminar object_name=%s detail=%s", object_name, str(exc))
        return False
