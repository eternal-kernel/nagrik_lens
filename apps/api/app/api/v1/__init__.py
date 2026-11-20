from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.affidavits import router as affidavits_router
from app.api.v1.candidates import router as candidates_router
from app.api.v1.elections import router as elections_router
from app.api.v1.health import router as health_router
from app.api.v1.poster import router as poster_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(health_router)
api_v1_router.include_router(elections_router)
api_v1_router.include_router(candidates_router)
api_v1_router.include_router(affidavits_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(poster_router)
