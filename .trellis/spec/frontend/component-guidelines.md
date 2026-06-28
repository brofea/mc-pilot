# Component Guidelines

Components are Jinja2 partials plus semantic HTML and optional JS controllers.

- Prefer native elements: forms, buttons, details/summary, lists, dialogs.
- Every interactive control has a visible label or `aria-label`.
- Render initial empty/loading/degraded states on the server; JS transitions between explicit states.
- Use `data-*` attributes for JS behavior. Do not encode behavior in CSS class names.
- Escape user/model content by default. Never inject untrusted strings with `innerHTML`; build DOM nodes or use `textContent`.
- Recipe trees must remain usable as nested lists when styling is unavailable.
- Transient death messages announce politely and do not steal focus.

CSS uses a small custom stylesheet with variables and responsive layout; no UI framework is required for M1.
