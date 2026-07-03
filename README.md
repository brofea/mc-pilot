# Minecraft Pilot Agent

面向 Minecraft Java Edition 26.2 的本地游戏助手。将中文 Wiki RAG、官方配方数据和本地游戏日志接到一个轻量 Agent 后端，并提供网页界面与可选的 Fabric 客户端 Mod。

## 项目状态

| 项目 | 状态 |
|---|---|
| 网页 MVP | 已完成，可通过 Docker 或本地 Python 运行 |
| 中文 Wiki RAG | 已实现，需要先构建 Qdrant 索引 |
| 官方配方与 N 层配方树 | 已实现，需要先构建 SQLite 数据 |
| 本地死亡日志建议 | 已实现，需要 Minecraft 日志和 DeepSeek API |
| Fabric 26.2 Mod | 已完成源码与可复现构建，属于第二阶段加分项 |
| 支持版本 | 仅 Minecraft Java Edition 26.2 正式版 |

当前质量门：Ruff 通过、Mypy strict 通过、`121 passed`、Docker Compose 配置校验通过、Fabric Wrapper 构建通过。

## 核心能力

1. **中文 Wiki RAG**：通过 `https://zh.minecraft.wiki/api.php` 采集白名单分类，使用 `BAAI/bge-small-zh-v1.5` 向量化并存入 Qdrant，查询结果保留页面 URL 与 revision ID。
2. **确定性配方树**：从 Mojang 官方版本清单下载 26.2 客户端 JAR，校验 SHA-1，提取配方、标签与语言资源，再由代码计算直接配方、N 层材料树和叶子材料汇总；LLM 不参与数量计算。
3. **游戏日志分析**：只读监听本地 `latest.log`，识别本地玩家和简中/英文死亡消息，每次有效死亡最多调用一次 DeepSeek，并通过 WebSocket 推送一条短建议。
4. **轻量 Agent**：支持自然语言、MCP 风格 Function Calling、6 轮短期记忆、工具白名单、调用轮次限制与 token 预算。
5. **开发者后台**：展示系统、游戏、配方、RAG、LLM 和脱敏配置状态；仅允许本机访问。

## 架构

```mermaid
flowchart LR
    Web[网页客户端] -->|HTTP / WebSocket| API[FastAPI 后端]
    Mod[Fabric 26.2 Mod] -->|HTTP / WebSocket| API
    API --> Agent[轻量 Agent 状态机]
    Agent -->|Function Calling| Recipes[配方服务]
    Agent -->|Function Calling| RAG[Wiki RAG]
    Agent --> DeepSeek[DeepSeek 兼容 API]
    Recipes --> SQLite[(SQLite)]
    RAG --> Qdrant[(Qdrant)]
    Log[latest.log] --> Game[日志监听与死亡解析]
    Game --> DeepSeek
    Game --> API
```

## 快速开始：Docker（推荐交付方式）

### 1. 前置条件

- macOS 优先；Linux 也可运行网页、RAG 和配方功能
- Docker Desktop 与 Docker Compose
- 可选：DeepSeek API Key。没有 Key 时，网页、健康检查、配方和已构建的 Wiki 检索仍可用；自然语言 Agent 与死亡建议不可用
- 若要监听游戏日志，本机需安装并运行 Minecraft Java Edition 26.2

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`：

```dotenv
# 可选，但自然语言 Agent 和死亡建议需要它
DEEPSEEK_API_KEY=你的_API_Key

# macOS Minecraft 目录。请替换成真实用户名；路径中可以包含空格
MC_PILOT_MINECRAFT_DIR=/Users/你的用户名/Library/Application Support/minecraft
```

不要把 `.env` 提交到 Git。项目不会在网页或日志中返回 API Key。

### 3. 启动网页与 Qdrant

```bash
docker compose up -d --build
docker compose ps
```

验证：

```bash
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready
```

预期结果：

- `live` 返回 `{"status":"alive","version":"0.1.0"}`；
- `ready` 中 SQLite 和 Qdrant 均为 `ready`；
- 浏览器可访问 <http://127.0.0.1:8000>；
- 开发者后台可访问 <http://127.0.0.1:8000/admin>；
- OpenAPI 文档可访问 <http://127.0.0.1:8000/docs>。

### 4. 构建可选数据

首次启动时数据库可以为空。按需要构建：

```bash
# 官方 26.2 配方数据 → Docker app-data 中的 SQLite
docker compose exec app python scripts/build_recipes.py

# 中文 Wiki → Qdrant；首次运行会下载本地嵌入模型
docker compose exec app python scripts/build_wiki.py

# DeepSeek 连通性测试
docker compose exec app python scripts/test_connectivity.py
```

配方构建通常较快。Wiki 构建会抓取九类页面并在 CPU 上生成数千条向量，首次运行可能需要数十分钟；看到连续的 Qdrant `points ... 200 OK` 属于正常进度，请等待终端出现 `Wiki index built` 并返回命令提示符。不要把终端工具超时或窗口断开误判成构建成功，可在另一终端用后台接口确认：

```bash
curl http://127.0.0.1:8000/admin/api/recipes
curl http://127.0.0.1:8000/admin/api/rag
```

构建完成后，两个接口应分别显示已有配方数据和 `"index_exists":true`。还可以发起不经过前端的真实查询：

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"/pilot recipe minecraft:crafting_table"}'

curl -X POST http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"/pilot wiki 石头"}'
```

`app-data` 和 `qdrant-data` 是命名卷；SQLite、Wiki API 缓存和 Hugging Face 模型缓存会在容器重建后保留。Minecraft 目录仅以只读方式挂载。

### 5. 停止服务

```bash
docker compose down
```

这不会删除数据卷。只有明确执行 `docker compose down -v` 才会删除本地项目数据。

## 本地开发模式

本项目只使用 `pip`、`.venv` 和 Docker，**不要使用 conda**。

### 1. Python 环境

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
cp .env.example .env
```

如果系统命令名是 `python3`，先用 `python3 --version` 确认版本为 3.12。

### 2. 只启动 Qdrant

```bash
docker compose up -d qdrant
```

### 3. 构建数据并启动 FastAPI

```bash
.venv/bin/python scripts/build_recipes.py
.venv/bin/python scripts/build_wiki.py
.venv/bin/uvicorn mc_pilot.app:create_app --factory --host 127.0.0.1 --port 8000
```

本地模式与全 Docker 模式使用不同的 SQLite 存储位置。请选择一种模式完成“构建数据 → 启动应用”，不要在宿主机生成数据后期待 Docker volume 自动同步。

## 使用方式

网页输入框接受自然语言和 `/pilot` 子命令：

| 输入 | 行为 | 前置条件 | 消耗 LLM |
|---|---|---|---|
| `/pilot wiki 末地传送门` | 直接检索 Wiki 片段并附来源 | 已构建 Wiki 索引 | 否 |
| `/pilot recipe minecraft:bow` | 返回确定性配方树与基础材料 | 已构建配方数据 | 否 |
| `/pilot 如何获得鞘翅？` | Agent 自主选择 Wiki/配方工具 | DeepSeek Key；相关数据按问题准备 | 是 |
| `你好，你能做什么？` | 普通 Agent 对话 | DeepSeek Key | 是 |
| `/pilot status` | 显示模型与 token 用量 | 无 | 否 |
| `/pilot clear` | 清除进程内短期记忆 | 无 | 否 |
| `/pilot help` | 显示命令帮助 | 无 | 否 |

配方物品建议使用完整资源 ID，例如 `minecraft:enchanting_table`。

### 死亡建议

Docker 模式从只读挂载的 `/minecraft/logs/latest.log` 读取新增内容；本地模式默认检查：

```text
~/Library/Application Support/minecraft/logs/latest.log
```

当日志存在、识别到本地玩家且 DeepSeek 已配置时：

1. 解析简体中文或英文死亡消息；
2. 忽略其他玩家并去重重复事件；
3. 不调用 Wiki 或配方工具；
4. 生成 2–5 句短建议；
5. 通过 `/ws` 推送到网页并自动淡出。

日志路径不能在当前网页里编辑。Docker 模式修改 `MC_PILOT_MINECRAFT_DIR`；本地模式可设置 `MC_PILOT_GAME_LOG_PATH`，然后重启应用。

## 数据来源与确定性边界

### 配方

- 信任根：Mojang 官方版本清单与客户端 JAR SHA-1；
- 当前构建目标：Java Edition 26.2 `release`；
- 提取内容：配方 JSON、物品标签和必要语言资源；
- 计算方式：代码递归遍历，含深度、循环与节点上限；
- 镜像：可通过 `build_recipes.py --mirror <URL>` 显式提供失败回退源，最终仍必须通过官方 SHA-1。

### Wiki

- API：`https://zh.minecraft.wiki/api.php`；
- 默认白名单：方块、物品、生物、群系、游戏规则、附魔、状态效果、结构与命令；
- 排除基岩版、教育版、快照、开发版和版本记录等页面；
- 检索结果包含来源 URL；当前 `/pilot wiki` 返回检索片段与来源，不额外调用 LLM 改写。

## 开发者后台

<http://127.0.0.1:8000/admin> 展示：

- 系统版本与运行环境；
- 游戏连接、玩家、日志和死亡次数；
- 配方版本；
- RAG、LLM 与 Agent 配置状态；
- 经 `Settings.safe_summary()` 脱敏后的配置；
- 健康检查与日志重连操作。

后台仅允许 loopback Host。`rebuild-wiki` 接口目前返回 `not_implemented`，真实索引构建请使用 `scripts/build_wiki.py`。

## API 摘要

完整交互式文档见 <http://127.0.0.1:8000/docs>。

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/health/live` | 进程存活 |
| GET | `/health/ready` | SQLite/Qdrant 就绪状态 |
| POST | `/api/chat` | Agent 与 `/pilot` 命令入口 |
| GET | `/api/agent-status` | 模型是否配置 |
| GET | `/api/recipes/{item_id}` | 直接配方查询 |
| POST | `/api/recipes/tree` | 数量与深度可配置的配方树 |
| GET | `/api/game-state` | 当前游戏状态 |
| WS | `/ws` | 状态心跳与死亡建议 |
| GET | `/admin/api/*` | 本机开发诊断接口 |

配方树示例：

```bash
curl -X POST http://127.0.0.1:8000/api/recipes/tree \
  -H 'Content-Type: application/json' \
  -d '{"item_id":"minecraft:diamond_sword","quantity":1,"max_depth":3}'
```

## Fabric Mod（第二阶段加分项）

要求：

- JDK 25；
- Minecraft Java Edition 26.2；
- 本地 Pilot 后端运行在 `127.0.0.1:8000`；
- Gradle 9.5.1 由仓库 Wrapper 提供，无需安装主机 Gradle。

构建：

```bash
cd fabric-mod
./gradlew clean build
```

产物：

```text
fabric-mod/build/libs/pilot-mod-0.1.0.jar
```

将 JAR 放入对应 Fabric 客户端的 `mods/` 目录。Mod 只注册本地 `/pilot` 客户端命令、发送 HTTP 请求、接收 WebSocket 事件并渲染本地聊天消息；知识、配方和推理逻辑仍在 Python 后端。API Key 不进入 Mod。

## 质量检查

```bash
.venv/bin/ruff check .
.venv/bin/mypy src tests
.venv/bin/pytest -q
docker compose config --quiet

cd fabric-mod
./gradlew clean build
```

自动化测试覆盖配方解析与递归树、官方哈希、SQLite、Wiki 分块与检索、Agent 工具与预算、双语死亡解析、日志轮转/截断、API 降级、WebSocket 清理、Docker 挂载、后台访问控制及 secret 脱敏。

## 项目结构

```text
.
├── src/mc_pilot/
│   ├── agent/          # DeepSeek 客户端、状态机、记忆与工具契约
│   ├── api/            # HTTP 与 WebSocket 适配层
│   ├── game/           # 日志发现、尾随、死亡解析与建议
│   ├── rag/            # MediaWiki 采集、分块、嵌入、Qdrant 检索
│   ├── recipes/        # 官方数据下载、提取、SQLite 与配方树
│   ├── admin/          # 本机开发诊断 API
│   ├── templates/      # Jinja2 页面
│   └── static/         # 原生 JavaScript 与 CSS
├── scripts/            # 配方、Wiki 与模型连通性脚本
├── tests/              # 离线确定性测试
├── fabric-mod/         # Fabric 26.2 客户端 Mod
├── docs/               # 课程要求与实验报告
├── compose.yaml
├── Dockerfile
└── pyproject.toml
```

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DEEPSEEK_API_KEY` | 空 | 自然语言 Agent 和死亡建议所需 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | OpenAI 兼容 API 根地址 |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | 发送给兼容 API 的模型名，可覆盖 |
| `MC_PILOT_HOST` | `127.0.0.1` | 本地运行绑定地址；Compose 内覆盖为 `0.0.0.0` |
| `MC_PILOT_PORT` | `8000` | HTTP 端口 |
| `MC_PILOT_SQLITE_URL` | `sqlite:///data/mc_pilot.db` | SQLite URL |
| `MC_PILOT_QDRANT_URL` | `http://localhost:6333` | Qdrant URL；Compose 内覆盖为服务名 |
| `MC_PILOT_QDRANT_TIMEOUT_SECONDS` | `2` | 健康探针超时 |
| `MC_PILOT_GAME_LOG_PATH` | 空 | 本地运行时覆盖 `latest.log` 路径 |
| `MC_PILOT_MINECRAFT_DIR` | macOS 默认目录 | Compose 只读挂载源；不是 Pydantic 应用配置 |

## 故障排查

### `ready` 显示 Qdrant degraded

```bash
docker compose ps
docker compose logs qdrant
```

本地开发模式确认 `.env` 中 `MC_PILOT_QDRANT_URL=http://localhost:6333`。

### 配方查询为空

确认数据构建发生在当前运行模式：

```bash
# Docker 模式
docker compose exec app python scripts/build_recipes.py

# 本地模式
.venv/bin/python scripts/build_recipes.py
```

### Wiki 提示知识库尚未构建

运行对应模式的 `build_wiki.py`。首次加载嵌入模型需要网络和较长时间；不要在中途删除 Qdrant volume。

### Docker 无法读取 Minecraft 目录

确认 `.env` 中路径真实存在，并在 Docker Desktop 中允许访问该 macOS 目录。容器内可检查：

```bash
docker compose exec app test -r /minecraft/logs/latest.log
```

### Agent 请求失败

```bash
docker compose exec app python scripts/test_connectivity.py
docker compose logs --tail=100 app
```

日志只应记录模型、耗时和脱敏后的用量，不应出现 API Key。

## 已知限制

- 仅覆盖 Java Edition 26.2 正式版，不承诺其他 26.x 版本；
- 网页后台尚不能输入任意日志路径，也不能直接重建 Wiki；
- 会话记忆保存在当前后端进程内，服务重启后清空；
- Wiki 采用白名单分类，不等于抓取整个中文 Minecraft Wiki；
- 未提供真实 DeepSeek Key 时，自动化测试不会证明线上模型账户与额度可用；
- Fabric Mod 当前固定连接 `127.0.0.1:8000`。
