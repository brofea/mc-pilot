<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import DOMPurify from "dompurify";
import { marked } from "marked";
import { Plus, RotateCw, Send, Sparkles, Trash2, Wifi, WifiOff } from "lucide-vue-next";
import { api, type Conversation, type Message, type StreamEvent } from "@/lib/api";

type Trace = { label: string; detail: string; done: boolean; success?: boolean };
const conversations = ref<Conversation[]>([]); const activeId = ref(""); const messages = ref<Message[]>([]);
const draft = ref(""); const loading = ref(false); const status = ref("Pilot 已就位"); const traces = ref<Trace[]>([]);
const game = ref<Record<string, unknown>>({ state: "disconnected" }); const error = ref(""); const expanded = ref(false); let socket: WebSocket | undefined;
const services = ref({ api: "connecting", game: "disconnected", recipes: "connecting", rag: "connecting" });
const markdown = (value: string) => DOMPurify.sanitize(marked.parse(value) as string);
const activeTitle = computed(() => conversations.value.find((item) => item.id === activeId.value)?.title ?? "新对话");
async function refresh() { conversations.value = await api.listConversations(); }
async function newChat() { const item = await api.createConversation(); activeId.value = item.id; messages.value = []; traces.value = []; await refresh(); }
async function select(item: Conversation) { const full = await api.getConversation(item.id); activeId.value = item.id; messages.value = full.messages ?? []; traces.value = []; }
async function remove(id: string) { await api.deleteConversation(id); if (id === activeId.value) { activeId.value = ""; messages.value = []; } await refresh(); }
function eventToTrace(event: StreamEvent) {
  if (event.type === "status" || event.type === "thinking") status.value = String(event.text ?? "正在处理…");
  if (event.type === "tool_start") traces.value.push({ label: String(event.label ?? event.name ?? "调用工具"), detail: String(event.detail ?? ""), done: false });
  if (event.type === "tool_end" && traces.value.length) { const last = traces.value.at(-1)!; last.done = true; last.success = Boolean(event.success); }
  if (event.type === "error") error.value = String(event.message ?? "请求出现问题");
}
async function send() {
  const text = draft.value.trim(); if (!text || loading.value) return;
  if (!activeId.value) await newChat();
  draft.value = ""; error.value = ""; loading.value = true; status.value = "正在思考…"; traces.value = []; expanded.value = true;
  messages.value.push({ role: "user", content: text }); let answer = "";
  try { await api.streamChat(text, activeId.value, (event) => { eventToTrace(event); if (event.type === "done" || event.type === "result") answer = String(event.answer ?? answer); }); if (answer) messages.value.push({ role: "assistant", content: answer }); status.value = "已完成"; await refresh(); }
  catch (cause) { error.value = cause instanceof Error ? cause.message : "请求失败"; status.value = "暂时不可用"; }
  finally { loading.value = false; expanded.value = false; await nextTick(); }
}
function connect() { const protocol = location.protocol === "https:" ? "wss:" : "ws:"; socket = new WebSocket(`${protocol}//${location.host}/ws`); socket.onmessage = (event) => { const data = JSON.parse(event.data) as Record<string, unknown>; if (data.type === "state") game.value = data; if (data.type === "death_advice") status.value = String(data.advice ?? status.value); }; }
async function refreshServices() { try { const [ready, gameState, recipes, rag] = await Promise.all([api.readiness(), api.gameState(), fetch("/api/recipes-health").then(r => r.json()), fetch("/api/rag-health").then(r => r.json())]); game.value = gameState; services.value = { api: ready.status === "ready" ? "ready" : "degraded", game: String(gameState.state), recipes: recipes.available ? "ready" : "degraded", rag: rag.available ? "ready" : "degraded" }; } catch { services.value.api = "degraded"; } }
async function reconnectGame() { await fetch("/api/game-state/reconnect", { method: "POST" }); await refreshServices(); }
onMounted(async () => { try { await refresh(); await refreshServices(); connect(); } catch { error.value = "后端状态暂不可用"; } }); onBeforeUnmount(() => socket?.close());
</script>

<template>
  <section class="chat-layout">
    <aside class="conversation-rail" aria-label="对话历史">
      <button class="primary-action" type="button" @click="newChat"><Plus :size="18" />新对话</button>
      <p class="rail-label">最近对话</p>
      <div class="conversation-list">
        <button v-for="item in conversations" :key="item.id" type="button" class="conversation" :class="{ active: item.id === activeId }" @click="select(item)">
          <span>{{ item.title || "新对话" }}</span><Trash2 :size="15" class="delete" @click.stop="remove(item.id)" aria-label="删除对话" />
        </button>
      </div>
    </aside>
    <div class="chat-stage">
      <header class="page-intro"><p class="eyebrow">AGENT WORKSPACE</p><h1>{{ activeTitle }}</h1><p>从配方到 Wiki，让 Pilot 和你一起探索。</p></header>
      <div class="message-flow" aria-live="polite">
        <div v-if="!messages.length" class="welcome-card"><Sparkles :size="26" /><p class="script">世界很大，陪你探索</p><h2>Steve / Alex 想知道什么？</h2><div class="prompt-grid"><button v-for="prompt in ['附魔金苹果的配方是？','介绍一下亮度机制','苍白橡木在哪里获得？','114514个红石中继器所需原始材料']" :key="prompt" type="button" @click="draft = prompt">{{ prompt }}</button></div></div>
        <article v-for="(message, index) in messages" :key="index" class="message" :class="message.role"><span>{{ message.role === "user" ? "你" : "PILOT" }}</span><div v-if="message.role === 'assistant'" class="markdown" v-html="markdown(message.content)" /><p v-else>{{ message.content }}</p></article>
        <div v-if="loading || traces.length" class="trace-card"><button type="button" class="trace-summary" :aria-expanded="loading || expanded" :disabled="loading" @click="!loading && (expanded = !expanded)"><span class="pulse" /><span>{{ status }}</span><span v-if="!loading" class="trace-toggle">{{ expanded ? "收起" : "查看轨迹" }}</span></button><ol v-if="(loading || expanded) && traces.length"><li v-for="(trace, index) in traces" :key="index"><Wifi v-if="trace.success" :size="15" /><WifiOff v-else :size="15" />{{ trace.label }}<small>{{ trace.detail }}</small></li></ol></div>
      </div>
      <p v-if="error" class="error-note" role="alert">{{ error }}</p>
      <form class="composer liquid-composer" @submit.prevent="send"><label class="sr-only" for="prompt">向 Pilot 提问</label><textarea id="prompt" v-model="draft" :disabled="loading" rows="1" placeholder="问问 Minecraft 世界…" @keydown.enter.exact.prevent="send" /><button class="send-button" type="submit" :disabled="loading || !draft.trim()" aria-label="发送"><Send :size="18" /></button></form>
    </div>
    <section class="service-card liquid-service" aria-label="服务状态"><p>服务状态</p><div v-for="(value, name) in services" :key="name" class="service-row"><span :class="['signal', value === 'ready' || value === 'connected' ? 'online' : value === 'degraded' ? 'warn' : '']" /><span>{{ name === 'api' ? 'Pilot 服务' : name === 'game' ? '游戏连接' : name === 'recipes' ? '配方树算法' : 'Wiki RAG' }}</span></div><button type="button" class="reconnect" @click="reconnectGame"><RotateCw :size="14" />重新扫描游戏日志</button></section>
  </section>
</template>
