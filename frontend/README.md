# WagaMaga frontend

React + strict TypeScript + Vite and React Router. The public homepage opens at `/` without an API/session dependency and links to login/registration. UM1 provides own-account and administrator account-management screens. The original M0 connection screen is at `/connection`. All existing screens share the creamy green/sage palette and locally hosted Plus Jakarta Sans from src/theme.css. Rounded cards, pill actions, accessible fields and native confirmation dialogs follow docs/UI_DESIGN.md. Auth pages reuse the generated field image on desktop and keep forms first on mobile. Planned cultivation capabilities remain labelled as future work on the homepage.

See [development](../docs/DEVELOPMENT.md), [testing](../docs/TESTING.md) and the [UM1 contract](../docs/USER_MANAGEMENT.md). Run npm commands here. Vite proxies health, OpenAPI and account API routes to `http://127.0.0.1:8000`. Access tokens stay in memory, refresh cookies are HttpOnly, and API permissions are enforced server-side. Browser tests use a guarded PostgreSQL test database and generated synthetic credentials; stop normal API/Vite processes before running them.

The production build is static. The development proxy does not become a production reverse proxy; deployment must explicitly route API/docs/health paths to FastAPI under the selected access policy.
