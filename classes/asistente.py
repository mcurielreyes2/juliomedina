import os
import json
import time
import sys
import io
import logging
from openai import OpenAI
from groundx import GroundX
from dotenv import load_dotenv

from classes.RAG import RAGService
from classes.instruction_parser import InstructionParser

# Cargar variables de entorno desde .env
load_dotenv()

# Optionally keep your stdout re-encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 1) Logging configuration
logging.basicConfig(
    level=logging.INFO,  # or INFO, etc.
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

class Asistente:
    def __init__(self, db):
        """
        Initialize the Asistente class with configurations for OpenAI and GroundX APIs.
        """

        # Initialize RAG service
        self.rag_service = RAGService()

        # Cargar API keys y bucket ID desde variables de entorno
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.groundx_api_key = os.getenv("GROUNDX_API_KEY")
        self.bucket_id_spanish = os.getenv("GROUNDX_BUCKET_ID_SPANISH")
        self.database_url = os.getenv("DATABASE_URL")
        # Load instruction from JSON file


        # If keys are not set in the environment, attempt to load from config.json
        if not self.openai_api_key or not self.groundx_api_key or not self.bucket_id_spanish:
            try:
                with open('config.json') as config_file:
                    config = json.load(config_file)
                    self.openai_api_key = self.openai_api_key or config.get("OPENAI_API_KEY")
                    self.groundx_api_key = self.groundx_api_key or config.get("GROUNDX_API_KEY")
                    self.bucket_id_spanish = self.bucket_id_spanish or config.get("GROUNDX_BUCKET_ID_SPANISH")
                    self.database_url = self.database_url or config.get("DATABASE_URL")
            except FileNotFoundError:
                raise ValueError("Error: No API key or bucket ID found in environment variables or config.json.")

        # Validate that the bucket ID is a valid integer
        if not self.bucket_id_spanish or not str(self.bucket_id_spanish).isdigit():
            raise ValueError("Error: GROUNDX_BUCKET_ID must be a valid integer.")

        # Convert bucket ID to integer
        self.bucket_id_spanish = int(self.bucket_id_spanish)
        #self.bucket_id_english = int(self.bucket_id_english)

        # Set other configurations
        self.completion_model = "gpt-4o-mini"
        instruction_parser = InstructionParser("instructions.json")
        self.instruction = instruction_parser.load_instruction()

        # Initialize GroundX and OpenAI clients
        self.groundx = GroundX(api_key=self.groundx_api_key)
        self.client = OpenAI(api_key=self.openai_api_key)

        # Initialize conversation context
        self.context_history = []

        # Load coffee keywords from external file
        self.coffee_keywords = self.rag_service.load_coffee_keywords("kw.txt")

        # Guardar referencia a la base de datos
        self.db = db


    def chat_completions(self, query: str) -> str:
        system_context = self.rag_service.groundx_search_content(query, query)

        logger.info("\n=== System Context (RAG Retrieval) ===")
        logger.info(system_context.encode('utf-8', errors='replace').decode('utf-8'))
        logger.info("=====================================\n")

        messages = [{"role": "system", "content": f"{self.instruction}\n===\n{system_context}\n==="}]
        for q, a in self.context_history:
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": a})

        messages.append({"role": "user", "content": query})

        logger.info("\n=== Messages Sent to OpenAI API ===")
        for msg in messages:
            role = msg['role']
            content = msg['content'].encode('utf-8', errors='replace').decode('utf-8')
            logger.info(f"Role: {role}, Content: {content}\n")
        logger.info("=====================================\n")

        response = self.client.chat.completions.create(
            model=self.completion_model,
            messages=messages,
            stream=False,
            store=True
        )
        assistant_response = response.choices[0].message.content.strip()

        self.context_history.append((query, assistant_response))
        if len(self.context_history) > 10:
            self.context_history.pop(0)

        return assistant_response

    def chat_completions_stream(self, query: str):
        """
        Similar to chat_completions, but uses stream=True to yield partial chunks.
        """
        # 0) Decide if we should do RAG at all
        if self.rag_service.should_call_groundx(query):
            start_time = time.time()
            logger.info(f"chat_completions_stream called with query='{query}'")

            # # 1) Translate the Spanish query into English
            # query_english = self.rag_service.translate_spanish_to_english(query)
            # logger.info(f"Translated to English => '{query_english}'")

            # 2) Retrieve RAG context from both Spanish & English buckets
            system_context = self.rag_service.groundx_search_content(query_spanish=query)

            after_groundx = time.time()
            logger.info("Received system_context...")
            logger.info(f"groundx_search_content took {after_groundx - start_time:.3f} seconds")

            # For debugging, print context
            logger.info("\n=== System Context (RAG Retrieval) START ===")
            logger.info(system_context.encode('utf-8', errors='replace').decode('utf-8'))
            logger.info("=System Context (RAG Retrieval) END \n")
        else:
            logger.info(f"No RAG called with query='{query}'")
            system_context = (
                "No documents retrieved for this question. "
                "Respond using only your general knowledge."
            )

        after_groundx = time.time()
        # 3) Build the messages array (system + conversation history + user query)
        messages = [{"role": "system", "content": f"{self.instruction}\n===\n{system_context}\n==="}]
        for q, a in self.context_history:
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": a})

        messages.append({"role": "user", "content": query})

        logger.info("\n=== Messages Sent to OpenAI API (Streaming) START ===")
        for msg in messages:
            role = msg['role']
            content = msg['content'].encode('utf-8', errors='replace').decode('utf-8')
            # logger.debug(f"Role: {role}, Content: {content}\n")
        logger.info("=== Messages Sent to OpenAI API (Streaming) END ===\n")

        pre_openai_time = time.time()
        logger.info(f"About to call OpenAI, {pre_openai_time - after_groundx:.3f}s since start")

        # 4) Call the OpenAI API with stream=True
        response = self.client.chat.completions.create(
            model=self.completion_model,
            messages=messages,
            stream=True,
            store=True
        )
        logger.info("Called OpenAI with stream=True")
        after_openai_call_time = time.time()
        logger.info(f"Called OpenAI, waiting for chunks, {after_openai_call_time - pre_openai_time:.3f}s since pre_call")

        # 5) The OpenAI API returns chunks as an iterator; yield partial text
        partial_answer = []
        try:
            for chunk in response:
                choice_delta = chunk.choices[0].delta
                chunk_text = choice_delta.content
                if chunk_text:
                    partial_answer.append(chunk_text)
                    yield chunk_text
        except Exception as e:
            logger.error(f"Streaming error: {e}")

        # 6) Once done, store the final combined answer in context
        final_answer = "".join(partial_answer).strip()
        self.context_history.append((query, final_answer))
        logger.info(f"Final answer length={len(final_answer)}")

        # Optionally limit history length
        if len(self.context_history) > 10:
            self.context_history.pop(0)
