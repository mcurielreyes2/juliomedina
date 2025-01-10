import os
import json
from flask import Flask, request, jsonify, render_template, Response, stream_with_context
from openai import OpenAI
from groundx import GroundX
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

class Asistente:
    def __init__(self):
        """
        Initialize the Asistente class with configurations for OpenAI and GroundX APIs.
        """
        # Load API keys and bucket ID from environment variables
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.groundx_api_key = os.getenv("GROUNDX_API_KEY")
        self.bucket_id_spanish = os.getenv("GROUNDX_BUCKET_ID_SPANISH")
        self.bucket_id_english = os.getenv("GROUNDX_BUCKET_ID_ENGLISH")

        # If keys are not set in the environment, attempt to load from config.json
        if not self.openai_api_key or not self.groundx_api_key or not self.bucket_id_spanish or not self.bucket_id_english:
            try:
                with open('config.json') as config_file:
                    config = json.load(config_file)
                    self.openai_api_key = self.openai_api_key or config.get("OPENAI_API_KEY")
                    self.groundx_api_key = self.groundx_api_key or config.get("GROUNDX_API_KEY")
                    self.bucket_id_spanish = self.bucket_id_spanish or config.get("GROUNDX_BUCKET_ID_SPANISH")
                    self.bucket_id_english = self.bucket_id_english or config.get("GROUNDX_BUCKET_ID_ENGLISH")
            except FileNotFoundError:
                raise ValueError("Error: No API key or bucket ID found in environment variables or config.json.")

        # Validate that the bucket ID is a valid integer
        if not self.bucket_id_spanish or not str(self.bucket_id_spanish).isdigit():
            raise ValueError("Error: GROUNDX_BUCKET_ID must be a valid integer.")

        # Convert bucket ID to integer
        self.bucket_id_spanish = int(self.bucket_id_spanish)
        self.bucket_id_english = int(self.bucket_id_english)

        # Set other configurations
        self.completion_model = "gpt-4o-mini"
        self.instruction = (
            "Eres un asistente especializado en café y en los procesos de producción del café."
            "Tu objetivo principal es utilizar los documentos proporcionados relacionados con el café como la base de conocimiento principal para responder a las consultas de los usuarios."
            "Estos documentos abarcan la clasificación del café, los procesos de tostado, la medición del contenido de humedad, las composiciones químicas y la evolución de las especies de café."
            "\n\n"
            "Resúmenes de Documentos:"
            "\n- **Green Coffee Classification**: Detalla los estándares de clasificación y defectos para granos de café Arábica verde, incluyendo el contenido de humedad y características visuales."
            "\n- **Measuring Moisture Content**: Explica métodos como el secado en horno y medidores electrónicos para evaluar los niveles de humedad de los granos de café y mantener su calidad."
            "\n- **Rate of Rise in Roasting**: Destaca la importancia de monitorear los cambios de temperatura de los granos durante el tostado para garantizar una calidad constante."
            "\n- **Chemical Composition of Roasts**: Discute cómo los tiempos y temperaturas de tostado afectan la composición química, el sabor y el aroma del café."
            "\n- **Roasting as Art and Science**: Explora los cambios físicos y químicos durante el tostado, enfatizando la interacción entre el calor y el tiempo."
            "\n- **Coffee Tree Family Chart**: Representación visual de la evolución de las especies de café, incluyendo Arábica, Robusta y Liberica."
            "\n\n"
            "Cómo Responder:"
            "\n- Responde preguntas específicas sobre tostado, clasificación y calidad del café utilizando las referencias detalladas de los documentos proporcionados."
            "\n- Para preguntas generales relacionadas con el café que no estén cubiertas en los documentos, proporciona respuestas basadas en tu conocimiento general, priorizando siempre el contenido de referencia proporcionado."
            "\n\n"
            "Priorización:"
            "\n- Siempre cita las referencias de los documentos para las respuestas basadas en estos." "Si el documento tiene un título en inglés, utiliza el TÍTULO COMPLETO o NOMBRE COMPLETO en inglés."
            "\n- Redirige las consultas no relacionadas con el café o que no sean relevantes a investigación externa o recursos de conocimiento general."
            "\n\n"
            "Ejemplos de Citas:"
            "\n- 'Según el documento **Green Coffee Classification** (página 1)...'"
            "\n- 'La sección sobre perfiles de tostado (**RoR**, página 3) indica...'"
            "\n\n"
            "Si la información solicitada no se encuentra en los documentos proporcionados, amablemente pide disculpas al usuario y sugiérele que contacte a Martín Garmendia de MCT (mgarmendia@mct-esco.com)."
            "No compartas enlaces externos en tus respuestas."
        )

        # Initialize GroundX and OpenAI clients
        self.groundx = GroundX(api_key=self.groundx_api_key)
        self.client = OpenAI(api_key=self.openai_api_key)

        # Initialize conversation context
        self.context_history = []

        #Load coffee keywords from external file
        self.coffee_keywords = self.load_coffee_keywords("kw_cafe.txt")

    def load_coffee_keywords(self, filename: str):
        # Resolve file path relative to this Python script or however you prefer
        file_path = os.path.join(os.path.dirname(__file__), filename)

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
            print(f"WARNING: Could not find {filename}, defaulting to empty keyword list.")
        return keywords
    def groundx_search_content(self, query_spanish: str, query_english: str) -> str:
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

        # 2) Search English bucket
        content_response_en = self.groundx.search.content(
            id=self.bucket_id_english,
            n=10,
            query=query_english
        )
        results_en = content_response_en.search
        text_en = results_en.text if results_en.text else ""

        t1 = time.time()
        print(f"[DEBUG] groundx_search_content took {t1 - t0:.3f}s", flush=True)

        # Combine both texts (Spanish + English)
        combined_text = f"{text_es}\n{text_en}".strip()
        if not combined_text:
            raise ValueError("No context found in either Spanish or English search.")

        return combined_text

    def should_call_groundx(self, query: str) -> bool:
        """
        Checks if the query has coffee-related keywords or if a separate classification
        says it's about coffee above a probability threshold.
        """
        # 1) Keyword Check
        lower_query = query.lower()
        for kw in self.coffee_keywords:
            if kw in lower_query:
                print(f"[DEBUG] Found keyword '{kw}' => definitely about coffee.")
                return True

        # 2) If no keywords found, fallback to probability-based classification:
        classification_prompt = f"""
            Eres un clasificador de textos sencillo.
            Dada la consulta del usuario, estima la probabilidad (0-100) de que la consulta sea sobre cafe y cualquier disciplina o tematica relacionada con el cafe
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
            print(f"WARNING: Unexpected classification response: '{result_text}'. Defaulting to 50.")
            probability = 50.0

        threshold = 50  # or 60, 70, etc.
        print(f"[DEBUG] Coffee probability: {probability}% (threshold={threshold})")
        return probability >= threshold

    # def should_call_groundx(self, query: str) -> bool:
    #     """
    #     Uses a quick classification call to OpenAI to decide if the query is about coffee.
    #     Returns True if we should call groundx.search.content(), otherwise False.
    #     """
    #     classification_prompt = f"""
    #         Responde ÚNICAMENTE con "Sí" o "No".
    #         "Eres un asistente especializado en cafe y en los procesos de producción de cafe."
    #         Tienes que responder cualquier pregunta relacionada con cafe
    #
    #         Ejemplos de "Sí":
    #         1) "¿Cómo impacta la humedad relativa en el tostado del cafe?"
    #         2) "¿Podrías describir la relación entre humedad y temperatura para el café?"
    #         3) "¿Podrías describir la composición quimica de distintos tipos de Cafe como el Arabica y Robusta? Que contenido en % de lipidos?"
    #
    #         Ejemplos de "No":
    #         1) "¿Cuál es la mejor forma de preparar un pastel de chocolate?"
    #         2) "¿Qué libros recomiendas para aprender francés?"
    #
    #         "No" si no se menciona nada dentro de este contexto.
    #
    #     Query: {query}
    #     """
    #     # Call the OpenAI ChatCompletion to classify the query
    #     response = self.client.chat.completions.create(
    #         model="gpt-3.5-turbo",
    #         messages=[
    #             {"role": "system", "content": "You are a short text classifier."},
    #             {"role": "user", "content": classification_prompt}
    #         ],
    #         temperature=0  # Keep it deterministic
    #     )
    #
    #     # Get the model's classification response
    #     result_text = response.choices[0].message.content.strip()
    #
    #     # Return True/False based on the response
    #     if result_text == "Sí":
    #         return True
    #     elif result_text == "No":
    #         return False
    #     else:
    #         # In case the model returns something else unexpectedly, default to True or handle separately
    #         print(f"WARNING: Unexpected classification response: '{result_text}'")
    #         return True

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

    def chat_completions(self, query: str) -> str:
        system_context = self.groundx_search_content(query)

        print("\n=== System Context (RAG Retrieval) ===")
        print(system_context.encode('utf-8', errors='replace').decode('utf-8'))
        print("=====================================\n")

        messages = [{"role": "system", "content": f"{self.instruction}\n===\n{system_context}\n==="}]
        for q, a in self.context_history:
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": a})

        messages.append({"role": "user", "content": query})

        print("\n=== Messages Sent to OpenAI API ===")
        for msg in messages:
            role = msg['role']
            content = msg['content'].encode('utf-8', errors='replace').decode('utf-8')
            print(f"Role: {role}, Content: {content}\n")
        print("=====================================\n")

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
        if self.should_call_groundx(query):

            start_time = time.time()
            # 0) Retrieve RAG context
            print(f"DEBUG: chat_completions_stream called with query='{query}'", flush=True)

            # 1) Translate the Spanish query into English
            query_english = self.translate_spanish_to_english(query)
            print(f"DEBUG: Translated to English => '{query_english}'", flush=True)

            # 2) Retrieve RAG context from both Spanish & English buckets
            system_context = self.groundx_search_content(query_spanish=query, query_english=query_english)

            after_groundx = time.time()
            print("DEBUG: Received system_context...", flush=True)
            print(f"[DEBUG] groundx_search_content took {after_groundx - start_time:.3f} seconds")

            # For debugging, print context
            print("\n=== System Context (RAG Retrieval) ===", flush=True)
            print(system_context.encode('utf-8', errors='replace').decode('utf-8'))
            print("=====================================\n", flush=True)
        else:
            print(f"DEBUG: No RAG called with query='{query}'", flush=True)
            system_context = (
                "No coffee documents retrieved for this question. "
                "Respond using only your general knowledge.")
        after_groundx = time.time()
        # 3) Build the messages array (system + conversation history + user query)
        messages = [{"role": "system", "content": f"{self.instruction}\n===\n{system_context}\n==="}]
        for q, a in self.context_history:
            messages.append({"role": "user", "content": q})
            messages.append({"role": "assistant", "content": a})

        messages.append({"role": "user", "content": query})

        # For debugging, print messages
        print("\n=== Messages Sent to OpenAI API (Streaming) ===")
        for msg in messages:
            role = msg['role']
            content = msg['content'].encode('utf-8', errors='replace').decode('utf-8')
            #print(f"Role: {role}, Content: {content}\n")
        print("=====================================\n")

        pre_openai_time = time.time()
        print(f"[DEBUG] About to call OpenAI, {pre_openai_time - after_groundx:.3f}s since start", flush=True)

        # 4) Call the OpenAI API with stream=True
        response = self.client.chat.completions.create(
            model=self.completion_model,
            messages=messages,
            stream=True,
            store=True
        )
        print("DEBUG: Called OpenAI with stream=True")
        after_openai_call_time = time.time()
        print(f"[DEBUG] Called OpenAI, waiting for chunks, {after_openai_call_time - pre_openai_time:.3f}s since pre_call",flush=True)

        # 5) The OpenAI API returns chunks as an iterator; yield partial text
        partial_answer = []  # We'll accumulate chunks here to store final in context_history
        try:
            for chunk in response:
                choice_delta = chunk.choices[0].delta
                chunk_text = choice_delta.content
                if chunk_text:
                    partial_answer.append(chunk_text)
                    # Yield text so Flask can stream it to the client
                    yield chunk_text
        except Exception as e:
            print(f"Streaming error: {e}")

        # 6) Once done, store the final combined answer in context
        final_answer = "".join(partial_answer).strip()
        self.context_history.append((query, final_answer))
        print(f"DEBUG: Final answer length={len(final_answer)}")

        # Optionally limit history length
        if len(self.context_history) > 10:
            self.context_history.pop(0)


# Flask Web App
app = Flask(__name__)
asistente = Asistente()


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    if not user_message:
        return jsonify({"message": "Error: No message provided"}), 400

    try:
        assistant_response = asistente.chat_completions(user_message)
        return jsonify({"message": assistant_response})
    except Exception as e:
        return jsonify({"message": f"Error: {e}"}), 500


@app.route("/erase", methods=["POST"])
def erase():
    """
    Elimina el último (query, respuesta) de la lista context_history
    y muestra el contenido de context_history en la consola con codificación UTF-8.
    """
    print("=== Before erase ===")
    print(json.dumps(asistente.context_history, indent=2, ensure_ascii=False),flush=True)

    if len(asistente.context_history) > 0:
        popped = asistente.context_history.pop()
        print(f"Popped last item: {json.dumps(popped, ensure_ascii=False)}", flush=True)

    print("=== After erase ===")
    print(json.dumps(asistente.context_history, indent=2, ensure_ascii=False), flush=True)

    return jsonify({"message": "Erased last user query and assistant response from context."}), 200

@app.route("/feedback", methods=["POST"])
def feedback():
    """
    Recibe el feedback del usuario y hace algo con él (ej. log, guardar en base de datos, etc.).
    """
    data = request.get_json()
    feedback_text = data.get("feedback", "")

    if not feedback_text.strip():
        return jsonify({"message": "Error: No feedback text provided"}), 400

    # Aquí podrías guardarlo en una BD, enviarlo a tu mail, etc.
    # Ejemplo: solo imprimir en consola
    print(f"=== FEEDBACK RECEIVED ===\n{feedback_text}\n========================\n", flush=True)

    return jsonify({"message": "¡Gracias por tu feedback!"}), 200

@app.route("/chat_stream", methods=["POST"])
def chat_stream():
    """
    Streams the OpenAI completion response chunk-by-chunk to the client.
    """
    data = request.get_json()
    user_message = data.get("message", "")

    if not user_message:
        return jsonify({"message": "Error: No message provided"}), 400

    try:
        # 1) We define a generator function that calls our new streaming method
        def generate():
            for chunk in asistente.chat_completions_stream(user_message):
                # Yield each chunk as it arrives
                yield chunk

        # 2) Wrap the generator in a Flask streaming Response
        return Response(
            stream_with_context(generate()),
            mimetype='text/plain'  # or text/event-stream if you prefer SSE
        )

    except Exception as e:
        return jsonify({"message": f"Error: {e}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
