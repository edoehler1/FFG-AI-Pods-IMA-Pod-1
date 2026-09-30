from fastapi import APIRouter

from app.api.signals import router as signals_router
from app.api.companies import router as companies_router
from app.api.contacts import router as contacts_router
from app.api.engagements import router as engagements_router
from app.api.upload import router as upload_router
from app.api.reports import router as reports_router
from app.api.profiles import router as profiles_router
from app.api.enrichments import router as enrichments_router
from app.api.relationships import router as relationships_router
from app.api.dashboard import router as dashboard_router
from app.api.outreach import router as outreach_router
from app.api.taxonomy import router as taxonomy_router
from app.api.benchmarks import router as benchmarks_router
from app.api.industries import router as industries_router

api_router = APIRouter(prefix="/api")
api_router.include_router(signals_router)
api_router.include_router(companies_router)
api_router.include_router(contacts_router)
api_router.include_router(engagements_router)
api_router.include_router(upload_router)
api_router.include_router(reports_router)
api_router.include_router(profiles_router)
api_router.include_router(enrichments_router)
api_router.include_router(relationships_router)
api_router.include_router(dashboard_router)
api_router.include_router(outreach_router)
api_router.include_router(taxonomy_router)
api_router.include_router(benchmarks_router)
api_router.include_router(industries_router)
