DC = docker compose

.PHONY: up up-d down restart build logs logs-db migrate revision seed seed-words seed-all psql shell lint fmt tts-clear tts-info ps gen-secret create-admin audit

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

tts-reset-volume:
	$(DC) stop backend
	$(DC) rm -f backend
	-docker volume rm english-dictionary_tts_models
	$(DC) up -d backend

tts-info:
	@echo "TTS_ENGINE переключается в .env (piper | kokoro). После изменения: make restart"

# --- Безопасность ---

# Генерирует новый JWT_SECRET (64 символа urlsafe). Скопируйте вывод в .env.
gen-secret:
	@python -c "import secrets; print(secrets.token_urlsafe(64))"

# Повышает существующего пользователя до админа.
# Email берётся из аргумента (make create-admin email=...) либо из .env (ADMIN_EMAIL).
create-admin:
	$(DC) exec backend python -m app.scripts.create_admin $(email)

# Выводит последние 50 записей audit_log.
audit:
	$(DC) exec db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB) -c \
		"SELECT created_at, action, user_id, ip FROM audit_log ORDER BY created_at DESC LIMIT 50;"
