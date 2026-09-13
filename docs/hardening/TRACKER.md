# TRACKER — 质量硬化进度

> 恢复状态**先读本文件**。流程规则见 [`LOOP-PROTOCOL.md`](LOOP-PROTOCOL.md)，ticket 定义见 [`tickets.md`](tickets.md)。

## 全局状态

> ⚠️ **审查基准一律使用显式 commit SHA，禁止写 `main` / `origin/main`。**
> 本机 `refs/remotes/**` 会被环境清扫（`git status -sb` 显示 `[gone]`），`origin/main` 不可解析。
> 远端真相：`git ls-remote origin refs/heads/main`。详见 `LOOP-PROTOCOL.md` §9。

| 字段 | 值 |
|------|-----|
| 计划起始基线 commit（第一批审查的 fixed point） | `9342913` |
| PRD / ticket 落盘 commit | `2047a77` |
| `main` 当前 tip（2026-09-13 核实，本地＝远端，已含 T01–T09 + T41 合并） | `0f3ceba839551f316fad29a651d42da7823984c1` |
| 当前批次 | 3（T07–T09） |
| 当前 fixed point（上一批审查结束 commit） | `57f69e0`（第 2 批审查修复 commit） |
| 当前分支命名 | `T<编号>-<短描述>`（**必须扁平，禁止 `/`**，见协议 §9.1） |
| 合并目标 | 本地 `main` 分支（merge commit，不用 squash） |
| 总 ticket 数 | 41（T01–T40 + 第 1 批审查衍生 T41） |
| 已完成 | 10 |
| 决策票待裁决 | T18、T19、T20、T37 |

## 批次审查记录

| 批次 | 覆盖 ticket | fixed point（起点） | 审查 commit（终点） | findings 数 | 修复 commit | 状态 |
|------|------------|--------------------|--------------------|------------|------------|------|
| 1 | T01–T03 | `9342913` | `5651c98` | 5 | `19547b0` | FIXED |
| 2 | T04–T06 + T41 | `19547b0` | `41009b9` | 11 | `57f69e0` | FIXED |

### 第 1 批审查 findings 明细（`9342913` → `5651c98`，修复 commit `19547b0`）

双轴并行审查：**标准轴 4 条 + 规格轴 3 条**，去重后 **5 条**。

| # | 轴 | finding | 处置 |
|---|----|---------|------|
| 1 | 标准 | `READMED.md:~96` 仍把**已失效**的 `JWT_SECRET_KEY` 示例值写成可用配置，照抄该文档会启动失败，与 T02 的强校验直接冲突（文档/代码漂移） | **已修** `19547b0` |
| 2 | 规格 | T02 令 `core.security` 在导入期校验，而 `core/__init__.py` 会导入 security → 任何 `import core.*` 都要求密钥存在；`tests/conftest.py` 未提供，导致 `tests/router/test_observability_router.py` 收集失败 | **已修** `19547b0`（conftest 用 `setdefault` 提供测试占位值） |
| 3 | 标准 + 规格 | 三处上传实现**重复且未并轨**：`attachment_router.py:148`、`knowledge_router.py:327` 仍把客户端文件名拼进路径（可穿越出 `UPLOAD_DIR`），三份 `ALLOWED_EXTENSIONS` 已漂移 | **转 T41（#75）**，决策票 |
| 4 | 标准 | 导入期校验偏离仓库其它配置「惰性读取 + 静默默认」的风格 | **保留判定**：T02 明确要求「启动即失败」，属有意设计 |
| 5 | 标准 | 源码 grep 型测试（`test_no_getenv_default_for_secret_key`、`test_module_source_contains_no_key_literals`）偏脆 | **保留判定**：作为回归锁可接受 |

**验收复核**：T01 / T02 的验收标准实质可满足；T03 可满足，但白名单一致性转入 T41。
T03 下游仍保留 `file_name=file.filename` —— 复核确认为**合规**（T03 #4 明允原始文件名仅作数据字段），无静默行为回归。

### 第 2 批审查 findings 明细（`19547b0` → `41009b9`，修复 commit `57f69e0`）

双轴并行审查：**标准轴 7 条 + 规格轴 7 条**，去重后 **11 条**。9 条已修，2 条保留判定。

| # | 轴 | finding | 处置 |
|---|----|---------|------|
| 1 | 标准 + 规格 | 台账未回填：`TRACKER.md` 中 T05 / T06 两行仍为 `TODO`、分支/Commit/PR/验收全空，与已合并事实矛盾；`main` tip 行也停在 `93d931c` | **已修**（本记录提交） |
| 2 | 规格 | `tickets.md` T41「改什么 #1」仍写「把 `ALLOWED_EXTENSIONS` 收拢共用」，与同一节已批准的**方案 A（白名单各自保留）**直接冲突 | **已修**（本记录提交） |
| 3 | 标准 | **重复代码**：`tests/router/test_document_auth.py`（T04）与 `test_router_auth.py`（T05）是同一套断言的两次实现 | **已修** `57f69e0`（合并为一处，document 路由并入参数表） |
| 4 | 标准 | **脆弱断言**：两处 `assert "dependencies=[Depends(...)]" in source` 是源码字符串匹配，格式化（换行/尾逗号）即误报 | **已修** `57f69e0`（改读结构化对象 `APIRouter.dependencies`） |
| 5 | 标准 | **误导注释**：`attachment_router.py` 称「不把整个文件先读进内存」，但 `read_upload_with_limit` 末尾 `return b"".join(chunks)`，峰值内存仍≈文件大小 | **已修** `57f69e0`（注释 + docstring 改为准确表述） |
| 6 | 标准 + 规格 | `news_router.py` 新注释写「9 个接口」，实测为 **8** 个 | **已修** `57f69e0` |
| 7 | 标准 | `knowledge_router.py` 导入 `sanitize_extension` 但从未使用（ruff F401 会拦） | **已修** `57f69e0` |
| 8 | 规格 | `.env.example` CORS 段写「一律禁用凭据」，但显式白名单分支仍是 `allow_credentials=True`，措辞与实现不符 | **已修** `57f69e0` |
| 9 | 规格 | T05 / T06 叙述「除 `/login` 与 `/404` 外都包在 `AuthGuard`」不准 —— 实际**只有 `/login` 匿名**，`/404` 虽标 `pure: true` 仍处于守卫子树内 | **已修措辞**（本记录提交） |
| 10 | 标准 | T06 新建 `core/cors.py` 偏离 ticket「**不要**新建 CORS 配置模块」 | **保留判定**：属纯逻辑抽离（与 `core/upload_security.py` 同构，为满足「无基础设施可验收」），已在 ticket「实施修正」自证理由 |
| 11 | 标准 | `conftest.py` 在 import 期**全局**注入 `service.docmind_service` 替身，需手动 `del sys.modules[...]` 才能还原 | **保留判定**：替身**抛 `NotImplementedError`** 而非伪造成功，不会把真实调用静默吞掉；还原方式已写入注释 |

**规格轴的关键复核（都独立复验通过）**：

- **R-03（T06）成立**：`withCredentials` 在 `frontend/src` 命中 **0 处** → 前端不依赖 CORS 凭据，
  通配 + `allow_credentials=False` 不影响联调。实现者结论正确。
- **T05「无匿名调用方」成立**：`routes.tsx` 中除 `/login` 外全部处于 `AuthGuard` 子树；
  `/search/web` 在 `frontend/src` 命中 0 处；`login.tsx` 只调 `api.auth.login/register`。
  风险条所述「公开落地页依赖匿名检索」的架构分叉**不成立**，无需用户裁决。
- **T41 方案 A 被忠实执行**：逐字比对 `attachment_router` / `knowledge_router` 的
  `ALLOWED_EXTENSIONS` 与 `document_router` 的 `SUPPORTED_FILE_TYPES`，
  **成员集合前后完全一致**，未并轨。
- 另：`docs/agents/issue-tracker.md` **不存在**，故规格来源取自本地 `prd.md` / `tickets.md`
  （本仓权威定义），未走 issue-tracker 工作流。若要启用该工作流需先跑 `/setup-matt-pocock-skills`。

## ticket 明细

状态取值：`TODO` / `DOING` / `DONE` / `BLOCKED` / `CANCELLED`

| ID | 标题 | Issue | 状态 | 分支 | Commit | PR | 验收 | 批次 | 批次审查 |
|----|------|-------|------|------|--------|----|------|------|---------|
| T01 | 移除 dr_g.py 硬编码 API Key | #32 | DONE | `T01-remove-hardcoded-credentials` | `ec5999d` | #72 | PASS（`pytest tests/service/test_dr_g_config.py -v` → 9 passed，见 P-02） | 1 | FIXED@19547b0 |
| T02 | JWT 密钥必填并在启动时校验 | #33 | DONE | `T02-require-jwt-secret` | `bd54b9b` | #73 | PASS（`pytest tests/core/test_security_jwt.py` → 6 passed） | 1 | FIXED@19547b0 |
| T03 | document_router 上传安全加固 | #34 | DONE | `T03-harden-document-upload` | `fef8eca` | #74 | PASS（`pytest tests/router/test_document_upload.py` → 21 passed；路径穿越净化验收打印 OK） | 1 | FIXED@19547b0 |
| T04 | document_router 增加鉴权 | #35 | DONE | `T04-document-router-auth` | `33724cc` | #78 | PASS（T04 当时 `pytest -q -k document_auth` → 10 passed；第 2 批审查并入 `test_router_auth.py` 后，现用 `-k router_auth` → 47 passed；鉴权依赖计数 = 2） | 2 | FIXED@57f69e0 |
| T05 | chat / search / news 路由补充鉴权 | #36 | DONE | `T05-harden-chat-search-news-auth` | `cee1c33` | #80 | PASS（`pytest -q -k "auth or unauthorized"` → 47 passed；三路由鉴权计数 = 2/2/2；`news_router` 实测 8 个端点非 9） | 2 | FIXED@57f69e0 |
| T06 | 收紧 CORS 配置 | #37 | DONE | `T06-tighten-cors` | `18ed8f8` | #81 | PASS（`pytest tests/core/test_cors_config.py` → 14 passed；通配 + 凭据的硬编码组合已消失；`py_compile app_main` 通过） | 2 | FIXED@57f69e0 |
| T07 | docker-compose 明文口令改为环境变量注入 | #38 | DONE | `T07-compose-secrets` | `1552d13` | #83 | PASS（`pytest tests/core/test_db_password_required.py` → 15 passed；`docker compose config --quiet` → exit=0；全仓 `grep postgres123\|minioadmin` 受控文件无残留） | 3 | PENDING |
| T08 | 修复 Scout 本地知识库检索的集合名不匹配 | #39 | DONE | `T08-scout-kb-collection` | `e16b313` | #85 | PASS（`! grep '"knowledge_base"' scout.py` → 无输出；`pytest tests/service/deep_research_v2 -q` → 25 passed；全量 `-m "not integration"` → 218 passed / 5 deselected；needs-infra 端到端验证因 Docker 未运行记 BLOCKED） | 3 | PENDING |
| T09 | 修复 text2sql SQL 校验可被 UNION SELECT 绕过 | #40 | DONE | `T09-text2sql-union` | `5649543` | #87 | PASS（票面验收脚本（路径修正为 `sys.path.insert(0,'app')`）→ 打印 `OK: UNION 绕过已封堵`；`pytest -k text2sql` → 27 passed；全量 `-m "not integration"` → 245 passed / 5 deselected） | 3 | PENDING |
| T10 | text2sql 使用只读数据库账号兜底 | #41 | BLOCKED | — | — | — | 等待用户创建只读角色 | 4 | PENDING |
| T11 | 清除裸 except 并补日志 | #42 | TODO | — | — | — | — | 4 | PENDING |
| T12 | 收敛数据库连接池与会话生命周期 | #43 | TODO | — | — | — | — | 4 | PENDING |
| T13 | 显式标注 LangGraph 运行时路径为有意保留 | #44 | TODO | — | — | — | — | 5 | PENDING |
| T14 | 显式标注 V1 ReAct 编排为保留的备选路线 | #45 | TODO | — | — | — | — | 5 | PENDING |
| T15 | 抽离 serialize_event | #46 | TODO | — | — | — | — | 5 | PENDING |
| T16 | 修复文档与代码漂移 | #47 | TODO | — | — | — | — | 6 | PENDING |
| T17 | 新增架构总览文档 | #48 | TODO | — | — | — | — | 6 | PENDING |
| T18 | requirements.txt 去重与依赖分区 | #49 | BLOCKED | — | — | — | 等待用户裁决锁定策略 | 6 | PENDING |
| T19 | 决策票：alembic 去留 | #50 | BLOCKED | — | — | — | 等待用户裁决 | — | — |
| T20 | 决策票：chat/index.tsx 是否拆分 | #51 | BLOCKED | — | — | — | 等待用户裁决 | — | — |
| T21 | 新增 LICENSE | #52 | TODO | — | — | — | — | 7 | PENDING |
| T22 | 新增 CONTRIBUTING.md | #53 | TODO | — | — | — | — | 7 | PENDING |
| T23 | 新增 .editorconfig | #54 | TODO | — | — | — | — | 7 | PENDING |
| T24 | 新增 issue 与 PR 模板 | #55 | TODO | — | — | — | — | 8 | PENDING |
| T25 | 新增 CHANGELOG.md 并初始化版本号 | #56 | TODO | — | — | — | — | 8 | PENDING |
| T26 | 新增后端 ruff 配置 | #57 | TODO | — | — | — | — | 8 | PENDING |
| T27 | 后端测试分层：无基础设施单测可独立运行 | #58 | TODO | — | — | — | — | 9 | PENDING |
| T28 | 新增 CI：后端 pytest | #59 | TODO | — | — | — | — | 9 | PENDING |
| T29 | 新增 CI：前端 lint + vitest + build | #60 | TODO | — | — | — | — | 9 | PENDING |
| T30 | 新增 backend/Dockerfile 并接入 compose | #61 | TODO | — | — | — | — | 10 | PENDING |
| T31 | start-services.sh 现代化 | #62 | TODO | — | — | — | — | 10 | PENDING |
| T32 | 清理 console.log 残留 | #63 | TODO | — | — | — | — | 10 | PENDING |
| T33 | eslint 启用 no-explicit-any 并收敛 store 层 any | #64 | TODO | — | — | — | — | 11 | PENDING |
| T34 | vite 构建分包 + 路由懒加载 | #65 | TODO | — | — | — | — | 11 | PENDING |
| T35 | ECharts 真正拆包 | #66 | TODO | — | — | — | — | 11 | PENDING |
| T36 | 清理注释死代码 | #67 | TODO | — | — | — | — | 12 | PENDING |
| T37 | 决策票：前端 JWT 存储方式 | #68 | BLOCKED | — | — | — | 等待用户裁决 | — | — |
| T38 | 清除 print 调试残留 | #69 | TODO | — | — | — | — | 12 | PENDING |
| T39 | 补 text2sql.validate_sql 单元测试 | #70 | TODO | — | — | — | — | 12 | PENDING |
| T40 | 补 security 鉴权单元测试 | #71 | TODO | — | — | — | — | 13 | PENDING |
| T41 | 合并三处上传实现，消除 attachment / knowledge 路径穿越 | #75 | DONE | `T41-consolidate-upload-security` | `1182ccb` | #76 | PASS（`pytest tests/router -k upload` → 40 passed；三路由 `py_compile` 通过） | 2 | FIXED@57f69e0 |

## 待办 / 未闭合项

> 与 ticket 状态解耦的独立跟踪项。

| ID | 事项 | 状态 | 说明 |
|----|------|------|------|
| **P-01** | 后端 venv 依赖安装（pytest 可用） | ✅ 已完成 | 已解决。可用 venv：`C:/Users/王浩宇/.workbuddy/binaries/python/envs/deepsearch/Scripts/python.exe`（Python 3.11.1 + pytest 9.1.1）。绕过 safe-delete 防护的完整配方见 `LOOP-PROTOCOL.md` §11。 |
| **P-02** | T01 的 pytest 补跑 | ✅ 已完成 | `pytest tests/service/test_dr_g_config.py -v` → **9 passed**（参数化展开后为 9 个用例，1 warning 为无关的 `asyncio_mode` 配置项告警）。 |
| **P-03** | 清理 `.runlogs/venv-broken-*`（约 5000 个文件） | 待处理 | 现存 1 个：`.runlogs/venv-broken-025154`。需用户确认后删除（批量删除防护会拦截）。 |
| **P-04** | 本地 `main` 与远端合并态同步 | ✅ 已完成 | 已 fast-forward 到 `b5abdbb`（PR #72 合并提交），本地＝远端。 |
| **P-05** | 删除已合并的 T01/T02/T03 本地/远端分支 | 待处理 | `T01-remove-hardcoded-credentials`、`T02-require-jwt-secret`、`T03-harden-document-upload` 均已并入 `main`，可择机清理，非阻塞。 |
| **P-06** | 工作树被反复清空（环境侧） | **反复出现（4 次），每票必查** | 现象从 `backend/tests`（20 文件）升级到 `backend/app` + `backend/tests`（114 → 111 文件），并会**在 git 命令执行中途**发生。已在 `LOOP-PROTOCOL.md` §9.2 / §9.3 固化恢复步骤与六条硬规则（**禁止 `git add -A`**、不 checkout main、commit 前状态必须为空）。 |
| **P-07** | venv 缺少 `bcrypt` | ✅ 已完成 | `passlib[bcrypt]` 的 extra 未随 primary 依赖装入。已用 `uv pip install --python <venv> "bcrypt>=4.0"` 补齐（bcrypt 5.0.0），配方同 §11。 |
| **P-08** | 文档文件也会被静默回退 | **每票必查** | 实测：某次 `TRACKER.md` 的编辑报「成功」但**未落盘**，被后来的提交带成旧内容；同一批里另一些编辑却保住了。**对策**：写完文档后 `sed -n` / `grep` 复核，再提交。 |
| **P-09** | `attachment_router` / `knowledge_router` 同源路径穿越 | **已转 T41（#75）** | 第 1 批审查的两条 findings 合并为决策票 T41，等用户裁决白名单策略后执行。 |
| **P-10** | 全量 pytest 恒有 1 条 `needs-infra` 失败（非回归） | 已知，非阻塞 | 该用例为 `tests/service/test_research_observability_service.py::test_run_event_lifecycle_sequence_pagination_and_user_scope`，带 `@pytest.mark.integration`，需真实 Postgres（Docker 未启动 → `localhost:5432` 连接被拒）。**判定：环境性失败，与任何 ticket 无关。** 跑验收请统一加 `-m "not integration"`（当前该口径为 **198 passed / 5 deselected**），不要把这条计入回归。 |
| **R-01** | 5 个历史泄露凭据的服务商侧吊销 | **未闭合** | 用户决定暂不处理 |

## 执行日志

> append-only。每完成一张 ticket 追加一行。

| 时间 | ticket | 动作 | 结果 |
|------|--------|------|------|
| 2026-09-13 | — | 基线整理：工作树入库、协议落盘、PRD 与 ticket 定义写入 `docs/hardening/` | 基线 commit `9342913` |
| 2026-09-13 | — | 推送 `main` 时发现 `git status -sb` 报 `[gone]`、`origin/main` 不可解析。核实本地＝远端＝`2047a77`，对象与历史完整，确认为远程跟踪引用被清扫的良性现象。修正文档：所有审查基准改为显式 commit SHA，并新增 `LOOP-PROTOCOL.md` §9 引用可用性说明 | 文档修正 commit（见下） |
| 2026-09-13 | — | 建立 GitHub 侧结构：16 个新标签（安全/类型/组件/process/阶段）、里程碑 `hardening-v1`、40 张 issue（`#32`–`#71`） | issue `#32`–`#71` 已创建 |
| 2026-09-13 | — | **事故与纠正**：首次批量创建 issue 的脚本因默认 120 秒执行超时被 SIGTERM，但已实际创建 `#1`–`#31`；输出被缓冲吞掉导致误判为「未创建」，第二次运行又建了一批，产生 31 张重复 issue。已核实映射后删除重复集 `#1`–`#31`，保留完整集 `#32`–`#71` | 现存 40 张，编号连续 |
| 2026-09-13 | T01 | 实施：`dr_g.py` 删除 2 个密钥常量改为缺失即失败的访问器、修正 `websearch` 缺失的 `Bearer` 前缀；`config.py` 清空 3 项凭据默认值；`document_service.py` 增加空密钥守卫；`.env.example` 补 3 项并注明裸密钥约定；新增回归测试 | 行为验收 4 项 PASS，见待办 P-02 |
| 2026-09-13 | T01 | **范围扩张**：按「修根因不修症状」全仓扫描后发现 `config.py` 3 处同类凭据泄露（首轮审计漏检）与 1 处潜在鉴权 bug，合并入本票；`database.py` 的弱口令默认值归 T07 | 记录于 `tickets.md` T01 |
| 2026-09-13 | — | 环境阻塞与定位：pip 被 safe-delete 防护拦截导致 venv 不一致（`No module named '_distutils_hack'`）；`rm -rf .venv` 触发批量删除确认；改用 uv + `CODEBUDDY_SAFE_DELETE_ENABLED=0` 绕过。完整配方落盘至 `LOOP-PROTOCOL.md` §11 | venv 重建中，见待办 P-01 |
| 2026-09-13 | — | **工作树事故与恢复**：开工前核查发现整个 `backend/tests/` 子树（20 个已跟踪文件）从工作树消失、且磁盘上已无副本，`.git/index.lock` 残留为陈旧锁。已清除锁 → `git checkout HEAD -- backend/tests` 恢复全部 20 个文件，工作树归零。原因未定，与镜像/杀软清理有关。新增 `LOOP-PROTOCOL.md` §9.2 记录该现象与恢复步骤 | 工作树干净，20 文件复原 |
| 2026-09-13 | — | **本地 main 同步**：远端 `main` 实为 `b5abdbb`（PR #72 合并提交），本地 `main` 仍停在 `bc58bc7` 且无 `b5abdbb` 对象。用 `git fetch origin main:main` 完成 fast-forward，本地＝远端＝`b5abdbb`。核实 `git ls-remote origin refs/heads/main` 一致 | 待办 P-04 关闭 |
| 2026-09-13 | T01 | **验收补跑**：`pytest tests/service/test_dr_g_config.py -v` → 9 passed（1 warning 为无关配置项告警）。T01 形式化验收闭合 | 待办 P-02 关闭，T01 全绿 |
| 2026-09-13 | — | **环境补丁**：跑 T02 测试时暴露 venv 缺 `bcrypt`（`passlib[bcrypt]` 的 extra 未装入）。用 `uv pip install --python <venv> "bcrypt>=4.0"` 补齐至 5.0.0 | 待办 P-07 关闭 |
| 2026-09-13 | T02 | 实施 + 合并：`security.py` 删除 `JWT_SECRET_KEY` 默认值改为导入期校验（缺失/空 → `RuntimeError`）、加 32 字符长度下限、新增 `KNOWN_WEAK_SECRET_KEYS` 拒绝名单；`app_main.py` lifespan 显式触发校验；`.env.example` 占位符留空；新增 `tests/core/test_security_jwt.py`（6 用例） | commit `bd54b9b`，PR #73 已 merge（`7e210e8`），issue #33 自动关闭 |
| 2026-09-13 | T02 | **实测发现真实漏洞**：本机 `backend/.env` 的 `JWT_SECRET_KEY` 正是沿用的历史默认值（42 字符，**纯长度校验拦不住**），即本地实例长期使用公开可知的签名密钥。据此把拒绝名单并入本票范围，并轮换本地 `.env` 为 64 字符强随机值（`.env` 已 gitignore，备份在 `.runlogs/`） | 记录于 `tickets.md` T02；本机已可正常启动 |
| 2026-09-13 | — | **工作树清空现象第 2 次复现**：合并 T02 后 `backend/tests` 再次整体消失，仅本次新建的 `tests/core/` 存活。再次 `git checkout HEAD -- backend/tests` 恢复（20 文件，状态归零） | 新增待办 P-06 |
| 2026-09-13 | T03 | 实施 + 合并：新增 `core/upload_security.py`（净化 / uuid 落盘名 / 白名单 / 分块限长读取），`document_router` 改为组合该模块，新增 50MB 上限；新增 `tests/router/test_document_upload.py`（21 用例） | commit `fef8eca`，PR #74 已 merge（`5651c98`），issue #34 自动关闭 |
| 2026-09-13 | T03 | **修正不可执行的验收命令**：原 `from app.router import document_router` 会连带引入 milvus/ES/docmind（实测缺 `tinytag`），且 `sys.path` 用法与项目约定不符；已把纯逻辑抽到 `core/upload_security.py` 并把验收改为可执行形式，修正记录写入 `tickets.md` T03 | 21 passed；路径穿越验收打印 OK |
| 2026-09-13 | T03 | **同源问题发现**：`attachment_router.py:148` 的 `f"{uuid}_{filename}"` 同样可被穿越（客户端文件名仍进路径）。已标注于 `tickets.md` T03，见待办 P-09 | 建议另开票 |
| 2026-09-13 | — | **工作树清空现象第 3、4 次复现（升级）**：合并 T03 时 `git checkout main` 被 SIGTERM 打断，留下陈旧 `index.lock` + 半截工作树；随后范围升级为 `backend/app` + `backend/tests` 共 **114 → 111 个文件**消失，`backend/app` 只剩刚被写过的 `core`、`router`。已核实**不是沙箱回滚**（独立进程复核写入可持久）、不是 git 行为、不是 Defender 隔离。恢复采用「清锁 → `git checkout HEAD -- .` → 状态归零」 | 新增/升级 `LOOP-PROTOCOL.md` §9.3（六条硬规则），待办 P-06 升级 |
| 2026-09-13 | — | **文档编辑静默丢失**：`TRACKER.md` 的部分编辑报成功但未落盘，被提交带成旧内容（主 tip / P-05 / P-06 / P-07 四处）。已逐项复核并重写，沉淀为「写完必复核」规则 | 新增待办 P-08 |
| 2026-09-13 | — | **第一阶段审查批次边界到达**：T01–T03 已完成，进入第 1 批 `code-review`（fixed point `9342913`，终点 `5651c98`） | 见批次审查记录 |
| 2026-09-13 | — | **第 1 批 `code-review`（双轴并行）**：标准轴 4 条 + 规格轴 3 条，去重后 5 条。修复 commit `19547b0`（conftest 补测试占位密钥；READMED 文档与强校验对齐）；2 条记为保留判定；1 条衍生决策票 | 三个回归测试文件 **36 passed**，JWT 相关收集错误归零 |
| 2026-09-13 | — | **新建 T41（#75）**：合并三处上传实现，消除 `attachment_router` / `knowledge_router` 的路径穿越。标 `needs-decision`（白名单是否并轨会改变上传类型），等用户裁决 | ticket 总数 40 → **41**；P-09 转 T41 |
| 2026-09-13 | T41 | **用户裁决方案 A**（只统一实现、白名单各自保留）。实施：`attachment_router` / `knowledge_router` 改用 `ensure_supported_extension` / `safe_filename` / `read_upload_with_limit`，删除各自 `get_file_extension` 与 `os.path.splitext`；补 50MB 上限；413 显式 re-raise 避免被兜底转 500；`document_router` 上限改用共享常量；清理无用 `shutil` 导入 | commit `1182ccb`，PR #76 已 merge（`bd1e635`），issue #75 自动关闭 |
| 2026-09-13 | T41 | 验收：`pytest tests/router -k upload` → **40 passed**；三路由 `py_compile` 通过。测试分纯函数层 + `ast` 源码层（路由因缺 `tinytag` 无法导入），并**锁定三份白名单成员集合**作为「零行为变更」证据 | 批次 2 起算 |
| 2026-09-13 | — | **新硬规则首次生效**：T41 全程用 `git fetch origin main:main` 同步 `main`（不 checkout），**未再触发工作树清空**；但再次出现**文档编辑静默丢失**（`决策票待裁决` 一行的 T41 未落盘），已再次确认「写完必逐行复核」 | §9.3 规则有效；P-08 仍成立 |
| 2026-09-13 | T04 | 实施 + 合并：`document_router` 在 **router 级**挂 `Depends(get_current_user_required)`，覆盖 `/upload`、`/list`、`/delete`、`/retrieve` 四个端点（全部为文档数据操作，无匿名端点）；新增 `tests/router/test_document_auth.py`（10 用例） | commit `33724cc`，PR #78 已 merge（`93d931c`），issue #35 自动关闭 |
| 2026-09-13 | T04 | **测试基建修正（后续所有 router 类测试共用，含 T05）**：① `conftest.py` 的 `service` 占位包缺顶层名字 → `from service import DocumentService, ServiceConfig` 收集期 ImportError，改为按需从轻量子模块挂名字（仍不执行重型 `service/__init__`，实测 >35s）；② `service.docmind_service` 导入实测 **~48s**，注入**抛 `NotImplementedError`** 的轻量替身（不伪造成功）；③ FastAPI 0.141 下 `TestClient(APIRouter)` 会报 `fastapi_middleware_astack not found`，改用最小 `FastAPI` 应用挂载被测 router | `pytest tests -q -k document_auth` → **10 passed** |
| 2026-09-13 | T04 | **R-02 实测结论**：前端源码对 `/documents/*` 调用命中 **0 处**（前端知识库走 `/knowledge-bases/...`），统一注入点 `frontend/src/api/request/plugins/auth.ts` 是**无条件**请求拦截器 → 前端无需改动；`tickets.md` T04 原验收 #3 写的 `frontend/src/api/request/auth.ts` **不存在**，已修正路径。真正的既有匿名调用方是两处 curl 文档示例，已补 `Authorization` 头 | 修正记录写入 `tickets.md` T04 |
| 2026-09-13 | — | **全量 pytest 首跑（含 integration）**：147 passed / 4 skipped / 1 failed。唯一失败为需真实 Postgres 的 `@pytest.mark.integration` 用例，**判定为环境性、非回归**，沉淀为待办 P-10 | 见 P-10；`-m "not integration"` 即可全绿 |
| 2026-09-13 | — | **台账纠错**：T01 行原写分支名 `ticket/T01-...`（带斜杠，与 §9.1 禁令冲突且与 GitHub 实际分支不符）且 Commit/PR 为空；T02 行仍停在 `TODO`（实际已合并）。已按 `gh pr list` 核实值回填：T01=`ec5999d`/#72、T02=`bd54b9b`/#73 | TRACKER 与 GitHub 现状一致 |
| 2026-09-13 | T05 | 实施 + 合并：`chat` / `search` / `news` 三个路由按 T04 同一模式在 router 级挂 `get_current_user_required`，覆盖 13 个端点；新增 `tests/router/test_router_auth.py`；`backend/README.md` 两条 chat curl 示例补 `Authorization` 头 | commit `cee1c33`，PR #80 已 merge（`7f14a6f`），issue #36 自动关闭 |
| 2026-09-13 | T05 | **匿名端点判定实测闭合**：`routes.tsx` 中除 `/login` 外全部处于 `AuthGuard` 子树；`/search/web` 在 `frontend/src` 命中 0 处；登录页只调 `api.auth.login/register`；仓库内无脚本/定时任务调用 → 风险条所述架构分叉**不成立**。另实测 `news_router` 是 **8** 个端点而非 9 | 验收 `pytest -k "auth or unauthorized"` → 47 passed |
| 2026-09-13 | T06 | 实施 + 合并：新增 `core/cors.py`（`parse_cors_origins` / `is_production_env` / `build_cors_kwargs`），`app_main.py` 改为 `add_middleware(CORSMiddleware, **build_cors_kwargs())`；通配来源强制 `allow_credentials=False` 并告警；生产环境来源为空则 `RuntimeError` 终止启动；`.env.example` 增 `CORS_ALLOW_ORIGINS` | commit `18ed8f8`，PR #81 已 merge（`41009b9`），issue #37 自动关闭 |
| 2026-09-13 | T06 | **R-03 实测闭合**：`withCredentials` 在 `frontend/src` 命中 0 处 → 前端不依赖 CORS 凭据，通配 + `credentials=False` 不影响本地联调，**不构成架构分叉**。另修正原验收 #2 不可执行的问题（`from app.app_main import ...` 会拉起全部路由与 DB 引擎；换成 `core.cors` 又会触发 `core/__init__` 的导入期 JWT 校验），改用 §11.3 的 `importlib` 按文件路径加载 | `pytest tests/core/test_cors_config.py` → 14 passed |
| 2026-09-13 | — | **第 2 批 `code-review`（双轴并行，fixed point `19547b0`）**：标准轴 7 条 + 规格轴 7 条，去重后 **11 条**（9 修 2 保留）。规格轴独立复验了三项关键声明：R-03 成立、T05 无匿名调用方成立、T41 方案 A 白名单未并轨成立。另发现 `docs/agents/issue-tracker.md` 不存在，规格来源取自本地 `prd.md`/`tickets.md` | 明细见「第 2 批审查 findings 明细」 |
| 2026-09-13 | — | **第 2 批 findings 修复**：合并两个重复的鉴权测试文件（`test_document_auth.py` 并入 `test_router_auth.py`，改为 4 路由 / 17 端点统一参数表）；把源码字符串匹配断言换成结构化 `APIRouter.dependencies`；修正「不占内存」误导注释、`news_router` 注释 9→8、`knowledge_router` 未使用导入、`.env.example` CORS 措辞 | commit `57f69e0`；`pytest tests -m "not integration"` → **198 passed / 5 deselected** |
| 2026-09-13 | T07 | 实施 + 合并：`core/database.py` 新增 `_require_env(name)`，`POSTGRES_PASSWORD` 改为导入期校验（缺失/空 → 抛 `RuntimeError` 并点名变量）；`docker-compose.yml` / `backend/docker-compose-base.yml` 的 postgres、minio 口令改为 `${POSTGRES_PASSWORD}` / `${MINIO_ROOT_USER}` / `${MINIO_ROOT_PASSWORD}` 注入，并给 milvus-standalone 补 `MINIO_ACCESS_KEY_ID` / `MINIO_SECRET_ACCESS_KEY`（原为硬编码弱口令）；新增根级 `.env.example` 与 `backend/.env.example` 的占位项；`READMED.md` / `start-services.sh` / `backend/README.md` 明文口令清除；新增 `tests/core/test_db_password_required.py`（15 用例） | commit `1552d13`，PR #83 已 merge（`e4d82a7`），issue #38 自动关闭 |
| 2026-09-13 | T07 | 验收：`pytest tests/core/test_db_password_required.py` → **15 passed**；`docker compose config --quiet` → exit=0；受控文件 `grep -rn "postgres123\|minioadmin"` 无残留。全量 `pytest tests -m "not integration"` → **213 passed / 5 deselected**（400.52s） | 批次 3 起算（fixed point `57f69e0`） |
| 2026-09-13 | T07 | **本机 `.env` 未轮换的决策**：本地 `backend/.env` 的 `POSTGRES_PASSWORD` 仍是 11 字符弱口令（等于 `postgres` + 数字后缀），与现有 DB volume 数据绑定。轮换需 `ALTER USER` 或 `docker compose down -v`（**丢数据**），故**不**在票据内自动执行；改为在 `.env.example` 注明轮换步骤，把决策留给用户 | 记录于本行；非回归 |
| 2026-09-13 | T08 | 实施 + 合并：`scout.py` 删除硬编码 `collection_name="knowledge_base"`（F-08），改走 `retrieval_service.retrieve_from_knowledge_base`（集合名转换只保留 retrieval_service 一处实现）；`kb_name` 为空时跳过本地检索并告警（与 V1 `dr_g.py` 的 `search_local and kb_name` 门控语义一致，**不引入全局检索语义**，无架构分叉）；顺带修复 `kb_name` 在 `_research_stream` 被丢弃的问题（补齐 `research → graph.run → create_initial_state → ResearchState` 透传链）；`DeepScout` 构造不再直连 Milvus（原 `MilvusService()` 构造即建连，唯一消费者已移除）；新增 `tests/service/deep_research_v2/test_scout_local_search.py`（5 用例，mock 检索服务） | commit `e16b313`，PR #85 已 merge（`10a973f`），issue #39 自动关闭 |
| 2026-09-13 | T08 | 验收：命令 1 `! grep '"knowledge_base"' scout.py` → PASS；命令 2 `pytest tests/service/deep_research_v2 -q` → **25 passed**；全量 `pytest tests -m "not integration"` → **218 passed / 5 deselected**（385.37s）；命令 3（needs-infra 端到端，需 Milvus + Postgres）Docker 未运行 → **BLOCKED**，未伪造 PASS。注意：测试环境里 `service.deep_research_v2(.agents)` 被 conftest 注册为命名空间桩、真实 `__init__.py` 不执行，graph 类测试须沿用 `test_graph_outline_checkpoint.py` 的「桩补占位类 + `object.__new__` 绕构造」模式 | 批次 3 第 2 张，剩 T09 后收批审查 |
| 2026-09-13 | T09 | 实施 + 合并：`validate_sql` 主判据改为「以 `SELECT` 或 `WITH` 开头 + 禁止任何形式的 `UNION`」，`FORBIDDEN` 黑名单降为辅助兜底；清理 `'--'` / `'UNION ALL SELECT'` / `'*/'` 重复项；`ALLOWED_KEYWORDS` 移除 `'UNION'`。**风险条核实（无架构分叉）**：`ALLOWED_KEYWORDS` 全仓无使用点（死配置）、prompt 无 UNION 指引、前端无 UNION 生成 → UNION 非有意支持的能力。验收 #1 票面脚本路径与项目约定不符，已修正并记录于 `tickets.md` T09「实施修正」；新增 `tests/service/test_text2sql_validate.py`（27 用例） | commit `5649543`，PR #87 已 merge（`0f3ceba`），issue #40 自动关闭 |
| 2026-09-13 | T09 | 验收：票面脚本 → 打印 `OK: UNION 绕过已封堵`；`pytest tests -q -k text2sql` → **27 passed**；全量 `pytest tests -m "not integration"` → **245 passed / 5 deselected**（388.38s）。ruff 无新增告警，密钥红线自查通过 | 批次 3（T07–T09）收批，进入第 3 批 `code-review`（fixed point `57f69e0`） |
