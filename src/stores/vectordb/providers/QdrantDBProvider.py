from ..VectorDBInterface import VectorDBInterface
from ..VectorDBEnums import DistanceMethodEnums, VectorDBEnums
from qdrant_client import QdrantClient,models
import logging
from typing import List
from models.db_schemes import RetrievedDocument

class QdrantDBProvider(VectorDBInterface):
    def __init__(self,db_client:str,
                 default_vector_size:int=786,
                 distance_method:str=None,
                 index_threadhold:int=100):
        
        self.client=None
        self.db_client=db_client
        self.distance_method=distance_method
        self.default_vector_size=default_vector_size

        if distance_method== DistanceMethodEnums.COSINE.value:
            self.distance_method=models.Distance.COSINE
        
        elif distance_method== DistanceMethodEnums.DOT.value:
            self.distance_method=models.Distance.DOT

        self.logger=logging.getLogger('uvicorn')

    async def connect(self):
        self.client=QdrantClient(path=self.db_client)

    async def disconnect(self):
        self.client=None

    async def is_collection_existed(self,collection_name:str)->bool:
        return self.client.collection_exists(collection_name)
        
    async def list_all_collections(self)->List:
        return self.client.get_collections()
        
    def get_collection_info(self,collection_name:str)->dict:
        return self.client.get_collection(collection_name)
        
    async def delete_collection(self,collection_name:str):
        if self.is_collection_existed(collection_name):
            self.client.delete_collection(collection_name)

    async def create_collection(self,collection_name:str,
                            embedding_size:int,
                            do_reset:bool=False):
        if do_reset:
            self.delete_collection(collection_name=collection_name)

        if not self.is_collection_existed(collection_name):
            self.logger.info(f"Creating new collection {collection_name} in QdrantDB")

            self.client.recreate_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=embedding_size,
                    distance=self.distance_method
                    )
                )      
            return True
        return False
        
    async def insert_one(self,collection_name:str,text:str,
                    vector:list,metadata:dict=None,
                    record_id:str=None):
            
        if not self.is_collection_existed(collection_name):
            self.logger.error(f"Collection {collection_name} does not exist in QdrantDB")
            return False
        try:
            self.client.upload_records(
                collection_name=collection_name,
                records=[
                    models.Record(
                        id=record_id,
                        vector=vector,
                        payload={"text":text,"metadata":metadata}
                    )
                ])
        except Exception as e:
            self.logger.error(f"Error while inserting record into QdrantDB: {e}")
            return False
            
        return True
        
    async def insert_many(self,collection_name:str,texts:str,
                    vectors:list,metadatas:dict=None,
                    record_ids:str=None,
                    batch_size:int=50):
            
        if metadatas is None:
            metadatas=[None]*len(texts)

        if record_ids is None:
            record_ids=list(range(0,len(texts)))

        for i in range(0,len(texts),batch_size):
            batch_end=i+batch_size
            batch_texts=texts[i:batch_end]
            batch_vectors=vectors[i:batch_end]  
            batch_metadatas=metadatas[i:batch_end]
            batch_record_ids=record_ids[i:batch_end]

            batch_records=[
                models.Record(
                    id=batch_record_ids[x],
                    vector=batch_vectors[x],
                    payload={"text":batch_texts[x],
                                "metadata":batch_metadatas[x]}
                )
                    for x in range(len(batch_texts))
            ]
            try:
                self.client.upload_records(
                    collection_name=collection_name,
                    records=batch_records
                )
            except Exception as e:
                self.logger.error(f"Error while inserting batch records into QdrantDB: {e}")
                return False
                
        return True
         
    async def search_by_vector(self,collection_name:str,vector:list,limit:int):
        results=self.client.search(collection_name=collection_name,
                                    query_vector=vector,
                                    limit=limit)
        
        if not results or len(results)==0:
            return None
        
        return [
            RetrievedDocument(**{
                "text": result.payload["text"],
                "score": result.score
            })
            for result in results
        ]