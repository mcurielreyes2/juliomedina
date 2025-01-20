import json
import logging
from flask import Flask, request, jsonify, render_template, Response, stream_with_context

# Import your Asistente class from the separate module
from classes.asistente import Asistente
from classes.RAG import RAGService
from classes.asistente_osma import AsistenteOSMA

# Optionally configure or tweak logging here
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
asistente = Asistente()  # Instantiate your class from classes/asistente.py
rag_service = RAGService()

@app.route("/", methods=["GET"])
def home():
    """Serve the main HTML page."""
    return render_template("index.html")

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

    return jsonify({"message": "¡Gracias por tu evaluación!"}), 200

@app.route("/feedback_rating", methods=["POST"])
def feedback_rating():
    data = request.get_json() or {}
    pregunta = data.get("pregunta", "")
    respuesta = data.get("respuesta", "")
    evaluacion = data.get("evaluacion", "")  # "up" o "down"
    fecha_str = data.get("fecha", "")
    motivo = data.get("motivo", "")  # Reason for thumbs-down, if any

    if not pregunta or not respuesta or not evaluacion:
        return jsonify({"message": "Error: faltan campos en el feedback de rating"}), 400

    # Ruta para feedback.json
    import os
    feedback_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feedback.json")

    # Cargar contenido previo
    if os.path.exists(feedback_file):
        with open(feedback_file, "r", encoding="utf-8") as f:
            try:
                feedback_data = json.load(f)
            except json.JSONDecodeError:
                feedback_data = []
    else:
        feedback_data = []

    # Crear registro
    registro = {
        "fecha": fecha_str,
        "pregunta": pregunta,
        "respuesta": respuesta,
        "evaluacion": evaluacion,
        "motivo": motivo
    }
    feedback_data.append(registro)

    # Guardar
    with open(feedback_file, "w", encoding="utf-8") as f:
        json.dump(feedback_data, f, indent=2, ensure_ascii=False)

    logger.info(f"=== FEEDBACK (PULGAR) RECIBIDO ===\n{registro}\n========================\n")

    return jsonify({"message": "¡Gracias por tu evaluación!"}), 200


@app.route("/check_rag", methods=["POST"])
def check_rag():
    """
    Check if the user's query should use RAG (GroundX retrieval).
    """
    data = request.get_json()
    user_message = data.get("message", "")
    rag_used = rag_service.should_call_groundx(user_message)
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


@app.route("/osma_init", methods=["POST"])
def osma_init():
    """
    Inicializa la sesión OSMA creando una instancia de AsistenteOSMA.
    Devuelve el prompt inicial y las opciones de servicios disponibles.
    """
    global osma_assistant
    osma_assistant = AsistenteOSMA()
    services = list(osma_assistant.data.keys())
    prompt = "¿Qué servicio(s) desea seleccionar?"
    logger.info("Se ha iniciado la sesión OSMA")
    return jsonify({"prompt": prompt, "services": services})


@app.route("/osma_respond", methods=["POST"])
def osma_respond():
    """
    Procesa la respuesta del usuario en el flujo OSMA y devuelve
    el siguiente prompt y, cuando corresponda, las opciones para el siguiente formulario.
    """
    global osma_assistant
    if osma_assistant is None:
        return jsonify({"error": "No se ha iniciado la sesión OSMA"}), 400

    data = request.get_json()
    respuesta = data.get("respuesta", "").strip()
    if respuesta == "":
        return jsonify({"error": "Respuesta vacía"}), 400

    next_prompt = osma_assistant.procesar_respuesta(respuesta)

    # Según el nuevo estado, devolvemos opciones para el próximo formulario.
    if osma_assistant.state == 1:
        # Paso 1: Monitoreables. Se agrupan de todos los servicios seleccionados.
        monitoreables = set()
        for serv in osma_assistant.servicio:
            monitoreables.update(osma_assistant.data.get(serv, {}).keys())
        return jsonify({"prompt": next_prompt, "monitoreables": list(monitoreables)})
    elif osma_assistant.state == 2:
        # Paso 2: Variables.
        variables = set()
        for mon in osma_assistant.monitoreable:
            for serv in osma_assistant.servicio:
                if mon in osma_assistant.data.get(serv, {}):
                    for var_item in osma_assistant.data[serv][mon]:
                        variables.add(var_item.get("Variable"))
        return jsonify({"prompt": next_prompt, "variables": list(variables)})
    elif osma_assistant.state == 4:
        # Paso 4: Intervalo; enviamos las opciones fijas
        intervals = ["Minuto", "Hora", "Día", "Mes"]
        return jsonify({"prompt": next_prompt, "intervals": intervals})
    else:
        return jsonify({"prompt": next_prompt})



if __name__ == "__main__":
    app.run(debug=False, port=5000)