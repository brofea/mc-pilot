# 最终验收修复

## Goal

修复独立验收发现的端到端缺陷，使 Docker 化网页 MVP 的日志监听、死亡建议、安全渲染和 Fabric 26.2 加分项均可真实运行、可测试、可复现构建，并在完整质量门通过后归档父任务。

## What I already know

- Python 静态检查与 108 项测试通过，但现有测试未覆盖应用生命周期到日志监听的真实接线。
- `GameStateService` 未在 FastAPI lifespan 中启动或停止，`GameLogListener` 也未注入 DeepSeek 客户端。
- Compose 未只读挂载 macOS Minecraft 日志目录，因此容器无法读取宿主机 `latest.log`。
- 聊天、死亡提示和后台键值渲染使用不安全的 `innerHTML`。
- Fabric 26.2 官方建议 Loom 1.17、Gradle 9.5.1、Loader 0.19.3；当前 Loom 1.10 构建失败，且仓库缺少 Wrapper 启动脚本。
- 父 PRD 要求 Docker/macOS 日志监听、每次死亡至多一次 DeepSeek 调用、2–5 句提示、WebSocket 低噪声推送和 Fabric 可复用后端。

## Requirements

### Backend lifecycle

- 应用启动时启动 `GameStateService`，关闭时可靠停止并等待监听任务结束。
- 使用与 Agent 相同配置创建死亡建议用 DeepSeek 客户端；未配置 API Key 时保持可见降级状态且不崩溃。
- 日志服务启动、停止、重复启动和取消必须安全。
- WebSocket 断开后移除回调，避免内存泄漏和重复推送。

### Docker/macOS log access

- Compose 支持通过环境变量指定宿主机 Minecraft 目录，并以只读方式挂载到固定容器路径。
- 容器通过显式配置使用挂载后的 `latest.log`，不依赖容器内 `Path.home()` 猜测。
- 未配置或文件不存在时，应用保持 `disconnected`，其他功能继续可用。
- README 和 `.env.example` 写明 macOS 配置方式。

### Browser safety and reliability

- 外部文本仅通过 `textContent`/文本节点渲染；保留换行与简单代码展示但不得解释任意 HTML。
- WebSocket 重连使用有上限的指数退避、避免重复连接，并在页面卸载时关闭。
- 消息载荷先做最小结构校验；格式错误进入可见降级状态。

### Fabric reproducibility

- 使用 Fabric 官方 26.2 推荐的 Loom/Loader/Fabric API 组合和 Java 25 工具链。
- 提交 Gradle 9.5.1 Wrapper 完整文件，并以 `./gradlew clean build` 作为唯一验收命令。
- 修正 26.2 API 编译错误，生成可安装 JAR。

### Verification

- 为生命周期接线、监听器回调清理、未配置模型降级和安全渲染增加回归测试。
- `ruff check .`、`mypy src`、`pytest -q`、`docker compose config --quiet` 全部通过。
- 当前镜像重建后容器健康，HTTP/WS 关键路径通过。
- `./gradlew clean build` 通过。
- 浏览器主页面和后台无控制台错误，关键布局可用。

## Acceptance Criteria

- [ ] FastAPI lifespan 自动启动并关闭日志监听；测试能观察到调用。
- [ ] 配置 API Key 时死亡监听器拥有 DeepSeek 客户端；未配置时安全降级。
- [ ] Docker Compose 只读挂载可配置的 Minecraft 日志目录，容器路径可配置。
- [ ] WebSocket 客户端断开会移除 advice callback。
- [ ] 用户、模型、日志和后台 API 文本无法通过 `<img onerror>` 等载荷注入 DOM。
- [ ] WebSocket 重连有上限、无重复连接、卸载时清理。
- [ ] Fabric 26.2 使用 Java 25 与官方推荐依赖，Wrapper 构建通过并产出 JAR。
- [ ] 全部静态检查、自动化测试、Docker 运行验证和浏览器检查通过。
- [ ] Git 工作树干净，修复任务与父任务按 Trellis 流程归档并记录日志。

## Definition of Done

- 代码、测试、Compose、文档与 Gradle 构建共同证明上述行为。
- 不以 mock-only 测试替代关键运行验收。
- 不泄露 API Key、完整日志行或宿主机敏感路径。

## Out of Scope

- 扩展到 Minecraft 26.2 之外版本。
- 新增游戏玩法功能或更换 LLM/RAG 技术栈。
- 将普通多人聊天发送给后端。

## Technical Notes

- 后端规范：`.trellis/spec/backend/`。
- 前端规范：`.trellis/spec/frontend/`。
- Fabric 26.2 官方建议：Loom 1.17、Gradle 9.5.1、Loader 0.19.3、Fabric API 0.154.0+26.2。
- 主要涉及 `app.py`、`game/`、`api/game_state.py`、`static/js/`、`compose.yaml`、`.env.example`、`fabric-mod/` 与测试。
