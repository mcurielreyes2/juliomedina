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

    // (1) Verificar si el backend va a usar RAG
  let isRag = false;
  try {
    const ragResp = await fetch("/check_rag", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });
    const ragData = await ragResp.json();
    isRag = ragData.is_rag;
  } catch (err) {
    console.error("Error checking RAG:", err);
  }

  // (2) Si isRag=true, mostramos un aviso especial, arriba de los typing indicators
  let ragMessageDiv = null;
  if (isRag) {
    ragMessageDiv = document.createElement("div");
    // Usa clases de "assistant-message" más una clase especial de blink
    ragMessageDiv.className = "assistant-message rag-status-blink";
    ragMessageDiv.innerText = "Buscando información en los documentos de referencia...";
    chatBox.appendChild(ragMessageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

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

    // Quitar el ragMessageDiv (si existe) cuando ya empieza la respuesta
    if (ragMessageDiv && ragMessageDiv.parentNode) {
      ragMessageDiv.parentNode.removeChild(ragMessageDiv);
    }

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
  if (done) {
    // When streaming is complete, check if math delimiters are balanced

    if (pendingText.length > 0) {
      assistantMessageDiv.innerHTML += pendingText;
      pendingText = "";
    }
    function isBalancedMath(text) {
      // Count the occurrences of \[ and \]
      const displayOpen = (text.match(/\\\[/g) || []).length;
      const displayClose = (text.match(/\\\]/g) || []).length;
      // Count the occurrences of \( and \)
      const inlineOpen = (text.match(/\\\(/g) || []).length;
      const inlineClose = (text.match(/\\\)/g) || []).length;
      return displayOpen === displayClose && inlineOpen === inlineClose;
    }

    // Once streaming is complete, call MathJax on the new assistantMessageDiv only
    if (window.MathJax) {
      console.log("Math delimiters balanced. Triggering MathJax typesetPromise on assistantMessageDiv.");
      window.MathJax.typesetPromise([assistantMessageDiv])
        .then(() => {
          console.log("MathJax re-typeset successfully after final chunk.");
        })
        .catch((err) => {
          console.error("MathJax typeset error:", err);
        });
    }
    return;
  }


      let chunkText = decoder.decode(value, { stream: true });

      // Accumulate chunk text
      pendingText += chunkText;

      // Start typing
      backgroundTyper(assistantMessageDiv, 12); // type chunk

      // Auto-scroll to bottom
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

async function sendOptionMessage(message) {
  // 1) Ocultar welcome-message y options-container si están visibles
  const welcomeMessageEl = document.querySelector(".welcome-message");
  const optionsContainerEl = document.querySelector(".options-container");
  if (welcomeMessageEl) welcomeMessageEl.style.display = "none";
  if (optionsContainerEl) optionsContainerEl.style.display = "none";

  // 2) Mostrar el mensaje del usuario en el chat
  const chatBox = document.getElementById("chat-box");
  const userMessageDiv = document.createElement("div");
  userMessageDiv.className = "user-message";
  userMessageDiv.innerText = message;
  chatBox.appendChild(userMessageDiv);
  chatBox.scrollTop = chatBox.scrollHeight;

  // 3) Verificar si el backend usará RAG (check_rag)
  let isRag = false;
  try {
    const ragResp = await fetch("/check_rag", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });
    const ragData = await ragResp.json();
    isRag = ragData.is_rag;  // true o false
  } catch (err) {
    console.error("Error checking RAG:", err);
  }

  // 4) Si RAG es True, mostrar un aviso especial antes de los typing indicators
  let ragMessageDiv = null;
  if (isRag) {
    ragMessageDiv = document.createElement("div");
    // Usa la clase de burbuja del asistente y una clase blink si quieres animar
    ragMessageDiv.className = "assistant-message rag-status-blink";
    ragMessageDiv.innerText = "Buscando información en los documentos de referencia...";
    chatBox.appendChild(ragMessageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
  }

  // 5) Mostrar indicador de escritura
  const typingIndicator = document.createElement("div");
  typingIndicator.className = "assistant-message";
  typingIndicator.innerHTML = `<span class="typing-indicator"></span> <span class="typing-indicator"></span><span class="typing-indicator"></span>`;
  chatBox.appendChild(typingIndicator);
  chatBox.scrollTop = chatBox.scrollHeight;

  // 6) Llamar al endpoint /chat_stream para obtener la respuesta en streaming
  try {
    const response = await fetch("/chat_stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });

    // Quitar el indicador de escritura (si aún está en el DOM)
    if (typingIndicator.parentNode) {
      typingIndicator.parentNode.removeChild(typingIndicator);
    }
    // Quitar el mensaje RAG si existe
    if (ragMessageDiv && ragMessageDiv.parentNode) {
      ragMessageDiv.parentNode.removeChild(ragMessageDiv);
    }

    // Crear contenedor para la respuesta del asistente
    const assistantMessageDiv = document.createElement("div");
    assistantMessageDiv.className = "assistant-message";
    chatBox.appendChild(assistantMessageDiv);

    // Si la respuesta no es OK, mostrar el error
    if (!response.ok) {
      const errorData = await response.json();
      assistantMessageDiv.innerText = `Error: ${errorData.message}`;
      return;
    }

    // 7) Procesar el streaming de la respuesta
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let pendingText = "";
    let isTyping = false;

    function backgroundTyper(element, speed = 12) {
      if (isTyping) return;
      isTyping = true;

      function typeNextChar() {
        if (pendingText.length > 0) {
          const nextChar = pendingText.charAt(0);
          pendingText = pendingText.slice(1);
          element.innerHTML += nextChar;
          setTimeout(typeNextChar, speed);
        } else {
          isTyping = false;
        }
      }
      typeNextChar();
    }


async function readChunk() {
  const { done, value } = await reader.read();
  if (done) {
    // When streaming is complete, check if math delimiters are balanced

    if (pendingText.length > 0) {
      assistantMessageDiv.innerHTML += pendingText;
      pendingText = "";
    }
    function isBalancedMath(text) {
      // Count the occurrences of \[ and \]
      const displayOpen = (text.match(/\\\[/g) || []).length;
      const displayClose = (text.match(/\\\]/g) || []).length;
      // Count the occurrences of \( and \)
      const inlineOpen = (text.match(/\\\(/g) || []).length;
      const inlineClose = (text.match(/\\\)/g) || []).length;
      return displayOpen === displayClose && inlineOpen === inlineClose;
    }

    // Once streaming is complete, call MathJax on the new assistantMessageDiv only
    if (window.MathJax) {
      console.log("Math delimiters balanced. Triggering MathJax typesetPromise on assistantMessageDiv.");
      window.MathJax.typesetPromise([assistantMessageDiv])
        .then(() => {
          console.log("MathJax re-typeset successfully after final chunk.");
        })
        .catch((err) => {
          console.error("MathJax typeset error:", err);
        });
    }
    return;
  }

      let chunkText = decoder.decode(value, { stream: true });

      // Accumulate chunk text
      pendingText += chunkText;

      // Start typing
      backgroundTyper(assistantMessageDiv, 12); // type chunk

      // Auto-scroll to bottom
      chatBox.scrollTop = chatBox.scrollHeight;  // auto-scroll

      readChunk(); // keep reading
    }
    readChunk();

  } catch (err) {
    // 8) Manejo de errores
    if (typingIndicator.parentNode) {
      typingIndicator.parentNode.removeChild(typingIndicator);
    }
    if (ragMessageDiv && ragMessageDiv.parentNode) {
      ragMessageDiv.parentNode.removeChild(ragMessageDiv);
    }
    const errorMessageDiv = document.createElement("div");
    errorMessageDiv.className = "assistant-message";
    errorMessageDiv.innerText = `Error: ${err}`;
    chatBox.appendChild(errorMessageDiv);
  }
}