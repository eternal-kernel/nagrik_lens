from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_v1_router
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables are ready on startup
    init_db()
    yield


app = FastAPI(
    title="Nagrik Lens API",
    description=(
        "Neutral, source-linked, multilingual civic-information platform "
        "converting ECI Form 26 affidavits into verified plain-language explanations."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 endpoints
app.include_router(api_v1_router)
