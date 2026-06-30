const diagOutput = document.getElementById("diag-output");

const panels = {
  sys: { el: document.getElementById("sys-data"), endpoint: "/admin/api/status" },
  game: { el: document.getElementById("game-data"), endpoint: "/admin/api/game" },
  recipe: { el: document.getElementById("recipe-data"), endpoint: "/admin/api/recipes" },
  rag: { el: document.getElementById("rag-data"), endpoint: "/admin/api/rag" },
  llm: { el: document.getElementById("llm-data"), endpoint: "/admin/api/llm" },
};

function renderKV(el, data) {
  if (!el) return;
  el.innerHTML = "";
  for (const [k, v] of Object.entries(data || {})) {
    const div = document.createElement("div");
    div.innerHTML = "<dt>" + k + "</dt><dd>" + (v ?? "—") + "</dd>";
    el.appendChild(div);
  }
}

async function loadPanel(key) {
  const panel = panels[key];
  if (!panel) return;
  try {
    const res = await fetch(panel.endpoint, { signal: AbortSignal.timeout(5000) });
    if (res.status === 403) {
      renderKV(panel.el, { error: "仅允许本机访问" });
      return;
    }
    const data = await res.json();
    renderKV(panel.el, data);
  } catch (_) {
    renderKV(panel.el, { error: "加载失败" });
  }
}

async function loadAll() {
  for (const key of Object.keys(panels)) {
    loadPanel(key);
  }
}

async function runAction(action) {
  diagOutput.textContent = "执行中…";
  try {
    const url = "/admin/api/" + action;
    const method = action.startsWith("health") ? "GET" : "POST";
    const res = await fetch(url, { method, signal: AbortSignal.timeout(10000) });
    const data = await res.json();
    diagOutput.textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    diagOutput.textContent = "操作失败: " + e.message;
  }
}

document.querySelectorAll("[data-action]").forEach(btn => {
  btn.addEventListener("click", () => {
    const action = btn.dataset.action;
    const destructive = action.startsWith("rebuild");
    if (destructive && !confirm("确认执行 " + action + "？")) return;
    runAction(action);
  });
});

loadAll();
