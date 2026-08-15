# Nadha Shop — Phase 1

Android-first shop ledger with a React/Vite/TypeScript/Capacitor client and FastAPI/SQLAlchemy/Alembic/PostgreSQL API.

## Development

1. `docker compose up -d db`
2. `cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
3. `cp .env.example .env && alembic upgrade head && uvicorn app.main:app --reload`
4. `cd frontend && npm install && npm run dev`

For Android, configure `VITE_API_URL` to an API reachable from the device, then run `npm run android:build`. The debug APK is below `frontend/android/app/build/outputs/apk/debug/`.

## Maintenance
- 2026-08-15: routine project maintenance check completed.

## Project Structure
- frontend/: React + Vite + TypeScript client
- backend/: FastAPI application
