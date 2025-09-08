from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .core.logging import setup_logging, logger
from .api.routers.search import router as search_router


def create_app() -> FastAPI:
    setup_logging("INFO")
    app = FastAPI(
        title="People DeepSearch AI",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    async def healthz():
        logger.info({"event": "healthz"})
        return {"status": "ok"}

    app.include_router(search_router, prefix="/search", tags=["search"])
    return app


app = create_app()

