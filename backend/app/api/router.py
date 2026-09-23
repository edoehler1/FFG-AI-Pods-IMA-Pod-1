from fastapi import APIRouter

from app.api.signals import router as signals_router

api_router = APIRouter(prefix="/api")
api_router.include_router(signals_router)
