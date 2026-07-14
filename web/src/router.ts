import { createRouter, createWebHistory } from "vue-router";
import ChatView from "./views/ChatView.vue";
import WipView from "./views/WipView.vue";
import AdminView from "./views/AdminView.vue";

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: ChatView, meta: { title: "Pilot" } },
    { path: "/knowledge", component: WipView, props: { kind: "knowledge" } },
    { path: "/recipes", component: WipView, props: { kind: "recipes" } },
    { path: "/game-link", component: WipView, props: { kind: "game" } },
    { path: "/admin", component: AdminView },
    { path: "/:pathMatch(.*)*", redirect: "/" }
  ],
  scrollBehavior: () => ({ top: 0 })
});
