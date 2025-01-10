// 1) GLOBAL abortController to handle streaming fetch
let abortController = null;

/**
 * On window load, show initial assistant message
 */
window.onload = function() {
  const chatBox = document.getElementById("chat-box");
  const welcomeMessage = document.createElement("div");
  welcomeMessage.className = "assistant-message";
  welcomeMessage.innerText = "Hola, soy un asistente experto en Cafe. ¿En qué puedo ayudarte?";
  chatBox.appendChild(welcomeMessage);
  chatBox.scrollTop = chatBox.scrollHeight;
};

/**
 * Send a standard (non-stream) message to Flask
 */
async function sendMessage() {
  const inputField = document.getElementById("user-input");
  const message = inputField.value.trim();
  if (message === "") return;
  inputField.value = "";

  // Display user message
  const chatBox = document.getElementById("chat-box");
  const userMessage = document.createElement("div");
  userMessage.className = "user-message";
  userMessage.innerText = message;
  chatBox.appendChild(userMessage);
  chatBox.scrollTop = chatBox.scrollHeight;

  // Display typing indicator
  const typingIndicator = document.createElement("div");
  typingIndicator.className = "assistant-message";
  typingIndicator.innerHTML =
    '<span class="typing-indicator"></span><span class="typing-indicator"></span><span class="typing-indicator"></span>';
  chatBox.appendChild(typingIndicator);
  chatBox.scrollTop = chatBox.scrollHeight;

  // Send message to Flask server
  const response = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: message }),
  });

  // Remove typing indicator
  chatBox.removeChild(typingIndicator);

  // Show assistant response with a typewriter effect
  const data = await response.json();
  const assistantMessage = document.createElement("div");
  assistantMessage.className = "assistant-message";
  chatBox.appendChild(assistantMessage);
  typeWriterEffect(assistantMessage, data.message);
  chatBox.scrollTop = chatBox.scrollHeight;
}

/**
 * Send a message to the streaming endpoint
 */
async function sendMessageStream() {
  const inputField = document.getElementById("user-input");
  const message = inputField.value.trim();
  if (message === "") return;
  inputField.value = "";

  // Hide welcome + options at first user message
  const welcomeMessageEl = document.querySelector(".welcome-message");
  const optionsContainerEl = document.querySelector(".options-container");
  if (welcomeMessageEl) welcomeMessageEl.style.display = "none";
  if (optionsContainerEl) optionsContainerEl.style.display = "none";

  // Display user message
  const chatBox = document.getElementById("chat-box");
  const userMessageDiv = document.createElement("div");
  userMessageDiv.className = "user-message";
  userMessageDiv.innerText = message;
  chatBox.appendChild(userMessageDiv);
  chatBox.scrollTop = chatBox.scrollHeight;

  // Show typing indicator
  const typingIndicator = document.createElement("div");
  typingIndicator.className = "assistant-message";
  typingIndicator.innerHTML =
    '<span class="typing-indicator"></span><span class="typing-indicator"></span><span class="typing-indicator"></span>';
  chatBox.appendChild(typingIndicator);
  chatBox.scrollTop = chatBox.scrollHeight;

  // IMPORTANT: Use an AbortController if you want to stop streaming
  abortController = new AbortController();
  try {
    const response = await fetch("/chat_stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: message }),
      signal: abortController.signal, // pass signal here
    });

    // Remove typing indicator
    chatBox.removeChild(typingIndicator);

    // Prepare assistant message container
    const assistantMessageDiv = document.createElement("div");
    assistantMessageDiv.className = "assistant-message";
    chatBox.appendChild(assistantMessageDiv);

    // Check response OK
    if (!response.ok) {
      const errorData = await response.json();
      assistantMessageDiv.innerText = `Error: ${errorData.message}`;
      return;
    }

    // We'll type out the streamed text chunk by chunk
    let pendingText = "";
    let isTyping = false;

    function backgroundTyper(element, speed = 12) {
      if (isTyping) return; // If already typing, do nothing
      isTyping = true;

      function typeNextChar() {
        if (pendingText.length > 0) {
          const nextChar = pendingText.charAt(0);
          pendingText = pendingText.slice(1);
          element.innerHTML += nextChar;
          setTimeout(typeNextChar, speed);
        } else {
          // Done typing for now
          isTyping = false;
        }
      }
      typeNextChar();
    }

    // Start reading streaming chunks
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");

    async function readChunk() {
      const { done, value } = await reader.read();
      if (done) return;

      const chunkText = decoder.decode(value, { stream: true });
      pendingText += chunkText; // add newly arrived text
      backgroundTyper(assistantMessageDiv, 12); // type chunk
      chatBox.scrollTop = chatBox.scrollHeight;  // auto-scroll

      readChunk(); // keep reading
    }
    readChunk();

  } catch (err) {
    // If there's an error or we aborted
    chatBox.removeChild(typingIndicator);

    const errorMessageDiv = document.createElement("div");
    errorMessageDiv.className = "assistant-message";
    errorMessageDiv.innerText = `Request error: ${err}`;
    chatBox.appendChild(errorMessageDiv);
  }
}

/**
 * Simple typewriter effect for static text
 */
function typeWriterEffect(element, text) {
  let index = 0;
  function type() {
    if (index < text.length) {
      element.innerHTML += text.charAt(index);
      index++;
      setTimeout(type, 50); // speed
    }
  }
  type();
}

/**
 * Remove the last user message from DOM
 */
function removeLastUserMessage() {
  const chatBox = document.getElementById("chat-box");
  const userMessages = chatBox.querySelectorAll(".user-message");
  if (userMessages.length > 0) {
    const lastUserMessage = userMessages[userMessages.length - 1];
    chatBox.removeChild(lastUserMessage);
  }
}

/**
 * Remove the last assistant message from DOM
 */
function removeLastAssistantMessage() {
  const chatBox = document.getElementById("chat-box");
  const assistantMessages = chatBox.querySelectorAll(".assistant-message");
  if (assistantMessages.length > 0) {
    const lastAssistantMessage = assistantMessages[assistantMessages.length - 1];
    chatBox.removeChild(lastAssistantMessage);
  }
}

/**
 * Borrar último mensaje (usuario + asistente), abort streaming, y notificar backend
 */
function eraseLastAndStop() {
  // Remove last user message from DOM
  removeLastUserMessage();

  // Remove last assistant message from DOM
  removeLastAssistantMessage();

  // Abort streaming if active
  if (abortController) {
    abortController.abort();
    abortController = null;
  }

  // Call the backend to remove the last conversation pair
  fetch("/erase", { method: "POST" })
    .then(response => response.json())
    .then(data => {
      console.log("Backend says:", data.message);
    })
    .catch(err => {
      console.error("Error calling /erase:", err);
    });
}

/**
 * Send with Enter key
 */
function checkEnter(event) {
  if (event.key === "Enter") {
    sendMessageStream();
  }
}

// 1) Obtener referencias a los elementos (asumiendo que ya lo hiciste en tu script)
const feedbackModal = document.getElementById("feedback-modal");
const feedbackButton = document.getElementById("feedback-button");
const closeFeedbackButton = document.getElementById("close-feedback");
const submitFeedbackButton = document.getElementById("submit-feedback");
const feedbackTextArea = document.getElementById("feedback-text");

// 2) Mostrar modal al hacer clic en “Feedback”
if (feedbackButton) {
  feedbackButton.addEventListener("click", () => {
    feedbackModal.style.display = "block";
  });
}

// 3) Función para cerrar el modal (la puedes reutilizar)
function closeFeedbackModal() {
  feedbackModal.style.display = "none";
  // Si quieres limpiar el textarea al cerrar, descomenta:
  // feedbackTextArea.value = "";
}

// 4) Cerrar con botón “Cerrar”
if (closeFeedbackButton) {
  closeFeedbackButton.addEventListener("click", closeFeedbackModal);
}

// 5) Al hacer clic en “Enviar reporte”
if (submitFeedbackButton) {
  submitFeedbackButton.addEventListener("click", () => {
    const feedbackText = feedbackTextArea.value.trim();
    if (!feedbackText) {
      alert("Por favor, ingrese un comentario primero.");
      return;
    }

    // Enviar el feedback al backend
    fetch("/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ feedback: feedbackText }),
    })
      .then(response => {
        if (!response.ok) {
          throw new Error("Error al enviar feedback");
        }
        return response.json();
      })
      .then(data => {
        // Opcional: mostrar mensaje de “gracias” devuelto por el backend
        alert(data.message || "¡Gracias por tu feedback!");

        // Cerrar el modal
        closeFeedbackModal();

        // (Opcional) Limpiar el contenido del textarea
        feedbackTextArea.value = "";
      })
      .catch(err => {
        console.error("Error:", err);
        alert("No se pudo enviar el feedback. Intente de nuevo.");
      });
  });
}

let assistantMessageDiv = null;  // scope superior

// Selecciona todos los option-boxes y les agrega un click listener
document.querySelectorAll('.option-box').forEach(box => {
  box.addEventListener('click', () => {
    // El texto que se envía como query será el innerText del box
    const message = box.innerText.trim();
    sendOptionMessage(message);
  });
});

function sendOptionMessage(message) {
  // 1) Ocultar welcome-message y options-container si están visibles
  const welcomeMessageEl = document.querySelector('.welcome-message');
  const optionsContainerEl = document.querySelector('.options-container');
  if (welcomeMessageEl) welcomeMessageEl.style.display = 'none';
  if (optionsContainerEl) optionsContainerEl.style.display = 'none';

  // 2) Mostrar el mensaje del usuario en el chat
  const chatBox = document.getElementById("chat-box");
  const userMessageDiv = document.createElement("div");
  userMessageDiv.className = "user-message";
  userMessageDiv.innerText = message;
  chatBox.appendChild(userMessageDiv);
  chatBox.scrollTop = chatBox.scrollHeight;

  // 3) Mostrar indicador de escritura
  const typingIndicator = document.createElement("div");
  typingIndicator.className = "assistant-message";
  typingIndicator.innerHTML = `<span class="typing-indicator"></span><span class="typing-indicator"></span><span class="typing-indicator"></span>`;
  chatBox.appendChild(typingIndicator);
  chatBox.scrollTop = chatBox.scrollHeight;

  // 4) Hacer la llamada al endpoint /chat_stream
  fetch("/chat_stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message })
  })
    .then(response => {
      // 5) Retirar el indicador de escritura (si sigue en el DOM)
      if (typingIndicator.parentNode) {
        typingIndicator.parentNode.removeChild(typingIndicator);
      }

      // Crear contenedor para la respuesta del asistente
      const assistantMessageDiv = document.createElement("div");
      assistantMessageDiv.className = "assistant-message";
      chatBox.appendChild(assistantMessageDiv);

      // Validar que la respuesta sea exitosa
      if (!response.ok) {
        return response.json().then(errorData => {
          assistantMessageDiv.innerText = `Error: ${errorData.message}`;
          return null;
        });
      }
      // 6) Procesar el streaming de la respuesta
      return response.body ? response.body : null;
    })
    .then(body => {
      if (!body) return; // si hubo error o no hay body, salimos

      const reader = body.getReader();
      const decoder = new TextDecoder("utf-8");
      let pendingText = "";
      let isTyping = false;

      // backgroundTyper: función que va tipeando poco a poco el texto acumulado
      function backgroundTyper(element, speed = 10) {
        // Evitamos arrancar la animación si ya está tipeando
        if (isTyping) return;
        isTyping = true;

        function typeNextChar() {
          // Validar que el elemento exista y siga en el DOM
          if (!element || !document.body.contains(element)) {
            isTyping = false;
            return;
          }
          if (pendingText.length > 0) {
            const nextChar = pendingText.charAt(0);
            pendingText = pendingText.slice(1);
            // Asignar el char
            element.innerHTML += nextChar;
            setTimeout(typeNextChar, speed);
          } else {
            isTyping = false;
          }
        }
        typeNextChar();
      }

      function readChunk() {
        reader.read().then(({ done, value }) => {
          if (done) return;

          const chunkText = decoder.decode(value, { stream: true });
          // Acumulamos el texto
          pendingText += chunkText;
          // Mandamos a “tipear”
          const assistantMessageDiv = chatBox.querySelector(
            ".assistant-message:last-of-type"
          );
          if (assistantMessageDiv) {
            backgroundTyper(assistantMessageDiv, 12);
          }

          // Auto-scroll
          chatBox.scrollTop = chatBox.scrollHeight;
          // Continuar leyendo
          readChunk();
        });
      }
      readChunk();
    })
    .catch(err => {
      // Manejo de cualquier error en fetch o streaming
      // Quitar typingIndicator si sigue presente
      if (typingIndicator.parentNode) {
        typingIndicator.parentNode.removeChild(typingIndicator);
      }

      // Crear un div para el error
      const errorMessageDiv = document.createElement("div");
      errorMessageDiv.className = "assistant-message";
      errorMessageDiv.innerText = `Error: ${err.message}`;
      chatBox.appendChild(errorMessageDiv);
    });
}

