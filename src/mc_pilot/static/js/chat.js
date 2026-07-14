const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const pilotInput = document.getElementById("pilot-input");
const sendBtn = document.getElementById("send-btn");
const newChatBtn = document.getElementById("new-chat-btn");
const conversationList = document.getElementById("conversation-list");
const conversationListSection = document.getElementById("conversation-list-section");
const contextIndicator = document.getElementById("context-indicator");
const contextCircle = document.getElementById("context-circle");
const contextLabel = document.getElementById("context-label");
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
let activeConversationId = "";
let contextPercent = 0;
let tokensUsed = 0;
let tokensLimit = 0;
let activeThinkingId = null;
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
  return article;
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

function createThinkingBlock() {
  hideWelcome();
  hasMessages = true;

  // Complete any previous unfinished thinking block
  if (activeThinkingId) {
    completePreviousThinking("(上一轮对话已被新消息取代)");
  }

  const uid = "thinking-" + Date.now();
  activeThinkingId = uid;

  const block = document.createElement("div");
  block.className = "thinking-block";
  block.id = uid;

  const header = document.createElement("div");
  header.className = "thinking-header";
  header.innerHTML =
    '<span class="thinking-spinner"></span>' +
    '<span class="thinking-label">正在处理…</span>';
  block.appendChild(header);

  const steps = document.createElement("div");
  steps.className = "thinking-steps";
  block.appendChild(steps);

  chatLog.appendChild(block);
  chatLog.scrollTop = chatLog.scrollHeight;
  return block;
}

function addThinkingStep(icon, text, cls) {
  if (!activeThinkingId) return;
  const block = document.getElementById(activeThinkingId);
  if (!block) return;
  const steps = block.querySelector(".thinking-steps");
  if (!steps) return;

  const step = document.createElement("div");
  step.className = `thinking-step ${cls || ""}`;

  const iconEl = document.createElement("span");
  iconEl.className = "step-icon";
  iconEl.textContent = icon;

  const textEl = document.createElement("span");
  textEl.className = "step-text";
  textEl.textContent = text;

  step.append(iconEl, textEl);
  steps.appendChild(step);

  chatLog.scrollTop = chatLog.scrollHeight;
  return step;
}

function updateThinkingLabel(text) {
  if (!activeThinkingId) return;
  const block = document.getElementById(activeThinkingId);
  if (!block) return;
  const label = block.querySelector(".thinking-label");
  if (label) label.textContent = text;
}

function finishThinking(answerText) {
  if (!activeThinkingId) return;
  const block = document.getElementById(activeThinkingId);
  if (!block) return;

  const spinner = block.querySelector(".thinking-spinner");
  if (spinner) spinner.style.display = "none";

  block.classList.add("thinking-done");

  if (answerText) {
    const answer = document.createElement("div");
    answer.className = "message-body thinking-answer";
    answer.innerHTML = renderMarkdown(String(answerText));
    block.appendChild(answer);
  }

  chatLog.scrollTop = chatLog.scrollHeight;
  activeThinkingId = null;
}

function completePreviousThinking(text) {
  const oldId = activeThinkingId;
  activeThinkingId = null;
  if (!oldId) return;
  const block = document.getElementById(oldId);
  if (!block) return;

  const spinner = block.querySelector(".thinking-spinner");
  if (spinner) spinner.style.display = "none";

  block.classList.add("thinking-done");
  const answer = document.createElement("div");
  answer.className = "message-body thinking-answer";
  answer.innerHTML = renderMarkdown(String(text));
  block.appendChild(answer);
}

function removeThinkingBlock() {
  if (activeThinkingId) {
    const block = document.getElementById(activeThinkingId);
    if (block) block.remove();
    activeThinkingId = null;
  }
}

async function checkOrCreateConversation() {
  if (activeThinkingId) {
    completePreviousThinking("");
    removeThinkingBlock();
  }
  if (!activeConversationId) {
    try {
      const res = await fetch("/api/conversations", { method: "POST" });
      if (res.ok) {
        const conv = await res.json();
        activeConversationId = conv.id;
        refreshConversationList();
      }
    } catch (_e) {
      /* proceed without */
    }
  }
}

async function sendMessageStream(message) {
  await checkOrCreateConversation();

  addMessage("user", message);
  pilotInput.disabled = true;
  sendBtn.disabled = true;

  const thinkingBlock = createThinkingBlock();

  try {
    const res = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        conversation_id: activeConversationId,
      }),
    });

    if (!res.ok) {
      removeThinkingBlock();
      const err = await res.json().catch(() => ({}));
      addMessage("pilot", "错误: " + (err.detail || "请求失败"));
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalAnswer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith("data: ")) continue;
        const dataStr = trimmed.slice(6);
        if (dataStr === "[DONE]") continue;

        try {
          const event = JSON.parse(dataStr);
          handleStreamEvent(event);

          if (event.type === "done" || event.type === "result") {
            finalAnswer = event.answer || finalAnswer;
          }
        } catch (_e) {
          /* ignore parse errors */
        }
      }
    }

    finishThinking(finalAnswer);
    refreshConversationList();
  } catch (e) {
    removeThinkingBlock();
    addMessage("pilot", "网络错误，请确认后端已启动。");
  } finally {
    pilotInput.disabled = false;
    sendBtn.disabled = false;
    pilotInput.focus();
  }
}

function handleStreamEvent(event) {
  switch (event.type) {
    case "status":
      updateThinkingLabel(event.text || "处理中…");
      break;
    case "thinking":
      updateThinkingLabel(event.text || "思考中…");
      break;
    case "tool_start": {
      const icon =
        event.name === "wiki_search" ? "🔍" :
        event.name === "recipe_query" ? "📋" : "🔧";
      addThinkingStep(icon, event.label || event.name, "tool-running");
      break;
    }
    case "tool_end": {
      if (!activeThinkingId) break;
      const block = document.getElementById(activeThinkingId);
      const last = block?.querySelector(".thinking-steps")?.lastElementChild;
      if (last) {
        last.classList.remove("tool-running");
        last.classList.add(event.success ? "success" : "error");
      }
      break;
    }
    case "error":
      addThinkingStep("❌", event.message || "未知错误", "error");
      break;
    case "done":
    case "result":
      updateThinkingLabel("完成");
      updateContextFromEvent(event);
      break;
  }
}

function updateContextFromEvent(event) {
  if (typeof event.tokens_used === "number" && typeof event.tokens_limit === "number") {
    tokensUsed = event.tokens_used;
    tokensLimit = event.tokens_limit;
    contextPercent = Math.min(100, Math.round((event.tokens_used / event.tokens_limit) * 100));
    updateContextDisplay();
  }
}

function updateContextDisplay() {
  if (!contextCircle) return;

  const circumference = 2 * Math.PI * 14;
  const offset = circumference - (contextPercent / 100) * circumference;
  contextCircle.style.strokeDasharray = circumference + " " + circumference;
  contextCircle.style.strokeDashoffset = String(offset);

  let color = "var(--accent)";
  if (contextPercent > 95) color = "var(--danger)";
  else if (contextPercent > 80) color = "#ffd484";
  contextCircle.style.stroke = color;

  contextLabel.textContent = contextPercent + "%";
}

async function sendMessage(message) {
  sendMessageStream(message);
}

async function loadConversation(conv) {
  if (activeThinkingId) {
    completePreviousThinking("(切换到其他对话)");
  }
  try {
    const res = await fetch("/api/conversations/" + conv.id);
    if (!res.ok) return;
    const data = await res.json();
    clearChat();

    const messages = data.messages || [];
    for (const m of messages) {
      if (m.role === "user") {
        addMessage("user", m.content);
      } else if (m.role === "assistant") {
        addMessage("pilot", m.content);
      }
    }

    activeConversationId = conv.id;
    highlightActiveConversation();
    chatLog.scrollTop = chatLog.scrollHeight;
  } catch (_e) {
    /* ignore */
  }
}

async function createNewConversation() {
  if (activeThinkingId) {
    completePreviousThinking("(已创建新对话)");
  }
  try {
    const res = await fetch("/api/conversations", { method: "POST" });
    if (!res.ok) return;
    const conv = await res.json();
    activeConversationId = conv.id;
    clearChat();
    contextPercent = 0;
    tokensUsed = 0;
    tokensLimit = 0;
    updateContextDisplay();
    refreshConversationList();
    pilotInput.focus();
  } catch (_e) {
    clearChat();
    activeConversationId = "";
    contextPercent = 0;
    updateContextDisplay();
    pilotInput.focus();
  }
}

async function refreshConversationList() {
  try {
    const res = await fetch("/api/conversations");
    if (!res.ok) return;
    const list = await res.json();

    conversationListSection.hidden = list.length === 0;

    conversationList.replaceChildren();
    for (const conv of list) {
      const item = document.createElement("div");
      item.className = "conversation-item";
      if (conv.id === activeConversationId) {
        item.classList.add("active");
      }
      item.dataset.id = conv.id;

      const title = document.createElement("span");
      title.className = "conversation-title";
      title.textContent = conv.title || "新对话";

      const deleteBtn = document.createElement("button");
      deleteBtn.className = "conversation-delete";
      deleteBtn.innerHTML = "&times;";
      deleteBtn.title = "删除对话";
      deleteBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        await deleteConversation(conv.id);
      });

      item.appendChild(title);
      item.appendChild(deleteBtn);

      item.addEventListener("click", () => loadConversation(conv));

      conversationList.appendChild(item);
    }
  } catch (_e) {
    /* ignore */
  }
}

function highlightActiveConversation() {
  conversationList.querySelectorAll(".conversation-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.id === activeConversationId);
  });
}

async function deleteConversation(convId) {
  try {
    await fetch("/api/conversations/" + convId, { method: "DELETE" });
    if (activeConversationId === convId) {
      activeConversationId = "";
      clearChat();
      contextPercent = 0;
      updateContextDisplay();
    }
    refreshConversationList();
  } catch (_e) {
    /* ignore */
  }
}

function clearChat() {
  activeThinkingId = null;
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
  const labels = {
    ready: "就绪", degraded: "降级",
    connecting: "连接中", disconnected: "离线",
  };
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

newChatBtn.addEventListener("click", createNewConversation);

document.querySelectorAll(".suggest-chip").forEach((btn) => {
  btn.addEventListener("click", () => {
    const prompt = btn.dataset.prompt;
    if (prompt) {
      pilotInput.value = prompt;
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
refreshConversationList();

reconnectBtn.addEventListener("click", reconnectGame);

window.addEventListener("pagehide", () => {
  shuttingDown = true;
  if (reconnectTimer) clearTimeout(reconnectTimer);
  ws?.close();
});
