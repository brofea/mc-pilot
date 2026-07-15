# 修复移动端导航与布局适配

## Goal

为手机端提供可展开的左侧导航抽屉，重新组织现有桌面侧栏、顶部导航、服务状态卡和输入栏，消除截图中服务卡和输入框覆盖正文的布局问题。

## What I already know

* 当前移动端隐藏 `.conversation-rail` 和桌面导航，保留底部五项导航。
* 当前服务状态卡在 `liquid-glass.css` 中仍被固定定位；输入栏为粘性定位，二者会在小屏幕上覆盖消息/知识内容。
* 当前五项路由定义集中在 `web/src/App.vue`；对话列表与服务状态卡位于 `web/src/views/ChatView.vue`。
* 用户要求手机端：左侧可展开菜单、菜单按钮位于 Logo 左侧且同尺寸、原顶部五项导航进入菜单顶部、对话列表位于导航之后、服务状态并入菜单底部且关闭时不可见、输入栏固定到底部并占满宽度。

## Decision (ADR-lite)

**Context**：移动端需要同时容纳路由导航、对话列表与服务状态，且不能再覆盖正文。

**Decision**：使用覆盖式左侧抽屉；抽屉不压缩正文，点击遮罩关闭。桌面布局保持不变。

**Consequences**：需要管理抽屉开闭、遮罩与键盘焦点；移动端底部导航移除。

## Requirements (evolving)

* 在移动断点显示与 Logo 同尺寸的菜单按钮，Logo 与标题整体右移。
* 菜单展开后按顺序显示五项导航、对话列表与服务状态；服务状态只在菜单打开时可见。
* 移动端移除底部五项路由导航。
* 输入栏固定在底部、横向占满可用宽度，且正文预留空间，不被输入栏覆盖。
* 点击抽屉外侧遮罩关闭抽屉；切换路由后关闭抽屉。
* 保持键盘可操作、可访问标签和现有路由/对话/服务状态逻辑。

## Acceptance Criteria (evolving)

* [ ] 手机宽度下，菜单按钮位于 Logo 左侧且尺寸一致。
* [ ] 展开菜单可访问所有五项导航、最近对话和服务状态；收起后服务状态不显示在正文中。
* [ ] 正文、输入栏、服务状态不再相互覆盖。
* [ ] 桌面布局未改变。
* [ ] `npm run typecheck` 与 `npm run build` 通过。

## Definition of Done

* 桌面与移动端布局、键盘操作和焦点状态均已检查。
* 类型检查和生产构建通过。

## Out of Scope

* 不重做聊天、服务状态 API 或桌面导航视觉设计。
* 不实现平板/横屏专用的独立信息架构。

## Technical Notes

* 预计改动：`web/src/App.vue`、`web/src/views/ChatView.vue`、`web/src/styles.css`、`web/src/theme.css`、`web/src/liquid-glass.css`。
* 避免在全局纹理层恢复 `mix-blend-mode`，以防与 Liquid Glass backdrop filter 冲突。
