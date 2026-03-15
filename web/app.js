const API_BASE = window.location.origin;

let token = localStorage.getItem('token');
let username = localStorage.getItem('username');
let requiresPasswordChange = false;
let currentConv = null;
let ws = null;

const loginScreen = document.getElementById('login-screen');
const chatScreen = document.getElementById('chat-screen');
const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');
const changePasswordModal = document.getElementById('change-password-modal');
const changePasswordForm = document.getElementById('change-password-form');
const dismissPasswordBtn = document.getElementById('dismiss-password');
const userDisplay = document.getElementById('user-display');
const logoutBtn = document.getElementById('logout-btn');
const dmList = document.getElementById('dm-list');
const roomList = document.getElementById('room-list');
const newDmUser = document.getElementById('new-dm-user');
const startDmBtn = document.getElementById('start-dm');
const newRoomName = document.getElementById('new-room-name');
const createRoomBtn = document.getElementById('create-room');
const noConversation = document.getElementById('no-conversation');
const conversation = document.getElementById('conversation');
const messagesEl = document.getElementById('messages');
const sendForm = document.getElementById('send-form');
const messageInput = document.getElementById('message-input');

function showScreen(screen) {
  loginScreen.style.display = screen === 'login' ? 'block' : 'none';
  chatScreen.style.display = screen === 'chat' ? 'block' : 'none';
}

function api(url, options = {}) {
  const headers = { ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }
  return fetch(API_BASE + url, { ...options, headers });
}

async function apiJson(url, options = {}) {
  const res = await api(url, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

function connectWebSocket() {
  if (ws) ws.close();
  const url = `${API_BASE.replace(/^http/, 'ws')}/ws?token=${encodeURIComponent(token)}`;
  ws = new WebSocket(url);
  ws.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.type === 'message' && currentConv &&
        data.conversation_type === currentConv.type &&
        data.conversation_id === currentConv.id) {
      appendMessage(data.message);
    }
  };
  ws.onclose = () => setTimeout(connectWebSocket, 3000);
}

function appendMessage(msg) {
  const div = document.createElement('div');
  div.className = 'message ' + (msg.sender_username === username ? 'own' : 'other');
  div.innerHTML = `<span class="sender">${escapeHtml(msg.sender_username)}</span>${escapeHtml(msg.content)}`;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  loginError.textContent = '';
  try {
    const body = {
      username: document.getElementById('login-username').value,
      password: document.getElementById('login-password').value,
    };
    const data = await apiJson('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(body),
    });
    token = data.access_token;
    username = body.username;
    requiresPasswordChange = data.requires_password_change || false;
    localStorage.setItem('token', token);
    localStorage.setItem('username', username);
    userDisplay.textContent = username;
    showScreen('chat');
    loadConversations();
    connectWebSocket();
    if (requiresPasswordChange) {
      changePasswordModal.style.display = 'flex';
    }
  } catch (err) {
    loginError.textContent = err.message;
  }
});

dismissPasswordBtn.addEventListener('click', () => {
  changePasswordModal.style.display = 'none';
});

changePasswordForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const current = document.getElementById('current-password').value;
  const newPwd = document.getElementById('new-password').value;
  const confirm = document.getElementById('confirm-password').value;
  if (newPwd !== confirm) {
    alert('New passwords do not match');
    return;
  }
  try {
    await apiJson('/api/auth/change-password', {
      method: 'PUT',
      body: JSON.stringify({ current_password: current, new_password: newPwd }),
    });
    changePasswordModal.style.display = 'none';
    requiresPasswordChange = false;
  } catch (err) {
    alert(err.message);
  }
});

logoutBtn.addEventListener('click', () => {
  token = null;
  username = null;
  localStorage.removeItem('token');
  localStorage.removeItem('username');
  if (ws) ws.close();
  ws = null;
  showScreen('login');
});

async function loadConversations() {
  try {
    const [dms, rooms] = await Promise.all([
      apiJson('/api/dms'),
      apiJson('/api/rooms'),
    ]);
    dmList.innerHTML = dms.map(d => `<li data-type="dm" data-id="${d.id}" data-name="${escapeHtml(d.other_username)}">${escapeHtml(d.other_username)}</li>`).join('');
    roomList.innerHTML = rooms.map(r => `<li data-type="room" data-id="${r.id}" data-name="${escapeHtml(r.name)}">${escapeHtml(r.name)}</li>`).join('');

    dmList.querySelectorAll('li').forEach(li => li.addEventListener('click', () => selectConversation('dm', li.dataset.id, li.dataset.name)));
    roomList.querySelectorAll('li').forEach(li => li.addEventListener('click', () => selectConversation('room', li.dataset.id, li.dataset.name)));
  } catch (err) {
    console.error(err);
  }
}

async function selectConversation(type, id, name) {
  currentConv = { type, id: parseInt(id), name };
  document.querySelectorAll('#sidebar li.active').forEach(li => li.classList.remove('active'));
  document.querySelector(`#sidebar li[data-type="${type}"][data-id="${id}"]`)?.classList.add('active');
  noConversation.style.display = 'none';
  conversation.style.display = 'flex';

  const endpoint = type === 'dm' ? `/api/dms/${id}/messages` : `/api/rooms/${id}/messages`;
  const data = await apiJson(endpoint);
  messagesEl.innerHTML = '';
  data.messages.forEach(appendMessage);
}

sendForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!currentConv || !messageInput.value.trim()) return;
  const content = messageInput.value.trim();
  messageInput.value = '';
  try {
    const endpoint = currentConv.type === 'dm'
      ? `/api/dms/${currentConv.id}/messages`
      : `/api/rooms/${currentConv.id}/messages`;
    const msg = await apiJson(endpoint, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
    appendMessage(msg);
  } catch (err) {
    alert(err.message);
  }
});

startDmBtn.addEventListener('click', async () => {
  const username = newDmUser.value.trim();
  if (!username) return;
  try {
    const data = await apiJson('/api/dms', {
      method: 'POST',
      body: JSON.stringify({ target_username: username }),
    });
    newDmUser.value = '';
    await loadConversations();
    selectConversation('dm', data.id, data.other_username);
  } catch (err) {
    alert(err.message);
  }
});

createRoomBtn.addEventListener('click', async () => {
  const name = newRoomName.value.trim();
  if (!name) return;
  try {
    const data = await apiJson('/api/rooms', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
    newRoomName.value = '';
    await loadConversations();
    selectConversation('room', data.id, data.name);
  } catch (err) {
    alert(err.message);
  }
});

if (token && username) {
  api('/api/dms').then(res => {
    if (res.ok) {
      userDisplay.textContent = username;
      showScreen('chat');
      loadConversations();
      connectWebSocket();
    } else {
      token = null;
      username = null;
      localStorage.removeItem('token');
      localStorage.removeItem('username');
      showScreen('login');
    }
  });
} else {
  token = null;
  username = null;
  showScreen('login');
}
