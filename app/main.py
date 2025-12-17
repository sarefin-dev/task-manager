from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.routers import tasks
from app.cache.layer import cache_layer


@asynccontextmanager
async def lifespan(app: FastAPI):
    await cache_layer.init_cache()
    yield


app = FastAPI(
    title="Task Management API",
    description="Simple async task management API with PostgreSQL and SQLModel",
    swagger_ui_parameters={"displayRequestDuration": True},
    version="1.0.0",
)

# Include routers
app.include_router(tasks.router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to Task Management API",
        "docs": "/docs",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
