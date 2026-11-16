# WagaMaga frontend

React + strict TypeScript + Vite. The M0 screen reports API and database connectivity; no business screens are implemented.

See [development](../docs/DEVELOPMENT.md) and [testing](../docs/TESTING.md) for commands. Run npm commands in this directory. The development server proxies health, OpenAPI and future API routes to `http://127.0.0.1:8000`.

The production build is static. The development proxy does not become a production reverse proxy; deployment must explicitly route API/docs/health paths to FastAPI under the selected access policy.
