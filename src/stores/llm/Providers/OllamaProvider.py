from ..LLMInterface import LLMInterface
from ..LLMEnums import OllamaEnums
import requests
import logging

class OllamaProvider(LLMInterface):

    def __init__(self, api_url: str = "http://localhost:11434",
                       default_input_max_characters: int = 1000,
                       default_generation_max_output_tokens: int = 1000,
                       default_generation_temperature: float = 0.1):

        self.api_url = api_url

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature

        self.generation_model_id = None

        self.embedding_model_id = None
        self.embedding_size = None

        self.client = requests.Session()

        self.enums=OllamaEnums

        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(self, text: str):
        return text[:self.default_input_max_characters].strip()

    def generate_text(self, prompt: str, chat_history: list = [], max_output_tokens: int = None,
                            temperature: float = None):

        if not self.client:
            self.logger.error("Ollama client was not set")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for Ollama was not set")
            return None

        max_output_tokens = max_output_tokens if max_output_tokens else self.default_generation_max_output_tokens
        temperature = temperature if temperature else self.default_generation_temperature

        chat_history.append(
            self.construct_prompt(prompt=prompt, role=OllamaEnums.USER.value)
        )

        payload = {
            "model": self.generation_model_id,
            "messages": chat_history,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_output_tokens
            }
        }

        try:
            response = self.client.post(
                f"{self.api_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            self.logger.error(f"Error while generating text with Ollama: {e}")
            return None

        if not data or not data.get("message") or not data["message"].get("content"):
            self.logger.error("Error while generating text with Ollama")
            return None

        return data["message"]["content"]

    def embed_text(self, text: str, document_type: str = None):

        if not self.client:
            self.logger.error("Ollama client was not set")
            return None

        if not self.embedding_model_id:
            self.logger.error("Embedding model for Ollama was not set")
            return None

        payload = {
            "model": self.embedding_model_id,
            "input": self.process_text(text)
        }

        try:
            response = self.client.post(
                f"{self.api_url}/api/embed",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            self.logger.error(f"Error while embedding text with Ollama: {e}")
            return None

        if not data or not data.get("embeddings") or len(data["embeddings"]) == 0:
            self.logger.error("Error while embedding text with Ollama")
            return None

        return data["embeddings"][0]

    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "content": prompt
        }