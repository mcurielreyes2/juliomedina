import os
import json
from flask import Flask, request, jsonify, render_template
from openai import OpenAI
from groundx import GroundX
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

class Asistente:
    def __init__(self):
        """
        Initialize the Asistente class with configurations for OpenAI and GroundX APIs.
        """
        # Load API keys and bucket ID
        openai_api_key = os.getenv("OPENAI_API_KEY")
        groundx_api_key = os.getenv("GROUNDX_API_KEY")
        bucket_id = os.getenv("GROUNDX_BUCKET_ID")

        if not openai_api_key or not groundx_api_key or not bucket_id:
            try:
                with open('config.json') as config_file:
                    config = json.load(config_file)
                    self.openai_api_key = config.get("OPENAI_API_KEY")
                    groundx_api_key = config.get("GROUNDX_API_KEY")
                    bucket_id = config.get("GROUNDX_BUCKET_ID")
            except FileNotFoundError:
                raise ValueError("Error: No se encontró la clave de API o bucket ID.")

        if not bucket_id or not str(bucket_id).isdigit():
            raise ValueError("Error: GROUNDX_BUCKET_ID debe ser un entero válido.")

        self.completion_model = "gpt-4o-mini"
        self.instruction = (
            "You are an assistant specialized in coffee."
            "You must also answer any user questions regarding the reference documents, their pages, and the location of the provided information in these references."
            "You should only respond to queries related to this specific topic."
            "Your task is to create detailed answers to the questions using the content provided below."
            "Do not share links."
            "If you cannot find the requested information in the content below, apologize to the user and kindly ask them to contact Martin Garmendia from MCT (mgarmendia@mct-esco.com)."
        )

        # GroundX setup
        self.groundx = GroundX(api_key=groundx_api_key)
        self.bucket_id = int(bucket_id)
        self.client = OpenAI(api_key=self.openai_api_key)
        self.context_history = []

    def groundx_search_content(self, query: str) -> str:
        content_response = self.groundx.search.content(id=self.bucket_id, query=query)
        results = content_response.search
        llm_text = results.text
        if not llm_text:
            raise ValueError("No context found in the response")
        return llm_text

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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
