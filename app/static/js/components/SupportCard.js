import { AnimatedContainer } from "./AnimatedContainer.js";
import { applyMotion } from "../theme/animations.js";

function parseResource(text) {
  const raw = String(text || "");
  const match = raw.match(/https?:\/\/[^\s]+/i);
  if (!match) {
    return { label: raw.trim(), url: "" };
  }
  const url = match[0];
  const label = raw.replace(url, "").replace(/[:\-]\s*$/, "").trim();
  return { label: label || raw.trim(), url };
}

export function SupportCard({ suggestion, index, interactive, iconLabel, onSelect }) {
  const { label, url } = parseResource(suggestion);
  const element = AnimatedContainer({
    tag: "li",
    className: "support-card",
    animation: "fadeInUp",
  });

  const icon = document.createElement("span");
  icon.className = "support-card__icon";
  icon.textContent = String(iconLabel || "").slice(0, 2).toUpperCase();
  icon.setAttribute("aria-hidden", "true");

  const content = document.createElement("div");
  content.className = "support-card__content";

  const text = document.createElement("p");
  text.className = "support-card__text";
  text.textContent = label;
  content.appendChild(text);

  if (url) {
    const action = document.createElement("a");
    action.className = "support-card__action support-card__action--link";
    action.href = url;
    action.target = "_blank";
    action.rel = "noopener noreferrer";
    action.textContent = "Open";
    action.setAttribute("aria-label", `Open resource ${index + 1}`);
    applyMotion(action, "scaleHover");
    content.appendChild(action);
  } else {
    const action = document.createElement("button");
    action.className = "support-card__action support-card__action--chip";
    action.type = "button";
    action.textContent = "Use in chat";
    action.disabled = !interactive;
    action.setAttribute("aria-label", `Use support suggestion ${index + 1}`);
    action.addEventListener("click", () => {
      if (!interactive || typeof onSelect !== "function") return;
      onSelect(label);
    });
    applyMotion(action, "scaleHover");
    content.appendChild(action);
  }

  element.append(icon, content);
  return element;
}
