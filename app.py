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
        # Load API keys and bucket ID from environment variables
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.groundx_api_key = os.getenv("GROUNDX_API_KEY")
        self.bucket_id = os.getenv("GROUNDX_BUCKET_ID")

        # If keys are not set in the environment, attempt to load from config.json
        if not self.openai_api_key or not self.groundx_api_key or not self.bucket_id:
            try:
                with open('config.json') as config_file:
                    config = json.load(config_file)
                    self.openai_api_key = self.openai_api_key or config.get("OPENAI_API_KEY")
                    self.groundx_api_key = self.groundx_api_key or config.get("GROUNDX_API_KEY")
                    self.bucket_id = self.bucket_id or config.get("GROUNDX_BUCKET_ID")
            except FileNotFoundError:
                raise ValueError("Error: No API key or bucket ID found in environment variables or config.json.")

        # Validate that the bucket ID is a valid integer
        if not self.bucket_id or not str(self.bucket_id).isdigit():
            raise ValueError("Error: GROUNDX_BUCKET_ID must be a valid integer.")

        # Convert bucket ID to integer
        self.bucket_id = int(self.bucket_id)

        # Set other configurations
        self.completion_model = "gpt-4o"
        self.instruction = (
            "You are an assistant specialized in coffee and coffee production processes. "
            "Your primary focus is to use the provided coffee-related documents as the main knowledge base to answer user queries. "
            "These documents cover coffee classification, roasting processes, moisture content measurement, chemical compositions, and the evolution of coffee species. "
            "Below are the document summaries to help you answer user questions effectively:"
            "\n\n"
            "Document Summaries:"
            "\n- Green Coffee Classification: Details the grading and defect standards for green Arabica coffee beans, including moisture content and visual characteristics."
            "\n- Measuring Moisture Content: Explains methods like oven-drying and electronic meters for assessing coffee bean moisture levels to maintain quality."
            "\n- Rate of Rise in Roasting: Highlights the importance of monitoring bean temperature changes during roasting to ensure consistent quality."
            "\n- Chemical Composition of Roasts: Discusses how roasting times and temperatures affect the chemical makeup, flavor, and aroma of coffee."
            "\n- Roasting as Art and Science: Explores physical and chemical changes during roasting, emphasizing the interplay of heat and time."
            "\n- Coffee Tree Family Chart: Visual representation of coffee species evolution, including Arabica, Robusta, and Liberica."
            "\n\n"
            "How to Respond:"
            "\n- Answer specific questions about coffee roasting, classification, and quality using the detailed references from the uploaded documents."
            "\n- For general coffee-related questions not covered in the documents, provide answers based on your general knowledge while always prioritizing the reference content provided."
            "\n\n"
            "Prioritization:"
            "\n- Always cite document references for document-based answers."
            "\n- Redirect non-coffee-related or unrelated queries to external research or general knowledge resources."
            "\n\n"
            "Example Citations:"
            "\n- 'According to the Green Coffee Classification document (page 1)...'"
            "\n- 'The section on roasting profiles (RoR, page 3) indicates...'"
            "\n\n"
            "If the requested information cannot be found in the provided documents, kindly apologize to the user and suggest they contact Martin Garmendia from MCT (mgarmendia@mct-esco.com). "
            "Do not share external links in your responses."
        )

        # Initialize GroundX and OpenAI clients
        self.groundx = GroundX(api_key=self.groundx_api_key)
        self.client = OpenAI(api_key=self.openai_api_key)

        # Initialize conversation context
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
