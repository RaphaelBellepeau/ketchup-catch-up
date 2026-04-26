# Gradbot voice bundles (vendored)

These files are copied from the `gradbot` Python package at
`backend/.venv/lib/python3.13/site-packages/gradbot/js_audio/`.

We vendor them into the frontend's `public/static/js/` because Web
Workers and AudioWorklets refuse cross-origin URLs even with full CORS
allow-all headers. Loading them from the same origin as the SPA is the
only reliable way to make voice work in production where the frontend
and backend live on different Cloud Run domains.

## Refresh after a gradbot upgrade

```sh
cp backend/.venv/lib/python3.13/site-packages/gradbot/js_audio/* public/static/js/
git add public/static/js
git diff --cached --stat
```

Pinned to gradbot **0.1.6**.
