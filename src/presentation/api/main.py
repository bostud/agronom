from __future__ import annotations

from fastapi import APIRouter, FastAPI

from src.presentation.api.field_router import router as field_router

app = FastAPI(title="Agronom API", openapi_url="/api/openapi.json", docs_url="/api/docs")

api_router = APIRouter(prefix="/api")
api_router.include_router(field_router)

app.include_router(api_router)
