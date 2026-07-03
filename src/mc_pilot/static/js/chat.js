const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const pilotInput = document.getElementById("pilot-input");
const sendBtn = document.getElementById("send-btn");
const newChatBtn = document.getElementById("new-chat-btn");
const deathToast = document.getElementById("death-toast");
const deathText = document.getElementById("death-text");
const apiDot = document.getElementById("api-dot");
const apiStatusText = document.getElementById("api-status-text");
const gameDot = document.getElementById("game-dot");
const gameStatusText = document.getElementById("game-status-text");
const gameDetail = document.getElementById("game-detail");
const gamePlayer = document.getElementById("game-player");
const gameVersion = document.getElementById("game-version");
const reconnectBtn = document.getElementById("reconnect-btn");
const sidebarToggle = document.getElementById("sidebar-toggle");
const sidebar = document.getElementById("sidebar");
const sidebarOverlay = document.getElementById("sidebar-overlay");

let ws = null;
let deathTimer = null;
let reconnectTimer = null;
let reconnectAttempts = 0;
let shuttingDown = false;
let hasMessages = false;
const MAX_RECONNECT_ATTEMPTS = 8;

marked.setOptions({ breaks: false, gfm: true });

function renderMarkdown(text) {
  const raw = marked.parse(String(text));
  return DOMPurify.sanitize(raw, {
    ALLOWED_TAGS: [
      "h1", "h2", "h3", "h4", "h5", "h6",
      "p", "br", "hr",
      "ul", "ol", "li",
      "strong", "em", "del", "code", "pre",
      "blockquote",
      "table", "thead", "tbody", "tr", "th", "td",
      "a", "img",
    ],
    ALLOWED_ATTR: ["href", "src", "alt", "title", "target"],
  });
}

function hideWelcome() {
  const welcome = chatLog.querySelector(".chat-welcome");
  if (welcome) welcome.remove();
}

function addMessage(role, text) {
  hideWelcome();
  hasMessages = true;
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const roleLabel = document.createElement("div");
  roleLabel.className = "message-role";
  roleLabel.textContent = role === "user" ? "你" : "Pilot";

  const body = document.createElement("div");
  body.className = "message-body";

  if (role === "user") {
    body.textContent = String(text);
  } else {
    body.innerHTML = renderMarkdown(String(text));
  }

  article.append(roleLabel, body);
  chatLog.appendChild(article);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function addSystemMessage(text) {
  const article = document.createElement("article");
  article.className = "message system";
  const body = document.createElement("div");
  body.className = "message-body";
  body.textContent = String(text);
  article.appendChild(body);
  chatLog.appendChild(article);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function showTyping() {
  hideWelcome();
  const indicator = document.createElement("div");
  indicator.className = "message pilot typing-indicator";
  indicator.id = "typing";
  for (let i = 0; i < 3; i++) {
    const dot = document.createElement("span");
    indicator.appendChild(dot);
  }
  chatLog.appendChild(indicator);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function hideTyping() {
  const el = document.getElementById("typing");
  if (el) el.remove();
}

async function sendMessage(message) {
  addMessage("user", message);
  pilotInput.disabled = true;
  sendBtn.disabled = true;
  showTyping();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    hideTyping();
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      addMessage("pilot", "错误: " + (err.detail || "请求失败"));
      return;
    }
    const data = await res.json();
    addMessage("pilot", data.answer || "(无回复)");
    if (data.stop_reason) {
      addSystemMessage("[系统提示: " + data.stop_reason + "]");
    }
  } catch (e) {
    hideTyping();
    addMessage("pilot", "网络错误，请确认后端已启动。");
  } finally {
    pilotInput.disabled = false;
    sendBtn.disabled = false;
    pilotInput.focus();
  }
}

function clearChat() {
  chatLog.replaceChildren();
  const welcome = document.createElement("div");
  welcome.className = "chat-welcome";
  welcome.innerHTML =
    '<div class="welcome-icon">&#9752;</div>' +
    '<h2>Minecraft Pilot 已就位</h2>' +
    '<p>输入 <code>/pilot help</code> 查看命令，或直接提问。</p>';
  chatLog.appendChild(welcome);
  hasMessages = false;
}

function showDeathToast(advice) {
  deathText.textContent = String(advice.advice);
  deathToast.hidden = false;
  deathToast.style.opacity = "1";
  if (deathTimer) clearTimeout(deathTimer);
  deathTimer = setTimeout(() => {
    deathToast.style.opacity = "0";
    setTimeout(() => {
      deathToast.hidden = true;
      deathToast.style.opacity = "";
    }, 500);
  }, 12000);
}

function connectWebSocket() {
  if (
    shuttingDown ||
    ws?.readyState === WebSocket.OPEN ||
    ws?.readyState === WebSocket.CONNECTING
  ) {
    return;
  }
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(proto + "//" + location.host + "/ws");
  ws.onopen = () => {
    reconnectAttempts = 0;
    updateApiStatus("ready");
  };
  ws.onclose = () => {
    ws = null;
    updateApiStatus("degraded");
    scheduleReconnect();
  };
  ws.onerror = () => updateApiStatus("degraded");
  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (isDeathAdvice(data)) showDeathToast(data);
      else if (isStateEvent(data)) updateGameStatus(data);
    } catch (_error) {
      /* ignore */
    }
  };
}

function scheduleReconnect() {
  if (shuttingDown || reconnectTimer || reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) return;
  const delay = Math.min(1000 * 2 ** reconnectAttempts, 30000);
  reconnectAttempts += 1;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connectWebSocket();
  }, delay);
}

function isDeathAdvice(data) {
  return data?.type === "death_advice" && typeof data.advice === "string";
}

function isStateEvent(data) {
  return data?.type === "state" && typeof data.state === "string";
}

function updateApiStatus(state) {
  apiDot.dataset.state = state;
  const labels = { ready: "就绪", degraded: "降级", connecting: "连接中", disconnected: "离线" };
  apiStatusText.textContent = labels[state] || state;
}

function updateGameStatus(data) {
  if (data.state === "connected") {
    gameDot.dataset.state = "ready";
    gameStatusText.textContent = "已连接游戏";
    gamePlayer.textContent = data.player_name || "";
    gameVersion.textContent = data.version_id || "";
    gameDetail.hidden = false;
  } else {
    gameDot.dataset.state = "disconnected";
    gameStatusText.textContent = "未连接游戏";
    gameDetail.hidden = true;
  }
}

async function fetchGameState() {
  try {
    const res = await fetch("/api/game-state", { signal: AbortSignal.timeout(3000) });
    if (res.ok) {
      const data = await res.json();
      updateGameStatus(data);
    }
  } catch (_error) {
    /* ignore */
  }
}

async function reconnectGame() {
  reconnectBtn.disabled = true;
  reconnectBtn.textContent = "扫描中…";
  try {
    const res = await fetch("/api/game-state/reconnect", {
      method: "POST",
      signal: AbortSignal.timeout(8000),
    });
    if (res.ok) {
      const data = await res.json();
      updateGameStatus(data);
    }
  } catch (_error) {
    /* ignore */
  } finally {
    reconnectBtn.disabled = false;
    reconnectBtn.textContent = "重连游戏日志";
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const msg = pilotInput.value.trim();
  if (!msg) return;
  pilotInput.value = "";
  pilotInput.style.height = "auto";
  sendMessage(msg);
});

pilotInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    chatForm.dispatchEvent(new Event("submit"));
  }
});

pilotInput.addEventListener("input", () => {
  pilotInput.style.height = "auto";
  pilotInput.style.height = Math.min(pilotInput.scrollHeight, 160) + "px";
});

newChatBtn.addEventListener("click", async () => {
  try {
    await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "/pilot clear" }),
    });
    clearChat();
    pilotInput.focus();
  } catch (_error) {
    clearChat();
    pilotInput.focus();
  }
});

document.querySelectorAll(".cmd-chip").forEach((btn) => {
  btn.addEventListener("click", () => {
    const cmd = btn.dataset.cmd;
    if (cmd) {
      pilotInput.value = cmd;
      chatForm.dispatchEvent(new Event("submit"));
    }
  });
});

sidebarToggle.addEventListener("click", () => {
  sidebar.classList.toggle("open");
  const isOpen = sidebar.classList.contains("open");
  sidebarOverlay.hidden = !isOpen;
  sidebarToggle.setAttribute("aria-expanded", String(isOpen));
});

sidebarOverlay.addEventListener("click", () => {
  sidebar.classList.remove("open");
  sidebarOverlay.hidden = true;
  sidebarToggle.setAttribute("aria-expanded", "false");
});

async function checkHealth() {
  try {
    const res = await fetch("/health/ready", { signal: AbortSignal.timeout(3000) });
    const data = await res.json();
    updateApiStatus(data.status === "ready" ? "ready" : "degraded");
  } catch (_error) {
    updateApiStatus("degraded");
  }
}

checkHealth();
fetchGameState();
connectWebSocket();

reconnectBtn.addEventListener("click", reconnectGame);

window.addEventListener("pagehide", () => {
  shuttingDown = true;
  if (reconnectTimer) clearTimeout(reconnectTimer);
  ws?.close();
});
