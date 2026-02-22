const chatWindow = document.getElementById('chatWindow');
const chatForm = document.getElementById('chatForm');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const retryButton = document.getElementById('retryButton');
const suggestionsList = document.getElementById('suggestionsList');
const contextTag = document.getElementById('contextTag');
const themeToggle = document.getElementById('themeToggle');

const STORAGE_KEYS = {
  theme: 'happybot_theme',
};

const LEGACY_HISTORY_STORAGE_KEY = 'happybot_chat_history_v1';
const REQUEST_TIMEOUTS_MS = {
  chat: 90000,
  suggestions: 15000,
};

const state = {
  inFlight: false,
  lastFailedMessage: null,
  typingNode: null,
};

const api = {
  async fetchJson(url, options = {}, timeoutMs = 0) {
    const controller = new AbortController();
    const hasTimeout = Number.isFinite(timeoutMs) && timeoutMs > 0;
    const timeoutId = hasTimeout ? window.setTimeout(() => controller.abort(), timeoutMs) : null;

    try {
      const response = await fetch(url, { ...options, signal: controller.signal });
      if (!response.ok) {
        let detail = '';
        try {
          const errPayload = await response.json();
          detail = errPayload.detail || errPayload.message || '';
        } catch (_unused) {
          detail = '';
        }
        throw new Error(detail || `Request failed (${response.status})`);
      }
      return await response.json();
    } catch (error) {
      if (error.name === 'AbortError') {
        throw new Error('Request timed out. Please try again.');
      }
      throw error;
    } finally {
      window.clearTimeout(timeoutId);
    }
  },

  loadSuggestions(context = 'general', sentiment = 'neutral', message = '') {
    const params = new URLSearchParams({
      context: context || 'general',
      sentiment: sentiment || 'neutral',
    });
    if ((message || '').trim()) {
      params.set('message', message.trim());
    }
    return api.fetchJson(`/api/suggestions?${params.toString()}`, {}, REQUEST_TIMEOUTS_MS.suggestions);
  },

  sendChat(message) {
    return api.fetchJson(
      '/api/chat',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      },
      REQUEST_TIMEOUTS_MS.chat,
    );
  },
};

const ui = {
  setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_KEYS.theme, theme);
    themeToggle.setAttribute('aria-pressed', String(theme === 'dark'));
    themeToggle.textContent = theme === 'dark' ? 'Light Mode' : 'Dark Mode';
  },

  initTheme() {
    const savedTheme = localStorage.getItem(STORAGE_KEYS.theme);
    if (savedTheme === 'dark' || savedTheme === 'light') {
      ui.setTheme(savedTheme);
      return;
    }
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    ui.setTheme(prefersDark ? 'dark' : 'light');
  },

  formatTime(timestamp) {
    const parsed = new Date(timestamp);
    if (Number.isNaN(parsed.getTime())) {
      return '';
    }
    return parsed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  },

  buildMeta(entry) {
    const parts = [];
    if (entry.timestamp) parts.push(ui.formatTime(entry.timestamp));
    if (entry.sentiment) parts.push(`mood: ${entry.sentiment}`);
    if (entry.context) parts.push(`context: ${entry.context}`);
    return parts.join(' | ');
  },

  scrollChatToBottom() {
    chatWindow.scrollTop = chatWindow.scrollHeight;
  },

  renderMessage(entry, { kind = '' } = {}) {
    const messageNode = document.createElement('article');
    messageNode.classList.add('msg', entry.role);
    if (kind) {
      kind
        .split(' ')
        .filter(Boolean)
        .forEach((token) => messageNode.classList.add(token));
    }

    const body = document.createElement('div');
    body.className = 'msg-body';
    body.textContent = entry.text;
    messageNode.appendChild(body);

    const metaText = ui.buildMeta(entry);
    if (metaText) {
      const meta = document.createElement('div');
      meta.className = 'msg-meta';
      meta.textContent = metaText;
      messageNode.appendChild(meta);
    }

    chatWindow.appendChild(messageNode);
    ui.scrollChatToBottom();
  },

  showTyping() {
    if (state.typingNode) return;
    const typingNode = document.createElement('article');
    typingNode.className = 'msg bot typing';

    const body = document.createElement('div');
    body.className = 'msg-body';
    body.textContent = 'HappyBot is typing';

    const dots = document.createElement('span');
    dots.className = 'typing-dots';
    for (let i = 0; i < 3; i += 1) {
      dots.appendChild(document.createElement('span'));
    }

    body.appendChild(dots);
    typingNode.appendChild(body);
    chatWindow.appendChild(typingNode);
    state.typingNode = typingNode;
    ui.scrollChatToBottom();
  },

  hideTyping() {
    if (!state.typingNode) return;
    state.typingNode.remove();
    state.typingNode = null;
  },

  setComposerBusy(isBusy) {
    state.inFlight = isBusy;
    messageInput.disabled = isBusy;
    sendButton.disabled = isBusy;
    retryButton.disabled = isBusy;
    sendButton.textContent = isBusy ? 'Sending...' : 'Send';
    document.querySelectorAll('.suggestion-chip').forEach((chip) => {
      const isInteractive = chip.dataset.interactive === 'true';
      chip.disabled = isBusy || !isInteractive;
    });
  },

  showRetry(show) {
    retryButton.hidden = !show;
  },

  autoResizeInput() {
    messageInput.style.height = 'auto';
    const nextHeight = Math.min(messageInput.scrollHeight, 180);
    messageInput.style.height = `${nextHeight}px`;
  },

  renderSuggestions(context, suggestions, { interactive = true } = {}) {
    contextTag.textContent = context || 'general';
    suggestionsList.innerHTML = '';

    suggestions.forEach((item) => {
      const text = typeof item === 'string' ? item : String(item || '');
      if (!text.trim()) return;
      const li = document.createElement('li');
      const match = typeof text === 'string' ? text.match(/https?:\/\/[^\s]+/i) : null;
      const linkUrl = match ? match[0] : '';

      if (linkUrl) {
        const title = document.createElement('p');
        title.className = 'suggestion-text';
        title.textContent = text.replace(linkUrl, '').replace(/[:\-]\s*$/, '').trim() || 'Helpful resource';

        const link = document.createElement('a');
        link.className = 'suggestion-link';
        link.href = linkUrl;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = 'Open resource';

        li.appendChild(title);
        li.appendChild(link);
      } else {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'suggestion-chip';
        button.textContent = text;
        button.dataset.interactive = String(interactive);
        button.disabled = !interactive || state.inFlight;

        button.addEventListener('click', () => {
          if (state.inFlight) return;
          controller.submitMessage(text);
        });

        li.appendChild(button);
      }

      suggestionsList.appendChild(li);
    });
  },
};

const controller = {
  async refreshSuggestions(context = 'general', sentiment = 'neutral', message = '') {
    try {
      const data = await api.loadSuggestions(context, sentiment, message);
      ui.renderSuggestions(data.context || 'general', data.suggestions || []);
    } catch (error) {
      ui.renderSuggestions(
        'general',
        ['Suggestions unavailable right now. Send a message to refresh.'],
        { interactive: false },
      );
      ui.renderMessage(
        {
          role: 'bot',
          text: 'I could not load suggestions right now, but chat is still available.',
          timestamp: new Date().toISOString(),
        },
        { kind: 'system error' },
      );
    }
  },

  async submitMessage(providedMessage = null) {
    if (state.inFlight) return;
    const message = (providedMessage ?? messageInput.value).trim();
    if (!message) return;

    state.lastFailedMessage = message;
    ui.showRetry(false);
    ui.setComposerBusy(true);
    ui.hideTyping();

    messageInput.value = '';
    ui.autoResizeInput();

    ui.renderMessage({
      role: 'user',
      text: message,
      timestamp: new Date().toISOString(),
    });

    ui.showTyping();

    try {
      const data = await api.sendChat(message);
      ui.hideTyping();
      const resolvedContext = data.context || 'general';
      const resolvedSentiment = data.sentiment || 'neutral';
      ui.renderMessage({
        role: 'bot',
        text: data.reply || '',
        // Use client clock for consistent local-time display in UI.
        timestamp: new Date().toISOString(),
        sentiment: resolvedSentiment,
        context: resolvedContext,
      });
      if (Array.isArray(data.suggestions) && data.suggestions.length > 0) {
        ui.renderSuggestions(resolvedContext, data.suggestions);
      }
      await controller.refreshSuggestions(resolvedContext, resolvedSentiment, message);
      state.lastFailedMessage = null;
      ui.showRetry(false);
    } catch (error) {
      ui.hideTyping();
      ui.renderMessage(
        {
          role: 'bot',
          text: error.message || 'I hit a connection issue. Please try again.',
          timestamp: new Date().toISOString(),
        },
        { kind: 'error' },
      );
      ui.showRetry(true);
    } finally {
      ui.setComposerBusy(false);
      messageInput.focus();
    }
  },

  init() {
    localStorage.removeItem(LEGACY_HISTORY_STORAGE_KEY);
    ui.initTheme();
    ui.autoResizeInput();
    ui.renderMessage({
      role: 'bot',
      text: 'Hi, I am HappyBot. Talk to me casually, ask for a joke, or ask for help sorting your thoughts.',
      timestamp: new Date().toISOString(),
      context: 'general',
    });
    controller.refreshSuggestions('general', 'neutral');
  },
};

chatForm.addEventListener('submit', (event) => {
  event.preventDefault();
  controller.submitMessage();
});

messageInput.addEventListener('input', ui.autoResizeInput);

messageInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    if (typeof chatForm.requestSubmit === 'function') {
      chatForm.requestSubmit();
    } else {
      chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
    }
  }
});

retryButton.addEventListener('click', () => {
  if (!state.lastFailedMessage) return;
  controller.submitMessage(state.lastFailedMessage);
});

themeToggle.addEventListener('click', () => {
  const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
  ui.setTheme(currentTheme === 'dark' ? 'light' : 'dark');
});

controller.init();
