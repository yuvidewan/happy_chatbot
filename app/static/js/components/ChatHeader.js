import { applyMotion } from "../theme/animations.js";

export function ChatHeader({ title, subtitle, modeLabels }) {
  const element = document.createElement("header");
  element.className = "chat-header";

  const textWrap = document.createElement("div");
  textWrap.className = "chat-header__text";

  const heading = document.createElement("h1");
  heading.className = "chat-header__title";
  heading.textContent = title;

  const subheading = document.createElement("p");
  subheading.className = "chat-header__subtitle";
  subheading.textContent = subtitle;

  textWrap.append(heading, subheading);

  const modeButton = document.createElement("button");
  modeButton.className = "chat-header__theme-toggle";
  modeButton.type = "button";
  modeButton.setAttribute("aria-label", "Toggle theme");
  modeButton.setAttribute("aria-pressed", "false");
  applyMotion(modeButton, "scaleHover");

  element.append(textWrap, modeButton);

  let toggleHandler = null;

  modeButton.addEventListener("click", () => {
    if (typeof toggleHandler === "function") {
      toggleHandler();
    }
  });

  function setThemeMode(mode) {
    const isDark = mode === "dark";
    modeButton.setAttribute("aria-pressed", String(isDark));
    const nextLabel = isDark ? modeLabels.light : modeLabels.dark;
    modeButton.textContent = nextLabel;
  }

  return {
    element,
    onToggleTheme(handler) {
      toggleHandler = handler;
    },
    setThemeMode,
  };
}
