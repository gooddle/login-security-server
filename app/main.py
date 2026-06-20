from collections.abc import AsyncGenerator
from typing import Any

import strawberry
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from app.core.database import Base, SessionLocal, engine
from app.graphql.mutations import Mutation
from app.graphql.types import Query

Base.metadata.create_all(bind=engine)


async def get_context(request: Request) -> AsyncGenerator[dict[str, Any], None]:
    db = SessionLocal()
    try:
        yield {"db": db, "request": request}
    finally:
        db.close()


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_router = GraphQLRouter(schema, context_getter=get_context)

app = FastAPI(title="Login Security Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(graphql_router, prefix="/graphql")
