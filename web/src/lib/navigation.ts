import { BookOpen, Link2, MessageSquareMore, Pickaxe, Settings2 } from "lucide-vue-next";

export const navigationLinks = [
  { to: "/", label: "对话", icon: MessageSquareMore },
  { to: "/knowledge", label: "知识库", icon: BookOpen },
  { to: "/recipes", label: "配方浏览", icon: Pickaxe },
  { to: "/game-link", label: "游戏链接", icon: Link2 },
  { to: "/admin", label: "控制台", icon: Settings2 }
];
