import { applyMotion } from "../theme/animations.js";

export function ChatInput({ placeholder, label, sendLabel, retryLabel, sendIcon }) {
  const element = document.createElement("form");
  element.className = "chat-input";
  element.setAttribute("novalidate", "novalidate");

  const fieldWrap = document.createElement("div");
  fieldWrap.className = "chat-input__field";

  const textarea = document.createElement("textarea");
  textarea.className = "chat-input__textarea";
  textarea.rows = 1;
  textarea.maxLength = 1000;
  textarea.required = true;
  textarea.placeholder = " ";
  textarea.setAttribute("aria-label", label);

  const floatingLabel = document.createElement("label");
  floatingLabel.className = "chat-input__label";
  floatingLabel.textContent = placeholder;

  fieldWrap.append(textarea, floatingLabel);

  const actions = document.createElement("div");
  actions.className = "chat-input__actions";

  const sendButton = document.createElement("button");
  sendButton.className = "chat-input__button chat-input__button--send";
  sendButton.type = "submit";
  sendButton.setAttribute("aria-label", sendLabel);
  sendButton.innerHTML = `<span class="chat-input__button-icon">${sendIcon}</span><span>${sendLabel}</span>`;
  applyMotion(sendButton, "scaleHover");

  const retryButton = document.createElement("button");
  retryButton.className = "chat-input__button chat-input__button--retry";
  retryButton.type = "button";
  retryButton.textContent = retryLabel;
  retryButton.hidden = true;
  retryButton.setAttribute("aria-label", retryLabel);
  applyMotion(retryButton, "scaleHover");

  actions.append(sendButton, retryButton);
  element.append(fieldWrap, actions);

  let submitHandler = null;
  let retryHandler = null;

  function syncValueState() {
    const hasValue = textarea.value.trim().length > 0;
    fieldWrap.dataset.hasValue = hasValue ? "true" : "false";
  }

  element.addEventListener("submit", (event) => {
    event.preventDefault();
    if (typeof submitHandler === "function") {
      submitHandler(textarea.value);
    }
  });

  textarea.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      element.requestSubmit();
    }
  });
  textarea.addEventListener("input", syncValueState);
  syncValueState();

  retryButton.addEventListener("click", () => {
    if (typeof retryHandler === "function") {
      retryHandler();
    }
  });

  return {
    element,
    setBusy(isBusy) {
      textarea.disabled = isBusy;
      sendButton.disabled = isBusy;
      retryButton.disabled = isBusy;
    },
    setRetryVisible(visible) {
      retryButton.hidden = !visible;
    },
    focus() {
      textarea.focus();
    },
    clear() {
      textarea.value = "";
      syncValueState();
    },
    getValue() {
      return textarea.value;
    },
    onSubmit(handler) {
      submitHandler = handler;
    },
    onRetry(handler) {
      retryHandler = handler;
    },
    setSendLabel(nextLabel) {
      sendButton.querySelector("span:last-child").textContent = nextLabel;
      sendButton.setAttribute("aria-label", nextLabel);
    },
  };
}
