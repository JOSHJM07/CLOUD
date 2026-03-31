import os
from typing import Dict, List, Tuple

from sqlalchemy import func

from app.database.connection import SessionLocal
from app.models import Consultorio, Especialidad, Medico

DEFAULT_CATALOG: List[Dict[str, str]] = [
    {
        "primer_nombre": "Ana",
        "segundo_nombre": "Maria",
        "primer_apellido": "Lopez",
        "segundo_apellido": "Rojas",
        "correo": "catalogo.ana.lopez@medicitas.com",
        "legacy_correo": "catalogo.ana.lopez@medicitas.local",
        "especialidad": "Medicina General",
    },
    {
        "primer_nombre": "Carlos",
        "segundo_nombre": "Javier",
        "primer_apellido": "Mendez",
        "segundo_apellido": "Vega",
        "correo": "catalogo.carlos.mendez@medicitas.com",
        "legacy_correo": "catalogo.carlos.mendez@medicitas.local",
        "especialidad": "Pediatria",
    },
    {
        "primer_nombre": "Sofia",
        "segundo_nombre": "Elena",
        "primer_apellido": "Ramirez",
        "segundo_apellido": "Castro",
        "correo": "catalogo.sofia.ramirez@medicitas.com",
        "legacy_correo": "catalogo.sofia.ramirez@medicitas.local",
        "especialidad": "Cardiologia",
    },
    {
        "primer_nombre": "Daniel",
        "segundo_nombre": "Andres",
        "primer_apellido": "Quesada",
        "segundo_apellido": "Salas",
        "correo": "catalogo.daniel.quesada@medicitas.com",
        "legacy_correo": "catalogo.daniel.quesada@medicitas.local",
        "especialidad": "Dermatologia",
    },
]


def _seed_enabled() -> bool:
    raw = os.getenv("ENABLE_STARTUP_SEED", "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _normalizar(value: str) -> str:
    return " ".join(value.split()).strip()


def _get_or_create_especialidad(db, descripcion: str) -> Tuple[Especialidad, bool]:
    normalized = _normalizar(descripcion)
    especialidad = (
        db.query(Especialidad)
        .filter(func.lower(Especialidad.descripcion) == normalized.lower())
        .first()
    )
    if especialidad:
        return especialidad, False

    especialidad = Especialidad(descripcion=normalized)
    db.add(especialidad)
    db.flush()
    return especialidad, True


def _get_or_create_medico(db, data: Dict[str, str]) -> Tuple[Medico, bool, bool]:
    correo = _normalizar(data["correo"]).lower()
    medico = db.query(Medico).filter(func.lower(Medico.correo) == correo).first()
    if medico:
        return medico, False, False

    legacy_correo = data.get("legacy_correo")
    if legacy_correo:
        legacy = _normalizar(legacy_correo).lower()
        medico = db.query(Medico).filter(func.lower(Medico.correo) == legacy).first()
        if medico:
            medico.correo = correo
            medico.primer_nombre = _normalizar(data["primer_nombre"])
            medico.segundo_nombre = _normalizar(data["segundo_nombre"])
            medico.primer_apellido = _normalizar(data["primer_apellido"])
            medico.segundo_apellido = _normalizar(data["segundo_apellido"])
            db.flush()
            return medico, False, True

    medico = Medico(
        primer_nombre=_normalizar(data["primer_nombre"]),
        segundo_nombre=_normalizar(data["segundo_nombre"]),
        primer_apellido=_normalizar(data["primer_apellido"]),
        segundo_apellido=_normalizar(data["segundo_apellido"]),
        correo=correo,
    )
    db.add(medico)
    db.flush()
    return medico, True, False


def _get_or_create_consultorio(db, id_medico: int, id_especialidad: int) -> bool:
    existing = (
        db.query(Consultorio)
        .filter(
            Consultorio.id_medico == id_medico,
            Consultorio.id_especialidad == id_especialidad,
        )
        .first()
    )
    if existing:
        return False

    db.add(Consultorio(id_medico=id_medico, id_especialidad=id_especialidad))
    db.flush()
    return True


def run_startup_seed() -> Dict[str, int | bool]:
    if not _seed_enabled():
        return {
            "enabled": False,
            "especialidades": 0,
            "medicos": 0,
            "medicos_actualizados": 0,
            "consultorios": 0,
        }

    created_especialidades = 0
    created_medicos = 0
    updated_medicos = 0
    created_consultorios = 0

    db = SessionLocal()
    try:
        for entry in DEFAULT_CATALOG:
            especialidad, new_esp = _get_or_create_especialidad(db, entry["especialidad"])
            medico, new_med, updated_med = _get_or_create_medico(db, entry)
            new_cons = _get_or_create_consultorio(db, medico.id_medico, especialidad.id_especialidad)

            created_especialidades += int(new_esp)
            created_medicos += int(new_med)
            updated_medicos += int(updated_med)
            created_consultorios += int(new_cons)

        db.commit()
        return {
            "enabled": True,
            "especialidades": created_especialidades,
            "medicos": created_medicos,
            "medicos_actualizados": updated_medicos,
            "consultorios": created_consultorios,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
