# Riskora frontend

`src/main.tsx` mounts `src/Stage.tsx`, which places the supplied white and gray dither background behind the research interface in `src/App.tsx`. The effect lives in `src/components/Dither.tsx`; the matching controls and surfaces are styled in `src/stage.css`. The animation is capped at 30 frames per second, respects reduced motion, and leaves a white background if WebGL2 is unavailable.

Run `npm ci` and `npm run dev`, then open <http://127.0.0.1:5173>. Vite proxies `/api` to the FastAPI server on port 8001. Set `$env:RISKORA_API_TARGET = 'http://127.0.0.1:8002'` before starting Vite to use another backend port.

The workspace includes fund disclosures, candidate rankings, supporting signals, evaluation, and data management. `src/domain.ts` defines API contracts; `src/api.ts` and `src/hooks/` handle requests and actions; `src/pages/` contains the screens; `src/components/` contains shared navigation, tables, and controls.

Verify changes with `npm run test`, `npm run lint`, `npm run format:check`, and `npm run build`. See the [root README](../README.md) for backend setup and model details.
