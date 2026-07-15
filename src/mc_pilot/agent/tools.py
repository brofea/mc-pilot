"""MCP-style tool contracts for wiki_search, recipe_query, and get_status."""

from __future__ import annotations

from mc_pilot.agent.models import ToolMessage

WIKI_SEARCH_TOOL = ToolMessage(
    name="wiki_search",
    description=(
        "在中文 Minecraft Wiki 知识库中搜索与查询相关的内容。"
        "返回包含来源 URL 和版本信息的文本片段。"
        "当你需要回答关于游戏机制、生物、方块特性等知识类问题时使用此工具。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索查询，例如'附魔台的作用'、'凋零骷髅的生成条件'",
            },
            "top_k": {
                "type": "integer",
                "description": "返回的结果数量，默认 8，最大 15",
                "default": 8,
                "minimum": 1,
                "maximum": 15,
            },
        },
        "required": ["query"],
    },
)

RECIPE_QUERY_TOOL = ToolMessage(
    name="recipe_query",
    description=(
        "查询物品合成配方树，返回 N 层递归材料树和叶子原料汇总。"
        "不确定物品 ID 时先用 wiki_search 确认。"
        "max_depth 控制递归深度：1=仅直接合成材料(合成配方), "
        "2=合成材料+子材料(详细配方), 10=追溯到原始材料(基础原料)。"
        "quantity 控制目标合成总数量，结果会按 quantity 倍乘。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "item_id": {
                "type": "string",
                "description": (
                    "目标物品的资源 ID，"
                    "如 minecraft:enchanting_table、minecraft:diamond_sword"
                ),
            },
            "quantity": {
                "type": "integer",
                "description": "目标合成总数量，默认 1。用户要 N 个就传 N。",
                "default": 1,
                "minimum": 1,
                "maximum": 999,
            },
            "max_depth": {
                "type": "integer",
                "description": (
                    "递归深度：用户问合成材料→1, "
                    "问详细材料→2~3, 问原始材料/基础原料→10。"
                ),
                "default": 1,
                "minimum": 1,
                "maximum": 100,
            },
        },
        "required": ["item_id"],
    },
)

RECIPE_DIRECT_TOOL = ToolMessage(
    name="recipe_direct",
    description="查询物品的直接合成配方列表，不展开材料树。用于快速查看合成方式。",
    parameters={
        "type": "object",
        "properties": {
            "item_id": {
                "type": "string",
                "description": "目标物品的资源 ID",
            },
        },
        "required": ["item_id"],
    },
)

GET_STATUS_TOOL = ToolMessage(
    name="get_status",
    description=(
        "查询 Minecraft Pilot 是否可用的公开服务概览。"
        "不会返回模型、服务器、配置、Token 用量或其他内部信息。"
    ),
    parameters={
        "type": "object",
        "properties": {},
        "required": [],
    },
)

ALL_TOOLS: tuple[ToolMessage, ...] = (
    WIKI_SEARCH_TOOL,
    RECIPE_QUERY_TOOL,
    RECIPE_DIRECT_TOOL,
    GET_STATUS_TOOL,
)

TOOL_WHITELIST: frozenset[str] = frozenset(t.name for t in ALL_TOOLS)
