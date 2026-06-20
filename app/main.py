import strawberry
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from app.core.database import Base, engine, SessionLocal
from app.graphql.mutations import Mutation
from app.graphql.types import Query

Base.metadata.create_all(bind=engine)


async def get_context(request=None):
    db = SessionLocal()
    try:
        yield {"db": db, "request": request}
    finally:
        db.close()


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_router = GraphQLRouter(schema, context_getter=get_context)

app = FastAPI(title="Login Security Server")
app.include_router(graphql_router, prefix="/graphql")
