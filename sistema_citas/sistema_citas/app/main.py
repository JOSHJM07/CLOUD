import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database.connection import Base, engine
from app.database.seeds import run_startup_seed
from app.routes import (
    cita_router,
    consultorio_router,
    especialidad_router,
    medico_router,
    paciente_router,
)

app = FastAPI(
    title="Sistema de Gestion de Citas",
    description="API REST para gestionar citas medicas",
    version="1.1.0",
)

logger = logging.getLogger("uvicorn.error")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    # Crea tablas en entorno academico para simplificar el arranque.
    Base.metadata.create_all(bind=engine)
    summary = run_startup_seed()
    logger.info("Startup seed summary: %s", summary)


STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(especialidad_router)
app.include_router(medico_router)
app.include_router(paciente_router)
app.include_router(consultorio_router)
app.include_router(cita_router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(STATIC_DIR / "index.html")
