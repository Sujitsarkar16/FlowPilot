.PHONY: dev-api dev-web dev-db dev-mail stop logs reset-db

dev-api:
	cd apps/api && .venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

dev-web:
	cd apps/web && npm run dev

dev-db:
	docker compose up -d postgres

dev-mail:
	docker compose --profile mail up -d mailpit

stop:
	docker compose down

logs:
	docker compose logs -f --tail=100

reset-db:
	@echo "This deletes the local PostgreSQL volume."
	docker compose down -v
