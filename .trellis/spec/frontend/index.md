# Frontend Development Guidelines

The frontend is server-rendered Jinja2 with small native JavaScript modules. React-specific concepts do not apply.

## Pre-Development Checklist

1. Read [Directory Structure](./directory-structure.md).
2. Read [Components](./component-guidelines.md), [State](./state-management.md), and [Type Safety](./type-safety.md).
3. Read [Browser Modules](./hook-guidelines.md) before adding fetch or WebSocket logic.
4. Read [Quality](./quality-guidelines.md) before changing user-visible behavior.

## Quality Check

- Pages work without a Node build step.
- Keyboard navigation, labels, focus, empty/loading/error states are present.
- Browser code never receives secrets or raw internal errors.
- WebSocket reconnects are bounded and do not duplicate messages.
