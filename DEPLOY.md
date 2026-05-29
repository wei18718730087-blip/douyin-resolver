# Douyin Link Resolver 部署指南

## 快速部署（Docker）

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止
docker-compose down
```

服务启动后：
- API: http://localhost:8000
- Web: http://localhost:8000 （自动 serve static/）
- Swagger: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health
- 监控指标: http://localhost:8000/metrics

## 手动部署

### 环境要求

- Python >= 3.9（推荐 3.11）
- Node.js >= 18（仅构建前端时需要）

### 安装

```bash
pip install .
```

### 构建前端

```bash
cd apps/web
npm install
npm run build
cp -r dist/* ../../static/
```

### 启动 API

```bash
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| LOG_LEVEL | info | 日志级别 |

## 缓存

- SQLite 缓存文件：`~/.cache/douyin-resolver/cache.db`
- TTL：1 小时
- Docker 中通过 volume `cache_data` 持久化

## 监控

```bash
# 健康检查
curl http://localhost:8000/health

# 监控指标（缓存统计、请求计数）
curl http://localhost:8000/metrics

# 清除过期缓存
curl -X POST http://localhost:8000/cache/clear
```

## 生产就绪检查清单

- [x] 核心解析功能
- [x] CLI JSON 输出
- [x] RESTful API
- [x] Web 前端
- [x] IP 限流（30 RPM）
- [x] SQLite 缓存
- [x] 监控指标端点
- [x] Docker 容器化
- [x] 健康检查
- [x] 结构化错误响应
- [ ] HTTPS（需反向代理）
- [ ] 日志持久化（建议 Loki/ELK）
- [ ] 告警规则（建议 Prometheus + Alertmanager）
