# from .BaseController import BaseController
# from models.db_schemes import Project,DataChunk
# from stores.llm.LLMEnums import DocumentTypeEnum
# from typing import List
# import json

# class NLPController(BaseController):
#     def __init__(self,vector_db_client,
#                       embedding_client,
#                       generation_client,
#                       template_parser):
#         super().__init__()

#         self.vector_db_client=vector_db_client
#         self.embedding_client=embedding_client
#         self.generation_client=generation_client
#         self.template_parser=template_parser


#     def create_collection_name(self,project_id:str):
#         return f"collection_{project_id}".strip()
    
#     async def reset_vector_db_collection(self,project:Project):
#         collection_name=await self.create_collection_name(project_id=project.project_id)
#         return self.vector_db_client.delete_collection(collection_name=collection_name)
    
#     async def get_vector_db_collection_info(self,project:Project):
#         collection_name=await self.create_collection_name(project_id=project.project_id)
#         collection_info=self.vector_db_client.get_collection_info(collection_name=collection_name)

#         return json.loads(
#             json.dumps(collection_info,default=lambda x:x.__dict__)
#         )
    
#     async def index_into_vector_db(self,project:Project,chunks:List[DataChunk],chunks_ids:List[int],do_reset:bool=False):

#         collection_name=self.create_collection_name(project_id=project.project_id)

#         texts=[c.chunk_text for c in chunks] 
#         metadata=[c.chunk_metadata for c in chunks]
#         vectors=self.embedding_client.embed_text(text=texts,
#                                             document_type=DocumentTypeEnum.DOCUMENT.value)
            
       
        
        
#         _=await self.vector_db_client.create_collection(
#             collection_name=collection_name,
#             embedding_size=self.embedding_client.embedding_size,
#             do_reset=do_reset,
#             )

#         _=await self.vector_db_client.insert_many(collection_name=collection_name,
#                                               texts=texts,
#                                               metadata=metadata,
#                                               vectors=vectors,
#                                               record_ids=chunks_ids)
        
#         return True
    
#     async def search_vector_db_collection(self,project:Project,text:str,limit:int=5):

#         collection_name=await self.create_collection_name(project_id=project.project_id)

#         vector=self.embedding_client.embed_text(text=text,
#                                             document_type=DocumentTypeEnum.QUERY.value)
#         if not vector or len(vector)==0:
#             return False
            

#         results=await self.vector_db_client.search_by_vector(collection_name=collection_name,
#                                                     vector=vector,
#                                                     limit=limit)
#         if not results:
#             return False
        
#         return results
    
#     async def answer_rag_questions(self,project:Project,query:str,limit:int=10):

#         answer,full_prompt,chat_history=None,None,None
#         #retrieve relevant documents from vector db
#         retrieved_documents=await self.search_vector_db_collection(project=project,
#                                                              text=query,
#                                                              limit=limit)
        
#         if not retrieved_documents or len(retrieved_documents)==0:
#             return answer,full_prompt,chat_history
        
#         #construct prompt for generation
#         system_prompt=self.template_parser.get("rag","system_prompt")


#         document_prompts="\n".join([
#             self.template_parser.get("rag","document_prompt",{
#                 "doc_no": idx+1,
#                 "chunk_text": self.generation_client.process_text(doc.text)
#             })
#             for idx, doc in enumerate(retrieved_documents)
#         ])

#         footer_prompt=self.template_parser.get("rag","footer_prompt",{
#             "query":query
#         })

#         chat_history=[
#             self.generation_client.construct_prompt(
#                 prompt=system_prompt,
#                 role=self.generation_client.enums.SYSTEM.value),
#         ]

#         full_prompt="\n\n".join([document_prompts,footer_prompt])

#         answer=self.generation_client.generate_text(
#             prompt=full_prompt,
#             chat_history=chat_history
#         )

#         return answer,full_prompt,chat_history
import logging

from .BaseController import BaseController
from models.db_schemes import Project, DataChunk
from stores.llm.LLMEnums import DocumentTypeEnum
from typing import List
import json



logger = logging.getLogger('uvicorn.error')

class NLPController(BaseController):
    def __init__(self, vector_db_client,
                       embedding_client,
                       generation_client,
                       template_parser):
        super().__init__()

        self.vector_db_client = vector_db_client
        self.embedding_client = embedding_client
        self.generation_client = generation_client
        self.template_parser = template_parser

    # FIX: removed async — this is a plain string operation, not a coroutine
    def create_collection_name(self, project_id: str):
        return f"collection_{project_id}".strip()

    async def reset_vector_db_collection(self, project: Project):
        collection_name = self.create_collection_name(project_id=project.project_id)  # FIX: removed await
        return await self.vector_db_client.delete_collection(collection_name=collection_name)  # FIX: added await

    async def get_vector_db_collection_info(self, project: Project):
        collection_name = self.create_collection_name(project_id=project.project_id)  # FIX: removed await
        collection_info = await self.vector_db_client.get_collection_info(collection_name=collection_name)  # FIX: added await

        return json.loads(
            json.dumps(collection_info, default=lambda x: x.__dict__)
        )

    async def index_into_vector_db(self, project: Project, chunks: List[DataChunk],
                                   chunks_ids: List[int], do_reset: bool = False):

        collection_name = self.create_collection_name(project_id=project.project_id)

        texts = [c.chunk_text for c in chunks]
        metadata = [c.chunk_metadata for c in chunks]

        # FIX: added await — embed_text is async; without it vectors is a coroutine, not a list
        vectors =self.embedding_client.embed_text(
            text=texts,
            document_type=DocumentTypeEnum.DOCUMENT.value
        )

        # if not vectors:
        #     self.logger.error("Embedding returned None or empty — aborting index")
        #     return False

        _ = await self.vector_db_client.create_collection(
            collection_name=collection_name,
            embedding_size=self.embedding_client.embedding_size,
            do_reset=do_reset,
        )

        _ = await self.vector_db_client.insert_many(
            collection_name=collection_name,
            texts=texts,
            metadata=metadata,
            vectors=vectors,
            record_ids=chunks_ids
        )

        return True

    async def search_vector_db_collection(self, project: Project, text: str, limit: int = 5):

        collection_name = self.create_collection_name(project_id=project.project_id)  # FIX: removed await

        # FIX: added await — same async issue as embed_text in index_into_vector_db
        vector =self.embedding_client.embed_text(
            text=text,
            document_type=DocumentTypeEnum.QUERY.value
        )

        if not vector or len(vector) == 0:
            return False

        results = await self.vector_db_client.search_by_vector(
            collection_name=collection_name,
            vector=vector,
            limit=limit
        )

        if not results:
            return False

        return results

    async def answer_rag_questions(self, project: Project, query: str, limit: int = 10):

        answer, full_prompt, chat_history = None, None, None

        retrieved_documents = await self.search_vector_db_collection(
            project=project,
            text=query,
            limit=limit
        )

        if not retrieved_documents or len(retrieved_documents) == 0:
            return answer, full_prompt, chat_history

        system_prompt = self.template_parser.get("rag", "system_prompt")

        document_prompts = "\n".join([
            self.template_parser.get("rag", "document_prompt", {
                "doc_no": idx + 1,
                "chunk_text": self.generation_client.process_text(doc.text)
            })
            for idx, doc in enumerate(retrieved_documents)
        ])

        footer_prompt = self.template_parser.get("rag", "footer_prompt", {
            "query": query
        })

        chat_history = [
            self.generation_client.construct_prompt(
                prompt=system_prompt,
                role=self.generation_client.enums.SYSTEM.value
            ),
        ]

        full_prompt = "\n\n".join([document_prompts, footer_prompt])

        answer = self.generation_client.generate_text(
            prompt=full_prompt,
            chat_history=chat_history
        )

        return answer, full_prompt, chat_history