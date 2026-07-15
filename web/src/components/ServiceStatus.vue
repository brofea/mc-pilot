<script setup lang="ts">
import { RotateCw } from "lucide-vue-next";

defineProps<{ services: Record<string, string>; card?: boolean }>();
defineEmits<{ reconnect: [] }>();

function serviceLabel(name: string) {
  return name === "api" ? "Pilot 服务" : name === "game" ? "游戏连接" : name === "recipes" ? "配方树算法" : "Wiki RAG";
}
</script>

<template>
  <section class="service-status" :class="{ 'service-card': card }" aria-label="服务状态">
    <p>服务状态</p><div v-for="(value, name) in services" :key="name" class="service-row"><span :class="['signal', value === 'ready' || value === 'connected' ? 'online' : value === 'degraded' ? 'warn' : '']" /><span>{{ serviceLabel(name) }}</span></div><button type="button" class="reconnect" @click="$emit('reconnect')"><RotateCw :size="14" />重新扫描游戏日志</button>
  </section>
</template>
