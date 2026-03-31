from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Medico
from app.schemas import MedicoCreate, MedicoOut, MedicoUpdate

router = APIRouter(prefix="/medicos", tags=["Medicos"])


def _normalizar_texto(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = " ".join(value.split()).strip()
    return value or None


def _correo_en_uso(db: Session, correo: Optional[str], excluir_id: Optional[int] = None) -> bool:
    if not correo:
        return False
    query = db.query(Medico).filter(func.lower(Medico.correo) == correo.lower())
    if excluir_id is not None:
        query = query.filter(Medico.id_medico != excluir_id)
    return query.first() is not None


@router.get("/", response_model=List[MedicoOut])
def listar_medicos(db: Session = Depends(get_db)):
    return db.query(Medico).order_by(Medico.id_medico.asc()).all()


@router.get("/{id_medico}", response_model=MedicoOut)
def obtener_medico(id_medico: int, db: Session = Depends(get_db)):
    medico = db.query(Medico).filter(Medico.id_medico == id_medico).first()
    if not medico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medico no encontrado")
    return medico


@router.post("/", response_model=MedicoOut, status_code=status.HTTP_201_CREATED)
def crear_medico(data: MedicoCreate, db: Session = Depends(get_db)):
    payload = data.model_dump()
    payload["primer_nombre"] = _normalizar_texto(payload["primer_nombre"])
    payload["segundo_nombre"] = _normalizar_texto(payload.get("segundo_nombre"))
    payload["primer_apellido"] = _normalizar_texto(payload["primer_apellido"])
    payload["segundo_apellido"] = _normalizar_texto(payload.get("segundo_apellido"))
    payload["correo"] = _normalizar_texto(payload.get("correo"))

    if _correo_en_uso(db, payload.get("correo")):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El correo del medico ya existe")

    nuevo = Medico(**payload)
    db.add(nuevo)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo crear el medico") from exc
    db.refresh(nuevo)
    return nuevo


@router.put("/{id_medico}", response_model=MedicoOut)
def actualizar_medico(id_medico: int, data: MedicoUpdate, db: Session = Depends(get_db)):
    medico = db.query(Medico).filter(Medico.id_medico == id_medico).first()
    if not medico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medico no encontrado")

    cambios = data.model_dump(exclude_unset=True)
    for campo in ["primer_nombre", "segundo_nombre", "primer_apellido", "segundo_apellido", "correo"]:
        if campo in cambios:
            cambios[campo] = _normalizar_texto(cambios[campo])

    if "correo" in cambios and _correo_en_uso(db, cambios.get("correo"), excluir_id=id_medico):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El correo del medico ya existe")

    for campo, valor in cambios.items():
        setattr(medico, campo, valor)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo actualizar el medico") from exc
    db.refresh(medico)
    return medico


@router.delete("/{id_medico}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_medico(id_medico: int, db: Session = Depends(get_db)):
    medico = db.query(Medico).filter(Medico.id_medico == id_medico).first()
    if not medico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medico no encontrado")

    db.delete(medico)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar el medico porque tiene registros asociados",
        ) from exc