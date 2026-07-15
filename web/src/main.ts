import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "./styles.css";
import "./theme.css";
import "./texture.css";
import "./liquid-glass.css";
import "./liquid-glass-browser.css";
import "./mobile.css";

createApp(App).use(router).mount("#app");
