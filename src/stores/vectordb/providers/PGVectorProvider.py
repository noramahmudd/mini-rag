from ..VectorDBInterface import VectorDBInterface
from ..VectorDBEnums import DistanceMethodEnums, VectorDBEnums, PgVectorDistanceMethodEnums, PgVectorIndexTypeEnums, PgVectorTableSchemaEnums
import logging
from typing import List
from models.db_schemes import RetrievedDocument
from sqlalchemy.sql import text as sql_text
import json


class PGVectorProvider(VectorDBInterface):
    def __init__(self, db_client, default_vector_size: int = 786,
                 distance_method: str = None,
                 index_threadhold: int = 100):

        self.db_client = db_client
        self.default_vector_size = default_vector_size
        self.distance_method = distance_method
        self.index_threadhold = index_threadhold

        self.pgvector_table_prefix = PgVectorTableSchemaEnums._PREFIX.value

        self.logger = logging.getLogger("uvicorn")

        self.default_index_name = lambda collection_name: f"{collection_name}_vector_idx"

    async def connect(self):
        async with self.db_client() as session:
            async with session.begin():
                await session.execute(sql_text("CREATE EXTENSION IF NOT EXISTS vector"))
                await session.commit()

    async def disconnect(self):
        pass

    async def is_collection_existed(self, collection_name: str) -> bool:
        record = None
        async with self.db_client() as session:
            async with session.begin():
                list_tbl = sql_text(
                    "SELECT tablename FROM pg_tables WHERE tablename = :collection_name"
                )
                results = await session.execute(list_tbl, {"collection_name": collection_name})
                record = results.scalar_one_or_none()
        return record is not None

    async def list_all_collections(self) -> List:
        records = []
        async with self.db_client() as session:
            async with session.begin():
                list_tbl = sql_text(
                    "SELECT tablename FROM pg_tables WHERE tablename LIKE :prefix"
                )
                results = await session.execute(list_tbl, {"prefix": f"{self.pgvector_table_prefix}%"})
                records = results.scalars().all()
        return records

    async def get_collection_info(self, collection_name: str) -> dict:
        async with self.db_client() as session:
            async with session.begin():
                table_info_sql = sql_text("""
                    SELECT schemaname, tablename, tableowner, tablespace, hasindexes
                    FROM pg_tables
                    WHERE tablename = :collection_name
                """)
                count_sql = sql_text(f'SELECT COUNT(*) FROM "{collection_name}"')

                table_info = await session.execute(table_info_sql, {"collection_name": collection_name})
                record_count = await session.execute(count_sql)

                table_data = table_info.fetchone()
                if not table_data:
                    return None

                return {
                    "table_info": dict(table_data._mapping),
                    "record_count": record_count.scalar_one()
                }

    async def delete_collection(self, collection_name: str):
        async with self.db_client() as session:
            async with session.begin():
                self.logger.info(f"Deleting collection {collection_name} in PGVector")
                # Table names cannot be parameterized — use f-string with quotes for safety
                delete_sql = sql_text(f'DROP TABLE IF EXISTS "{collection_name}"')
                await session.execute(delete_sql)
                await session.commit()
        return True

    async def create_collection(self, collection_name: str, embedding_size: int, do_reset: bool = False):
        if do_reset:
            await self.delete_collection(collection_name=collection_name)

        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)
        if not is_collection_existed:
            self.logger.info(
                f"Creating collection {collection_name} in PGVector with embedding size {embedding_size}"
            )
            # FIX: removed nested db_client session (was double-opening), and removed trailing comma in schema
            async with self.db_client() as session:
                async with session.begin():
                    create_sql = sql_text(f"""
                        CREATE TABLE "{collection_name}" (
                            {PgVectorTableSchemaEnums.ID.value} BIGSERIAL PRIMARY KEY,
                            {PgVectorTableSchemaEnums.TEXT.value} TEXT,
                            {PgVectorTableSchemaEnums.METADATA.value} JSONB DEFAULT '{{}}',
                            {PgVectorTableSchemaEnums.VECTOR.value} VECTOR({embedding_size}),
                            {PgVectorTableSchemaEnums.CHUNK_ID.value} INTEGER
                        )
                    """)
                    await session.execute(create_sql)
                    await session.commit()
            return True
        return False

    async def is_index_existed(self, collection_name: str) -> bool:
        index_name = self.default_index_name(collection_name)
        async with self.db_client() as session:
            async with session.begin():
                index_sql = sql_text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE tablename = :collection_name AND indexname = :index_name"
                )
                results = await session.execute(
                    index_sql, {"collection_name": collection_name, "index_name": index_name}
                )
                return bool(results.scalar_one_or_none())

    async def create_vector_index(self, collection_name: str,
                                  index_type: str = PgVectorIndexTypeEnums.HNSW.value):
        is_index_existed = await self.is_index_existed(collection_name=collection_name)
        if is_index_existed:
            self.logger.info(f"Index already exists for collection {collection_name} in PGVector")
            return False

        async with self.db_client() as session:
            async with session.begin():
                # FIX: table names can't be bind params — use f-string with quotes
                count_sql = sql_text(f'SELECT COUNT(*) FROM "{collection_name}"')
                count_result = await session.execute(count_sql)
                record_count = count_result.scalar_one_or_none()

                if record_count is None or record_count < self.index_threadhold:
                    return False

                self.logger.info(
                    f"Creating vector index for collection {collection_name} "
                    f"in PGVector with index type {index_type}"
                )

                index_name = self.default_index_name(collection_name)
                # FIX: table name interpolated directly (not as bind param), added missing space
                create_index_sql = sql_text(
                    f'CREATE INDEX "{index_name}" ON "{collection_name}" '
                    f'USING {index_type} ({PgVectorTableSchemaEnums.VECTOR.value} {self.distance_method})'
                )
                await session.execute(create_index_sql)

                self.logger.info(f"END: Creating vector index for collection {collection_name} in PGVector")
                return True

    async def reset_vector_index(self, collection_name: str,
                                 index_type: str = PgVectorIndexTypeEnums.HNSW.value):
        index_name = self.default_index_name(collection_name)
        async with self.db_client() as session:
            async with session.begin():
                drop_index_sql = sql_text(f'DROP INDEX IF EXISTS "{index_name}"')
                await session.execute(drop_index_sql)

        return await self.create_vector_index(collection_name=collection_name, index_type=index_type)

    async def insert_one(self, collection_name: str, text: str, vector: list,
                         metadata: dict = None, record_id: str = None):
        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)
        if not is_collection_existed:
            self.logger.error(f"Collection {collection_name} does not exist in PGVector")
            return False

        if not record_id:
            self.logger.error(
                f"Record ID is required for inserting into PGVector collection {collection_name}"
            )
            return False

        async with self.db_client() as session:
            async with session.begin():
                # FIX: table name can't be a bind param — interpolated directly with quotes
                insert_sql = sql_text(
                    f'INSERT INTO "{collection_name}" '
                    f"({PgVectorTableSchemaEnums.TEXT.value}, "
                    f"{PgVectorTableSchemaEnums.METADATA.value}, "
                    f"{PgVectorTableSchemaEnums.VECTOR.value}, "
                    f"{PgVectorTableSchemaEnums.CHUNK_ID.value}) "
                    f"VALUES (:text, :metadata, :vector, :chunk_id)"
                )
                await session.execute(insert_sql, {
                    "text": text,
                    "metadata": json.dumps(metadata),
                    "vector": "[" + ",".join([str(v) for v in vector]) + "]",
                    "chunk_id": record_id
                })
                await session.commit()
        return True

    async def insert_many(self, collection_name: str, texts: list, vectors: list,
                          metadata: list = None, record_ids: list = None, batch_size: int = 50):
        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)
        if not is_collection_existed:
            self.logger.error(f"Collection {collection_name} does not exist in PGVector")
            return False

        if not metadata or len(metadata) == 0:
            metadata = [None] * len(texts)

        # FIX: table name can't be a bind param — interpolated directly with quotes
        batch_insert_sql = sql_text(
            f'INSERT INTO "{collection_name}" '
            f"({PgVectorTableSchemaEnums.TEXT.value}, "
            f"{PgVectorTableSchemaEnums.METADATA.value}, "
            f"{PgVectorTableSchemaEnums.VECTOR.value}, "
            f"{PgVectorTableSchemaEnums.CHUNK_ID.value}) "
            f"VALUES (:text, :metadata, :vector, :chunk_id)"
        )

        async with self.db_client() as session:
            async with session.begin():
                for i in range(0, len(texts), batch_size):
                    batch_texts = texts[i:i + batch_size]
                    batch_vectors = vectors[i:i + batch_size]
                    batch_metadata = metadata[i:i + batch_size]
                    batch_record_ids = record_ids[i:i + batch_size]

                    values = []
                    for _text, _vector, _metadata, _record_id in zip(
                        batch_texts, batch_vectors, batch_metadata, batch_record_ids
                    ):
                        values.append({
                            "text": _text,
                            "metadata": json.dumps(_metadata),
                            "vector": "[" + ",".join([str(v) for v in _vector]) + "]",
                            "chunk_id": _record_id
                        })

                    await session.execute(batch_insert_sql, values)
        return True

    async def search_by_vector(self, collection_name: str, vector: list, limit: int) -> List[RetrievedDocument]:
        is_collection_existed = await self.is_collection_existed(collection_name=collection_name)
        if not is_collection_existed:
            self.logger.error(f"Collection {collection_name} does not exist in PGVector")
            return []

        vector_str = "[" + ",".join([str(v) for v in vector]) + "]"

        async with self.db_client() as session:
            async with session.begin():
                # FIX: sql_text takes ONE string arg; added missing spaces between clauses;
                # table name interpolated directly (not as bind param)
                search_sql = sql_text(
                    f"SELECT {PgVectorTableSchemaEnums.TEXT.value} AS text, "
                    f"1 - ({PgVectorTableSchemaEnums.VECTOR.value} <=> :vector) AS score "
                    f'FROM "{collection_name}" '
                    f"ORDER BY score DESC "
                    f"LIMIT {limit}"
                )

                results = await session.execute(search_sql, {"vector": vector_str})
                records = results.fetchall()

                return [
                    RetrievedDocument(
                        text=record.text,
                        score=record.score
                    )
                    for record in records
                ]