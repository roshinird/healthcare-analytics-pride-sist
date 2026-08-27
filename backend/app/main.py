from fastapi import FastAPI
from app.routers.patients import router

app = FastAPI()

app.include_router(router)