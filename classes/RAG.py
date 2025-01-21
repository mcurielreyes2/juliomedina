import os
import json
import time
import logging
from groundx import GroundX
from openai import OpenAI

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        # 1) Load environment vars or config (similar to what you had in Asistente)
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.groundx_api_key = os.getenv("GROUNDX_API_KEY")
        self.bucket_id_spanish = os.getenv("GROUNDX_BUCKET_ID_SPANISH")
        #self.bucket_id_english = os.getenv("GROUNDX_BUCKET_ID_ENGLISH")

        if not self.openai_api_key or not self.groundx_api_key \
           or not self.bucket_id_spanish:
            try:
                with open('config.json') as config_file:
                    config = json.load(config_file)
                    self.openai_api_key = self.openai_api_key or config.get("OPENAI_API_KEY")
                    self.groundx_api_key = self.groundx_api_key or config.get("GROUNDX_API_KEY")
                    self.bucket_id_spanish = self.bucket_id_spanish or config.get("GROUNDX_BUCKET_ID_SPANISH")
                    #self.bucket_id_english = self.bucket_id_english or config.get("GROUNDX_BUCKET_ID_ENGLISH")
            except FileNotFoundError:
                raise ValueError("No API key or bucket ID found in environment variables or config.json.")

        if not self.bucket_id_spanish or not str(self.bucket_id_spanish).isdigit():
            raise ValueError("Error: GROUNDX_BUCKET_ID_SPANISH must be a valid integer.")

        # Convert to integer
        self.bucket_id_spanish = int(self.bucket_id_spanish)
        #self.bucket_id_english = int(self.bucket_id_english)

        # 2) Initialize GroundX
        self.groundx = GroundX(api_key=self.groundx_api_key)

        # 3) Store an OpenAI client if you want classification & translation
        self.client = OpenAI(api_key=self.openai_api_key)

        # 4) Load coffee keywords
        self.coffee_keywords = self.load_coffee_keywords("kw.txt")

    def load_coffee_keywords(self, filename: str):

        # Get the root directory of the project
        project_root = os.path.dirname(os.path.abspath(__file__))  # Path to this script
        project_root = os.path.join(project_root, "..")  # Go one level up to the root
        file_path = os.path.join(project_root, filename)

        keywords = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Ignore empty lines or comment lines
                    if not line or line.startswith("#"):
                        continue
                    keywords.append(line.lower())
        except FileNotFoundError:
            logger.warning(f"Could not find {filename}, defaulting to empty keyword list.")
        return keywords

    def should_call_groundx(self, query: str) -> bool:
        """
        Checks if the query has infectologia-related keywords or if a separate classification
        says it's about infectologia above a probability threshold.
        """
        # 1) Keyword Check
        lower_query = query.lower()
        for kw in self.coffee_keywords:
            if kw in lower_query:
                logger.info(f"Found keyword '{kw}' => definitely about infectologia.")
                return True

        # 2) If no keywords found, fallback to probability-based classification:
        classification_prompt = f"""
            Eres un clasificador de textos sencillo.
            Dada la consulta del usuario, estima la probabilidad (0-100) de que la consulta sea sobre infectologia o cualquier disciplina o tematica relacionada con la infectologia 
            Devuelve SOLO un número del 0 al 100 (un entero). Sin texto adicional.

            User query: {query}
        """
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a short text classifier."},
                {"role": "user", "content": classification_prompt}
            ],
            temperature=0
        )
        result_text = response.choices[0].message.content.strip()

        try:
            probability = float(result_text)
        except ValueError:
            logger.info(f"Unexpected classification response: '{result_text}'. Defaulting to 50.")
            probability = 50.0

        threshold = 50
        logger.info(f"Infectologia probability: {probability}% (threshold={threshold})")
        return probability >= threshold

    def groundx_search_content(self, query_spanish: str, query_english:str) -> str:
        """
        Perform two GroundX searches: one in the Spanish bucket using the
        Spanish query, and one in the English bucket using the English query.
        Combine and return both sets of text.
        """
        t0 = time.time()

        # 1) Search Spanish bucket
        content_response_es = self.groundx.search.content(
            id=self.bucket_id_spanish,
            n=10,
            query=query_spanish
        )
        results_es = content_response_es.search
        text_es = results_es.text if results_es.text else ""

        # # 2) Search English bucket
        content_response_en = self.groundx.search.content(
             id=self.bucket_id_spanish,
             n=10,
             query=query_english
         )
        results_en = content_response_en.search
        text_en = results_en.text if results_en.text else ""

        t1 = time.time()
        logger.info(f"groundx_search_content took {t1 - t0:.3f}s")

        # Combine both texts (Spanish + English)
        combined_text = f"{text_es}\n{text_en}".strip()
        if not combined_text:
            raise ValueError("No context found in either Spanish or English search.")

        return combined_text

    def translate_spanish_to_english(self, text: str) -> str:
        translation_prompt = f"""
            Translate the following text from Spanish to English. 
            Output only the translated text, nothing else.

            Text to translate:
            {text}
        """

        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a translator. You translate Spanish text into English."},
                {"role": "user", "content": translation_prompt}
            ],
            temperature=0,
            max_tokens=1000
        )
        english_translation = response.choices[0].message.content.strip()
        return english_translation