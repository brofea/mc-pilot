const statusElements = document.querySelectorAll("[data-service-status]");
const readinessOutput = document.querySelector("[data-readiness-output]");

function updateStatus(state, label) {
  statusElements.forEach((element) => {
    element.dataset.state = state;
    element.textContent = label;
  });
}

async function loadReadiness() {
  updateStatus("connecting", "正在检查后端…");
  try {
    const response = await fetch("/health/ready", {
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(3000),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    const state = payload.status === "ready" ? "ready" : "degraded";
    updateStatus(state, state === "ready" ? "服务已就绪" : "服务降级运行");
    if (readinessOutput) readinessOutput.textContent = JSON.stringify(payload, null, 2);
  } catch (_error) {
    updateStatus("degraded", "无法连接后端");
    if (readinessOutput) readinessOutput.textContent = "健康检查失败";
  }
}

void loadReadiness();
