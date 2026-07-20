.PHONY: dev-api dev-web dev-mail stop-mail logs-mail

dev-api:
	cd apps/api && .venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

dev-web:
	cd apps/web && npm run dev

dev-mail:
	docker compose --profile mail up -d mailpit

stop-mail:
	docker compose --profile mail down

logs-mail:
	docker compose --profile mail logs -f --tail=100
