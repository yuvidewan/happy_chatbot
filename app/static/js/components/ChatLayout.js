export function ChatLayout() {
  const element = document.createElement("div");
  element.className = "app-scene";

  const radialLayer = document.createElement("div");
  radialLayer.className = "scene-radial";
  radialLayer.setAttribute("aria-hidden", "true");

  const grainLayer = document.createElement("div");
  grainLayer.className = "scene-grain";
  grainLayer.setAttribute("aria-hidden", "true");

  const vignetteLayer = document.createElement("div");
  vignetteLayer.className = "scene-vignette";
  vignetteLayer.setAttribute("aria-hidden", "true");

  const layout = document.createElement("main");
  layout.className = "chat-layout";

  const conversation = document.createElement("section");
  conversation.className = "conversation-shell";
  conversation.setAttribute("aria-label", "Conversation");

  const headerSlot = document.createElement("div");
  headerSlot.className = "conversation-shell__header";

  const chatLog = document.createElement("div");
  chatLog.className = "conversation-shell__log";
  chatLog.setAttribute("role", "log");
  chatLog.setAttribute("aria-live", "polite");
  chatLog.setAttribute("aria-relevant", "additions text");
  chatLog.setAttribute("aria-atomic", "false");

  const inputSlot = document.createElement("div");
  inputSlot.className = "conversation-shell__input";

  conversation.append(headerSlot, chatLog, inputSlot);

  const supportSlot = document.createElement("section");
  supportSlot.className = "support-shell";
  supportSlot.setAttribute("aria-label", "Support");

  layout.append(conversation, supportSlot);
  element.append(radialLayer, grainLayer, vignetteLayer, layout);

  function scrollToBottom() {
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    chatLog.scrollTo({
      top: chatLog.scrollHeight,
      behavior: prefersReducedMotion ? "auto" : "smooth",
    });
  }

  return {
    element,
    mountHeader(node) {
      headerSlot.replaceChildren(node);
    },
    mountInput(node) {
      inputSlot.replaceChildren(node);
    },
    mountSupportPanel(node) {
      supportSlot.replaceChildren(node);
    },
    mountEmotionVisualizer(node) {
      element.appendChild(node);
    },
    appendMessage(node) {
      chatLog.appendChild(node);
      scrollToBottom();
    },
    removeNode(node) {
      if (node && node.parentNode === chatLog) {
        node.remove();
      }
    },
    scrollToBottom,
  };
}
