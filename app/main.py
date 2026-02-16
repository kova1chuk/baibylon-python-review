from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.services.nlp_utils import ensure_nltk_data
from app.routers import health, text, enrichment, translation, image


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_nltk_data()
    yield


app = FastAPI(
    title="Vocairo Text Analyzer",
    description="Text analysis API: EPUB, subtitles, plain text, word enrichment, and translation.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(text.router)
app.include_router(enrichment.router)
app.include_router(translation.router)
app.include_router(image.router)


@app.get("/")
async def root():
    return {
        "service": "Vocairo Text Analyzer",
        "version": "2.0.0",
        "docs": "/docs",
    }
