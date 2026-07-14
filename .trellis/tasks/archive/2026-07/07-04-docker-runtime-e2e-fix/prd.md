# 修复 Docker 数据构建与对话链路

## Goal

修复 README 推荐 Docker 流程中配方构建、Wiki RAG 构建和网页对话的真实运行故障，并以完整端到端执行而非静态存在性检查完成验收。

## What I already know

- `docker compose exec app python scripts/build_recipes.py` 当前会报错。
- Wiki 构建能连接 Qdrant，但在 `logger.info(..., extra={"name": ...})` 处因覆盖 `LogRecord.name` 抛出 `KeyError`。
- `scripts/test_connectivity.py` 成功，但网页对话返回“内部错误，请重试”。
- Docker App 与 Qdrant 容器可启动，健康检查此前返回 ready。
- 用户要求真正跑通，而不是只验证脚本存在、单元测试或健康接口。

## Assumptions

- 保持现有 Python 3.12、FastAPI、Qdrant、SQLite、DeepSeek 兼容 API 架构。
- 使用现有 `.env` 配置进行真实对话验收，但任何密钥不得输出到日志或回复。
- 对完整中文 Wiki 的耗时构建，可以先用可控的小规模真实数据完成回归，再视资源与时间运行全量流程；修复必须同样适用于全量构建。

## Requirements

- 定位并修复容器内配方构建失败的根因。
- 修复所有会覆盖 Python `LogRecord` 保留字段的结构化日志参数，而不仅是已暴露的单点。
- 定位网页对话内部错误的实际异常，并修复相应运行时、数据或错误处理问题。
- 数据构建脚本应适合重复执行，失败后可重新运行。
- README 命令必须与最终验证过的流程一致。
- 新增自动化回归测试，覆盖本次根因和关键 Docker 契约。

## Acceptance Criteria

- [ ] 在新构建的 Compose App 容器内，配方构建命令退出码为 0，并生成可查询的配方数据库。
- [ ] Wiki 构建不再因 logging `extra` 保留字段冲突失败，并能写入/切换可查询的 Qdrant 集合。
- [ ] Connectivity 脚本退出码为 0。
- [ ] 通过真实 HTTP 对话请求验证至少一个配方问题和一个 Wiki/常识问题不返回内部错误。
- [ ] 如配置了 DeepSeek API，真实模型调用成功；若外部服务失败，能明确区分外部依赖失败与代码故障。
- [ ] Ruff、Mypy、Pytest 和 Compose 配置校验全部通过。
- [ ] README 中的首跑步骤已按真实成功顺序更新。

## Definition of Done

- 自动化测试与真实 Docker 端到端验收均通过。
- 记录导致上次假阳性验收的测试缺口，并沉淀到 Trellis 规范。
- 不安装或使用 Conda。

## Out of Scope

- 重构整个 Agent 架构。
- 改变 DeepSeek 服务商或前端视觉设计。
- 扩展到 Minecraft Java 26.2 之外的版本。

## Technical Notes

- 重点检查 `scripts/build_recipes.py`、`scripts/build_wiki.py`、`src/mc_pilot/rag/`、Agent API/服务、Dockerfile、Compose、README 和容器日志。
- 验收必须执行真实容器命令和真实 HTTP 请求，不能以 mock 测试替代。
