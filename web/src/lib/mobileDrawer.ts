import type { InjectionKey, Ref } from "vue";

export type MobileDrawer = {
  open: Ref<boolean>;
  close: () => void;
  toggle: () => void;
};

export const mobileDrawerKey: InjectionKey<MobileDrawer> = Symbol("mobileDrawer");
