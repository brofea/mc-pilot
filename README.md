# Minecraft Pilot Agent

Minecraft Pilot 是一个面向 Minecraft Java Edition 26.2 的本地游戏助手。网页 MVP 结合了中文 Wiki RAG、确定性配方树和本地玩家死亡建议。轻量 Fabric 客户端 Mod 作为可选阶段二。

这是非官方的课程项目，与 Mojang 或 Microsoft 无关。

## 功能概览

- Wiki RAG: 从中文 Minecraft Wiki 采集知识、嵌入 BGE-small-zh-v1.5、Qdrant 向量检索、带来源引用和未验证补充分区
- 配方树: 从 Mojang 官方 26.2 版本提取配方、SHA-1 验证、确定性 N 层材料树、多配方候选和标签材料处理
- DeepSeek Agent: 工具调用（wiki_search / recipe_query / recipe_direct）、状态机（received→deciding→tool_running→observing→answered/stopped/failed）、短会话记忆、token 预算
- 游戏日志: macOS 日志监听、zh_cn/en_us 双语死亡解析、去重、唯一 DeepSeek 死亡建议、WebSocket 推送
- 网页聊天: FastAPI + Jinja2 + 原生 JavaScript、/pilot 指令路由、WebSocket 游戏状态、死亡气泡淡出
- 开发者后台: /admin 仪表盘、系统/游戏/RAG/配方/LLM 状态、诊断操作、仅 loopback 访问

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.12, FastAPI, Pydantic, SQLAlchemy 2.x |
| 向量库 | Qdrant (Docker) |
| LLM | DeepSeek (OpenAI 兼容 API) |
| Embedding | BAAI/bge-small-zh-v1.5 (sentence-transformers) |
| 网页 | Jinja2, 原生 JavaScript, 零 Node 构建 |
| 容器 | Docker Compose (Qdrant + App) |

## 快速开始

Python 3.12 必需。本项目使用 pip + .venv，不使用 conda。

```bash
# 环境初始化
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY
```

```bash
# 启动 Qdrant (Docker)
docker compose up -d qdrant

# 启动开发服务器
.venv/bin/uvicorn mc_pilot.app:create_app --factory --reload

# 启动完整 Docker 服务
docker compose up --build
```

打开 http://127.0.0.1:8000/ 和 http://127.0.0.1:8000/admin。

## 数据构建

```bash
# 构建配方数据库 (从 Mojang CDN 下载 26.2 JAR)
.venv/bin/python scripts/build_recipes.py

# 构建 Wiki 知识库 (从中文 Wiki API 采集)
.venv/bin/python scripts/build_wiki.py

# DeepSeek 连通性测试
.venv/bin/python scripts/test_connectivity.py
```

## 质量检查

```bash
.venv/bin/ruff check .
.venv/bin/mypy src tests
.venv/bin/pytest -q
docker compose config --quiet
```

## 项目结构

```
src/mc_pilot/
├── app.py              # FastAPI 工厂
├── config.py           # Pydantic 配置
├── errors.py           # 领域异常
├── logging_config.py   # JSON 结构日志
├── api/                # HTTP/WebSocket 适配
│   ├── chat.py         # /api/chat (Agent 对话)
│   ├── recipes.py      # /api/recipes (配方查询)
│   ├── game_state.py   # /api/game-state, /ws (游戏状态)
│   ├── health.py       # /health/live, /health/ready
│   ├── pages.py        # 页面路由
│   └── models.py       # 共享 API 模型
├── admin/              # 开发者后台
│   └── routes.py       # /admin/api/* (loopback-only)
├── agent/              # Agent 核心
│   ├── client.py       # DeepSeek 客户端
│   ├── loop.py         # 状态机循环
│   ├── memory.py       # 会话记忆
│   ├── models.py       # Agent 领域模型
│   ├── tools.py        # MCP 风格工具契约
│   └── service.py      # Agent 服务
├── game/               # 游戏日志
│   ├── detector.py     # macOS 进程/日志检测
│   ├── tailer.py       # 日志尾随 (轮转/截断)
│   ├── death_parser.py # 双语死亡解析
│   ├── listener.py     # 日志监听循环
│   ├── models.py       # 游戏状态模型
│   └── service.py      # 游戏服务
├── rag/                # Wiki RAG
│   ├── client.py       # MediaWiki API 客户端
│   ├── chunker.py      # 文本清洗/切块
│   ├── embedder.py     # BGE 嵌入适配器
│   ├── indexer.py      # Qdrant 索引 (staging→live)
│   ├── retriever.py    # 密集检索 + 标题 boost
│   ├── models.py       # RAG 领域模型
│   └── service.py      # RAG 服务
├── recipes/            # 配方数据
│   ├── downloader.py   # Mojang 下载 + SHA-1
│   ├── extractor.py    # JAR 提取
│   ├── tree.py         # 配方树算法
│   ├── store.py        # SQLite 持久化
│   ├── models.py       # 配方领域模型
│   └── service.py      # 配方服务
├── storage/            # 持久化适配
│   ├── qdrant.py       # Qdrant 健康探针
│   └── sqlite.py       # SQLite 引擎
├── templates/          # Jinja2 模板
│   ├── base.html
│   ├── index.html      # 主聊天页
│   └── admin.html      # 开发者后台
└── static/             # 静态资源
    ├── css/app.css
    └── js/ (chat.js, admin.js)
```

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `MC_PILOT_HOST` | `127.0.0.1` | 绑定地址 |
| `MC_PILOT_PORT` | `8000` | 绑定端口 |
| `MC_PILOT_LOG_LEVEL` | `INFO` | 日志级别 |
| `MC_PILOT_SQLITE_URL` | `sqlite:///data/mc_pilot.db` | SQLite 路径 |
| `MC_PILOT_QDRANT_URL` | `http://localhost:6333` | Qdrant 地址 |
| `DEEPSEEK_API_KEY` | — | DeepSeek API 密钥（必需） |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | API 基础 URL |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | 模型名 |

## 课程验收要点

- 真实模型连通性: `python scripts/test_connectivity.py`
- Agent 工具调用: 发送 `/pilot 查询附魔台配方` 验证 wiki_search + recipe_query 工具选择
- 离线测试: `pytest -q` (91+ 自动化测试)
- 安全红线和错误出口: 工具白名单、未知工具拒绝、超预算停止、参数校验
- 成本受控: Agent 最多 4 轮工具调用、输出约 800 tokens、每日 200k tokens 上限
- 所有秘密通过 .env 提供，仓库不包含密钥或未脱敏日志
