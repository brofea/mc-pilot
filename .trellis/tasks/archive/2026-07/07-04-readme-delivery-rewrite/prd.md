# README 交付质量重写

## Goal

将 README 重写为课程交付级、事实可核验、命令可复制执行的项目入口，并修复阻碍 README 所述 Docker 数据构建流程的最小镜像配置缺口。

## What I already know

- 当前 README 结构完整但存在过时数字、Fabric 构建命令冲突、占位 clone 地址和未实现功能表述。
- 全 Docker 模式的镜像未复制 `scripts/`，无法按文档在持久化 SQLite volume 内构建配方数据。
- 当前权威质量结果为 Ruff/Mypy 通过、115 项 Pytest 通过、Fabric Wrapper clean build 通过。
- Docker App/Qdrant 仅发布到 `127.0.0.1`，Minecraft 目录只读挂载。
- `/admin/api/rebuild-wiki` 返回 `not_implemented`；后台没有手动日志路径输入框。

## Requirements

- README 首屏说明项目定位、三项核心能力、MVP/加分项和当前支持边界。
- 提供 Docker 推荐路径与本地开发路径，两者不能混写数据目录。
- 所有命令必须对应当前仓库文件和真实入口；不提供占位仓库 URL。
- 明确区分“无需数据即可用”“需先构建数据”“需 API Key”“需 Minecraft 日志”。
- Docker 镜像复制 `scripts/`，允许通过 `docker compose exec app python scripts/...` 把数据写入持久化 volume。
- 模型缓存位于 `/app/data/models`，随 app-data volume 持久化。
- 修正 Fabric 为 JDK 25 + `./gradlew clean build` + Gradle 9.5.1 Wrapper。
- API 列表只记录真实可用接口；未实现后台重建动作列入限制，不伪装成可用能力。
- 更新测试数量、目录结构和故障排查。
- 保留不使用 conda、secret 脱敏、loopback-only 等项目约束。

## Acceptance Criteria

- [ ] README 中不存在 `[用户名]`、`108 passed`、主机 `gradle build` 或 `Gradle 9.6+`。
- [ ] README 不声称后台能输入日志路径或在线重建 Wiki。
- [ ] Docker 数据构建命令在镜像中找到对应脚本，并写入持久化路径。
- [ ] README 中的 API 路径与 FastAPI 路由一致。
- [ ] `docker compose config --quiet`、Ruff、Mypy、Pytest 全部通过。
- [ ] `./gradlew clean build` 仍通过。
- [ ] Markdown 标题、目录链接、代码块和相对文件链接可读。

## Definition of Done

- 新用户只读 README 即可选择一种运行模式并完成健康检查。
- 课程答辩者能从 README 找到架构、数据来源、安全边界、验证证据与已知限制。
- Git 提交、Trellis 归档和开发日志完成。

## Out of Scope

- 实现后台 Wiki 重建按钮。
- 新增 README 截图素材或对外发布仓库 URL。
- 改写实验报告正文。

## Technical Notes

- 权威配置：`compose.yaml`、`Dockerfile`、`.env.example`、`pyproject.toml`。
- 权威入口：`scripts/`、`src/mc_pilot/api/`、`src/mc_pilot/admin/routes.py`。
- Fabric：`fabric-mod/BUILDING.md`、`gradle/wrapper/gradle-wrapper.properties`。
