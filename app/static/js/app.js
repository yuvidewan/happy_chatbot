const chatWindow = document.getElementById('chatWindow');
const chatForm = document.getElementById('chatForm');
const messageInput = document.getElementById('messageInput');
const suggestionsList = document.getElementById('suggestionsList');
const contextTag = document.getElementById('contextTag');
const themeToggle = document.getElementById('themeToggle');

function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('happybot_theme', theme);
  themeToggle.textContent = theme === 'dark' ? 'Light Mode' : 'Dark Mode';
}

function initTheme() {
  const saved = localStorage.getItem('happybot_theme');
  if (saved === 'dark' || saved === 'light') {
    setTheme(saved);
    return;
  }

  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  setTheme(prefersDark ? 'dark' : 'light');
}

function addMessage(role, text) {
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  div.textContent = text;
  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function renderSuggestions(context, suggestions) {
  contextTag.textContent = context;
  suggestionsList.innerHTML = '';
  suggestions.forEach((item) => {
    const li = document.createElement('li');
    li.textContent = item;
    suggestionsList.appendChild(li);
  });
}

async function loadSuggestions() {
  const res = await fetch('/api/suggestions');
  const data = await res.json();
  renderSuggestions(data.context, data.suggestions);
}

chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const message = messageInput.value.trim();
  if (!message) return;

  addMessage('user', message);
  messageInput.value = '';

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });

    if (!res.ok) {
      throw new Error('Chat request failed');
    }

    const data = await res.json();
    addMessage('bot', data.reply);
    renderSuggestions(data.context || 'general', data.suggestions);
  } catch (err) {
    addMessage('bot', 'I hit a connection issue. Please try again.');
  }
});

themeToggle.addEventListener('click', () => {
  const current = document.documentElement.getAttribute('data-theme') || 'light';
  setTheme(current === 'dark' ? 'light' : 'dark');
});

initTheme();
addMessage('bot', 'Hi, I am HappyBot. Talk to me casually, ask for a joke, or ask for help sorting your thoughts.');
loadSuggestions();
