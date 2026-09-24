from __future__ import annotations

from fastapi import FastAPI

from src.presentation.api.field_router import router as field_router

app = FastAPI(title="Agronom")
app.include_router(field_router, prefix="/api")
