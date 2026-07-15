# 将网页前端玻璃替换为 Liquid Glass 材质

## Goal

将现有网页工作台中已具玻璃质感的顶部栏、服务状态卡片和聊天输入框升级为基于 SVG 位移滤镜的 Liquid Glass 材质，同时维持现有布局、交互和响应式行为。

## What I already know

* 用户提供了桌面样例工程：`/Users/brofea/Desktop/LGlass.html`、`LGlass.css` 与 `LGlass.js`。
* 当前三个目标组件已经分别带有 `liquid-topbar`、`liquid-service`、`liquid-composer` 类，样式集中在 `web/src/liquid-glass.css`。
* 顶部栏位于 `web/src/App.vue`；服务状态卡片和输入框位于 `web/src/views/ChatView.vue`。
* 样例使用 SVG `feDisplacementMap`、RGB 通道分离/合成与动态生成的位移贴图；当前浏览器支持限制需要作为降级条件考虑。

## Requirements (evolving)

* 仅升级以下三类玻璃组件：顶部栏、服务状态卡片、聊天输入框。
* 从 LGlass 样例抽取并接入真实 Liquid Glass 位移材质，而不是仅调整普通 `backdrop-filter` 参数。
* 使用用户指定的材质参数：
  * alpha：`0.93`
  * lightness：`49`
  * input blur：`11`
  * output blur：`0.0`
  * channel x：`R`
  * channel y：`B`
  * blend：`soft-light`
  * scale：`-180`
  * chromatic：red `0`、green `5`、blue `10`
* 保持现有导航、状态刷新、输入发送、键盘操作、可访问性和移动端布局不变。
* 为不支持 SVG URL `backdrop-filter` 的浏览器保留可读的现有半透明毛玻璃降级效果。

## Acceptance Criteria (evolving)

* [ ] 三个指定组件均渲染 Liquid Glass 位移效果，且使用给定参数。
* [ ] 三个组件的圆角分别与现有尺寸/响应式断点一致，位移贴图随组件尺寸变化更新。
* [ ] Chromium 中能观察到折射/色差式液态玻璃效果；不支持的浏览器中仍保持清晰、可用的毛玻璃界面。
* [ ] 前端 TypeScript 检查与生产构建通过。

## Definition of Done

* 前端构建和类型检查通过。
* 变更经桌面与移动断点的视觉检查。
* 不改变本任务范围外的页面或业务行为。

## Decision (ADR-lite)

**Context**：用户要求将既有三块玻璃组件升级为桌面 LGlass 样例中的液态玻璃材质；样例使用的 SVG URL `backdrop-filter` 在 Chromium 之外支持有限。

**Decision**：将样例的动态位移贴图与 RGB 色差滤镜封装为前端内部实现，限定应用到三个指定组件。Chromium 使用完整材质；其他浏览器沿用经过调校的半透明毛玻璃回退。

**Consequences**：无需增加运行时依赖，并保留现有组件布局；需要针对每个组件尺寸维护独立位移图，并在组件尺寸变化时刷新。

## Out of Scope (explicit)

* 不改造欢迎卡、消息气泡、管理后台面板或移动底部导航。
* 不修改后端 API、对话逻辑或 Fabric Mod。
* 不引入第三方运行时依赖。

## Technical Notes

* 样例中的 SVG 滤镜需要由 Vue 组件的模板生成，并由客户端代码为每个目标元素创建与尺寸、圆角相匹配的位移贴图。
* 现有视觉基础样式：`web/src/liquid-glass.css`；全局 UI 结构：`web/src/App.vue`、`web/src/views/ChatView.vue`。
