# 行业信息助手 (Industry Information Assistant)

一个基于 AI 的深度研究助手，支持智能搜索、知识图谱、数据可视化等功能。

## 目录
- [环境要求](#环境要求)
- [快速启动](#快速启动)
- [详细配置](#详细配置)
- [常见问题](#常见问题)

---

## 环境要求

| 依赖 | 版本要求 | 说明 |
|------|---------|------|
| Docker | 20.0+ | 运行所有基础服务（PostgreSQL、Redis、Milvus、Elasticsearch） |
| Python | 3.10+ | 后端服务 |
| Node.js | 18+ | 前端构建 |

---

## 快速启动

### 1. 下载项目
```bash
cd industry_information_assistant
```

### 2. 一键启动所有基础服务 (推荐)

**方式 A: 使用启动脚本（推荐）**
```bash
# 在项目根目录执行
chmod +x start-services.sh
./start-services.sh start
```

**方式 B: 使用 Docker Compose**
```bash
# 在项目根目录执行
docker compose up -d
```

验证服务状态：
```bash
# 方式 A
./start-services.sh status

# 方式 B
docker compose ps

# 应该看到以下服务运行中:
# - industry_postgres (PostgreSQL)
# - industry_redis (Redis)
# - industry_milvus (Milvus)
# - industry_elasticsearch (Elasticsearch)
# - industry_minio (MinIO)
# - industry_etcd (etcd)
```

**服务访问地址：**
- PostgreSQL: `localhost:5432` (用户名: `postgres`, 密码: 见你配置的 `POSTGRES_PASSWORD`)
- Redis: `localhost:6379`
- Milvus: `localhost:19530`
- Elasticsearch: `localhost:1200`
- MinIO Console: `localhost:9001` (账号/密码: 见你配置的 `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`)

> ⚠️ 这些口令自 T07 起不再明文写在仓库里，改为从 `.env` 注入：
> 根目录 `.env`（供 `docker compose` 用）与 `backend/.env`（供后端与 `docker-compose-base.yml` 用）。
> 模板分别是根目录 `.env.example` 与 `backend/.env.example`。

### 3. 配置环境变量

```bash
cd backend

# 复制示例配置文件
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key
```

**必填的 API Key（其他配置已预配置好）：**
```env
# 阿里云百炼 (LLM & Embedding) - 必填
DASHSCOPE_API_KEY=your-dashscope-api-key

# 搜索服务 - 必填
BOCHA_API_KEY=your-bocha-api-key

# PostgreSQL 配置（连接地址按 Docker 默认，通常无需修改）
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
# 必填：留空会导致后端【启动失败】（历史弱口令默认值已移除）
# 生成方式: python -c "import secrets; print(secrets.token_urlsafe(24))"
# 须与仓库根目录 .env 中的 POSTGRES_PASSWORD 一致
POSTGRES_PASSWORD=
POSTGRES_DB=industry_assistant

# MinIO（供 docker-compose-base.yml 使用；须与根目录 .env 一致）
MINIO_ROOT_USER=
MINIO_ROOT_PASSWORD=

# JWT 密钥（必填，长度 ≥ 32；留空、过短或沿用示例值都会导致后端【启动失败】）
# 生成方式: python -c "import secrets; print(secrets.token_urlsafe(48))"
JWT_SECRET_KEY=
```

**注意：**
- PostgreSQL、Redis、Milvus 的配置已在 Docker Compose 中设置好
- `.env.example` 文件中的默认值与 Docker 配置匹配
- 如果使用 Docker，数据库相关配置**通常无需修改**
- `JWT_SECRET_KEY` 为**必填项**：留空、长度不足 32 字符、或沿用历史默认值
  `your-super-secret-key-change-in-production`，后端都会在**启动阶段**直接报错退出。
  这是有意行为 —— 公开可知的签名密钥可被用来伪造任意 Token。

### 4. 安装后端依赖 & 启动

```bash
cd backend

# 创建虚拟环境 (推荐)
conda create -n deepresearch python=3.10
conda activate deepresearch

# 安装依赖
pip install -r requirements.txt

# 启动后端服务
python app/app_main.py
```

后端默认运行在 `http://localhost:8000`

#### 数据库建表（schema 初始化）

后端启动**默认不执行** `create_all` 自动建表 —— 建表以 `backend/migrations/` 的手写迁移 SQL 为准，
避免 ORM 模型与迁移 SQL 两套 schema 来源漂移。请按顺序执行：

```bash
# 1) 先起数据库（含 postgres），迁移 SQL 作用于其中的 industry_assistant 库
docker compose up -d postgres

# 2) 依次执行迁移 SQL（已执行过的会因 IF NOT EXISTS / 幂等语句而无副作用）
docker compose exec -T postgres psql -U postgres -d industry_assistant < backend/migrations/20260719_research_observability.sql
docker compose exec -T postgres psql -U postgres -d industry_assistant < backend/migrations/20260719_unique_research_checkpoint_session_id.sql
```

如果只是**本地开发**想跳过迁移、由 ORM 直接建表，在 `backend/.env` 设置：

```bash
DB_AUTO_CREATE=1
```

> 注意：两种方式不要混用同一张表 —— `create_all` 只创建缺失的表，不会补迁移里
> `ALTER TABLE` 增加的列；混用容易出现「表存在但缺列」的中间态。

### 5. 安装前端依赖 & 启动

```bash
cd frontend

# 安装依赖
npm install --legacy-peer-deps

# 开发模式启动
npm run dev
```

前端默认运行在 `http://localhost:5173/login`

---

## 详细配置

### 环境变量说明

#### 必填配置

| 变量名 | 说明 | 申请地址 |
|--------|------|----------|
| `DASHSCOPE_API_KEY` | 阿里云百炼 (LLM & Embedding) | https://bailian.console.aliyun.com/ |
| `BOCHA_API_KEY` | 博查搜索 API | https://open.bochaai.com/ |
| `POSTGRES_*` | PostgreSQL 连接配置 | - |
| `REDIS_HOST/PORT` | Redis 连接配置 | - |
| `MILVUS_HOST/PORT` | Milvus 向量数据库配置 | - |
| `JWT_SECRET_KEY` | JWT 认证密钥 (自定义字符串) | - |

#### 其它配置

| 变量名 | 说明 | 申请地址 |
|--------|------|----------|
| `DOCMIND_ACCESS_KEY_ID` | 阿里云 DocMind 文档解析 | https://help.aliyun.com/zh/ram/user-guide/create-an-accesskey-pair |
| `DOCMIND_ACCESS_KEY_SECRET` | 阿里云 DocMind Secret | 同上 |
| `BID_APP_KEY` | 招投标信息 API | https://market.aliyun.com/detail/cmapi00063550?spm=5176.730005.result.20.3188414aM3Wls9&innerSource=search_%E6%8B%9B%E6%8A%95%E6%A0%87#sku=yuncode5755000002 |
| `BID_APP_SECRET` | 招投标 API Secret | 同上 |
| `BID_APP_CODE` | 招投标 API Code | 同上 |
| `JUHE_STOCK_API_KEY` | 聚合数据 - 股票行情 | https://www.juhe.cn/docs/api/id/21 |
| `OPENROUTER_API_KEY` | OpenRouter (多模型网关) | https://openrouter.ai/ |


### 高级部署选项

#### 使用本地 PostgreSQL（不推荐新手）

如果你想使用本地安装的 PostgreSQL 而不是 Docker：

1. **安装 PostgreSQL**
   ```bash
   # macOS
   brew install postgresql@15
   brew services start postgresql@15
   ```

2. **创建数据库和用户**
   ```bash
   # 连接 PostgreSQL（口令用你实际配置的强随机值，不要沿用任何示例口令）
   psql postgres

   # 创建用户
   CREATE USER postgres WITH PASSWORD '<你的强随机口令>';

   # 创建数据库
   CREATE DATABASE industry_assistant OWNER postgres;

   # 退出
   \q
   ```

3. **修改 Docker Compose 配置**
   ```bash
   # 编辑 docker-compose.yml，注释掉 postgres 服务
   # 或者使用 backend/docker-compose-base.yml（只包含 Redis 和 Milvus）
   cd backend
   docker compose -f docker-compose-base.yml up -d
   ```

4. **确保 `.env` 配置正确**
   ```env
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_USER=postgres
   # 必填，用你实际配置的强随机值（与仓库根目录 .env 保持一致）
   POSTGRES_PASSWORD=
   POSTGRES_DB=industry_assistant
   ```

### 数据库初始化

首次启动时，后端会自动创建数据库表。如果遇到问题，可手动执行：

```sql
-- 连接数据库
-- Docker: docker exec -it industry_postgres psql -U postgres -d industry_assistant
-- 本地: psql -U postgres -d industry_assistant

-- 确保 research_checkpoints 表有完整的列
ALTER TABLE research_checkpoints ADD COLUMN IF NOT EXISTS ui_state_json JSONB;
ALTER TABLE research_checkpoints ADD COLUMN IF NOT EXISTS final_report TEXT;
```

### 服务管理

#### 使用启动脚本（推荐）

```bash
# 启动所有服务
./start-services.sh start

# 查看服务状态
./start-services.sh status

# 查看日志
./start-services.sh logs              # 所有服务
./start-services.sh logs postgres     # 特定服务

# 重启服务
./start-services.sh restart

# 停止服务
./start-services.sh stop

# 清理数据（危险操作！）
./start-services.sh clean
```

#### 使用 Docker Compose

```bash
# 启动
docker compose up -d

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f
docker compose logs -f postgres    # 特定服务

# 停止
docker compose down

# 停止并删除数据卷（危险操作！）
docker compose down -v
```

### 上传测试文档 (可选)

> 该接口自 T04 起要求认证（router 级 `get_current_user_required`），请先从 `/auth/login` 取 Token 并带上 `Authorization` 头。

```bash
cd backend
curl -X POST "http://localhost:8000/documents/upload" \
  -H "Authorization: Bearer <你的Token>" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@./test/test_doc.pdf"
```

---

## 常见问题

### Q: Docker 容器启动失败？
```bash
# 使用启动脚本查看状态
./start-services.sh status

# 查看具体服务日志
./start-services.sh logs postgres    # 查看 PostgreSQL 日志
./start-services.sh logs             # 查看所有服务日志

# 重启所有容器
./start-services.sh restart

# 或使用 Docker Compose
docker compose down
docker compose up -d
```

### Q: 后端连接数据库失败？
**常见原因：**
1. Docker 服务未启动
   ```bash
   ./start-services.sh status   # 检查服务状态
   ./start-services.sh start    # 启动服务
   ```

2. `.env` 文件配置错误
   ```bash
   # 确保配置与 Docker 一致（口令为必填项，不要沿用任何示例值）
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=<你的强随机口令>
   POSTGRES_DB=industry_assistant
   ```

3. 端口被占用（如已安装本地 PostgreSQL）
   ```bash
   # 停止本地 PostgreSQL（如果有）
   brew services stop postgresql
   # 或者修改 docker-compose.yml 中的端口映射
   ```

### Q: 前端 npm install 报错？
```bash
# 使用 legacy-peer-deps 解决依赖冲突
npm install --legacy-peer-deps

# 或清除缓存后重试
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps
```

### Q: 研究历史无法恢复右侧面板数据？
执行数据库迁移：
```sql
ALTER TABLE research_checkpoints ADD COLUMN IF NOT EXISTS ui_state_json JSONB;
ALTER TABLE research_checkpoints ADD COLUMN IF NOT EXISTS final_report TEXT;
```
然后重启后端服务。

---

## 项目结构

```
industry_information_assistant/
├── backend/
│   ├── app/
│   │   ├── api/          # API 路由
│   │   ├── core/         # 核心配置
│   │   ├── models/       # 数据模型
│   │   ├── service/      # 业务逻辑
│   │   └── app_main.py   # 入口文件
│   ├── docker-compose-base.yml
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── api/          # API 调用
│   │   ├── components/   # 组件
│   │   ├── pages/        # 页面
│   │   └── store/        # 状态管理
│   └── package.json
└── READMED.md
```

---

## 监控与全链路追踪（LangFuse）

项目集成了 LangFuse 自托管监控，支持 LLM 全链路追踪、成本分析、错误聚合。

详细部署和使用见：[LangFuse 监控使用指南](docs/langfuse-monitoring.md)

快速启动：
```bash
# 1. 启动 LangFuse 服务
cd docker/langfuse
cp .env.example .env
# 编辑 .env 生成密钥（openssl rand -hex 32）
docker compose up -d

# 2. 在 backend/.env 中启用监控
# LANGFUSE_ENABLED=true
# LANGFUSE_BASE_URL=http://localhost:3000
# LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxx
# LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxx

# 3. 安装 SDK 并配置模型价格
cd backend
pip install 'langfuse>=3.0.0'
python -m app.scripts.config_langfuse_models
```

启动后访问 `http://localhost:3000` 查看 trace。

---

## API 文档

启动后端后访问：`http://localhost:8000/docs`
