# Minecraft Pilot Agent

Minecraft Pilot 是一个面向 Minecraft Java Edition 26.2 的本地游戏助手。结合中文 Wiki RAG、确定性配方树和游戏日志分析，通过网页聊天和 Fabric Mod 为玩家提供帮助。

**非官方课程项目**，与 Mojang 或 Microsoft 无关。

---

## 目录

- [QuickStart](#quickstart)
- [功能概览](#功能概览)
- [使用教程](#使用教程)
- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [环境变量](#环境变量)
- [质量检查](#质量检查)
- [API 文档](#api-文档)
- [Fabric Mod](#fabric-mod-可选)
- [数据构建](#数据构建)

---

## QuickStart

从头开始，三步跑通。

### 第一步：环境准备

```bash
# 1. 克隆仓库
git clone https://github.com/[用户名]/mc-pilot.git
cd mc-pilot

# 2. 创建虚拟环境并安装依赖
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'

# 3. 配置 API 密钥
cp .env.example .env
# 编辑 .env，将 DEEPSEEK_API_KEY= 后面填上你的 DeepSeek API 密钥
# macOS 使用 Docker 时，将 MC_PILOT_MINECRAFT_DIR 改为当前用户的 Minecraft 目录
# 获取密钥: https://platform.deepseek.com/api_keys
```

> **注意** 本项目使用 pip + .venv，**不使用 conda**。macOS / Linux 均可，Windows 需自行调整路径分隔符。

### 第二步：启动服务

```bash
# 4. 启动 Qdrant 向量数据库（需要 Docker）
docker compose up -d qdrant

# 5. 启动 Pilot 后端
.venv/bin/uvicorn mc_pilot.app:create_app --factory --reload --host 127.0.0.1 --port 8000
```

> 如果不想手动分步启动，也可以一条命令拉起全部服务：
> ```bash
> docker compose up --build
> ```

### 第三步：打开网页

浏览器打开 http://127.0.0.1:8000

你应该看到 **Minecraft Pilot** 主页面，聊天框里已有欢迎消息。此时页面右上角应显示绿色的"就绪"状态。

**验证连接**：
```bash
curl http://127.0.0.1:8000/health/ready
# {"status":"ready","components":[{"name":"sqlite","status":"ready",...},{"name":"qdrant","status":"ready",...}]}
```

---

## 功能概览

完成 QuickStart 后，你有四条核心使用路径：

| 序号 | 能力 | 需要什么 | 如何使用 |
|---|---|---|---|
| 1 | Agent 对话 | DeepSeek API Key | 在网页输入框输入问题 |
| 2 | 配方查询 | 先运行 `build_recipes` | `/pilot recipe <物品ID>` |
| 3 | Wiki 问答 | 先运行 `build_wiki` | `/pilot wiki <关键词>` |
| 4 | 死亡建议 | 启动 Minecraft 26.2 并打开日志监听 | 游戏中死亡时自动触发 |

### 能力 1：Agent 智能对话

当你配置了 `DEEPSEEK_API_KEY`，Agent 立即可用。无需额外数据。

```
在网页输入框中输入：
/pilot 如何合成附魔台？
```

Agent 会自动调用 `wiki_search` 查询知识库，或调用 `recipe_query` 查询配方，然后用中文回复。

**首次验证**：先运行连通性测试确认模型可访问：
```bash
.venv/bin/python scripts/test_connectivity.py
# 预期输出：Connectivity OK model=deepseek-v4-flash latency_ms=850
```

### 能力 2：确定性配方查询

需要先构建本地配方数据库（需要网络，约 100MB 下载）：

```bash
# 从 Mojang CDN 下载 Java 26.2 客户端 JAR，提取配方到 SQLite
.venv/bin/python scripts/build_recipes.py
```

然后在网页中输入：
```
/pilot recipe minecraft:enchanting_table
```

Agent 会返回附魔台所需的全部材料：黑曜石 ×4、钻石 ×2、书 ×1。配方树是完全确定性计算的，不依赖模型生成。

### 能力 3：Wiki 知识问答

需要先构建 Wiki 索引（需要网络，首次约 5-10 分钟，需要约 2GB 模型下载）：

```bash
# 从中文 Minecraft Wiki API 采集知识，嵌入到 Qdrant
.venv/bin/python scripts/build_wiki.py
```

然后在网页中输入：
```
/pilot wiki 凋零骷髅在哪生成？
```

Agent 从 Qdrant 检索相关 Wiki 片段，整合后返回带来源 URL 的回答。

### 能力 4：死亡建议（自动触发）

这是**自动触发**的能力，无需手动调用。

1. 确认后端正在运行
2. 启动 **Minecraft Java Edition 26.2**（单人生存模式）
3. 在网页上，你应看到右上角状态从"未连接游戏"变为"玩家名 · 26.2"
4. 当玩家角色在游戏中死亡时，网页会弹出红色气泡，显示 2-5 句生存建议

如果未能自动检测到游戏日志，在网页开发后台手动指定日志路径：
http://127.0.0.1:8000/admin → 重连日志

---

## 使用教程

### 网页聊天（主界面）

打开 http://127.0.0.1:8000

```
┌─────────────────────────────────────────┐
│  Minecraft Pilot                        │
│  Java Edition 26.2                      │
├─────────────────────────────────────────┤
│  Pilot 对话           [玩家 · 26.2] [就绪] │
│                                         │
│  ┌─ Pilot 已就位 ─────────────────────┐  │
│  │                                    │  │
│  │  (对话历史)                         │  │
│  │                                    │  │
│  └────────────────────────────────────┘  │
│                                         │
│  消息: [________________] [发送]        │
├─────────────────────────────────────────┤
│  配方树 (点 /pilot recipe 自动展示)      │
└─────────────────────────────────────────┘
```

**可用指令**：

| 输入 | 效果 | 是否消耗 LLM |
|---|---|---|
| `/pilot 如何做附魔台` | Agent 自动路由 → wiki_search + recipe_query | 是 |
| `/pilot wiki 末地传送门` | 直接 wiki_search，返回带来源的回答 | 否（子命令直连） |
| `/pilot recipe minecraft:bow` | 直接 recipe_query，返回配方树 | 否（子命令直连） |
| `/pilot status` | 显示模型名、token 用量 | 否 |
| `/pilot clear` | 清除 6 轮会话记忆 | 否 |
| `/pilot help` | 显示帮助 | 否 |
| `你好，你能做什么？` | Agent 对话（自然语言） | 是 |

### 开发者后台

打开 http://127.0.0.1:8000/admin

展示 7 个面板：系统状态、游戏连接、配方数据、RAG/Qdrant、LLM/Agent、安全配置（脱敏）、诊断操作。

**安全限制**：仅允许本机访问。从其他 IP 访问返回 403。

### 游戏日志监听

后端启动后，自动尝试检测 macOS 下 Minecraft 日志路径：

```
~/Library/Application Support/minecraft/logs/latest.log
```

如果日志存在且 Minecraft 正在运行：
- 页面显示绿色的"玩家名 · 26.2"
- 死亡事件被解析，生成建议，通过 WebSocket 推送到网页

**手动指定日志路径**（如果自动检测失败）：
1. 打开 http://127.0.0.1:8000/admin
2. 点击"重连日志"
3. 或直接通过 API：`POST /admin/api/reconnect-log`

---

## 技术栈

| 层 | 选型 |
|---|---|
| 语言 | Python 3.12 + Java 25 (Mod) |
| Web 框架 | FastAPI + Jinja2 + 原生 JavaScript（零 Node 构建） |
| 数据模型 | Pydantic + SQLAlchemy 2.x |
| 向量库 | Qdrant 1.15 (Docker) |
| LLM | DeepSeek v4-flash (OpenAI 兼容 API) |
| Embedding | BAAI/bge-small-zh-v1.5 (sentence-transformers, 本地运行) |
| 传输协议 | HTTP (REST) + WebSocket (实时推送) |
| 容器 | Docker Compose |
| Mod 框架 | Fabric (Minecraft) |

---

## 项目结构

```
.
├── src/mc_pilot/
│   ├── app.py                 # FastAPI 工厂
│   ├── config.py              # Pydantic 配置（环境变量→Settings）
│   ├── errors.py              # 领域异常 AppError
│   ├── logging_config.py      # JSON 结构化日志
│   ├── api/                   # HTTP/WebSocket 路由层
│   │   ├── chat.py            # POST /api/chat
│   │   ├── recipes.py         # GET/POST /api/recipes
│   │   ├── game_state.py      # GET /api/game-state, WS /ws
│   │   ├── health.py          # /health/live, /health/ready
│   │   ├── pages.py           # 页面路由 (/ 和 /admin)
│   │   └── models.py          # 共享 API 响应模型
│   ├── admin/
│   │   └── routes.py          # /admin/api/* (loopback-only)
│   ├── agent/                 # DeepSeek Agent 核心
│   │   ├── client.py          # DeepSeek OpenAI 兼容客户端
│   │   ├── loop.py            # Agent 状态机
│   │   ├── memory.py          # 6 轮会话记忆 + token 预算
│   │   ├── models.py          # Agent 领域模型
│   │   ├── tools.py           # 3 个 MCP 风格工具契约
│   │   └── service.py         # Agent 服务（/pilot 路由）
│   ├── game/                  # 游戏日志
│   │   ├── detector.py        # macOS 日志/进程检测
│   │   ├── tailer.py          # 日志尾随（轮转/截断恢复）
│   │   ├── death_parser.py    # zh_cn/en_us 双语死亡解析（~60 条规则）
│   │   ├── listener.py        # 日志监听循环 + 死亡建议生成
│   │   ├── models.py          # 游戏状态模型
│   │   └── service.py         # 游戏服务
│   ├── rag/                   # Wiki RAG 管线
│   │   ├── client.py          # MediaWiki API 客户端（分页、缓存、限速）
│   │   ├── chunker.py         # 文本清洗 + 段落级切块
│   │   ├── embedder.py        # BAAI/bge-small-zh-v1.5 嵌入适配器
│   │   ├── indexer.py         # Qdrant staging→live 原子交换
│   │   ├── retriever.py       # 密集检索 + 标题精确加权
│   │   ├── models.py          # RAG 领域模型
│   │   └── service.py         # RAG 服务
│   ├── recipes/               # 官方配方管线
│   │   ├── downloader.py      # Mojang 清单 + JAR 下载 + SHA-1 校验
│   │   ├── extractor.py       # JAR 配方/tag/本地化提取
│   │   ├── tree.py            # 确定性 N 层配方树算法
│   │   ├── store.py           # SQLite 持久化
│   │   ├── models.py          # 配方领域模型
│   │   └── service.py         # 配方服务
│   ├── storage/               # 持久化适配
│   │   ├── qdrant.py          # Qdrant 健康探针
│   │   └── sqlite.py          # SQLite 引擎
│   ├── templates/             # Jinja2 模板
│   │   ├── base.html          # 基础布局（导航 + 动态脚本区）
│   │   ├── index.html         # 主聊天页
│   │   └── admin.html         # 开发者后台
│   └── static/                # 静态资源
│       ├── css/app.css        # 全局样式
│       └── js/
│           ├── chat.js         # 聊天 UI + WebSocket
│           └── admin.js        # 后台仪表盘
├── fabric-mod/                # Fabric 26.2 客户端 Mod（可选加分项）
│   ├── build.gradle
│   ├── src/main/java/mc/pilot/mod/
│   │   ├── PilotMod.java      # Mod 入口
│   │   ├── PilotClient.java   # HTTP/WebSocket 客户端
│   │   ├── PilotCommandHandler.java  # /pilot 路由
│   │   └── ChatRenderer.java  # 本地聊天渲染
│   └── src/main/resources/fabric.mod.json
├── scripts/                   # 运维脚本
│   ├── build_recipes.py       # 构建配方数据库
│   ├── build_wiki.py          # 构建 Wiki 索引
│   └── test_connectivity.py   # DeepSeek 连通性测试
├── tests/                     # 自动化测试 (108 个)
├── docs/                      # 课程文档
│   ├── 实验报告.md            # 完整实验报告
│   ├── instruction.md
│   └── 实验报告提交及评分标准.md
├── compose.yaml               # Docker Compose
├── Dockerfile                 # App 镜像
├── pyproject.toml             # Python 项目元数据
└── .env.example               # 环境变量模板
```

---

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `MC_PILOT_HOST` | `127.0.0.1` | 服务绑定地址 |
| `MC_PILOT_PORT` | `8000` | 服务端口 |
| `MC_PILOT_LOG_LEVEL` | `INFO` | 日志级别 (DEBUG/INFO/WARNING/ERROR) |
| `MC_PILOT_SQLITE_URL` | `sqlite:///data/mc_pilot.db` | SQLite 数据库路径 |
| `MC_PILOT_QDRANT_URL` | `http://localhost:6333` | Qdrant 服务地址 |
| `MC_PILOT_QDRANT_TIMEOUT_SECONDS` | `2` | Qdrant 连接超时 |
| `MC_PILOT_MINECRAFT_DIR` | macOS 默认游戏目录 | Docker 只读挂载的宿主机 Minecraft 目录 |
| `MC_PILOT_GAME_LOG_PATH` | 自动检测 | 原生运行时可覆盖的 `latest.log` 路径 |
| `DEEPSEEK_API_KEY` | — | DeepSeek API 密钥 (**必需**) |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | API 基础 URL |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | 模型标识符 |

**获取 API 密钥**：https://platform.deepseek.com/api_keys

复制 `.env.example` → `.env`，填入 `DEEPSEEK_API_KEY=` 后面的值。
Docker Compose 会将 `MC_PILOT_MINECRAFT_DIR` 只读挂载到容器。目录或
`logs/latest.log` 暂不存在时，日志分析保持未连接，聊天、Wiki 和配方仍可使用。

---

## 质量检查

```bash
# 代码风格（0 errors）
.venv/bin/ruff check .

# 类型检查（0 errors）
.venv/bin/mypy src tests

# 自动化测试（108 passed）
.venv/bin/pytest -q

# Docker 配置语法验证
docker compose config --quiet
```

测试覆盖范围：
- 配方解析 (shaped/shapeless/smelting/stonecutting)
- 配方树算法 (递归/循环检测/标签展开/叶子汇总)
- SHA-1 哈希校验
- 中英文死亡解析 (~60 条规则)
- 日志尾随 (轮转/截断恢复)
- SQLite 存储 CRUD
- 工具白名单安全
- Token 预算管理
- 密钥脱敏
- API 路由冒烟测试
- Docker Compose 配置验证

---

## API 文档

### 健康检查

```
GET /health/live     → {"status":"alive","version":"0.1.0"}
GET /health/ready    → {"status":"ready","components":[...]}
```

### Agent 对话

```
POST /api/chat
Content-Type: application/json
{"message": "/pilot 如何合成附魔台？"}

Response:
{
  "state": "answered",
  "answer": "附魔台需要...",
  "stop_reason": null
}
```

### 配方查询

```
GET  /api/recipes/minecraft:enchanting_table
POST /api/recipes/tree  {"item_id": "minecraft:diamond_sword", "quantity": 1, "max_depth": null}
```

### 游戏状态

```
GET /api/game-state    → {"state":"connected","player_name":"Steve","version_id":"26.2"}
WS  /ws                 → {"type":"death_advice","advice":"..."} | {"type":"state",...}
```

### 管理后台 API（仅 loopback）

```
GET /admin/api/status         # 系统状态
GET /admin/api/game           # 游戏连接
GET /admin/api/recipes        # 配方数据状态
GET /admin/api/rag            # RAG/Qdrant 状态
GET /admin/api/llm            # LLM/Agent 状态
GET /admin/api/config         # 配置（脱敏）
POST /admin/api/reconnect-log # 重连游戏日志
POST /admin/api/rebuild-wiki  # 重建 Wiki 索引
```

---

## Fabric Mod（可选）

**目标**：在游戏内通过 `/pilot` 指令使用 Agent，所有消息仅本地可见（不会发送到多人服务器）。

```bash
cd fabric-mod
gradle build
# 输出：build/libs/pilot-mod-0.1.0.jar → 放入 .minecraft/mods/
```

游戏中：
```
/pilot 如何获得下界合金锭？  → Agent 回答（本地聊天 HUD）
/pilot wiki 末影龙             → 直接 wiki 搜索
/pilot recipe diamond_sword    → 直接配方查询
/pilot status                  → 连接状态
```

**构建需求**：JDK 25 + Gradle 9.6+。详见 `fabric-mod/BUILDING.md`。

---

## 数据构建

以下脚本需要网络连接，首次运行需下载依赖数据。

```bash
# DeepSeek 连通性测试（验证 API Key 可用）
.venv/bin/python scripts/test_connectivity.py

# 构建配方数据库（从 Mojang 下载 26.2 JAR，提取配方 → SQLite）
.venv/bin/python scripts/build_recipes.py

# 构建 Wiki 索引（从中文 Wiki API 采集，嵌入 → Qdrant）
.venv/bin/python scripts/build_wiki.py
```

**注意事项**：
- `build_recipes.py` 需要 ~100MB 下载，SHA-1 校验确保文件正确
- `build_wiki.py` 首次运行需下载 BGE 模型（~400MB），抓取 Wiki 页面约 5-10 分钟
- 配方和 Wiki 数据是独立的，可以先构建其中一个
- 即使没有构建数据，Agent 对话功能仍可用（模型依赖自身知识回答）
