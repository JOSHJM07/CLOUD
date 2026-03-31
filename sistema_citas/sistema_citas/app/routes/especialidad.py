from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Especialidad
from app.schemas import EspecialidadCreate, EspecialidadOut, EspecialidadUpdate

router = APIRouter(prefix="/especialidades", tags=["Especialidades"])


def _normalizar_descripcion(value: str) -> str:
    return " ".join(value.split()).strip()


@router.get("/", response_model=List[EspecialidadOut])
def listar_especialidades(db: Session = Depends(get_db)):
    return db.query(Especialidad).order_by(Especialidad.id_especialidad.asc()).all()


@router.get("/{id_especialidad}", response_model=EspecialidadOut)
def obtener_especialidad(id_especialidad: int, db: Session = Depends(get_db)):
    esp = db.query(Especialidad).filter(Especialidad.id_especialidad == id_especialidad).first()
    if not esp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Especialidad no encontrada")
    return esp


@router.post("/", response_model=EspecialidadOut, status_code=status.HTTP_201_CREATED)
def crear_especialidad(data: EspecialidadCreate, db: Session = Depends(get_db)):
    descripcion = _normalizar_descripcion(data.descripcion)
    existente = (
        db.query(Especialidad)
        .filter(func.lower(Especialidad.descripcion) == descripcion.lower())
        .first()
    )
    if existente:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La especialidad ya existe")

    nueva = Especialidad(descripcion=descripcion)
    db.add(nueva)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo crear la especialidad") from exc
    db.refresh(nueva)
    return nueva


@router.put("/{id_especialidad}", response_model=EspecialidadOut)
def actualizar_especialidad(id_especialidad: int, data: EspecialidadUpdate, db: Session = Depends(get_db)):
    esp = db.query(Especialidad).filter(Especialidad.id_especialidad == id_especialidad).first()
    if not esp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Especialidad no encontrada")

    cambios = data.model_dump(exclude_unset=True)
    if "descripcion" in cambios:
        descripcion = _normalizar_descripcion(cambios["descripcion"])
        existente = (
            db.query(Especialidad)
            .filter(
                func.lower(Especialidad.descripcion) == descripcion.lower(),
                Especialidad.id_especialidad != id_especialidad,
            )
            .first()
        )
        if existente:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La especialidad ya existe")
        esp.descripcion = descripcion

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo actualizar la especialidad") from exc
    db.refresh(esp)
    return esp


@router.delete("/{id_especialidad}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_especialidad(id_especialidad: int, db: Session = Depends(get_db)):
    esp = db.query(Especialidad).filter(Especialidad.id_especialidad == id_especialidad).first()
    if not esp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Especialidad no encontrada")
    db.delete(esp)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar la especialidad porque tiene consultorios asociados",
        ) from exc