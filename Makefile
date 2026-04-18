DC = docker compose

.PHONY: up down restart build logs logs-db migrate revision seed psql shell lint ps

up:
	$(DC) up --build

up-d:
	$(DC) up --build -d

down:
	$(DC) down

restart:
	$(DC) restart

build:
	$(DC) build

logs:
	$(DC) logs -f backend

logs-db:
	$(DC) logs -f db

ps:
	$(DC) ps

migrate:
	$(DC) exec backend alembic upgrade head

revision:
	$(DC) exec backend alembic revision --autogenerate -m "$(m)"

seed:
	$(DC) exec backend python -m app.seeds.categories

seed-words:
	$(DC) exec backend python -m app.seeds.words

seed-all: seed seed-words

psql:
	$(DC) exec db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

shell:
	$(DC) exec backend sh

lint:
	$(DC) exec backend sh -c "ruff check app && black --check app"

fmt:
	$(DC) exec backend sh -c "ruff check --fix app && black app"

tts-clear:
	$(DC) exec db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c "DELETE FROM word_audio;"

tts-info:
	@echo "TTS_ENGINE переключается в .env (piper | kokoro). После изменения: make restart"
