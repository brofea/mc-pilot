<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

// Developer-tuned Liquid Glass parameters. Keep this as the single source of truth.
const liquidGlassConfig = {
  alpha: 0.93,
  lightness: 49,
  inputBlur: 6,
  outputBlur: 0.5,
  channelX: "R",
  channelY: "B",
  blend: "soft-light",
  scale: -180,
  chromaticRed: 0,
  chromaticGreen: 2,
  chromaticBlue: 4,
  frost: 0.5,
  saturation: 1,
  border: 0.07
} as const;

const props = withDefaults(defineProps<{ as?: string; filterId: string; frost?: number }>(), { as: "div" });

const surface = ref<HTMLElement>();
const width = ref(1);
const height = ref(1);
const radius = ref(16);
let observer: ResizeObserver | undefined;

const mapImage = computed(() => {
  const border = Math.min(width.value, height.value) * (liquidGlassConfig.border * 0.5);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width.value} ${height.value}"><defs><linearGradient id="red" x1="100%" y1="0%" x2="0%" y2="0%"><stop offset="0%" stop-color="#000"/><stop offset="100%" stop-color="red"/></linearGradient><linearGradient id="blue" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" stop-color="#000"/><stop offset="100%" stop-color="blue"/></linearGradient></defs><rect width="${width.value}" height="${height.value}" fill="#000"/><rect width="${width.value}" height="${height.value}" rx="${radius.value}" fill="url(#red)"/><rect width="${width.value}" height="${height.value}" rx="${radius.value}" fill="url(#blue)" style="mix-blend-mode:${liquidGlassConfig.blend}"/><rect x="${border}" y="${border}" width="${Math.max(0, width.value - border * 2)}" height="${Math.max(0, height.value - border * 2)}" rx="${radius.value}" fill="hsl(0 0% ${liquidGlassConfig.lightness}% / ${liquidGlassConfig.alpha})" style="filter:blur(${liquidGlassConfig.inputBlur}px)"/></svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
});

function updateSize(entries: ResizeObserverEntry[]) {
  const entry = entries[0];
  if (!entry || !surface.value) return;
  width.value = Math.max(1, Math.round(entry.contentRect.width));
  height.value = Math.max(1, Math.round(entry.contentRect.height));
  radius.value = Number.parseFloat(getComputedStyle(surface.value).borderRadius) || 16;
}

onMounted(() => {
  if (!surface.value) return;
  observer = new ResizeObserver(updateSize);
  observer.observe(surface.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>

<template>
  <component :is="as" ref="surface" class="liquid-glass" :style="{ '--liquid-filter': `url(#${filterId})`, '--liquid-frost': props.frost ?? liquidGlassConfig.frost, '--liquid-saturation': liquidGlassConfig.saturation }">
    <svg class="liquid-glass-filter" aria-hidden="true" focusable="false">
      <defs>
        <filter :id="filterId" color-interpolation-filters="sRGB">
          <feImage :href="mapImage" result="map" />
          <feDisplacementMap in="SourceGraphic" in2="map" :xChannelSelector="liquidGlassConfig.channelX" :yChannelSelector="liquidGlassConfig.channelY" :scale="liquidGlassConfig.scale + liquidGlassConfig.chromaticRed" result="disp-red" />
          <feColorMatrix in="disp-red" type="matrix" values="1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0" result="red" />
          <feDisplacementMap in="SourceGraphic" in2="map" :xChannelSelector="liquidGlassConfig.channelX" :yChannelSelector="liquidGlassConfig.channelY" :scale="liquidGlassConfig.scale + liquidGlassConfig.chromaticGreen" result="disp-green" />
          <feColorMatrix in="disp-green" type="matrix" values="0 0 0 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 1 0" result="green" />
          <feDisplacementMap in="SourceGraphic" in2="map" :xChannelSelector="liquidGlassConfig.channelX" :yChannelSelector="liquidGlassConfig.channelY" :scale="liquidGlassConfig.scale + liquidGlassConfig.chromaticBlue" result="disp-blue" />
          <feColorMatrix in="disp-blue" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 0 0 1 0" result="blue" />
          <feBlend in="red" in2="green" mode="screen" result="red-green" />
          <feBlend in="red-green" in2="blue" mode="screen" result="output" />
          <feGaussianBlur in="output" :stdDeviation="liquidGlassConfig.outputBlur" />
        </filter>
      </defs>
    </svg>
    <span class="liquid-glass-effect" aria-hidden="true" />
    <slot />
  </component>
</template>
