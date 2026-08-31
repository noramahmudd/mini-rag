from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str
    FILE_ALLOWED_TYPES: List[str]
    FILE_MAX_SIZE: int
    FILE_DEFAULT_CHUNK_SIZE: int
    
    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_MAIN_DATABASE: str

    GENERATION_BACKEND: str
    EMBEDDING_BACKEND: str

    OLLAMA_API_URL: str = "http://localhost:11434"

    GENERATION_MODEL_ID: Optional[str] = None
    EMBEDDING_MODEL_ID: Optional[str] = None
    EMBEDDING_MODEL_SIZE: Optional[int] = None
    INPUT_DEFAULT_MAX_CHARACTERS: Optional[int] = None
    GENERATION_DEFAULT_MAX_TOKENS: Optional[int] = None
    GENERATION_DEFAULT_TEMPERATURE: Optional[float] = None

    VECTOR_DB_BACKEND_LITERAL: List[str]
    VECTOR_DB_BACKEND: str
    QDRANT_DB_PATH: str
    QDRANT_DB_DISTANCE_METHOD: str
    VECTOR_DB_PGVEC_INDEX_THREADHOLD: int = 100
    
    PRIMARY_LANG: str = "en"
    DEFAULT_LANG: str = "en"

    model_config = SettingsConfigDict(env_file=str(ENV_PATH))

def get_settings():
    return Settings()


# from pydantic_settings import BaseSettings, SettingsConfigDict
# from typing import List

# class Settings(BaseSettings):
#     APP_NAME: str
#     APP_VERSION: str
#     FILE_ALLOWED_TYPES: List[str]
#     FILE_MAX_SIZE: int
#     FILE_DEFAULT_CHUNK_SIZE: int
    
#     POSTGRES_USERNAME: str
#     POSTGRES_PASSWORD: str
#     POSTGRES_HOST: str
#     POSTGRES_PORT: int
#     POSTGRES_MAIN_DATABASE: str

#     GENERATION_BACKEND: str
#     EMBEDDING_BACKEND: str

#     OLLAMA_API_URL: str = "http://localhost:11434"


#     GENERATION_MODEL_ID: str = None
#     EMBEDDING_MODEL_ID: str = None
#     EMBEDDING_MODEL_SIZE: int = None
#     INPUT_DEFAULT_MAX_CHARACTERS: int = None
#     GENERATION_DEFAULT_MAX_TOKENS: int = None
#     GENERATION_DEFAULT_TEMPERATURE: float = None

#     VECTOR_DB_BACKEND_LITERAL: List[str] = None
#     VECTOR_DB_BACKEND: str
#     QDRANT_DB_PATH: str
#     QDRANT_DB_DISTANCE_METHOD: str
#     VECTOR_DB_PGVEC_INDEX_THREADHOLD: int=100
    
#     PRIMARY_LANG: str = "en"
#     DEFAULT_LANG: str = "en"
#     model_config = SettingsConfigDict(env_file=".env")

# def get_settings():
#     return Settings()