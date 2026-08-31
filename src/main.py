from fastapi import FastAPI
from routes import base, data, nlp
from helpers.config import get_settings
from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.vectordb.VectorDBProviderFactory import VectorDBProviderFactory
from stores.llm.templates.template_parser import TemplateParser
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from utils.metrics import setup_metrics

app = FastAPI()

setup_metrics(app)

@app.on_event("startup")
async def startup_span():
    settings = get_settings()

    postgres_conn = f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"

    app.db_engine = create_async_engine(postgres_conn)
    app.db_client = sessionmaker(
        app.db_engine,
        expire_on_commit=False,
        class_=AsyncSession
    )

    llm_provider_factory = LLMProviderFactory(settings)
    vectordb_provider_factory = VectorDBProviderFactory(settings, db_client=app.db_client)

    # generation client
    app.generation_client = llm_provider_factory.create(settings.GENERATION_BACKEND)
    app.generation_client.set_generation_model(
        model_id=settings.GENERATION_MODEL_ID
    )

    # embedding client
    app.embedding_client = llm_provider_factory.create(settings.EMBEDDING_BACKEND)
    app.embedding_client.set_embedding_model(
        model_id=settings.EMBEDDING_MODEL_ID,
        embedding_size=settings.EMBEDDING_MODEL_SIZE
    )

    # vector db client
    app.vector_db_client = vectordb_provider_factory.create(settings.VECTOR_DB_BACKEND)
    await app.vector_db_client.connect()

    app.template_parser = TemplateParser(
        language=settings.PRIMARY_LANG,
        default_language=settings.DEFAULT_LANG
    )


@app.on_event("shutdown")
async def shutdown_span():
    await app.db_engine.dispose()
    await app.vector_db_client.disconnect()


app.include_router(base.base_router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)

# from fastapi import FastAPI
# from routes import base, data, nlp
# #from motor.motor_asyncio import AsyncIOMotorClient
# from helpers.config import get_settings
# from stores.llm.LLMProviderFactory import LLMProviderFactory
# from stores.vectordb.VectorDBProviderFactory import VectorDBProviderFactory
# from stores.llm.templates.template_parser import TemplateParser
# from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
# from sqlalchemy.orm import sessionmaker

# app = FastAPI()

# @app.on_event("startup")
# async def startup_span():

#     settings = get_settings()

#     postgres_conn=f"postgresql+asyncpg://{settings.POSTGRES_USERNAME}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_MAIN_DATABASE}"
#     app.db_engine=create_async_engine(postgres_conn)
#     app.db_client=sessionmaker(
#         app.db_engine,
#         expire_on_commit=False,
#         class_=AsyncSession
#     )

#     # MongoDB
#     #app.mongo_conn = AsyncIOMotorClient(settings.MONGODB_URL)
#     #app.db_client = app.mongo_conn[settings.MONGODB_DATABASE]


#     llm_provider_factory = LLMProviderFactory(settings)
#     vectordb_provider_factory = VectorDBProviderFactory(settings)


#     # generation client
#     app.generation_client = llm_provider_factory.create(
#         settings.GENERATION_BACKEND
#     )


#     app.generation_client.set_generation_model(
#         model_id=settings.GENERATION_MODEL_ID
#     )

#     # embedding client
#     app.embedding_client = llm_provider_factory.create(
#         settings.EMBEDDING_BACKEND
#     )

#     await app.embedding_client.connect()

#     app.embedding_client.set_embedding_model(
#         model_id=settings.EMBEDDING_MODEL_ID,
#         embedding_size=settings.EMBEDDING_MODEL_SIZE
#     )

#     # vector db client
#     app.vector_db_client = vectordb_provider_factory.create(
#         settings.VECTOR_DB_BACKEND
#     )
#     await app.vector_db_client.connect()


#     app.template_parser=TemplateParser(language=settings.PRIMARY_LANG,
#                                        default_language=settings.DEFAULT_LANG)


# @app.on_event("shutdown")
# async def shutdown_span():
#     app.db_engine.dispose()
#     await app.vector_db_client.disconnect()

# app.include_router(base.base_router)
# app.include_router(data.data_router)
# app.include_router(nlp.nlp_router)