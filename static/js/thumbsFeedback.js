// thumbsFeedback.js

/**
 * Envía un pulgar arriba/abajo al endpoint /feedback_rating
 */
export function sendThumbsFeedback({ question, answer, evaluation, reason = "", containerEl }) {
  const payload = {
    fecha: getLocalDateTimeString(),
    pregunta: question,
    respuesta: answer,
    evaluacion: evaluation,
    motivo: reason // Include the reason if provided
  };

  fetch("/feedback_rating", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
    .then(res => {
      if (!res.ok) {
        throw new Error("Error al enviar feedback");
      }
      return res.json();
    })
    .then(data => {
      console.log("Feedback response:", data.message);

      // Show a small confirmation message in the UI
      const msgEl = document.createElement("div");
      msgEl.className = "thumbs-confirmation";
      msgEl.innerText = "¡Gracias por tu evaluación!";

      containerEl.appendChild(msgEl);

      // Optionally disable the thumbs buttons to prevent multiple submissions
      const buttons = containerEl.querySelectorAll(".thumbs-btn");
      buttons.forEach(btn => { btn.disabled = true; });
    })
    .catch(err => {
      console.error("Error sending thumbs feedback:", err);
      alert("No se pudo enviar el feedback. Intente de nuevo.");
    });
}

/**
 * Crea y agrega los botones de pulgar arriba/abajo debajo de la respuesta
 */
export function insertThumbsFeedbackUI({ question, assistantDiv }) {
  // Grab the final text that was streamed into assistantDiv
  const finalAnswer = assistantDiv.innerText;

  // Create a container for the thumbs buttons
  const feedbackContainer = document.createElement("div");
  feedbackContainer.className = "feedback-container";

  // Insert the thumbs buttons HTML
  feedbackContainer.innerHTML = `
    <button class="thumbs-btn thumbs-up" data-type="up">
      <span class="thumb-icon"><i class="fas fa-thumbs-up"></i></span>
      <span class="thumb-label">Correcto</span>
    </button>
    <button class="thumbs-btn thumbs-down" data-type="down">
      <span class="thumb-icon"><i class="fas fa-thumbs-down"></i></span>
      <span class="thumb-label">Incorrecto</span>
    </button>
  `;

  // Append the feedback container to the assistant's answer div
  assistantDiv.appendChild(feedbackContainer);

  // Select the thumbs-up and thumbs-down buttons
  const upBtn = feedbackContainer.querySelector('.thumbs-up');
  const downBtn = feedbackContainer.querySelector('.thumbs-down');

  // Event listener for thumbs-up button
  upBtn.addEventListener("click", () => {
    sendThumbsFeedback({
      question,
      answer: finalAnswer,
      evaluation: "up",
      reason: "", // No reason needed for thumbs-up
      containerEl: feedbackContainer
    });
  });

  // Event listener for thumbs-down button
  downBtn.addEventListener("click", () => {
    // Show the thumbs-down modal instead of sending feedback immediately
    showThumbsDownModal(question, finalAnswer, feedbackContainer);
  });
}



/**
 * Called once DOM is ready
 * Finds the modal elements and wires up event listeners.
 */
export function initThumbsDownModal() {
  // Query for the modal elements
  const thumbsDownModal = document.getElementById("thumbs-down-modal");
  const reasonTextarea = document.getElementById("thumbs-down-reason");
  const cancelBtn = document.getElementById("cancel-thumbs-down");
  const submitBtn = document.getElementById("submit-thumbs-down");

  if (!thumbsDownModal || !reasonTextarea || !cancelBtn || !submitBtn) {
    console.error("Thumbs-down modal elements not found in DOM.");
    return;
  }

  // Event listener to hide the modal when 'Cancelar' is clicked
  cancelBtn.addEventListener("click", () => {
    hideThumbsDownModal(thumbsDownModal);
  });

  // Event listener to handle feedback submission when 'Enviar' is clicked
  submitBtn.addEventListener("click", () => {
    const reason = reasonTextarea.value.trim();

    // Validate input (optional)
    if (reason === "") {
      alert("Por favor, proporciona una breve explicación.");
      return;
    }

    // Send the thumbs-down feedback with the provided reason
    sendThumbsFeedback({
      question: currentQuestion,
      answer: currentAnswer,
      evaluation: "down",
      reason: reason,
      containerEl: currentContainerEl
    });

    // Hide the modal after submission
    hideThumbsDownModal(thumbsDownModal);
  });
}

/** Show the thumbs-down modal, storing the relevant data for submission. */
export function showThumbsDownModal(question, answer, containerEl) {
  // Store the current context to be used when submitting feedback
  currentQuestion = question;
  currentAnswer = answer;
  currentContainerEl = containerEl;

  // Clear any previous reason input
  const reasonTextarea = document.getElementById("thumbs-down-reason");
  if (reasonTextarea) {
    reasonTextarea.value = "";
  }

  // Show the modal
  const thumbsDownModal = document.getElementById("thumbs-down-modal");
  if (thumbsDownModal) {
    thumbsDownModal.style.display = "flex";
  }
}

/** Hide the thumbs-down modal. */
function hideThumbsDownModal(thumbsDownModal) {
  if (thumbsDownModal) {
    thumbsDownModal.style.display = "none";
  }
}

// We'll store these so we know what data to send once the user finishes typing
let currentQuestion = "";
let currentAnswer = "";
let currentContainerEl = null;


// Function to get current local time of the machine

function getLocalDateTimeString() {
  // This creates a human-readable local datetime string based on your system's locale
  const now = new Date();
  // For example, "en-US" = US English. Adjust to your preference or omit to use the user's default locale
  return now.toLocaleString("en-US");
}

