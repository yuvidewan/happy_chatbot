import { ChatHeader } from "./components/ChatHeader.js";
import { ChatInput } from "./components/ChatInput.js";
import { ChatLayout } from "./components/ChatLayout.js";
import { ChatMessage } from "./components/ChatMessage.js";
import { EmotionVisualizer } from "./components/EmotionVisualizer.js";
import { SupportPanel } from "./components/SupportPanel.js";
import { TypingIndicator } from "./components/TypingIndicator.js";
import { ThemeProvider } from "./theme/ThemeProvider.js";

const STORAGE_KEYS = {
  theme: "happybot_theme",
};

const LEGACY_HISTORY_STORAGE_KEY = "happybot_chat_history_v1";

const REQUEST_TIMEOUTS_MS = {
  chat: 0,
  suggestions: 15000,
};

const state = {
  inFlight: false,
  lastFailedMessage: null,
  typingNode: null,
  suggestionsFingerprint: "",
};

const api = {
  async fetchJson(url, options = {}, timeoutMs = 0) {
    const controller = new AbortController();
    const hasTimeout = Number.isFinite(timeoutMs) && timeoutMs > 0;
    const timeoutId = hasTimeout ? window.setTimeout(() => controller.abort(), timeoutMs) : null;

    try {
      const response = await fetch(url, { ...options, signal: controller.signal });
      if (!response.ok) {
        let detail = "";
        try {
          const errPayload = await response.json();
          detail = errPayload.detail || errPayload.message || "";
        } catch (_unused) {
          detail = "";
        }
        throw new Error(detail || `Request failed (${response.status})`);
      }
      return await response.json();
    } catch (error) {
      if (error.name === "AbortError") {
        throw new Error("Request timed out. Please try again.");
      }
      throw error;
    } finally {
      window.clearTimeout(timeoutId);
    }
  },

  loadSuggestions(context = "general", sentiment = "neutral", message = "") {
    const params = new URLSearchParams({
      context: context || "general",
      sentiment: sentiment || "neutral",
    });
    if ((message || "").trim()) {
      params.set("message", message.trim());
    }
    return api.fetchJson(`/api/suggestions?${params.toString()}`, {}, REQUEST_TIMEOUTS_MS.suggestions);
  },

  sendChat(message) {
    return api.fetchJson(
      "/api/chat",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      },
      REQUEST_TIMEOUTS_MS.chat,
    );
  },
};

const themeProvider = new ThemeProvider({ storageKey: STORAGE_KEYS.theme });
themeProvider.init();
const themeSnapshot = themeProvider.getSnapshot();

const layout = ChatLayout();
const header = ChatHeader({
  title: themeSnapshot.meta.appTitle,
  subtitle: themeSnapshot.meta.appSubtitle,
  modeLabels: themeSnapshot.meta.modeToggle,
});
const input = ChatInput({
  placeholder: themeSnapshot.meta.inputPlaceholder,
  label: themeSnapshot.meta.inputLabel,
  sendLabel: themeSnapshot.meta.sendLabel,
  retryLabel: themeSnapshot.meta.retryLabel,
  sendIcon: themeSnapshot.icons.send,
});
const supportPanel = SupportPanel({
  title: themeSnapshot.meta.supportPanelTitle,
  subtitle: themeSnapshot.meta.supportPanelSubtitle,
  icons: themeSnapshot.icons.supportCardSymbols,
  onSuggestion: (text) => {
    submitMessage(text);
  },
});
const visualizer = EmotionVisualizer();

layout.mountHeader(header.element);
layout.mountInput(input.element);
layout.mountSupportPanel(supportPanel.element);
layout.mountEmotionVisualizer(visualizer.element);

const appRoot = document.getElementById("appRoot");
if (appRoot) {
  appRoot.appendChild(layout.element);
}

const supportMediaQuery = window.matchMedia("(max-width: 960px)");
function syncResponsiveSupportPanel() {
  supportPanel.setCollapsed(supportMediaQuery.matches);
}
syncResponsiveSupportPanel();
supportMediaQuery.addEventListener("change", syncResponsiveSupportPanel);

themeProvider.subscribe((snapshot) => {
  header.setThemeMode(snapshot.mode);
  supportPanel.setTitle(snapshot.meta.supportPanelTitle);
});

header.onToggleTheme(() => {
  themeProvider.toggleMode();
});

input.onSubmit((rawValue) => {
  submitMessage(rawValue);
});

input.onRetry(() => {
  if (!state.lastFailedMessage) return;
  submitMessage(state.lastFailedMessage);
});

function setComposerBusy(isBusy) {
  state.inFlight = isBusy;
  input.setBusy(isBusy);
  input.setSendLabel(isBusy ? themeSnapshot.meta.sendingLabel : themeSnapshot.meta.sendLabel);
  supportPanel.setBusy(isBusy);
}

function renderMessage(entry, options = {}) {
  const node = ChatMessage(entry, options);
  layout.appendMessage(node);
}

function showTyping() {
  if (state.typingNode) return;
  const indicator = TypingIndicator({ label: themeSnapshot.meta.thinkingLabel });
  state.typingNode = indicator.element;
  layout.appendMessage(state.typingNode);
}

function hideTyping() {
  if (!state.typingNode) return;
  layout.removeNode(state.typingNode);
  state.typingNode = null;
}

function updateEmotionTheme({ context, sentiment }) {
  themeProvider.setEmotionSignals({
    context: context || "general",
    sentiment: sentiment || "neutral",
  });
}

function renderSupportSuggestions(suggestions, { interactive = true } = {}) {
  const list = Array.isArray(suggestions) ? suggestions : [];
  const fingerprint = JSON.stringify({ list, interactive });
  if (fingerprint === state.suggestionsFingerprint) return;
  state.suggestionsFingerprint = fingerprint;
  supportPanel.setSuggestions(list, { interactive });
}

async function refreshSuggestions(context = "general", sentiment = "neutral", message = "") {
  try {
    const data = await api.loadSuggestions(context, sentiment, message);
    renderSupportSuggestions(data.suggestions || []);
    updateEmotionTheme({ context: data.context || context, sentiment });
  } catch (_error) {
    renderSupportSuggestions([themeSnapshot.meta.unavailableSupportMessage], { interactive: false });
    renderMessage(
      {
        role: "bot",
        text: themeSnapshot.meta.supportRetryMessage,
        timestamp: new Date().toISOString(),
      },
      { kind: "system" },
    );
  }
}

async function submitMessage(providedMessage = null) {
  if (state.inFlight) return;

  const message = String(providedMessage ?? input.getValue()).trim();
  if (!message) return;

  state.lastFailedMessage = message;
  input.setRetryVisible(false);
  setComposerBusy(true);
  hideTyping();
  input.clear();

  renderMessage({
    role: "user",
    text: message,
    timestamp: new Date().toISOString(),
  });

  showTyping();

  try {
    const data = await api.sendChat(message);
    hideTyping();

    const resolvedContext = data.context || "general";
    const resolvedSentiment = data.sentiment || "neutral";
    updateEmotionTheme({ context: resolvedContext, sentiment: resolvedSentiment });

    renderMessage({
      role: "bot",
      text: data.reply || "",
      timestamp: data.timestamp || new Date().toISOString(),
    });

    if (Array.isArray(data.suggestions) && data.suggestions.length > 0) {
      renderSupportSuggestions(data.suggestions);
    }

    const suggestionBasis = String(data.reply || message || "").trim();
    refreshSuggestions(resolvedContext, resolvedSentiment, suggestionBasis);
    state.lastFailedMessage = null;
    input.setRetryVisible(false);
  } catch (error) {
    hideTyping();
    renderMessage(
      {
        role: "bot",
        text: error.message || themeSnapshot.meta.chatErrorMessage,
        timestamp: new Date().toISOString(),
      },
      { kind: "error" },
    );
    input.setRetryVisible(true);
  } finally {
    setComposerBusy(false);
    input.focus();
  }
}

function init() {
  localStorage.removeItem(LEGACY_HISTORY_STORAGE_KEY);
  updateEmotionTheme({ context: "general", sentiment: "neutral" });
  renderMessage({
    role: "bot",
    text: themeSnapshot.meta.welcomeMessage,
    timestamp: new Date().toISOString(),
  });
  refreshSuggestions("general", "neutral");
  input.focus();
}

init();
