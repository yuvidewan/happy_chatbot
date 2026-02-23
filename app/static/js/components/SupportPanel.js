import { applyMotion } from "../theme/animations.js";
import { SupportCard } from "./SupportCard.js";

export function SupportPanel({ title, subtitle, icons, onSuggestion }) {
  const element = document.createElement("aside");
  element.className = "support-panel";
  element.setAttribute("aria-label", "Support panel");
  element.dataset.collapsed = "false";

  const header = document.createElement("header");
  header.className = "support-panel__header";

  const headingWrap = document.createElement("div");
  headingWrap.className = "support-panel__heading-wrap";

  const heading = document.createElement("h2");
  heading.className = "support-panel__title";
  heading.textContent = title;

  const subheading = document.createElement("p");
  subheading.className = "support-panel__subtitle";
  subheading.textContent = subtitle;

  headingWrap.append(heading, subheading);

  const toggle = document.createElement("button");
  toggle.className = "support-panel__toggle";
  toggle.type = "button";
  toggle.setAttribute("aria-expanded", "true");
  toggle.setAttribute("aria-label", "Collapse support panel");
  toggle.innerHTML = "<span aria-hidden=\"true\">−</span>";
  applyMotion(toggle, "scaleHover");

  header.append(headingWrap, toggle);

  const content = document.createElement("div");
  content.className = "support-panel__content";
  applyMotion(content, "smoothCollapse");

  const list = document.createElement("ul");
  list.className = "support-panel__list";
  list.setAttribute("aria-live", "polite");

  content.appendChild(list);
  element.append(header, content);

  let collapsed = false;

  function setCollapsed(nextCollapsed) {
    collapsed = Boolean(nextCollapsed);
    element.dataset.collapsed = String(collapsed);
    toggle.setAttribute("aria-expanded", String(!collapsed));
    toggle.setAttribute("aria-label", `${collapsed ? "Expand" : "Collapse"} support panel`);
    toggle.innerHTML = `<span aria-hidden="true">${collapsed ? "+" : "−"}</span>`;
  }

  toggle.addEventListener("click", () => {
    setCollapsed(!collapsed);
  });

  function setBusy(isBusy) {
    list.querySelectorAll("button.support-card__action--chip").forEach((button) => {
      button.disabled = isBusy || button.dataset.interactive !== "true";
    });
  }

  function setSuggestions(suggestions, { interactive = true } = {}) {
    const safeSuggestions = Array.isArray(suggestions) ? suggestions : [];
    list.innerHTML = "";

    safeSuggestions.forEach((suggestion, index) => {
      const symbolPool = Array.isArray(icons) && icons.length > 0 ? icons : ["item"];
      const iconLabel = symbolPool[index % symbolPool.length];
      const card = SupportCard({
        suggestion,
        index,
        interactive,
        iconLabel,
        onSelect: onSuggestion,
      });
      const actionButton = card.querySelector("button.support-card__action--chip");
      if (actionButton) {
        actionButton.dataset.interactive = String(interactive);
      }
      list.appendChild(card);
    });
  }

  return {
    element,
    setCollapsed,
    setBusy,
    setSuggestions,
    setTitle(nextTitle) {
      heading.textContent = nextTitle;
    },
  };
}
