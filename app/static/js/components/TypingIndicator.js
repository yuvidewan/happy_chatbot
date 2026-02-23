import { AnimatedContainer } from "./AnimatedContainer.js";
import { applyMotion } from "../theme/animations.js";

export function TypingIndicator({ label }) {
  const element = AnimatedContainer({
    tag: "article",
    className: "chat-message chat-message--bot typing-indicator",
    animation: "fadeInUp",
  });
  element.setAttribute("role", "status");
  element.setAttribute("aria-live", "polite");

  const body = document.createElement("div");
  body.className = "chat-message__body";

  const text = document.createElement("span");
  text.className = "typing-indicator__label";
  text.textContent = label;

  const dots = document.createElement("span");
  dots.className = "typing-indicator__dots";
  applyMotion(dots, "typingDots");
  for (let index = 0; index < 3; index += 1) {
    dots.appendChild(document.createElement("span"));
  }

  body.append(text, dots);
  element.appendChild(body);

  return { element };
}
