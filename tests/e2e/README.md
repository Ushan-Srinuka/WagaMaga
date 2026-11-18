# Browser journeys

The implemented UM1 Playwright suite lives in frontend/e2e/ with frontend/playwright.config.ts, next to its package manifest. It starts the real FastAPI/Vite servers and uses a guarded PostgreSQL `_test` database with generated synthetic credentials. TESTING.md owns setup, exact commands and results. Future farming/AI journeys can extend that suite; no placeholder test claims those features are covered.
