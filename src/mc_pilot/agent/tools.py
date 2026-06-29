"""MCP-style tool contracts for wiki_search and recipe_query."""

from __future__ import annotations

from mc_pilot.agent.models import ToolMessage

WIKI_SEARCH_TOOL = ToolMessage(
    name="wiki_search",
    description=(
        "在中文 Minecraft Wiki 知识库中搜索与查询相关的内容。"
        "返回包含来源 URL 和版本信息的文本片段。"
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
                "description": "返回的结果数量，默认 5，最大 10",
                "default": 5,
                "minimum": 1,
                "maximum": 10,
            },
        },
        "required": ["query"],
    },
)

RECIPE_QUERY_TOOL = ToolMessage(
    name="recipe_query",
    description=(
        "查询物品合成配方树。返回直接配方、递归材料树和叶结点原料汇总。"
        "不确定物品 ID 时先用 wiki_search 确认。"
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
                "description": "目标合成数量，默认 1",
                "default": 1,
                "minimum": 1,
                "maximum": 100,
            },
            "max_depth": {
                "type": "integer",
                "description": "最大递归深度，None 表示不限制",
            },
        },
        "required": ["item_id"],
    },
)

RECIPE_DIRECT_TOOL = ToolMessage(
    name="recipe_direct",
    description="查询物品的直接合成配方列表，不展开材料树。",
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

ALL_TOOLS: tuple[ToolMessage, ...] = (
    WIKI_SEARCH_TOOL,
    RECIPE_QUERY_TOOL,
    RECIPE_DIRECT_TOOL,
)

TOOL_WHITELIST: frozenset[str] = frozenset(t.name for t in ALL_TOOLS)
