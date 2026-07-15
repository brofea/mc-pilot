<script setup lang="ts">
import { provide, ref, watch } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";
import { Heart, Menu, X } from "lucide-vue-next";
import LiquidGlass from "@/components/LiquidGlass.vue";
import { mobileDrawerKey } from "@/lib/mobileDrawer";
import { navigationLinks } from "@/lib/navigation";

const route = useRoute();
const mobileDrawerOpen = ref(false);
const closeMobileDrawer = () => { mobileDrawerOpen.value = false; };
const toggleMobileDrawer = () => { mobileDrawerOpen.value = !mobileDrawerOpen.value; };

provide(mobileDrawerKey, { open: mobileDrawerOpen, close: closeMobileDrawer, toggle: toggleMobileDrawer });
watch(route, closeMobileDrawer);
</script>

<template>
  <div class="ambient ambient-a" aria-hidden="true" />
  <div class="ambient ambient-b" aria-hidden="true" />
  <div class="app-frame">
    <LiquidGlass as="header" filter-id="topbar-liquid-filter" class="topbar liquid-topbar">
      <button class="mobile-menu-button" type="button" aria-label="打开菜单" aria-controls="mobile-navigation-drawer" :aria-expanded="mobileDrawerOpen" @click="toggleMobileDrawer"><Menu :size="24" /></button>
      <RouterLink class="brand" to="/" aria-label="Minecraft Pilot 首页">
        <img class="brand-logo" src="https://github.com/user-attachments/assets/880c6c14-bf9f-43e6-a8b1-08a37830af9e" alt="" />
        <span><strong>Minecraft Pilot</strong><small>Java 26.2 · Agent</small></span>
      </RouterLink>
      <nav aria-label="主导航" class="desktop-nav">
        <RouterLink v-for="link in navigationLinks" :key="link.to" :to="link.to" class="nav-link">
          <component :is="link.icon" :size="16" /><span>{{ link.label }}</span>
        </RouterLink>
      </nav>
      <a class="support-link" href="https://github.com/brofea/mc-pilot#" target="_blank" rel="noreferrer">
        <Heart :size="16" fill="currentColor" /> 支持项目
      </a>
    </LiquidGlass>
    <div v-if="mobileDrawerOpen && route.path !== '/'" class="mobile-drawer-layer">
      <button class="mobile-drawer-backdrop" type="button" aria-label="关闭菜单" @click="closeMobileDrawer" />
      <LiquidGlass id="mobile-navigation-drawer" as="aside" filter-id="mobile-navigation-liquid-filter" class="mobile-drawer" :frost="0.86" role="dialog" aria-modal="true" aria-label="主菜单">
        <header class="mobile-drawer-header"><span>导航</span><button type="button" aria-label="关闭菜单" @click="closeMobileDrawer"><X :size="22" /></button></header>
        <nav aria-label="移动端主导航" class="mobile-drawer-nav">
          <RouterLink v-for="link in navigationLinks" :key="link.to" :to="link.to" class="nav-link" @click="closeMobileDrawer"><component :is="link.icon" :size="18" /><span>{{ link.label }}</span></RouterLink>
        </nav>
      </LiquidGlass>
    </div>
    <main id="main-content" tabindex="-1"><RouterView /></main>
  </div>
</template>
