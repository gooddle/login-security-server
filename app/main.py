from fastapi import FastAPI

from app.api.routes import auth
from app.core.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Login Security Server")
app.include_router(auth.router)
