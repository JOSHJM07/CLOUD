import logging
import os
from typing import Any, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from google.api_core.exceptions import GoogleAPIError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Cita, CitaDocumento, Consultorio, Medico, Paciente
from app.schemas import CitaCreate, CitaDocumentoOut, CitaOut, CitaUpdate
from app.services import delete_object, storage_status, upload_bytes

router = APIRouter(prefix="/citas", tags=["Citas"])
logger = logging.getLogger("uvicorn.error")


def _env_int(name: str, default: int) -> int:
    try:
        value = int((os.getenv(name) or str(default)).strip())
        return max(1, value)
    except ValueError:
        return default


MAX_FILES_PER_UPLOAD = _env_int("MAX_FILES_PER_UPLOAD", 3)
MAX_FILES_PER_CITA = _env_int("MAX_FILES_PER_CITA", 5)
MAX_UPLOAD_FILE_SIZE_MB = _env_int("MAX_UPLOAD_FILE_SIZE_MB", 5)
MAX_UPLOAD_FILE_SIZE_BYTES = MAX_UPLOAD_FILE_SIZE_MB * 1024 * 1024


def _validar_relaciones_cita(db: Session, data: dict[str, Any]):
    paciente = db.query(Paciente).filter(Paciente.cedula_paciente == data["cedula_paciente"]).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El paciente seleccionado no existe")

    medico = db.query(Medico).filter(Medico.id_medico == data["id_medico"]).first()
    if not medico:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El medico seleccionado no existe")

    consultorio = db.query(Consultorio).filter(Consultorio.id_consultorio == data["id_consultorio"]).first()
    if not consultorio:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El consultorio seleccionado no existe")

    if consultorio.id_medico != data["id_medico"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El medico no corresponde al consultorio seleccionado",
        )


def _horario_ocupado(
    db: Session,
    id_consultorio: int,
    fecha_cita,
    hora,
    excluir_id: int | None = None,
) -> bool:
    query = db.query(Cita).filter(
        Cita.id_consultorio == id_consultorio,
        Cita.fecha_cita == fecha_cita,
        Cita.hora == hora,
    )
    if excluir_id is not None:
        query = query.filter(Cita.id_cita != excluir_id)
    return query.first() is not None


def _obtener_cita_o_404(db: Session, id_cita: int, incluir_documentos: bool = False) -> Cita:
    query = db.query(Cita)
    if incluir_documentos:
        query = query.options(selectinload(Cita.documentos))
    cita = query.filter(Cita.id_cita == id_cita).first()
    if not cita:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
    return cita


@router.get("/", response_model=List[CitaOut])
def listar_citas(db: Session = Depends(get_db)):
    return (
        db.query(Cita)
        .options(selectinload(Cita.documentos))
        .order_by(Cita.fecha_cita.desc(), Cita.hora.desc())
        .all()
    )


@router.get("/{id_cita}", response_model=CitaOut)
def obtener_cita(id_cita: int, db: Session = Depends(get_db)):
    return _obtener_cita_o_404(db, id_cita, incluir_documentos=True)


@router.post("/", response_model=CitaOut, status_code=status.HTTP_201_CREATED)
def crear_cita(data: CitaCreate, db: Session = Depends(get_db)):
    payload = data.model_dump()
    payload["cedula_paciente"] = payload["cedula_paciente"].strip()

    _validar_relaciones_cita(db, payload)
    if _horario_ocupado(db, payload["id_consultorio"], payload["fecha_cita"], payload["hora"]):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cita en ese consultorio para la fecha y hora indicadas",
        )

    nueva = Cita(**payload)
    db.add(nueva)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo crear la cita") from exc
    db.refresh(nueva)
    logger.info(
        "event=cita_creada id_cita=%s cedula_paciente=%s id_medico=%s id_consultorio=%s fecha=%s hora=%s",
        nueva.id_cita,
        nueva.cedula_paciente,
        nueva.id_medico,
        nueva.id_consultorio,
        nueva.fecha_cita,
        nueva.hora,
    )
    return nueva


@router.put("/{id_cita}", response_model=CitaOut)
def actualizar_cita(id_cita: int, data: CitaUpdate, db: Session = Depends(get_db)):
    cita = _obtener_cita_o_404(db, id_cita)

    cambios = data.model_dump(exclude_unset=True)
    if "cedula_paciente" in cambios and cambios["cedula_paciente"]:
        cambios["cedula_paciente"] = cambios["cedula_paciente"].strip()

    validacion = {
        "cedula_paciente": cambios.get("cedula_paciente", cita.cedula_paciente),
        "id_consultorio": cambios.get("id_consultorio", cita.id_consultorio),
        "id_medico": cambios.get("id_medico", cita.id_medico),
        "fecha_cita": cambios.get("fecha_cita", cita.fecha_cita),
        "hora": cambios.get("hora", cita.hora),
    }

    _validar_relaciones_cita(db, validacion)
    if _horario_ocupado(
        db,
        validacion["id_consultorio"],
        validacion["fecha_cita"],
        validacion["hora"],
        excluir_id=id_cita,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cita en ese consultorio para la fecha y hora indicadas",
        )

    for campo, valor in cambios.items():
        setattr(cita, campo, valor)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo actualizar la cita") from exc
    db.refresh(cita)
    logger.info("event=cita_actualizada id_cita=%s campos=%s", cita.id_cita, ",".join(sorted(cambios.keys())))
    return cita


@router.get("/{id_cita}/documentos", response_model=List[CitaDocumentoOut])
def listar_documentos_cita(id_cita: int, db: Session = Depends(get_db)):
    _obtener_cita_o_404(db, id_cita)
    return (
        db.query(CitaDocumento)
        .filter(CitaDocumento.id_cita == id_cita)
        .order_by(CitaDocumento.fecha_carga.desc())
        .all()
    )


@router.post(
    "/{id_cita}/documentos",
    response_model=List[CitaDocumentoOut],
    status_code=status.HTTP_201_CREATED,
)
async def cargar_documentos_cita(
    id_cita: int,
    archivos: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    _obtener_cita_o_404(db, id_cita)

    if not archivos:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se recibieron archivos para cargar")
    if len(archivos) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se permiten {MAX_FILES_PER_UPLOAD} archivos por envio",
        )

    config_storage = storage_status()
    if not config_storage["enabled"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cloud Storage no esta habilitado. Configura ENABLE_GCS_UPLOAD y GCS_BUCKET_NAME",
        )

    total_actual = db.query(CitaDocumento).filter(CitaDocumento.id_cita == id_cita).count()
    if total_actual + len(archivos) > MAX_FILES_PER_CITA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La cita permite un maximo de {MAX_FILES_PER_CITA} documentos",
        )

    registros: List[CitaDocumento] = []
    objetos_subidos: List[str] = []

    try:
        for archivo in archivos:
            if not archivo.filename:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Todos los archivos deben tener nombre")

            contenido = await archivo.read()
            tamano = len(contenido)
            if tamano == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El archivo '{archivo.filename}' esta vacio",
                )
            if tamano > MAX_UPLOAD_FILE_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El archivo '{archivo.filename}' excede {MAX_UPLOAD_FILE_SIZE_MB} MB",
                )

            object_name, gcs_uri = upload_bytes(
                id_cita=id_cita,
                filename=archivo.filename,
                content=contenido,
                content_type=archivo.content_type,
            )
            objetos_subidos.append(object_name)

            registro = CitaDocumento(
                id_cita=id_cita,
                nombre_archivo=archivo.filename,
                tipo_mime=archivo.content_type,
                tamano_bytes=tamano,
                gcs_object_name=object_name,
                gcs_uri=gcs_uri,
            )
            db.add(registro)
            registros.append(registro)
    except HTTPException:
        for object_name in objetos_subidos:
            delete_object(object_name)
        db.rollback()
        raise
    except (RuntimeError, GoogleAPIError) as exc:
        for object_name in objetos_subidos:
            delete_object(object_name)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No fue posible cargar documentos en Cloud Storage: {str(exc)}",
        ) from exc

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        for object_name in objetos_subidos:
            delete_object(object_name)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudieron registrar los documentos") from exc

    for registro in registros:
        db.refresh(registro)

    logger.info(
        "event=documentos_cargados id_cita=%s cantidad=%s bucket=%s",
        id_cita,
        len(registros),
        config_storage["bucket"],
    )
    return registros


@router.delete("/{id_cita}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cita(id_cita: int, db: Session = Depends(get_db)):
    cita = _obtener_cita_o_404(db, id_cita, incluir_documentos=True)
    object_names = [doc.gcs_object_name for doc in cita.documentos]

    db.delete(cita)
    db.commit()

    for object_name in object_names:
        delete_object(object_name)

    logger.info("event=cita_eliminada id_cita=%s documentos_eliminados=%s", id_cita, len(object_names))
