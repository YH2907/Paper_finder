.PHONY: help install dev test lint format clean docker-up docker-down db-migrate db-upgrade

# 默认目标
help:
	@echo "Paper Finder Agent - 可用命令:"
	@echo ""
	@echo "  安装和开发:"
	@echo "    make install      安装依赖"
	@echo "    make dev          启动开发服务器"
	@echo "    make test         运行测试"
	@echo ""
	@echo "  代码质量:"
	@echo "    make lint         代码检查"
	@echo "    make format       代码格式化"
	@echo ""
	@echo "  Docker:"
	@echo "    make docker-up    启动所有服务"
	@echo "    make docker-down  停止所有服务"
	@echo ""
	@echo "  数据库:"
	@echo "    make db-migrate   生成迁移文件"
	@echo "    make db-upgrade   执行数据库迁移"
	@echo ""
	@echo "  清理:"
	@echo "    make clean        清理临时文件"

# 安装依赖
install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

# 启动开发服务器
dev:
	cd frontend && npm run dev &
	cd backend && uvicorn app.main:app --reload --port 8000

# 运行测试
test:
	cd backend && pytest tests/ -v

# 代码检查
lint:
	cd backend && ruff check app/
	cd frontend && npm run lint

# 代码格式化
format:
	cd backend && ruff format app/
	cd frontend && npm run format

# Docker 命令
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# 数据库迁移
db-migrate:
	cd backend && alembic revision --autogenerate -m "$(msg)"

db-upgrade:
	cd backend && alembic upgrade head

db-downgrade:
	cd backend && alembic downgrade -1

# 清理
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -prune -o -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true

# 创建数据库
db-create:
	docker-compose exec postgres psql -U paperfinder -c "CREATE DATABASE paperfinder;" 2>/dev/null || true

# 初始化 pgvector
db-init-vector:
	docker-compose exec postgres psql -U paperfinder -d paperfinder -c "CREATE EXTENSION IF NOT EXISTS vector;"
