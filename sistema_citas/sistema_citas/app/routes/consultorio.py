from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Consultorio, Especialidad, Medico
from app.schemas import ConsultorioCreate, ConsultorioOut, ConsultorioUpdate

router = APIRouter(prefix="/consultorios", tags=["Consultorios"])


def _validar_relaciones(db: Session, id_medico: int, id_especialidad: int):
    medico = db.query(Medico).filter(Medico.id_medico == id_medico).first()
    if not medico:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El medico seleccionado no existe")

    especialidad = db.query(Especialidad).filter(Especialidad.id_especialidad == id_especialidad).first()
    if not especialidad:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La especialidad seleccionada no existe")


def _duplicado(db: Session, id_medico: int, id_especialidad: int, excluir_id: int | None = None) -> bool:
    query = db.query(Consultorio).filter(
        Consultorio.id_medico == id_medico,
        Consultorio.id_especialidad == id_especialidad,
    )
    if excluir_id is not None:
        query = query.filter(Consultorio.id_consultorio != excluir_id)
    return query.first() is not None


@router.get("/", response_model=List[ConsultorioOut])
def listar_consultorios(db: Session = Depends(get_db)):
    return db.query(Consultorio).order_by(Consultorio.id_consultorio.asc()).all()


@router.get("/{id_consultorio}", response_model=ConsultorioOut)
def obtener_consultorio(id_consultorio: int, db: Session = Depends(get_db)):
    cons = db.query(Consultorio).filter(Consultorio.id_consultorio == id_consultorio).first()
    if not cons:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultorio no encontrado")
    return cons


@router.post("/", response_model=ConsultorioOut, status_code=status.HTTP_201_CREATED)
def crear_consultorio(data: ConsultorioCreate, db: Session = Depends(get_db)):
    _validar_relaciones(db, data.id_medico, data.id_especialidad)
    if _duplicado(db, data.id_medico, data.id_especialidad):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un consultorio para ese medico y especialidad",
        )

    nuevo = Consultorio(**data.model_dump())
    db.add(nuevo)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo crear el consultorio") from exc
    db.refresh(nuevo)
    return nuevo


@router.put("/{id_consultorio}", response_model=ConsultorioOut)
def actualizar_consultorio(id_consultorio: int, data: ConsultorioUpdate, db: Session = Depends(get_db)):
    cons = db.query(Consultorio).filter(Consultorio.id_consultorio == id_consultorio).first()
    if not cons:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultorio no encontrado")

    cambios = data.model_dump(exclude_unset=True)
    id_medico = cambios.get("id_medico", cons.id_medico)
    id_especialidad = cambios.get("id_especialidad", cons.id_especialidad)

    _validar_relaciones(db, id_medico, id_especialidad)
    if _duplicado(db, id_medico, id_especialidad, excluir_id=id_consultorio):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un consultorio para ese medico y especialidad",
        )

    for campo, valor in cambios.items():
        setattr(cons, campo, valor)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se pudo actualizar el consultorio") from exc
    db.refresh(cons)
    return cons


@router.delete("/{id_consultorio}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_consultorio(id_consultorio: int, db: Session = Depends(get_db)):
    cons = db.query(Consultorio).filter(Consultorio.id_consultorio == id_consultorio).first()
    if not cons:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consultorio no encontrado")

    db.delete(cons)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar el consultorio porque tiene citas asociadas",
        ) from exc