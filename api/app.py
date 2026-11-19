from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from api.routes import router

app = FastAPI(title="Uy Bor API", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Mini App statik fayllari
static_dir = Path(__file__).parent.parent / "webapp"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="webapp")
