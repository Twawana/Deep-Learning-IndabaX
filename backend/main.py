from fastapi import FastAPI

from routes.recommendation import router as recommendation_router

app = FastAPI()

app.include_router(recommendation_router)