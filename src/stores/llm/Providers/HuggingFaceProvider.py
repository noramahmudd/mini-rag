from ..LLMInterface import LLMInterface
from ..LLMEnums import HuggingFaceEnums, DocumentTypeEnum
from sentence_transformers import SentenceTransformer
import logging
from typing import List,Union

class HuggingFaceProvider(LLMInterface):

    def __init__(self, default_input_max_characters: int = 1000,
                       default_generation_max_output_tokens: int = 1000,
                       default_generation_temperature: float = 0.1):

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature

        self.generation_model_id = None

        self.embedding_model_id = None
        self.embedding_size = None

        self._embedding_client = None  # lazy-loaded SentenceTransformer
        self.enums=HuggingFaceEnums

        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: str):
        # HuggingFace provider is primarily used for embeddings in RAG;
        # generation is delegated to OllamaProvider
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size
        self._embedding_client = SentenceTransformer(model_id)

    def process_text(self, text: str):
        return text[:self.default_input_max_characters].strip()

    def generate_text(self, prompt: str, chat_history: list = [], max_output_tokens: int = None,
                            temperature: float = None):
        # Not implemented for HuggingFace embedding-only provider
        self.logger.error("generate_text is not supported by HuggingFaceProvider; use OllamaProvider for generation")
        return None
    def embed_text(self, text: Union[str, List[str]], document_type: str = None):

        if not self._embedding_client:
            self.logger.error("Embedding model for HuggingFace was not set")
            return None

        try:
            # FIX: handle list vs single string separately
            if isinstance(text, list):
                processed = [self.process_text(t) for t in text]
            else:
                processed = self.process_text(text)

            embeddings = self._embedding_client.encode(
                processed,
                normalize_embeddings=True
            )
        except Exception as e:
            self.logger.error(f"Error while embedding text with HuggingFace: {e}")
            return None

        if embeddings is None or len(embeddings) == 0:
            self.logger.error("Error while embedding text with HuggingFace")
            return None

        # FIX: for a list input, encode() returns a 2D array → list of lists (one per chunk)
        # for a single string, encode() returns a 1D array → flat list
        if isinstance(text, list):
            return embeddings.tolist()   # shape: [[...], [...], ...] ✓
        else:
            return embeddings.tolist()   # shape: [...] ✓ (flat, for search_by_vector)
    # def embed_text(self, text: Union[str, List[str]], document_type: str = None):

    #     if not self._embedding_client:
    #         self.logger.error("Embedding model for HuggingFace was not set")
    #         return None
        

    #     try:
    #         embedding = self._embedding_client.encode(
    #             self.process_text(text),
    #             normalize_embeddings=True
    #         )
    #     except Exception as e:
    #         self.logger.error(f"Error while embedding text with HuggingFace: {e}")
    #         return None

    #     if embedding is None or len(embedding) == 0:
    #         self.logger.error("Error while embedding text with HuggingFace")
    #         return None

    #     return embedding.tolist()

    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "content": prompt
        }