import { AnimatedContainer } from "./AnimatedContainer.js";
import { formatConversationTime } from "../utils/time.js";

function resolveRoleClass(role) {
  return role === "user" ? "chat-message--user" : "chat-message--bot";
}

export function ChatMessage(entry, { kind = "" } = {}) {
  const element = AnimatedContainer({
    tag: "article",
    className: `chat-message ${resolveRoleClass(entry.role)}`,
    animation: "fadeInUp",
  });

  if (kind) {
    element.classList.add(`chat-message--${kind}`);
  }

  const body = document.createElement("p");
  body.className = "chat-message__body";
  body.textContent = entry.text || "";
  element.appendChild(body);

  const humanTime = formatConversationTime(entry.timestamp);
  if (humanTime) {
    const meta = document.createElement("time");
    meta.className = "chat-message__meta";
    meta.textContent = humanTime;
    meta.dateTime = new Date(entry.timestamp).toISOString();
    element.appendChild(meta);
  }

  return element;
}
