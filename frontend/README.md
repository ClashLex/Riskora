# Riskora frontend

Canonical frontend: `src/main.tsx` and `src/App.tsx`. Run `npm ci` and `npm run dev`; open <http://127.0.0.1:5173>. Vite proxies `/api` to the FastAPI server on port 8001.

The interface has a labelled navigation sidebar, a searchable fund library, and a research pane. On narrow screens, use the bottom navigation or open the modal fund library from the header. Each section has a shareable URL fragment, such as `/#predictions`. The original `/#evidence` link opens Supporting signals.

The interface uses native links, inputs, tables, disclosure controls, and a dialog. It keeps Tabler icons and a restrained green palette. There are no WebGL or continuous background effects. Table search, sorting, and pagination operate on real API results. Imported and sample data are labelled separately, and evaluation results are scoped by dataset, period, and saved run.

`src/domain.ts` defines API contracts; `src/api.ts` formats server and field-validation errors; `src/hooks/` owns request state and actions; `src/pages/` contains the six screens; `src/components/` contains shared UI. Requests are cancelled on context changes and stale responses cannot populate another selection. Tokens remain in memory.

For an isolated backend on a different port, set `$env:RISKORA_API_TARGET = 'http://127.0.0.1:8002'` in the terminal before starting Vite. The default remains port 8001.

See the [root README](../README.md) for backend setup, data imports, model workflow, and known limitations. Verify with `npm test`, `npm run lint`, `npm run format:check`, and `npm run build`. Use `npm run format` after editing the frontend.
