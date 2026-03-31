from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Cita, Consultorio, Medico, Paciente
from app.schemas import CitaCreate, CitaOut, CitaUpdate

router = APIRouter(prefix="/citas", tags=["Citas"])


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


@router.get("/", response_model=List[CitaOut])
def listar_citas(db: Session = Depends(get_db)):
    return db.query(Cita).order_by(Cita.fecha_cita.desc(), Cita.hora.desc()).all()


@router.get("/{id_cita}", response_model=CitaOut)
def obtener_cita(id_cita: int, db: Session = Depends(get_db)):
    cita = db.query(Cita).filter(Cita.id_cita == id_cita).first()
    if not cita:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
    return cita


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
    return nueva


@router.put("/{id_cita}", response_model=CitaOut)
def actualizar_cita(id_cita: int, data: CitaUpdate, db: Session = Depends(get_db)):
    cita = db.query(Cita).filter(Cita.id_cita == id_cita).first()
    if not cita:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")

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
    return cita


@router.delete("/{id_cita}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cita(id_cita: int, db: Session = Depends(get_db)):
    cita = db.query(Cita).filter(Cita.id_cita == id_cita).first()
    if not cita:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")

    db.delete(cita)
    db.commit()