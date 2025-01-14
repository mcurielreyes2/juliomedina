import json
import logging
from flask import Flask, request, jsonify, render_template, Response, stream_with_context

# Import your Asistente class from the separate module
from classes.asistente import Asistente

# Optionally configure or tweak logging here
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
asistente = Asistente()  # Instantiate your class from classes/asistente.py

@app.route("/", methods=["GET"])
def home():
    """Serve the main HTML page."""
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    """
    Handle non-streaming chat (one-shot).
    """
    data = request.get_json()
    user_message = data.get("message", "")
    if not user_message:
        return jsonify({"message": "Error: No message provided"}), 400

    try:
        assistant_response = asistente.chat_completions(user_message)
        return jsonify({"message": assistant_response})
    except Exception as e:
        logger.error(f"Error in /chat: {e}")
        return jsonify({"message": f"Error: {e}"}), 500

@app.route("/erase", methods=["POST"])
def erase():
    """
    Erase the last (query, response) pair from context_history.
    """
    logger.debug("=== Before erase ===")
    logger.debug(json.dumps(asistente.context_history, indent=2, ensure_ascii=False))

    if asistente.context_history:
        popped = asistente.context_history.pop()
        logger.debug(f"Popped last item: {json.dumps(popped, ensure_ascii=False)}")

    logger.debug("=== After erase ===")
    logger.debug(json.dumps(asistente.context_history, indent=2, ensure_ascii=False))

    return jsonify({"message": "Erased last user query and assistant response from context."}), 200

@app.route("/feedback", methods=["POST"])
def feedback():
    """
    Receive feedback from the user and log/save it somewhere.
    """
    data = request.get_json()
    feedback_text = data.get("feedback", "")

    if not feedback_text.strip():
        return jsonify({"message": "Error: No feedback text provided"}), 400

    # Example: print or log to console
    logger.info(f"=== FEEDBACK RECEIVED ===\n{feedback_text}\n========================\n")

    return jsonify({"message": "¡Gracias por tu feedback!"}), 200

@app.route("/check_rag", methods=["POST"])
def check_rag():
    """
    Check if the user's query should use RAG (GroundX retrieval).
    """
    data = request.get_json()
    user_message = data.get("message", "")
    rag_used = asistente.should_call_groundx(user_message)
    return jsonify({"is_rag": rag_used})

@app.route("/chat_stream", methods=["POST"])
def chat_stream():
    """
    Streams the completion response chunk-by-chunk to the client.
    """
    data = request.get_json()
    user_message = data.get("message", "")

    if not user_message:
        return jsonify({"message": "Error: No message provided"}), 400

    try:
        def generate():
            # Use your Asistente's streaming method
            for chunk in asistente.chat_completions_stream(user_message):
                yield chunk

        return Response(
            stream_with_context(generate()),
            mimetype='text/plain'  # or text/event-stream for SSE
        )
    except Exception as e:
        logger.error(f"Error in /chat_stream: {e}")
        return jsonify({"message": f"Error: {e}"}), 500

if __name__ == "__main__":
    app.run(debug=False, port=5000)