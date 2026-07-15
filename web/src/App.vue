<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from "vue-router";
import { BookOpen, Heart, Link2, MessageSquareMore, Pickaxe, Settings2 } from "lucide-vue-next";
import LiquidGlass from "@/components/LiquidGlass.vue";

const route = useRoute();
const links = [
  { to: "/", label: "对话", icon: MessageSquareMore },
  { to: "/knowledge", label: "知识库", icon: BookOpen },
  { to: "/recipes", label: "配方浏览", icon: Pickaxe },
  { to: "/game-link", label: "游戏链接", icon: Link2 },
  { to: "/admin", label: "控制台", icon: Settings2 }
];
</script>

<template>
  <div class="ambient ambient-a" aria-hidden="true" />
  <div class="ambient ambient-b" aria-hidden="true" />
  <div class="app-frame">
    <LiquidGlass as="header" filter-id="topbar-liquid-filter" class="topbar liquid-topbar">
      <RouterLink class="brand" to="/" aria-label="Minecraft Pilot 首页">
        <img class="brand-logo" src="https://github.com/user-attachments/assets/880c6c14-bf9f-43e6-a8b1-08a37830af9e" alt="" />
        <span><strong>Minecraft Pilot</strong><small>Java 26.2 · Agent</small></span>
      </RouterLink>
      <nav aria-label="主导航" class="desktop-nav">
        <RouterLink v-for="link in links" :key="link.to" :to="link.to" class="nav-link">
          <component :is="link.icon" :size="16" /><span>{{ link.label }}</span>
        </RouterLink>
      </nav>
      <a class="support-link" href="https://github.com/brofea/mc-pilot#" target="_blank" rel="noreferrer">
        <Heart :size="16" fill="currentColor" /> 支持项目
      </a>
    </LiquidGlass>
    <main id="main-content" tabindex="-1"><RouterView /></main>
    <nav aria-label="移动端主导航" class="mobile-nav">
      <RouterLink v-for="link in links" :key="link.to" :to="link.to" class="mobile-nav-link">
        <component :is="link.icon" :size="19" /><span>{{ link.label }}</span>
      </RouterLink>
    </nav>
  </div>
</template>
