.PHONY: help up down logs

help:
	@echo "up       Start local MinIO"
	@echo "down     Stop local containers"
	@echo "logs     Follow MinIO logs"

up:
	docker compose up -d minio

down:
	docker compose down

logs:
	docker compose logs -f minio
