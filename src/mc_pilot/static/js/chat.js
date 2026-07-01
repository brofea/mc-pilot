const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const pilotInput = document.getElementById("pilot-input");
const sendBtn = document.getElementById("send-btn");
const deathBubble = document.getElementById("death-bubble");
const gameStatus = document.getElementById("game-status");
const apiStatus = document.getElementById("api-status");
const recipeSection = document.getElementById("recipe-section");
const recipeContent = document.getElementById("recipe-content");
const recipeCloseBtn = document.getElementById("recipe-close-btn");

let ws = null;
let deathTimer = null;
let reconnectTimer = null;
let reconnectAttempts = 0;
let shuttingDown = false;
const MAX_RECONNECT_ATTEMPTS = 8;

function addMessage(role, text) {
  const li = document.createElement("li");
  li.className = role === "user" ? "user-message" : "pilot-message";
  li.textContent = String(text);
  chatLog.appendChild(li);
  chatLog.scrollTop = chatLog.scrollHeight;
}

async function sendMessage(message) {
  addMessage("user", message);
  pilotInput.disabled = true;
  sendBtn.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    if (!res.ok) {
      const err = await res.json();
      addMessage("pilot", "错误: " + (err.detail || "请求失败"));
      return;
    }
    const data = await res.json();
    addMessage("pilot", data.answer || "(无回复)");
    if (data.stop_reason) {
      addMessage("pilot", "[系统提示: " + data.stop_reason + "]");
    }
  } catch (e) {
    addMessage("pilot", "网络错误，请确认后端已启动。");
  } finally {
    pilotInput.disabled = false;
    sendBtn.disabled = false;
    pilotInput.focus();
  }
}

function showDeathBubble(advice) {
  deathBubble.replaceChildren();
  const heading = document.createElement("strong");
  heading.textContent = "死亡事件";
  const message = document.createElement("span");
  message.textContent = String(advice.advice);
  deathBubble.append(heading, document.createElement("br"), message);
  deathBubble.hidden = false;
  if (deathTimer) clearTimeout(deathTimer);
  deathTimer = setTimeout(() => {
    deathBubble.style.opacity = "0";
    setTimeout(() => { deathBubble.hidden = true; deathBubble.style.opacity = ""; }, 500);
  }, 12000);
}

function connectWebSocket() {
  if (shuttingDown || ws?.readyState === WebSocket.OPEN || ws?.readyState === WebSocket.CONNECTING) {
    return;
  }
  const proto = location.protocol === "https:" ? "wss:" : "ws:";
  ws = new WebSocket(proto + "//" + location.host + "/ws");
  ws.onopen = () => {
    reconnectAttempts = 0;
    updateApiStatus("ready", "已连接");
  };
  ws.onclose = () => {
    ws = null;
    updateApiStatus("degraded", "断开");
    scheduleReconnect();
  };
  ws.onerror = () => updateApiStatus("degraded", "连接错误");
  ws.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (isDeathAdvice(data)) showDeathBubble(data);
      else if (isStateEvent(data)) updateGameStatus(data);
      else if (data?.type !== "pong") updateApiStatus("degraded", "消息格式错误");
    } catch (_error) {
      updateApiStatus("degraded", "消息格式错误");
    }
  };
}

function scheduleReconnect() {
  if (shuttingDown || reconnectTimer || reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) return;
  const delay = Math.min(1000 * (2 ** reconnectAttempts), 30000);
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

function updateApiStatus(state, label) {
  apiStatus.dataset.state = state;
  apiStatus.textContent = label;
}

function updateGameStatus(data) {
  if (data.state === "connected") {
    gameStatus.dataset.state = "ready";
    gameStatus.textContent = (data.player_name || "玩家") + " · " + (data.version_id || "");
  } else {
    gameStatus.dataset.state = "degraded";
    gameStatus.textContent = "未连接游戏";
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const msg = pilotInput.value.trim();
  if (!msg) return;
  pilotInput.value = "";
  sendMessage(msg);
});

recipeCloseBtn?.addEventListener("click", () => {
  recipeSection.hidden = true;
});

async function checkHealth() {
  try {
    const res = await fetch("/health/ready", { signal: AbortSignal.timeout(3000) });
    const data = await res.json();
    updateApiStatus(data.status === "ready" ? "ready" : "degraded",
      data.status === "ready" ? "就绪" : "降级");
  } catch (_) {
    updateApiStatus("degraded", "后端离线");
  }
}

checkHealth();
connectWebSocket();

window.addEventListener("pagehide", () => {
  shuttingDown = true;
  if (reconnectTimer) clearTimeout(reconnectTimer);
  ws?.close();
});
