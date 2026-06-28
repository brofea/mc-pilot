# Frontend Directory Structure

```text
src/mc_pilot/
├── templates/
│   ├── base.html
│   ├── index.html
│   └── admin.html
└── static/
    ├── css/app.css
    └── js/
        ├── api.js
        ├── chat.js
        ├── recipe-tree.js
        ├── status-stream.js
        └── admin.js
```

- Templates own semantic document structure; JS enhances behavior.
- Split JS by feature responsibility, not by execution order.
- Shared HTTP parsing lives in `api.js`; do not duplicate fetch/error code.
- Static assets use kebab-case names. DOM IDs are stable interface names, not visual descriptions.
- Keep game/admin views separate while sharing `base.html` and small reusable partials.

Current examples: `templates/base.html`, `templates/index.html`, `templates/admin.html`, and `static/js/status-stream.js`.
