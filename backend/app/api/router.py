from fastapi import APIRouter

from app.api.signals import router as signals_router
from app.api.companies import router as companies_router
from app.api.contacts import router as contacts_router
from app.api.engagements import router as engagements_router
from app.api.upload import router as upload_router
from app.api.reports import router as reports_router

api_router = APIRouter(prefix="/api")
api_router.include_router(signals_router)
api_router.include_router(companies_router)
api_router.include_router(contacts_router)
api_router.include_router(engagements_router)
api_router.include_router(upload_router)
api_router.include_router(reports_router)
