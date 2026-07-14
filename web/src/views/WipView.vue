<script setup lang="ts">
import { computed } from "vue"; import { BookOpen, Construction, Pickaxe } from "lucide-vue-next"; import { RouterLink } from "vue-router";
const props = defineProps<{ kind: "knowledge" | "recipes" | "game" }>();
const copy = computed(() => props.kind === "knowledge" ? { title: "Minecraft 知识库", text: "把中文 Wiki、可靠来源与探索路径组织成一处沉浸式资料库。", icon: BookOpen, steps: ["来源卡片与版本标记", "主题化知识路径", "可引用的探索笔记"] } : { title: "配方浏览", text: "以材料树和确定性计算为核心，构建更直观的合成探索空间。", icon: Pickaxe, steps: ["物品与材料关系图", "可视化配方树", "收藏与建造清单"] });
</script>
<template><section class="wip-page" :class="`wip-${kind}`"><div class="wip-orb" aria-hidden="true" /><p class="eyebrow">IN EXCAVATION · {{ kind.toUpperCase() }}</p><component :is="copy.icon" :size="34" /><h1>{{ copy.title }}</h1><p class="script">{{ copy.text }}</p><span class="wip-badge"><Construction :size="15" /> WIP · 正在挖掘</span><div v-if="kind === 'game'" class="link-preview"><span>LOCAL GAME GATEWAY</span><strong>等待 Minecraft 实例</strong><small>日志、玩家与世界连接将在此聚合。</small></div><ol><li v-for="step in copy.steps" :key="step">{{ step }}</li></ol><RouterLink class="primary-action" to="/">回到与 Pilot 对话</RouterLink></section></template>
