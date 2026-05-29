.PHONY: help install dev build test lint clean docker-up docker-down

help:  ## 显示帮助
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## 安装 Python 依赖
	pip install -e ".[dev]"

dev:  ## 启动开发服务（API + 热重载）
	uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

dev-web:  ## 启动前端开发服务
	cd apps/web && npm run dev

build:  ## 构建前端并复制到 static/
	cd apps/web && npm run build
	rm -rf static/
	cp -r apps/web/dist/ static/
	@echo "✅ 前端构建完成 → static/"

test:  ## 运行测试
	python3 -m pytest tests/ -v

lint:  ## 代码检查
	cd apps/web && npx eslint src/
	python3 -m py_compile apps/api/main.py
	python3 -m py_compile apps/cli/main.py
	python3 -m py_compile packages/core/cache.py

clean:  ## 清理构建产物
	rm -rf static/ apps/web/dist/ apps/web/node_modules/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache/ *.egg-info/

docker-up:  ## Docker 启动
	docker-compose up -d --build

docker-down:  ## Docker 停止
	docker-compose down

docker-logs:  ## Docker 日志
	docker-compose logs -f

health:  ## 健康检查
	curl -s http://localhost:8000/health | python3 -m json.tool

metrics:  ## 查看监控指标
	curl -s http://localhost:8000/metrics | python3 -m json.tool

resolve:  ## 解析链接（用法: make resolve URL="https://v.douyin.com/xxx/")
	@curl -s -X POST http://localhost:8000/api/v1/douyin/resolve \
		-H "Content-Type: application/json" \
		-d '{"url": "$(URL)"}' | python3 -m json.tool
