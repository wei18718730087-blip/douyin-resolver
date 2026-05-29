# Douyin Link Resolver

抖音公开分享链接解析工具 — CLI / API / Web 三端统一。

## 功能

- 抖音短链/长链/分享文本解析
- 作品信息获取（标题、作者、封面）
- 视频资源获取（合规边界内最高质量）
- 热门评论获取
- CLI JSON 输出（Agent 友好）
- RESTful API
- Web 测试页面
- SQLite 缓存（1 小时 TTL，避免重复请求）
- 监控指标端点（/metrics）

## 快速开始

### 安装

```bash
pip install -e .
```

### CLI 使用

```bash
# 基本解析
douyin-resolver "https://v.douyin.com/xxxx/"

# 从分享文本提取
douyin-resolver "复制打开抖音，看看... https://v.douyin.com/xxxx/"

# 人类可读模式
douyin-resolver "https://v.douyin.com/xxxx/" --human

# 获取评论
douyin-resolver "https://v.douyin.com/xxxx/" --comments 20
```

### API 服务

```bash
# Makefile 快捷命令
make dev            # 启动 API 热重载
make build          # 构建前端
make test           # 运行测试
make health         # 健康检查
make metrics        # 查看监控
make resolve URL="https://v.douyin.com/xxx/"  # 解析链接

# 手动启动
uvicorn apps.api.main:app --reload

# 健康检查
curl http://localhost:8000/health

# 解析链接
curl -X POST http://localhost:8000/api/v1/douyin/resolve \
  -H "Content-Type: application/json" \
  -d '{"url": "https://v.douyin.com/xxxx/"}'
```

### Docker 部署

```bash
make docker-up      # 构建并启动
make docker-logs    # 查看日志
make docker-down    # 停止
```

### Web 前端开发

```bash
make dev-web        # 启动前端开发服务
```

## 项目结构

```
douyin-resolver/
├── apps/
│   ├── api/              # FastAPI 服务
│   │   ├── main.py
│   │   ├── rate_limiter.py
│   │   ├── error_handler.py
│   │   └── routes/
│   │       ├── health.py
│   │       ├── resolve.py
│   │       └── metrics.py
│   ├── web/              # React 前端
│   └── cli/              # Typer CLI
├── packages/
│   └── core/             # 核心解析逻辑
│       ├── schemas.py
│       ├── errors.py
│       ├── input_parser.py
│       ├── url_resolver.py
│       ├── douyin_provider.py
│       ├── comment_provider.py
│       └── cache.py      # SQLite 缓存层
├── tests/
├── scripts/
├── static/               # 前端构建产物
├── .github/workflows/    # CI/CD
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── DEPLOY.md
└── pyproject.toml
```

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 监控端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /health | 健康检查 |
| GET | /metrics | 服务监控指标（缓存统计、请求计数） |
| POST | /cache/clear | 手动清除过期缓存 |

## 错误码

| 错误码 | 含义 |
|--------|------|
| INVALID_INPUT | 输入不是有效 URL |
| UNSUPPORTED_PLATFORM | 非抖音链接 |
| RESOLVE_FAILED | 短链跳转失败 |
| AWEME_ID_NOT_FOUND | 未找到作品 ID |
| MEDIA_UNAVAILABLE | 无可访问视频资源 |
| COMMENTS_UNAVAILABLE | 评论不可访问 |
| RATE_LIMITED | 请求过于频繁 |
| UPSTREAM_CHANGED | 上游页面结构变化 |

## 合规声明

本工具仅用于授权内容解析与测试。请确认你拥有下载和使用该内容的权利。
