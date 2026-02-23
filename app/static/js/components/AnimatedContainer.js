import { applyMotion } from "../theme/animations.js";

export function AnimatedContainer({ tag = "div", className = "", animation = "fadeInUp" } = {}) {
  const element = document.createElement(tag);
  if (className) {
    element.className = className;
  }
  applyMotion(element, animation);
  return element;
}
