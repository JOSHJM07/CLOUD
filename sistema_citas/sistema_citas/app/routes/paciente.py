from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Paciente
from app.schemas import PacienteCreate, PacienteOut, PacienteUpdate

router = APIRouter(prefix="/pacientes", tags=["Pacientes"])


def _normalizar_texto(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = " ".join(value.split()).strip()
    return value or None


def _correo_en_uso(db: Session, correo: Optional[str], excluir_cedula: Optional[str] = None) -> bool:
    if not correo:
        return False
    query = db.query(Paciente).filter(func.lower(Paciente.correo) == correo.lower())
    if excluir_cedula is not None:
        query = query.filter(Paciente.cedula_paciente != excluir_cedula)
    return query.first() is not None


@router.get("/", response_model=List[PacienteOut])
def listar_pacientes(db: Session = Depends(get_db)):
    return db.query(Paciente).order_by(Paciente.primer_apellido.asc(), Paciente.primer_nombre.asc()).all()


@router.get("/{cedula}", response_model=PacienteOut)
def obtener_paciente(cedula: str, db: Session = Depends(get_db)):
    paciente = db.query(Paciente).filter(Paciente.cedula_paciente == cedula).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
    return paciente


@router.post("/", response_model=PacienteOut, status_code=status.HTTP_201_CREATED)
def crear_paciente(data: PacienteCreate, db: Session = Depends(get_db)):
    payload = data.model_dump()
    payload["cedula_paciente"] = _normalizar_texto(payload["cedula_paciente"])
    payload["primer_nombre"] = _normalizar_texto(payload["primer_nombre"])
    payload["segundo_nombre"] = _normalizar_texto(payload.get("segundo_nombre"))
    payload["primer_apellido"] = _normalizar_texto(payload["primer_apellido"])
    payload["segundo_apellido"] = _normalizar_texto(payload.get("segundo_apellido"))
    payload["telefono"] = _normalizar_texto(payload.get("telefono"))
    payload["correo"] = _normalizar_texto(payload.get("correo"))

    existente = db.query(Paciente).filter(Paciente.cedula_paciente == payload["cedula_paciente"]).first()
    if existente:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un paciente con esa cedula")

    if _correo_en_uso(db, payload.get("correo")):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El correo del paciente ya existe")

    nuevo = Paciente(**payload)
    db.add(nuevo)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo crear el paciente") from exc
    db.refresh(nuevo)
    return nuevo


@router.put("/{cedula}", response_model=PacienteOut)
def actualizar_paciente(cedula: str, data: PacienteUpdate, db: Session = Depends(get_db)):
    paciente = db.query(Paciente).filter(Paciente.cedula_paciente == cedula).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    cambios = data.model_dump(exclude_unset=True)
    for campo in [
        "primer_nombre",
        "segundo_nombre",
        "primer_apellido",
        "segundo_apellido",
        "telefono",
        "correo",
    ]:
        if campo in cambios:
            cambios[campo] = _normalizar_texto(cambios[campo])

    if "correo" in cambios and _correo_en_uso(db, cambios.get("correo"), excluir_cedula=cedula):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El correo del paciente ya existe")

    for campo, valor in cambios.items():
        setattr(paciente, campo, valor)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo actualizar el paciente") from exc
    db.refresh(paciente)
    return paciente


@router.delete("/{cedula}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_paciente(cedula: str, db: Session = Depends(get_db)):
    paciente = db.query(Paciente).filter(Paciente.cedula_paciente == cedula).first()
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    db.delete(paciente)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar el paciente porque tiene citas asociadas",
        ) from exc