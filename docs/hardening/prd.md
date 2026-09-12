# PRD：行业信息助手（deepsearch）质量硬化

| 项目 | 内容 |
|------|------|
| 文档版本 | v1.0 |
| 编写日期 | 2026-09-13 |
| 仓库 | https://github.com/EricKingWhy/deepsearch （PUBLIC） |
| 本地目录 | `D:\LLMapply\industry_information_assistant` |
| 基线 commit | `9342913`（`chore: 整理工作树基线并落盘交接文档`） |
| 执行协议 | [`docs/hardening/LOOP-PROTOCOL.md`](LOOP-PROTOCOL.md) —— **优先级高于本文档** |
| ticket 定义 | [`docs/hardening/tickets.md`](tickets.md) |
| 进度追踪 | [`docs/hardening/TRACKER.md`](TRACKER.md) |

> **本文档面向后续接手的 AI 与人类协作者。要求：不需要任何口头补充即可独立执行。**
> 任何「见上文讨论」「按之前的约定」式表述都是本 PRD 的缺陷，发现即应修正。

---

## 1. 背景

`industry_information_assistant` 是一个 AI 深度研究助手：后端 FastAPI + LangGraph/LangChain + 多智能体协作，前端 React 19 + Ant Design 5，基础设施 Postgres / Redis / Milvus / ES / MinIO。

项目已具备完整功能（深度研究 SSE 流式、知识库 RAG、可观测性栈、大纲审批），但**长期缺少工程化约束**，积累了四类问题：

1. **安全**：真实 API 密钥硬编码入库、上传路径穿越、鉴权覆盖不全、CORS 配置错误、容器口令明文；
2. **正确性**：至少一处导致「用户上传的文档检不到」的检索缺陷，以及 NL2SQL 校验可绕过；
3. **可接手性**：三套研究编排并存却无任何标注，大型文件（1953 行前端单文件）难以定位改动点，文档与代码漂移；
4. **工程化底座**：零 CI、无 LICENSE/CONTRIBUTING/模板、后端无静态检查、核心模块零测试。

目标是把上述四层收敛到一个「**任何 AI 或人类接手后能安全改动**」的状态。

---

## 2. 范围与非目标

### 2.1 在范围内（四个层次全做）

| 层次 | 内容 |
|------|------|
| A. 安全 | 密钥去硬编码、上传加固、鉴权补全、CORS、容器口令 |
| B. 正确性 | 检索缺陷、SQL 校验绕过、异常吞噬、数据库连接治理 |
| C. 可接手性 | 既有设计的显式标注、公共函数抽离、文档漂移修复、架构总览文档 |
| D. 工程化底座 | LICENSE / CONTRIBUTING / 模板 / CHANGELOG / ruff / 测试分层 / CI / 容器化 / 启动脚本 |

### 2.2 明确不做（Non-Goals）

以下均为**用户明确确认的决定**，任何 ticket 都不得违背：

| 编号 | 非目标 | 理由 / 用户决定 |
|------|--------|----------------|
| **NG-1** | **不新增任何产品功能** | 用户明确要求「四层全做，不含新功能」 |
| **NG-2** | **不删除 LangGraph 运行时路径** | `graph.py` 的 `_build_langgraph` / 6 个 `_*_node` / `_run_with_langgraph` 是**有意保留**的并行实现，未来要在「手写异步状态机」与「LangGraph 运行时」之间做选择。只允许加标注，禁止删除实现或移除 `langgraph` 依赖 |
| **NG-3** | **不删除 V1 ReAct 编排** | `dr_g.py` / `react_controller.py` / `tool_executor.py` 是 `version=v1` 的备选路线，**有意保留**。只允许加标注、抽离被外部引用的公共函数 |
| **NG-4** | **本期不吊销已泄露的历史密钥** | 用户已知悉风险并决定暂不处理（见 §5.2 风险登记 R-01）。但**新增提交不得再引入任何密钥** |
| **NG-5** | 不引入 i18n 方案 | 无多语言需求，YAGNI |
| **NG-6** | 不做 chat 长消息列表虚拟化 | 无性能投诉，缺乏证据，YAGNI |
| **NG-7** | 不建立 alembic 正迁移体系（除非决策票 T20 获批） | 当前手写 SQL 迁移未造成实际痛点 |

### 2.3 大重构的处置方式

**大重构一律拆成独立决策票（带 `needs-decision` 标记），由用户逐张决定是否执行，不进入自动循环。**

本期识别出 3 张决策票：T20（alembic 去留）、T21（`chat/index.tsx` 1953 行是否拆分）、T38（前端 JWT 存储方式）。

---

## 3. 成功标准

全部条件同时满足才算完成：

1. `docs/hardening/tickets.md` 中**所有非 `needs-decision` ticket** 状态为 `DONE`，且每张都有可复现的验收命令与 `PASS` 记录；
2. `needs-decision` ticket 要么被用户批准执行并 `DONE`，要么被用户明确驳回并记为 `CANCELLED`（**不允许留在未裁决状态**）；
3. 批量审查（每 3 张一次）与最终全量审查（**fixed point 为显式 commit SHA，不是 `origin/main`**）的**所有 findings 已消除**，TRACKER 中的批次审查状态全部推进到修复 commit；
4. 仓库中**不存在新增的硬编码密钥**：`git grep -nE "sk-[A-Za-z0-9]{20,}"` 的命中数不高于基线；
5. CI 在 `main` 上为**绿色**；
6. 未触碰 NG-2 / NG-3 所列的既有实现（用 `git log --diff-filter=D --stat` 自查无删除记录）。

---

## 4. 现状事实清单（带证据）

所有条目均已核实到「文件:行号」，可直接作为 ticket 的输入。

### 4.1 安全

| # | 位置 | 事实 |
|---|------|------|
| F-01 | `backend/app/service/dr_g.py:29-30` | 硬编码真实密钥：`SEARCH_API_KEY = os.getenv("BOCHA_API_KEY", "Bearer sk-...")`、`LLM_API_KEY = os.getenv("DASHSCOPE_API_KEY", "sk-...")`。已随 `ccbb38a Initial project import` 进入提交历史，仓库为 PUBLIC |
| F-01b | `backend/app/service/config.py:20-22` | 同类缺陷，**上一轮审计漏检**（正则只匹配 `sk-` 前缀，未覆盖 `'api_key': os.environ.get(..., '<值>')` 这种字典键写法）。泄露 3 项：RAGFlow `api_key`、RAGFlow `default_dataset_id`、Serper `api_key`（40 位十六进制） |
| F-01c | `backend/app/service/dr_g.py:29` | **潜在鉴权 bug**：该常量默认值内嵌 `"Bearer "` 前缀，而全仓统一约定是「环境变量存裸密钥、调用处拼前缀」（`scout.py:1080`、`news_collection_service.py:62`、`document_service.py:20`）。本地 `.env` 按裸密钥存放，因此 `websearch()` 发出的 `Authorization` 头缺少 `Bearer ` 前缀 |
| F-02 | `backend/app/router/document_router.py:66` | `f"/tmp/{file.filename}"` 直接使用用户上传的原始文件名 → 路径穿越；无大小限制 |
| F-03 | `backend/app/router/document_router.py` | 全文件无鉴权依赖（`Depends(get_current_user_required)` 计数为 0） |
| F-04 | `backend/app/router/chat_router.py`、`search_router.py`、`news_router.py` | 同样无鉴权依赖 |
| F-05 | `backend/app/app_main.py:83-89` | `allow_origins=["*"]` 与 `allow_credentials=True` 同时开启：浏览器会拒绝该组合，实际鉴权放行不可用且配置危险 |
| F-06 | `backend/app/core/security.py:13` | `JWT_SECRET_KEY` 默认值为 `"your-super-secret-key-change-in-production"`，无启动期校验 |
| F-07 | `docker-compose.yml:11`、`:71-72` | `POSTGRES_PASSWORD: postgres123`、MinIO `minioadmin/minioadmin` 明文写入受版本控制的文件 |

### 4.2 正确性

| # | 位置 | 事实 |
|---|------|------|
| F-08 | `backend/app/service/deep_research_v2/agents/scout.py:1031` | `collection_name="knowledge_base"` 硬编码；而用户上传入库走 `kb_{知识库名}`（`knowledge_router.py:93`）。两者不匹配 → **DeepResearch 的本地知识库检索搜不到用户文档**。详见 `docs/RAG架构分析.md` 第二节 |
| F-09 | `backend/app/service/text2sql_service.py:210-242` | SQL 校验使用黑名单，`FORBIDDEN` 含 `'UNION ALL SELECT'` 但 `UNION` 本身在 `ALLOWED` 中 → `UNION SELECT` 可绕过 |
| F-10 | `backend/app/service/text2sql_service.py:386` | `execute_sql` 使用 `text(sql)` 直连主库，未使用只读账号兜底 |
| F-11 | `graph.py:511`、`dr_g.py:370`、`news_collection_service.py:619/643/694`、`smart_analyzer.py:224/276/327` | 使用裸 `except:`，会吞掉 `KeyboardInterrupt` / `SystemExit` |
| F-12 | `backend/app/core/database.py:19` | **审计更正**：`pool_pre_ping=True` **已经设置**（首轮审计误判为未设置）。实际缺失的是 `pool_size` / `max_overflow` / `pool_recycle`。另 `:14` 的 `POSTGRES_PASSWORD` 默认值为弱口令 `postgres123`（归 T07） |
| F-13 | `backend/app/app_main.py:43` | 启动时执行 `create_all`，与 `backend/migrations/` 手写 SQL 并存 → schema 漂移风险 |

### 4.3 可接手性

| # | 位置 | 事实 |
|---|------|------|
| F-14 | `deep_research_v2/graph.py:150,214-249` | `_build_langgraph()` 在每次实例化时执行并 `compile()`；结果 `self.graph` 仅在 `:379`（`_run_with_langgraph`）使用，而该分支的调用点在 `:366` **已被注释**。6 个 `_*_node` 方法无任何调用点 → 属**有意保留**（NG-2），但当前**无任何标注**，接手者极易误删 |
| F-15 | `service/dr_g.py`(791 行)、`react_controller.py`(951 行)、`tool_executor.py`(661 行) | V1 ReAct 编排共 2403 行。前端 `deepsearch()`（`frontend/src/api/session.ts:175-192`）不发送 `version` 字段，后端默认 `"v2"`（`research_router.py:50`）→ V1 仅显式传 `version=v1` 可达。属**有意保留**（NG-3），但无标注 |
| F-16 | `backend/app/router/research_router.py:18` | `from service.dr_g import serialize_event` —— 仅为一个序列化函数就耦合了整套 V1 编排 |
| F-17 | `READMED.md:385,391` | 文档称 `pip install 'langfuse>=3.0.0'` 且 `LANGFUSE_ENABLED=true`，实际 `requirements.txt:28` 为 `langfuse>=4.0.0`，`.env.example:82` 默认为 `false` |
| F-18 | `knowledge_router.py:76`、`docmind_service.py:258` | 注释仍写「ES 存储 / ES 索引」，实现已全量迁移 Milvus |
| F-19 | `READMED.md:3` | 宣称支持「知识图谱」，但无对应后端模块 |
| F-20 | `backend/requirements.txt:28,69` | `langfuse` 重复声明两次，且版本约束不一致（`>=4.0.0` 与 `>=4.0.0,<5.0.0`） |
| F-21 | `backend/requirements.txt:10` | 声明 `alembic>=1.12.0`，但仓库无 `alembic.ini` / `env.py`，从未使用 |
| F-22 | `frontend/src/pages/chat/index.tsx` | 1953 行，含 12 个 `useEffect` / 13 个 `useMemo` |

### 4.4 工程化底座

| # | 位置 | 事实 |
|---|------|------|
| F-23 | 仓库根 | 无 `.github/`，零 CI/CD |
| F-24 | 仓库根 | 无 `LICENSE`、`CONTRIBUTING.md`、`.editorconfig`、issue 模板、PR 模板、`CHANGELOG.md` |
| F-25 | `backend/` | `requirements.txt:79` 列出了 `ruff`，但无 `ruff.toml` / `pyproject.toml` 配置，也无 pre-commit（前端反之齐全：`.prettierrc`、`.lintstagedrc`、`eslint.config.js`、`.husky/pre-commit`） |
| F-26 | `backend/` | 无 `Dockerfile`，`docker-compose.yml` 只编排中间件，后端跑在宿主机 |
| F-27 | `start-services.sh:47,50` | 使用旧式 `docker-compose` 命令（README 用 `docker compose`）；`start` 后仅 `sleep 10`，不等待 healthcheck |
| F-28 | `docker-compose.yml` | 各服务均有 healthcheck、镜像版本均已固定，但**无任何资源限制**（ES / Logstash 易 OOM） |
| F-29 | `docker/langfuse/` | 被 `.gitignore:45` 的 `langfuse/` 规则忽略 → 部署文件不在版本库，可复现性差 |
| F-30 | `backend/tests/`（17 个测试文件） | 覆盖 observability、deep_research_v2 子模块、checkpoint；`conftest.py` 仅设 `sys.path` 与 `ENV=test`，**无 DB/Redis/Milvus fixture** → 依赖外部服务的用例无法在 CI 独立运行 |
| F-31 | `backend/app/service/` | text2sql、chat、document、auth、dr_g、react_controller **零测试** |
| F-32 | `frontend/src` | 约 30 处 `console.log` 残留（`chat/index.tsx` 密集）；`error-toast.ts:11-24` 的 `NETWORK_ERROR_MAP` 除 429 外全被注释；`chat/index.tsx` 含约 128 行注释代码；59 处 `any` |
| F-33 | `frontend/vite.config.ts` | 无 `build` 配置 → 无 `manualChunks`、无分包策略 |
| F-34 | `frontend/src/router/routes.tsx:8-17` | 全部静态 `import`，无路由懒加载 |
| F-35 | `frontend/src/pages/chat/component/knowledge-graph.tsx:7`、`process-report.tsx:8` | 静态引入 `echarts-for-react`（依赖完整 echarts），导致 `chart/index.tsx:23` 的动态 `import('echarts')` 失效，echarts 仍进主包 |
| F-36 | `backend/app/service/chat_service_v2.py:42-117`、`knowledge_router.py:463/468/470`、`redis_client.py:43-103`、`embedding_service.py:52/119`、`llm_config.py:16-207` | `print` 调试残留（应改为 logger） |

---

## 5. 约束、红线与风险

### 5.1 密钥红线（不可违反）

1. **严禁**把真实密钥 / Token / 口令写入任何被 git 跟踪的文件 —— 包括本 PRD、tickets、issue 正文、commit message、日志输出、截图。
2. 代码中读取密钥一律 `os.getenv(...)`，**不留默认值兜底**。
3. 需要密钥的验证从 `backend/.env`（已被 gitignore）读取，**不得**把值打印到终端或落盘。
4. 每次 push 前自查：`git grep -nE "(sk-[A-Za-z0-9]{20,}|Bearer [A-Za-z0-9]{20,})"`。
5. 用户已授权在本地使用这两个密钥做请求测试；授权**仅限本地运行**，不构成写入文件的许可。

### 5.2 风险登记

| 编号 | 风险 | 影响 | 处置 |
|------|------|------|------|
| **R-01** | **5 个凭据泄露在 PUBLIC 仓库的 `ccbb38a` 提交历史中**：`dr_g.py` 的 Bocha / DashScope 密钥、`config.py` 的 RAGFlow api_key、RAGFlow dataset id、Serper 密钥。任何人在克隆仓库后都能读到；只要未在服务商侧吊销，这些凭据持续有效 | 可被他人盗用配额、产生费用或读取数据 | 用户已知悉并决定**暂不吊销**（NG-4）。本期只做「后续不再引入」（T01）。**这是已知的未闭合风险**，T01 完成后仍应在 TRACKER 中保持标注，并在服务商侧吊销后更新本条 |
| **R-02** | 新增鉴权（T05/T06）可能打断现有前端调用 | 前端若未携带 Token，接口将返回 401，功能不可用 | ticket 中必须核查前端调用链是否已注入 `Authorization`（`frontend/src/api/request/auth.ts` 统一注入）。如有遗漏，在同一 ticket 内补齐 |
| **R-03** | 收紧 CORS（T07）可能打断本地开发跨域 | 开发环境前端 :5183 → 后端 :8000 请求失败 | 保留开发环境通配，但必须 `allow_credentials=False`；生产从环境变量读取显式白名单 |
| **R-04** | 优化过程中误删 NG-2 / NG-3 的既有实现 | 破坏用户有意保留的技术选择 | 协议文件 §8 已列出禁止清单；每张 ticket 的验收含自查步骤 |
| **R-05** | Docker 未启动导致需要基础设施的验证无法执行 | 相关 ticket 无法完成验收 | 相关 ticket 打 `needs-infra` 标记并写清所需容器；优先设计无基础设施的验证方式；确实无法验证时记 `BLOCKED`，**不得伪造 PASS** |
| **R-06** | 37 张 ticket 的编码阶段改动集中在鉴权与异常处理，可能在批量审查时暴露交叉回归 | 回归修复成本上升 | 按协议「每 3 张一批」控制 diff 规模；每张 ticket 自带验证，回归在批次审查时定位 |

---

## 6. 执行模型

**严格执行 [`docs/hardening/LOOP-PROTOCOL.md`](LOOP-PROTOCOL.md)，本文档不重复其内容。** 摘要：

1. 每张 ticket 开工前**强制重读**协议文件，禁止凭记忆推断流程；
2. `/implement` 完成 ticket，**跳过其自带的 `/code-review`**，测试全绿后自行 commit 并登记 TRACKER；
3. 每完成 3 张 ticket（批大小可在 2–4 浮动）对累计 diff 做一次批量审查，fixed point = 上一批审查结束时的 commit SHA；
4. 全部完成后对整条分支做最终全量审查，fixed point = 基线 commit `9342913`（即本计划开始前的 `main` tip）；
5. 每张 ticket 一条分支 `T<编号>-<描述>`（**必须扁平，禁止 `/`** —— 带斜杠的分支引用在本机会被清扫导致 `HEAD` 悬空，见 `LOOP-PROTOCOL.md` §9.1）→ 开 PR → merge commit 合并（**不用 squash**）；
6. 全程自动，**仅**在「规格实质冲突」或「架构分叉」时停下征求用户裁决。

> ⚠️ **不要用 `main` / `origin/main` 作为审查基准。** 本机的 `refs/remotes/**` 会被环境清扫，`origin/main` 不可解析，`git diff origin/main` 会硬失败。统一使用显式 commit SHA，远端真相用 `git ls-remote origin refs/heads/main` 获取。详见 `LOOP-PROTOCOL.md` §9。

---

## 7. 验收口径

### 7.1 通用规则

- **禁止把「人工检查」当作验收方式。** 验收必须是「可执行命令 + 可判定输出」。
- 每张 ticket 优先设计成**不依赖基础设施**即可验证。优先顺序：纯函数单测 → mock 单测 → 前端 vitest → 构建 / lint / 静态断言脚本。
- 确实需要跨服务的 ticket 打 `needs-infra` 标记，并在 ticket 内写明需要启动哪些容器、执行什么命令。
- 需要用户本人在第三方后台操作的 ticket 打 `needs-human` 标记，写清操作步骤，**不得跳过或假装完成**。
- 无法验证的 ticket 状态记为 `BLOCKED`，在 TRACKER 中写明阻塞原因。

### 7.2 各层次的最低验收线

| 层次 | 最低验收线 |
|------|-----------|
| A. 安全 | 针对该缺陷的**回归测试失败于修复前、通过于修复后**；或可复现的静态断言脚本 |
| B. 正确性 | 同上，且必须包含一个**失败于修复前**的复现用例 |
| C. 可接手性 | 文档 / 注释类：内容可被 grep 命中且与代码事实一致；抽离类：`pytest` 通过 + `grep` 验证旧引用已改指向 |
| D. 工程化底座 | 该设施本身**真实可运行**（CI 变绿、脚本可执行、lint 可跑通），不接受「写了配置文件就算完成」 |

---

## 8. 术语表

| 术语 | 含义 |
|------|------|
| ticket | 一张可独立交付、独立验证的最小工作单元，与一个 GitHub issue 一一对应 |
| 决策票 | 带 `needs-decision` 标记的 ticket，需用户裁决后才执行，不进入自动循环 |
| 批量审查 | 每 3 张 ticket（2–4 浮动）对累计 diff 做的一次 `/code-review` |
| fixed point | 代码审查的对比基准 commit |
| needs-infra | 验收需要 Postgres / Redis / Milvus / ES 等容器运行 |
| needs-human | 验收需要用户本人在第三方后台操作 |
| V1 编排 | `version=v1` 的 ReAct 研究路线，实现于 `dr_g.py` / `react_controller.py` / `tool_executor.py` |
| V2 编排 | `version=v2` 的多智能体研究路线，实现于 `service/deep_research_v2/`，当前默认路线 |
