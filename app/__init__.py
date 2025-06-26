from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .utils.core import scan, ensure_user, FILES_DIR
from .api import files


def create_app() -> FastAPI:
    scan()
    ensure_user()

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(files.router, prefix="/api")

    app.mount("/files", StaticFiles(directory=FILES_DIR), name="files")
    app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

    return app
