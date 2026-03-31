from datetime import date, time
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

ESTADOS_VALIDOS = ("pendiente", "confirmada", "cancelada", "completada")
TIPOS_SANGRE_VALIDOS = ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")


class EspecialidadBase(BaseModel):
    descripcion: str = Field(..., min_length=3, max_length=100)


class EspecialidadCreate(EspecialidadBase):
    pass


class EspecialidadUpdate(BaseModel):
    descripcion: Optional[str] = Field(default=None, min_length=3, max_length=100)


class EspecialidadOut(EspecialidadBase):
    id_especialidad: int

    model_config = {"from_attributes": True}


class MedicoBase(BaseModel):
    primer_nombre: str = Field(..., min_length=2, max_length=50)
    segundo_nombre: Optional[str] = Field(default=None, max_length=50)
    primer_apellido: str = Field(..., min_length=2, max_length=50)
    segundo_apellido: Optional[str] = Field(default=None, max_length=50)
    correo: Optional[EmailStr] = None


class MedicoCreate(MedicoBase):
    pass


class MedicoUpdate(BaseModel):
    primer_nombre: Optional[str] = Field(default=None, min_length=2, max_length=50)
    segundo_nombre: Optional[str] = Field(default=None, max_length=50)
    primer_apellido: Optional[str] = Field(default=None, min_length=2, max_length=50)
    segundo_apellido: Optional[str] = Field(default=None, max_length=50)
    correo: Optional[EmailStr] = None


class MedicoOut(MedicoBase):
    id_medico: int

    model_config = {"from_attributes": True}


class PacienteBase(BaseModel):
    cedula_paciente: str = Field(..., min_length=5, max_length=20)
    id_rol: Optional[int] = Field(default=None, ge=1)
    primer_nombre: str = Field(..., min_length=2, max_length=50)
    segundo_nombre: Optional[str] = Field(default=None, max_length=50)
    primer_apellido: str = Field(..., min_length=2, max_length=50)
    segundo_apellido: Optional[str] = Field(default=None, max_length=50)
    edad: Optional[int] = Field(default=None, ge=0, le=120)
    tipo_sangre: Optional[str] = Field(default=None, max_length=5)
    telefono: Optional[str] = Field(default=None, max_length=20)
    correo: Optional[EmailStr] = None

    @field_validator("tipo_sangre")
    @classmethod
    def tipo_sangre_valido(cls, value: Optional[str]):
        if value is None:
            return value
        if value not in TIPOS_SANGRE_VALIDOS:
            raise ValueError(f"Tipo de sangre invalido. Opciones: {TIPOS_SANGRE_VALIDOS}")
        return value


class PacienteCreate(PacienteBase):
    pass


class PacienteUpdate(BaseModel):
    id_rol: Optional[int] = Field(default=None, ge=1)
    primer_nombre: Optional[str] = Field(default=None, min_length=2, max_length=50)
    segundo_nombre: Optional[str] = Field(default=None, max_length=50)
    primer_apellido: Optional[str] = Field(default=None, min_length=2, max_length=50)
    segundo_apellido: Optional[str] = Field(default=None, max_length=50)
    edad: Optional[int] = Field(default=None, ge=0, le=120)
    tipo_sangre: Optional[str] = Field(default=None, max_length=5)
    telefono: Optional[str] = Field(default=None, max_length=20)
    correo: Optional[EmailStr] = None

    @field_validator("tipo_sangre")
    @classmethod
    def tipo_sangre_valido(cls, value: Optional[str]):
        if value is None:
            return value
        if value not in TIPOS_SANGRE_VALIDOS:
            raise ValueError(f"Tipo de sangre invalido. Opciones: {TIPOS_SANGRE_VALIDOS}")
        return value


class PacienteOut(PacienteBase):
    model_config = {"from_attributes": True}


class ConsultorioBase(BaseModel):
    id_medico: int = Field(..., gt=0)
    id_especialidad: int = Field(..., gt=0)


class ConsultorioCreate(ConsultorioBase):
    pass


class ConsultorioUpdate(BaseModel):
    id_medico: Optional[int] = Field(default=None, gt=0)
    id_especialidad: Optional[int] = Field(default=None, gt=0)


class ConsultorioOut(ConsultorioBase):
    id_consultorio: int

    model_config = {"from_attributes": True}


class CitaBase(BaseModel):
    cedula_paciente: str = Field(..., min_length=5, max_length=20)
    id_consultorio: int = Field(..., gt=0)
    id_medico: int = Field(..., gt=0)
    fecha_cita: date
    hora: time
    motivo: Optional[str] = Field(default=None, max_length=500)
    estado: Literal["pendiente", "confirmada", "cancelada", "completada"] = "pendiente"


class CitaCreate(CitaBase):
    pass


class CitaUpdate(BaseModel):
    cedula_paciente: Optional[str] = Field(default=None, min_length=5, max_length=20)
    id_consultorio: Optional[int] = Field(default=None, gt=0)
    id_medico: Optional[int] = Field(default=None, gt=0)
    fecha_cita: Optional[date] = None
    hora: Optional[time] = None
    motivo: Optional[str] = Field(default=None, max_length=500)
    estado: Optional[Literal["pendiente", "confirmada", "cancelada", "completada"]] = None


class CitaOut(CitaBase):
    id_cita: int

    model_config = {"from_attributes": True}