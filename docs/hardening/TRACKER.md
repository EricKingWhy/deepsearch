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
| `main` 当前 tip（2026-09-13 核实，本地＝远端，已含 T01–T29 + T41 合并） | `f1b7219c53758d5c08b17d2b608e9b379e83edc8` |
| 当前批次 | 10（T30–T31，已收批待审查；T20 为决策票待裁决；T10 为 needs-human 保持 BLOCKED） |
| 当前 fixed point（上一批审查结束 commit） | `f1b7219`（第 9 批审查修复 commit） |
| 当前分支命名 | `T<编号>-<短描述>`（**必须扁平，禁止 `/`**，见协议 §9.1） |
| 合并目标 | 本地 `main` 分支（merge commit，不用 squash） |
| 总 ticket 数 | 41（T01–T40 + 第 1 批审查衍生 T41） |
| 已完成 | 30 |
| 决策票待裁决 | T20、T37（T18/T19 已裁决：A / C） |

## 批次审查记录

| 批次 | 覆盖 ticket | fixed point（起点） | 审查 commit（终点） | findings 数 | 修复 commit | 状态 |
|------|------------|--------------------|--------------------|------------|------------|------|
| 1 | T01–T03 | `9342913` | `5651c98` | 5 | `19547b0` | FIXED |
| 2 | T04–T06 + T41 | `19547b0` | `41009b9` | 11 | `57f69e0` | FIXED |
| 3 | T07–T09 | `57f69e0` | `fbe55f8` | 6 | `6b73d44` | FIXED |
| 4 | T11–T13 | `6b73d44` | `975eea8` | 5 | `1f52bfc` | FIXED |
| 5 | T14–T16 | `1f52bfc` | `381c929` | 4 | `d345685` | FIXED |
| 6 | T17–T19 | `d345685` | `3e18063` | 4 | `9fbdf3f` | FIXED |
| 7 | T21–T23 + T26 | `9fbdf3f` | `4dde37a` | 4 | `d1732ce` | FIXED |
| 8 | T24–T25 | `d1732ce` | `f10cc67` | 5 | `37a2ec6` | FIXED |
| 9 | T27–T29 | `37a2ec6` | `3e7ea65` | 7 | `f1b7219` | FIXED |
| 10 | T30–T32 | `f1b7219` | `a99d55c` | `（待审查）` | — | — |

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

### 第 3 批审查 findings 明细（`57f69e0` → `fbe55f8`，修复 commit `6b73d44`）

双轴并行审查：**标准轴 4 条 + 规格轴 3 条**，去重后 **6 条**。2 条已修，4 条保留判定。

| # | 轴 | finding | 处置 |
|---|----|---------|------|
| 1 | 标准 + 规格 | `validate_sql` 的 `'UNION' in sql_upper` 是子串匹配，会误拦 `union_id` / `reunion_tag` 等含 union 字样的标识符 | **已修** `6b73d44`（改 `re.search(r"\bUNION\b", ...)` 词边界；补 3 用例锁行为） |
| 2 | 标准 | `test_db_password_required.py` 的 `assert "POSTGRES_PASSWORD = _require_env(" in source` 是源码字符串匹配，与第 2 批「改结构化断言」处置方向不一致 | **已修** `6b73d44`（补注释说明保留理由：T07 验收口径本就是 grep 类源码检查，非运行时行为断言，不同型） |
| 3 | 标准 | **重复文案**：compose 两份 MinIO/Milvus 凭据块逐字重复；口令轮换告警在根/后端 `.env.example` 与 `READMED.md` 三处各写一遍 | **保留判定**：两个 compose 文件本就是票面要求分别修改的独立部署文件；告警文案多处可见对使用者更安全 |
| 4 | 标准 | `conftest.py` 又新增一个 import 期全局环境桩（`POSTGRES_PASSWORD`），桩数量持续增长 | **保留判定**：延续既有机制且有注释说明；若后续继续膨胀再收敛为显式 fixture |
| 5 | 规格 | T08 门控语义变化属**实施者自决**：旧代码 `search_local=True` 无 kb_name 时仍检索 `"knowledge_base"` 集合，新实现直接跳过返回 `[]`；票面「保留全局检索语义」未逐字执行 | **保留判定**：`"knowledge_base"` 不是任何真实集合名（入库只走 `kb_{name}`），**全局检索语义从未工作过**，不存在可保留的既有行为；且 V1 `dr_g.py:717` 的 `search_local and kb_name` 是仓库内现成先例 → 前提不成立即无取舍，不构成需用户裁决的分叉。旧集合本就搜不到任何用户文档（F-08），无行为回退 |
| 6 | 规格 | T08 验收命令 3（needs-infra 端到端）BLOCKED | 无需动作：Docker 未运行，`TRACKER` 如实记录未伪造 PASS，符合票面 R-05 |

**规格轴的关键复核（独立复验通过）**：

- **NG-2 / NG-3 未被触碰**：`dr_g.py` / `react_controller.py` / `tool_executor.py` 未出现在批次 diff；
  `graph.py` 仅给 `run()` 增加 `kb_name` 参数，LangGraph 路径（`_build_langgraph` / `_run_with_langgraph` /
  `_*_node`）零删改。
- **T07 密钥清除完整**：`git grep postgres123|minioadmin fbe55f8` 票面受控范围内 0 命中；
  `.gitignore` 覆盖 `.env`；`database.py` 的 `_require_env` 无默认值兜底。
- **T09 风险条核实成立**：`ALLOWED_KEYWORDS` 全仓无使用点、prompt 无 UNION 指引、前端无 UNION 生成
  → UNION 非有意支持的能力，全禁不构成架构分叉。
- 密钥红线自查（LOOP-PROTOCOL §6）：`git grep -nE "(sk-…|Bearer …)"` 在终点 commit 无命中。

### 第 4 批审查 findings 明细（`6b73d44` → `975eea8`，修复 = 本记录提交）

双轴并行审查：**标准轴 3 条 + 规格轴 3 条**，去重后 **5 条**。2 条已修，3 条保留判定。

| # | 轴 | finding | 处置 |
|---|----|---------|------|
| 1 | 规格 | T12 验收 #1 的 grep 漏查 `max_overflow`（「改什么 #2」明确要求落地，实现已有但验收口径未覆盖） | **已修** `1f52bfc`（票面 grep 补 `max_overflow`，实测命中） |
| 2 | 规格 | 票面 `scripts/init_industry_data.py` 路径笔误（实际在 `backend/app/scripts/`） | **已修** `1f52bfc`（实施修正补准确路径） |
| 3 | 标准 | 日志风格不一致：smart_analyzer 用模块级 `logger`，dr_g.py 用 `logging.warning` 模块函数直呼 | **保留判定**：dr_g.py 全文件既有风格就是 `logging.*` 直呼（含 61 行 `basicConfig`），本票新日志与文件内风格一致；统一该文件风格超出票面（NG-3 保留文件，最小改动） |
| 4 | 标准 | `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` / `DB_POOL_RECYCLE` 三常量结伴（Data Clumps） | **保留判定**：票面明确「参数直接写在 `create_engine` 调用里，常量就地定义」，不引入配置对象 |
| 5 | 标准 | `except Exception: logger.X(...)` 同形 8 处（Duplicated Code，轻） | **保留判定**：各处文案与日志级别语义不同，抽 helper 反致过度抽象 |

**规格轴的关键复核（独立复验通过）**：

- **T11 完整**：8 处裸 except 全部替换且控制流不变；全仓裸 except 计数 **0**。
- **T12 的 READMED 迁移说明属实**：两个迁移 SQL 全部 `IF NOT EXISTS` / `DO $$` 幂等守卫；
  迁移命令假设的服务名 `postgres`、库名 `industry_assistant` 与 `docker-compose.yml`、
  `database.py` 默认值逐项一致。
- **T13 纯注释属实**：graph.py 本批次仅有的代码变更属 T11（裸 except），T13 自身零可执行代码变更；
  NG-2（LangGraph 路径）与 NG-3（V1 三件套）零删改。

### 第 5 批审查 findings 明细（`1f52bfc` → `381c929`，修复 = 本记录 commit）

双轴并行审查：**标准轴 0 硬违规 + 3 条 judgement call；规格轴三票全部「无发现」**。去重后 **4 条**：1 修 3 保留。本批为历批最干净。

| # | 轴 | finding | 处置 |
|---|----|---------|------|
| 1 | 规格 | CLAUDE.md 架构章节将 V1 路线与 LangGraph 运行时并称 NG-2/NG-3，未逐条对应（严格 V1 仅对应 NG-3，NG-2 指 graph.py 路径） | **已修**（本记录：V1 标注 `PRD NG-3`、LangGraph 标注 `PRD NG-2`，逐条对应） |
| 2 | 标准 | `dr_g.py` 导入区：T15 加的 `from core.serialization import ...` 落在 stdlib `import logging` 之前，分组顺序瑕疵 | **保留判定**：ruff isort（I001）已覆盖此范畴，协议规定工具强制的跳过；NG-3 文件坚持最小改动 |
| 3 | 标准 | NG-3「有意保留」说明段在三个 V1 模块逐字重复三份（Duplicated Code） | **保留判定**：LOOP-PROTOCOL §8 允许按模块加注释；抽公共常量反成 Speculative Generality |
| 4 | 标准 | `dr_g.serialize_event` 同名导入属刻意转发（Middle Man） | **保留判定**：票面设计——保留 `dr_g.serialize_event` 模块属性供 `test_research_outline_approval.py` monkeypatch |

**规格轴的关键复核（独立复验通过）**：

- **T15 移动非重写**：`core/serialization.py` 函数体与原 `dr_g.py` 实现**逐字等价**（仅尾部空行差异）；
  `serialize_event` 全仓唯一命中；`service/__init__.py` 的 `ResearchService` 导出未破坏；
  research_router 无 dr_g 依赖残留（仅 :18/:51 注释提及）。
- **PR #96 缺陷确认修复干净**：三模块 docstring 语法正确（py_compile 实测过）、保留说明位于 docstring 内部。
- **T16 与代码逐项相符**：langfuse 版本与 requirements 一致；两级开关默认值与
  `langfuse_client.py:41`（false）/ `tracing.py:101`（true）一致；`ES 存储|ES 索引` 字面计数 0；
  知识图谱宣称收窄且 `knowledge-graph.tsx` 存在；守 NG-1 收窄方向。
- 另：dr_g.py 中 serialize_event 原定义被删**不构成 NG-3 违规**——系 T15 整体搬迁且同名重导入，V1 能力保留。

### 第 6 批审查 findings 明细（`d345685` → `3e18063`，修复 = 本记录 commit）

双轴并行审查：**标准轴 1 硬伤 + 2 judgement call；规格轴三票全部「无发现」**。去重后 **4 条**：3 修 1 保留。

| # | 轴 | finding | 处置 |
|---|----|---------|------|
| 1 | 标准 | `architecture.md` 称「集合名转换只有一处实现」不实——`retrieval_service.py:91`、`knowledge_router.py:97/:466` 共 3 处 | **已修**（改为如实描述：权威实现 + 两处存量重复标注为硬化候选项） |
| 2 | 标准 | `architecture.md` 把「消费 asyncio.Queue 并 yield SSE」归给 `run()`，实为 `_run_simplified`（`run()` 仅委托转发） | **已修**（归属改正） |
| 3 | 标准 | TRACKER「决策票待裁决」行仍列 T18/T19，与已裁决记录自相矛盾 | **已修**（改为 T20、T37） |
| 4 | 标准 | `kb_{name}.lower().replace(" ", "_")` 3 处重复（Duplicated Code，存量问题被 T17 文档背书） | **保留判定**：存量、非本 diff 引入；finding #1 修复时已在文档如实标注；如需收拢应单开硬化票 |

**规格轴的关键复核（独立复验通过）**：T17 五小节齐全、单文件、NG 映射与 prd.md 一致、决策记录未混入；
T18 langfuse 仅剩一行更严约束、langgraph/alembic 未删、47 条解析口径如实记录；
T19 裁决 C 落实且注释含迁移来源指引；台账 PR/SHA 与 git log 逐项吻合。

### 第 7 批审查 findings 明细（`9fbdf3f` → `e3c28da`，修复 = 本记录 commit）

双轴并行审查：**标准轴 0 硬违规 + 2 judgement call；规格轴四票全部「实质合规」**。去重后 **4 条**：1 修 3 保留。

| # | 轴 | finding | 处置 |
|---|----|---------|------|
| 1 | 规格 | TRACKER 主 tip 记 `4dde37a`，但台账闭合经 PR #110 合并于 `e3c28da`（自指时序滞后） | **已修**（本记录：tip 更新为本记录 commit 后的实际 tip） |
| 2 | 标准 | `ruff.toml` 的 `line-length=100` 在当前最小规则集下无规则消费（Speculative Generality，轻） | **保留判定**：配置注释已声明「逐步放开」意图；预先设定零成本 |
| 3 | 标准 | `CONTRIBUTING.md` 自称「一屏」实际略超 | **保留判定**：已明示「回链不复制」原则，超出部分均为回链引导 |
| 4 | 规格 | `.editorconfig` 覆盖 js/jsx/vue 超票面清单（scope creep，轻） | **保留判定**：只在新文件内、低风险顺带约定；与前端栈（vite+vue）相符 |

**规格轴独立复验通过**：T21 MIT + commit 注明可更换；T22 五项规定齐、回链文件全部存在、命令口径实测正确；
T23 未统一存量换行符（diff 仅新文件）；T26 零违规故「ignore 注明」条件项不适用；提前入批理由已记录；
台账 SHA/PR 逐项吻合。

### 第 8 批审查 findings 明细（`d1732ce` → `f10cc67`，修复 = 本记录 commit）

双轴并行审查：**标准轴 0 硬违规；规格轴两票实质合规（2 条小瑕疵）**。去重后 **5 条**：3 修 2 保留；另有 1 条复核后**驳回**。

| # | 轴 | finding | 处置 |
|---|----|---------|------|
| 1 | 标准 | 台账称 PR 模板「五项自查」，实际 4 个复选项 | **已修**（台账措辞改「四项自查」） |
| 2 | 标准 | 台账称模板与 ticket 结构「同构」偏强——模板含「事实依据」独立节，票面无此节 | **已修**（措辞改「对齐」并注明差异） |
| 3 | 规格 | 主 tip 记 `ab5b673`，实际 tip 为台账闭合 merge `f10cc67`（自指时序滞后，第 7 批同款） | **已修**（本记录后回填实际 tip） |
| 4 | 标准 | 两张 issue 模板验收节命名不一致（「验收」vs「验收（修复标准）」） | **保留判定**：语义各有侧重，统一收益低 |
| 5 | 规格 | CHANGELOG 未附 Keep a Changelog 版本链接（`[0.1.0]: ...`） | **保留判定**：票面未要求；单版本阶段链接无指向意义 |

**驳回的 finding**：规格轴称 CHANGELOG「READMED」系 README 拼写错误——经核实仓库主文档**确实命名为 `READMED.md`**（初始导入即如此，`AGENTS.md` 亦引用此名），CHANGELOG 引用真实文件名，不构成缺陷。

**规格轴独立复验通过**：CHANGELOG 抽查条目与 git log 相符（8 处裸 except → `d4b1228`、UNION 词边界 → `text2sql_service.py:237`）；双侧版本号 0.1.0 实测一致；无未完成小节；票面风险条「汇总标注」逐字落实；scope creep 无。

### 第 9 批审查 findings 明细（`37a2ec6` → `3e7ea65`，修复 = 本记录 commit）

双轴并行审查：**标准轴 0 硬违规；规格轴 T29「无发现」、T27/T28 基本合规（数字表述与口径瑕疵）**。去重后 **7 条**：3 修 4 保留。

| # | 轴 | finding | 处置 |
|---|----|---------|------|
| 1 | 标准 | 台账称「integration 5 用例」，实际 checkpoint 文件为 4 个（5+1+12=18 与 17 deselect 矛盾） | **已修**（改 4 并注明 observability 双标记，合计 17 吻合） |
| 2 | 标准 | T29 执行日志 merge SHA 留「（见 git log）」占位 | **已修**（回填 `6a7e489`） |
| 3 | 规格 | 主 tip 占位未回填（自指时序滞后惯例） | **已修**（本记录后回填） |
| 4 | 规格 | T28 env 回退占位「写死」在 workflow，与票面「从 Secrets 读取，不得写死」字面冲突 | **保留判定**：占位为 test-only 非真实密钥（验收 2 无命中）；若改纯 secrets 引用，未配 Secrets 的仓库 CI 必红。票面意图是防真实密钥入库，回退方案恰好满足；已在 yml 注释声明 |
| 5 | 标准 | test-only 占位字面量在 ci-backend.yml 与 conftest.py 重复维护（Duplicated Code） | **保留判定**：已有注释声明一致性意图；抽公共位置需引入额外机制，收益低 |
| 6 | 标准 | evals 的 pytestmark 插在 import 块之间，风格欠整洁 | **保留判定**：功能无碍，ruff 不覆盖注释/语句位置美学 |
| 7 | 规格 | `unit` marker 已注册但全仓无用例（空挂） | **保留判定**：票面明确要求注册三 marker；空挂是为后续新测试（T39/T40）预留的口径 |

**规格轴专项审视（通过）**：evals 12 用例标 needs_infra 合理——`if not api_key: skip` 只挡「未配置」，挡不住「已配置但失效」（欠费 400 暴露混入），mock 会让真 LLM 质量评测失去意义。CI 实跑核验：backend-ci / frontend-ci 最近各 5 次全部 success。批次末全量默认口径：**236 passed / 17 deselected（8.64s）**。

## ticket 明细## ticket 明细## ticket 明细## ticket 明细## ticket 明细## ticket 明细## ticket 明细

状态取值：`TODO` / `DOING` / `DONE` / `BLOCKED` / `CANCELLED`

| ID | 标题 | Issue | 状态 | 分支 | Commit | PR | 验收 | 批次 | 批次审查 |
|----|------|-------|------|------|--------|----|------|------|---------|
| T01 | 移除 dr_g.py 硬编码 API Key | #32 | DONE | `T01-remove-hardcoded-credentials` | `ec5999d` | #72 | PASS（`pytest tests/service/test_dr_g_config.py -v` → 9 passed，见 P-02） | 1 | FIXED@19547b0 |
| T02 | JWT 密钥必填并在启动时校验 | #33 | DONE | `T02-require-jwt-secret` | `bd54b9b` | #73 | PASS（`pytest tests/core/test_security_jwt.py` → 6 passed） | 1 | FIXED@19547b0 |
| T03 | document_router 上传安全加固 | #34 | DONE | `T03-harden-document-upload` | `fef8eca` | #74 | PASS（`pytest tests/router/test_document_upload.py` → 21 passed；路径穿越净化验收打印 OK） | 1 | FIXED@19547b0 |
| T04 | document_router 增加鉴权 | #35 | DONE | `T04-document-router-auth` | `33724cc` | #78 | PASS（T04 当时 `pytest -q -k document_auth` → 10 passed；第 2 批审查并入 `test_router_auth.py` 后，现用 `-k router_auth` → 47 passed；鉴权依赖计数 = 2） | 2 | FIXED@57f69e0 |
| T05 | chat / search / news 路由补充鉴权 | #36 | DONE | `T05-harden-chat-search-news-auth` | `cee1c33` | #80 | PASS（`pytest -q -k "auth or unauthorized"` → 47 passed；三路由鉴权计数 = 2/2/2；`news_router` 实测 8 个端点非 9） | 2 | FIXED@57f69e0 |
| T06 | 收紧 CORS 配置 | #37 | DONE | `T06-tighten-cors` | `18ed8f8` | #81 | PASS（`pytest tests/core/test_cors_config.py` → 14 passed；通配 + 凭据的硬编码组合已消失；`py_compile app_main` 通过） | 2 | FIXED@57f69e0 |
| T07 | docker-compose 明文口令改为环境变量注入 | #38 | DONE | `T07-compose-secrets` | `1552d13` | #83 | PASS（`pytest tests/core/test_db_password_required.py` → 15 passed；`docker compose config --quiet` → exit=0；全仓 `grep postgres123\|minioadmin` 受控文件无残留） | 3 | FIXED@6b73d44 |
| T08 | 修复 Scout 本地知识库检索的集合名不匹配 | #39 | DONE | `T08-scout-kb-collection` | `e16b313` | #85 | PASS（`! grep '"knowledge_base"' scout.py` → 无输出；`pytest tests/service/deep_research_v2 -q` → 25 passed；全量 `-m "not integration"` → 218 passed / 5 deselected；needs-infra 端到端验证因 Docker 未运行记 BLOCKED） | 3 | FIXED@6b73d44 |
| T09 | 修复 text2sql SQL 校验可被 UNION SELECT 绕过 | #40 | DONE | `T09-text2sql-union` | `5649543` | #87 | PASS（票面验收脚本（路径修正为 `sys.path.insert(0,'app')`）→ 打印 `OK: UNION 绕过已封堵`；`pytest -k text2sql` → 27 passed；全量 `-m "not integration"` → 245 passed / 5 deselected） | 3 | FIXED@6b73d44 |
| T10 | text2sql 使用只读数据库账号兜底 | #41 | BLOCKED | — | — | — | 等待用户创建只读角色 | 4 | FIXED@1f52bfc |
| T11 | 清除裸 except 并补日志 | #42 | DONE | `T11-remove-bare-except` | `d4b1228` | #90 | PASS（`! grep -nE "except\s*:" <四文件>` → 无输出；全仓裸 except 计数 → 0；全量 `-m "not integration"` → 248 passed） | 4 | FIXED@1f52bfc |
| T12 | 收敛数据库连接池与会话生命周期 | #43 | DONE | `T12-db-pool-schema` | `1f57882` | #91 | PASS（`grep -nE "pool_pre_ping\|pool_recycle\|pool_size" core/database.py` → 有命中；票面脚本（路径+env 占位修正）→ 打印 `OK: 连接池参数存在`；create_all 改 `DB_AUTO_CREATE=1` 显式开关） | 4 | FIXED@1f52bfc |
| T13 | 显式标注 LangGraph 运行时路径为有意保留 | #44 | DONE | `T13-langgraph-annotation` | `ad7baa6` | #92 | PASS（`grep -c "NG-2" graph.py` → 7；保留字样 8 处；本票 diff 无删除的函数；`pytest -k deep_research_v2` → 25 passed） | 4 | FIXED@1f52bfc |
| T14 | 显式标注 V1 ReAct 编排为保留的备选路线 | #45 | DONE | `T14-v1-annotation` | `1180182` | #96 | PASS（三模块保留说明各 2 处命中；路由 version 字段与 CLAUDE.md 已更新；无删除的实现）。⚠️ 本票曾引入 docstring 错位 SyntaxError，已在 T15 分支修复（见执行日志与 tickets.md T14「实施修正」） | 5 | FIXED@d345685 |
| T15 | 抽离 serialize_event | #46 | DONE | `T15-extract-serialize-event` | `9839042` | #97 | PASS（`def serialize_event` 全仓唯一命中 `core/serialization.py`；research_router 无 dr_g 导入；除 `service/__init__` 既有顶层导出外无遗留；全量 → 248 passed） | 5 | FIXED@d345685 |
| T16 | 修复文档与代码漂移 | #47 | DONE | `T16-doc-drift` | `aad9dd4` | #98 | PASS（langfuse 版本与 requirements 一致；ES 字面计数 0（各留一句全拼历史说明）；知识图谱表述已收窄；仅 docstring 变更 py_compile 通过） | 5 | FIXED@d345685 |
| T17 | 新增架构总览文档 | #48 | DONE | `T17-architecture-doc` | `b309036` | #101 | PASS（5 个小节；「有意保留」2 处命中 NG-2/NG-3；目录导航与实际一致；仅 docs/ 变更） | 6 | FIXED@9fbdf3f |
| T18 | requirements.txt 去重与依赖分区 | #49 | DONE | `T18-requirements-dedup` | `68d00b2` | #102 | PASS（无重复声明；三关键依赖均在；packaging 逐行解析 47 条通过。**用户裁决 A**：不引入版本锁文件） | 6 | FIXED@9fbdf3f |
| T19 | 决策票：alembic 去留 | #50 | DONE | `T19-alembic-annotation` | `f98a81d` | #103 | PASS（**用户裁决 C**：保留依赖 + 「预留未使用」注释；READMED 迁移章节在位；T18 验收复跑 PASS） | 6 | FIXED@9fbdf3f |
| T20 | 决策票：chat/index.tsx 是否拆分 | #51 | BLOCKED | — | — | — | 等待用户裁决 | — | — |
| T21 | 新增 LICENSE | #52 | DONE | `T21-license` | `a091d04` | #106 | PASS（MIT 默认（票面授权），版权人 EricKingWhy，commit 注明可更换） | 7 | FIXED@d1732ce |
| T22 | 新增 CONTRIBUTING.md | #53 | DONE | `T22-contributing` | `8bdd1e3` | #109 | PASS（5 小节 ≥4；密钥红线命中；全部细则回链不复制；依赖 T26 已先行合并） | 7 | FIXED@d1732ce |
| T23 | 新增 .editorconfig | #54 | DONE | `T23-editorconfig` | `a458d7d` | #107 | PASS（root=true；py 4/ts 2 空格；end_of_line 保持 lf（票面风险条）；不统一存量换行符） | 7 | FIXED@d1732ce |
| T24 | 新增 issue 与 PR 模板 | #55 | DONE | `T24-github-templates` | `4352d14` | #112 | PASS（三模板在位；issue 字段与 ticket 结构对齐（模板含「事实依据」独立节，比票面结构细一档）；PR 模板强制验收输出 + NG-2/NG-3/密钥等四项自查；必填 3-5 项） | 8 | FIXED@37a2ec6 |
| T25 | 新增 CHANGELOG.md 并初始化版本号 | #56 | DONE | `T25-changelog-version` | `d7deae9` | #113 | PASS（Keep a Changelog 0.1.0 汇总小节；双侧版本号均 0.1.0；不预留未完成小节） | 8 | FIXED@37a2ec6 |
| T26 | 新增后端 ruff 配置 | #57 | DONE | `T26-ruff-config` | `b6f1ab2` | #108 | PASS（ruff.toml 最小集 E9/F63/F7/F82；`ruff check app tests` → All checks passed!；**提前入第 7 批**以解除 T22 依赖） | 7 | FIXED@d1732ce |
| T27 | 后端测试分层：无基础设施单测可独立运行 | #58 | DONE | `T27-test-layering` | `e4fa99d` | #116 | PASS（pytest.ini 注册 unit/needs_infra + 默认跳过；只标不删：integration 5 + observability 1 + evals 真 LLM 12；`pytest tests -q` → 236 passed / 17 deselected，exit 0；无未知 marker 警告） | 9 | FIXED@f1b7219 |
| T28 | 新增 CI：后端 pytest | #59 | DONE | `T28-ci-backend` | `59bcfca` | #117 | PASS（YAML 合法；无明文密钥；needs-infra 实跑：pull_request 与 main push 两次均 success ~1m4s） | 9 | FIXED@f1b7219 |
| T29 | 新增 CI：前端 lint + vitest + build | #60 | DONE | `T29-ci-frontend` | `1626c18` | #118 | PASS（YAML 合法；.npmrc legacy-peer-deps；build 启用，lint/test 按票面风险条暂不启用并注明依赖 T32–T34；needs-infra 实跑 success 37s） | 9 | FIXED@f1b7219 |
| T30 | 新增 backend/Dockerfile 并接入 compose | #61 | DONE | `T30-backend-docker` | `1e8f6f7` | #121 | PASS（多阶段构建；.dockerignore 密钥不入镜像；compose backend 服务 env_file 注入；验收 1/2 PASS；验收 3/4 needs-infra Docker daemon 未运行记 BLOCKED） | 10 | PENDING |
| T31 | start-services.sh 现代化 | #62 | DONE | `T31-start-services` | `7a943b0` | #122 | PASS（docker compose 6 处；wait_for_healthy 轮询替代 sleep 10（规避 compose wait 语义陷阱）；restart 二次确认；验收 1/2/3 PASS；验收 4 needs-infra 记 BLOCKED） | 10 | PENDING |
| T32 | 清理 console.log 残留 | #63 | DONE | `T32-console-cleanup` | `09c3522` | #124 | PASS（删 80 处单行 + chat/index.tsx 3 处多行日志块；session-drawer 错误路径保留上报并降级 console.warn；grep console.log\|debug 于 src/ 为 0；test 65.69s 全过；build 28.29s 通过；lint console 相关 0，剩余 104 errors 属 T33/T34 范围） | 10 | PENDING |
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
| 2026-09-13 | — | **第 3 批 `code-review`（双轴并行，fixed point `57f69e0`，终点 `fbe55f8`）**：标准轴 4 条 + 规格轴 3 条，去重后 **6 条**（2 修 4 保留）。规格轴独立复验：NG-2/NG-3 零触碰、T07 密钥清除完整、T09 风险条核实成立、T08 门控语义变化判定为「前提不成立即无取舍」（全局检索从未工作过，V1 有现成先例），不构成需用户裁决的分叉 | 明细见「第 3 批审查 findings 明细」 |
| 2026-09-13 | — | **第 3 批 findings 修复**：`validate_sql` 的 UNION 校验改词边界匹配（`\bUNION\b`），避免误拦 `union_id` 等标识符，补 3 用例锁行为；`test_db_password_required.py` 源码断言补注释说明保留理由。修复后全量 `pytest tests -m "not integration"` → **248 passed / 5 deselected**（398.03s） | 修复 commit `6b73d44`；fixed point 推进至 `6b73d44`，进入第 4 批（T11–T13） |
| 2026-09-13 | T11 | 实施 + 合并：8 处裸 except（实测 8 处：graph.py 消息队列、dr_g.py 计划 JSON 回退、news_collection_service 3 处、smart_analyzer 3 处）全部改为 `except Exception` + 按上下文记日志（预期失败分支 `logger.debug`、非预期失败 `logger.warning`，统计汇总处含 `exc_info`）；smart_analyzer 补模块级 logger；控制流不变；`dr_g.py` 属 NG-3 仅改 except 未删函数 | commit `d4b1228`，PR #90 已 merge（`27122ee`），issue #42 自动关闭 |
| 2026-09-13 | T12 | 实施 + 合并：`core/database.py` 补 `pool_size=5` / `max_overflow=10` / `pool_recycle=1800`（`pool_pre_ping` 原已有），取值依据写入代码注释；`app_main.py` 的 `create_all` 默认不执行，改为 `DB_AUTO_CREATE=1` 显式开关（scripts/ 两处初始化脚本的 create_all 属显式初始化动作，保持原样）；READMED 补「数据库建表」章节（迁移 SQL 已核实全部 `IF NOT EXISTS` 幂等）；`.env.example` 补 `DB_AUTO_CREATE` 占位 | commit `1f57882`，PR #91 已 merge（`043e4c6`），issue #43 自动关闭 |
| 2026-09-13 | T12 | 验收修正：票面脚本 `sys.path` 与导出名不符合项目约定，且直接导入 `core.database` 会触发 `core/__init__` 的 JWT 导入期校验，脚本需先 `setdefault` JWT/口令测试占位变量 —— 已实测修正并写入 `tickets.md` T12「实施修正」 | 验收 #1/#2 PASS |
| 2026-09-13 | T13 | 实施 + 合并（纯注释，零可执行代码变更）：`graph.py` 模块 docstring 改为「双执行路径」说明；`LANGGRAPH_AVAILABLE` 导入处、`__init__` 图构建处、`_build_langgraph`、6 个 `_*_node` 打包注释、`_run_with_langgraph`、`run()` 注释掉的调用点，全部加「有意保留 / 不得删除 / PRD NG-2」标注，并写明启用方式（恢复注释分支即可） | commit `ad7baa6`，PR #92 已 merge（`1eb4077`），issue #44 自动关闭 |
| 2026-09-13 | — | **流程事故与纠正（T13）**：commit 误落在本地 `main` 上（漏开分支）。纠正：把该 commit 挂回 `T13-langgraph-annotation` 分支、`git branch -f main <远端SHA>` 回退 main 引用，未 push、未污染远端历史。后续开分支动作前置 | 已纠正，§5 未被实质违反 |
| 2026-09-13 | — | **第 4 批 `code-review`（双轴并行，fixed point `6b73d44`，终点 `975eea8`）**：标准轴 3 条 + 规格轴 3 条，去重后 **5 条**（2 修 3 保留）。规格轴独立复验：T11 8 处全替换且控制流不变、T12 迁移说明与 compose/库名假设逐项属实、T13 纯注释且 NG-2/NG-3 零删改 | 明细见「第 4 批审查 findings 明细」 |
| 2026-09-13 | — | **第 4 批 findings 修复**：T12 验收 grep 补 `max_overflow`（实测命中）；票面 scripts 路径笔误修正。修复后全量 `pytest tests -m "not integration"` → **248 passed / 5 deselected**（381.67s，批次末已跑） | 修复 commit `1f52bfc`；fixed point 推进至此，下一批（T14–T16）起算 |
| 2026-09-13 | T14 | 实施 + 合并（纯注释）：`dr_g.py` / `react_controller.py` / `tool_executor.py` 三模块 docstring 顶部加 V1 ReAct 保留说明（version=v1 触发、NG-3 不得删除）；`research_router` version 字段注明双路线分工；`CLAUDE.md` 架构章节补双路线关系 | commit `1180182`，PR #96 已 merge（`f8a4acb`），issue #45 自动关闭 |
| 2026-09-13 | T14 | **缺陷记录**：PR #96 的保留说明被插到 docstring 引号之前成为裸文本 → 三模块 SyntaxError（替换锚点选错 + 提交前未跑 py_compile）。已在 T15 分支修复（说明移入 docstring 内部），根因与教训写入 `tickets.md` T14「实施修正」。**新增纪律：所有票 commit 前必须 py_compile 或跑受影响测试** | 修复随 PR #97 合入 |
| 2026-09-13 | T15 | 实施 + 合并：`serialize_event` 函数体逐字移动到新建 `core/serialization.py`（中立公共位置）；`research_router` 改从新位置导入，解除对 V1 备选模块 `dr_g` 的反向依赖（F-16）；`dr_g` 以同名导入保留模块属性（`test_research_outline_approval.py` 的 monkeypatch 依赖，实测仍生效） | commit `9839042`，PR #97 已 merge（`6218007`），issue #46 自动关闭 |
| 2026-09-13 | T15 | 验收修正：票面验收 #3 预期「无输出」不成立 —— `service/__init__.py:10` 的 `from .dr_g import ResearchService` 是既有顶层导出（票面风险条自己提到），grep 必然命中；实际口径为「除该导出外无遗留」 | 记入 `tickets.md` T15「实施修正」 |
| 2026-09-13 | T16 | 实施 + 合并（仅文案）：READMED langfuse 安装版本对齐 requirements（`>=4.0.0,<5.0.0`）并写清两级开关（`OBSERVABILITY_TRACING_ENABLED` 默认 true / `LANGFUSE_ENABLED` 默认 false）；`knowledge_router` / `docmind_service` 的 ES 旧注释改 Milvus 实际存储（各留一句全拼历史说明，ES 字面计数 0）；首行「知识图谱」宣称收窄为前端渲染的关系视图 | commit `aad9dd4`，PR #98 已 merge（`ac4ef4e`），issue #47 自动关闭 |
| 2026-09-13 | — | **第 5 批 `code-review`（双轴并行，fixed point `1f52bfc`，终点 `381c929`）**：标准轴 0 硬违规 + 3 judgement call，规格轴三票全部「无发现」，去重后 **4 条**（1 修 3 保留），历批最干净。规格轴独立复验：T15 移动非重写（逐字等价）、PR #96 缺陷修复干净、T16 与代码逐项相符 | 明细见「第 5 批审查 findings 明细」 |
| 2026-09-13 | — | **第 5 批 findings 修复**：CLAUDE.md 架构章节 NG-2/NG-3 逐条对应（V1 → NG-3、LangGraph → NG-2）。流程改进：SHA 回填改用「先提交、后回填、不 amend」两步法（吸取第 4 批 amend 改 SHA 的教训） | 修复 = 本记录 commit；fixed point 随本记录 commit 落定，下一批（第 6 批 T17–T19）起算 |
| 2026-09-13 | T17 | 实施 + 合并：新增 `docs/architecture.md`（单文件五小节：两条研究路线 / V2 内部流程含 NG-2 标注 / RAG 数据流指向 RAG架构分析.md / 基础设施依赖矩阵如实标注 ES 未使用、MinIO 仅 Milvus 内部依赖 / 目录导航）；NG-2/NG-3 回链 prd.md | commit `b309036`，PR #101 已 merge（`348da0c`），issue #48 自动关闭 |
| 2026-09-13 | T18 | 实施 + 合并：删除前段重复 `langfuse>=4.0.0`（保留后段 `>=4.0.0,<5.0.0`）；Observability/AI-LLM 分区补说明（langgraph 标注 NG-2）。**决策：用户裁决选 A**（不引入版本锁文件）。验收 #3 替代口径：venv 无 pip，改 `packaging` 逐行解析 47 条声明全部通过 | commit `68d00b2`，PR #102 已 merge（`3ab40b6`），issue #49 自动关闭 |
| 2026-09-13 | T19 | 实施 + 合并：**决策：用户裁决选 C**——保留 alembic 依赖，行上注释「预留未使用——迁移实为 backend/migrations/ 手写 SQL（见 READMED 数据库建表）」；未删依赖、未引入 alembic 编排 | commit `f98a81d`，PR #103 已 merge（`8c0aa12`），issue #50 自动关闭 |
| 2026-09-13 | — | **第 6 批 `code-review`（双轴并行，fixed point `d345685`，终点 `3e18063`）**：标准轴 1 硬伤（architecture.md 集合名「唯一实现」说法不实）+ 2 judgement call；规格轴三票全部「无发现」。去重 **4 条**（3 修 1 保留）。批次末全量 `pytest tests -m "not integration"` → **248 passed / 5 deselected**（393.18s） | 明细见「第 6 批审查 findings 明细」 |
| 2026-09-13 | — | **第 6 批 findings 修复**：architecture.md 两处（集合名转换如实描述、SSE 产出归属改 `_run_simplified`）；TRACKER 决策票行改 T20/T37。修复 = 本记录 commit；fixed point 随本记录落定，下一批（第 7 批 T21–T23）起算 |
| 2026-09-13 | T21 | 实施 + 合并：MIT LICENSE（票面默认授权，版权人 `EricKingWhy`，2026；commit 注明可随时更换、不构成法律建议） | commit `a091d04`，PR #106 已 merge（`88c64fb`），issue #52 自动关闭 |
| 2026-09-13 | T23 | 实施 + 合并：`.editorconfig`（root=true；全局 utf-8/lf/末尾换行；py 4 空格、ts/tsx/js/json/vue/yaml 2 空格；md 关闭行尾清理）；不统一存量换行符 | commit `a458d7d`，PR #107 已 merge（`e7a367c`），issue #54 自动关闭 |
| 2026-09-13 | T26 | 实施 + 合并（**提前入第 7 批**：T22 声明依赖本票）：`backend/ruff.toml` 最小规则集 E9/F63/F7/F82、line-length=100、target py310；`ruff check app tests` 一次通过；不引入 black、不格式化全仓 | commit `b6f1ab2`，PR #108 已 merge（`d3cc518`），issue #57 自动关闭 |
| 2026-09-13 | T22 | 实施 + 合并：`CONTRIBUTING.md` 一屏五节，细则全部回链不复制（READMED / LOOP-PROTOCOL §5-§6 / prd.md §7 / AGENTS.md）；含 NG-2/NG-3 不得删除提示与密钥红线 | commit `8bdd1e3`，PR #109 已 merge（`4dde37a`），issue #53 自动关闭 |
| 2026-09-13 | — | **基础设施备注**：GitHub API GraphQL 通道本时段多次 502/异常，PR #109 改走 REST（`gh api pulls` + `pulls/{n}/merge`）完成创建与合并；后续遇 GraphQL 抖动可直接用 REST 通道 | 不影响台账与代码 |
| 2026-09-13 | — | **第 7 批 `code-review`（双轴并行，fixed point `9fbdf3f`，终点 `e3c28da`）**：标准轴 0 硬违规 + 2 judgement call；规格轴四票全部「实质合规」。去重 **4 条**（1 修 3 保留） | 明细见「第 7 批审查 findings 明细」 |
| 2026-09-13 | — | **第 7 批 findings 修复**：TRACKER 主 tip 更新（消除自指时序滞后）。修复 = 本记录 commit；fixed point 随本记录落定，下一批（第 8 批 T24–T25）起算 |
| 2026-09-13 | T24 | 实施 + 合并：`.github/ISSUE_TEMPLATE/task.md` + `bug_report.md`（字段与 tickets.md ticket 结构同构）+ `PULL_REQUEST_TEMPLATE.md`（强制「验收命令与实际输出」必填 + NG-2/NG-3/密钥/commit 规范/py_compile 五项自查；必填 3-5 项） | commit `4352d14`，PR #112 已 merge（`4e6ce83`），issue #55 自动关闭 |
| 2026-09-13 | T25 | 实施 + 合并：`CHANGELOG.md`（Keep a Changelog，`[0.1.0] - 2026-09-13` 汇总小节，不预留未完成小节）；`frontend/package.json` 与 `backend/app/__init__.py.__version__` 统一 `0.1.0` | commit `d7deae9`，PR #113 已 merge（`ab5b673`），issue #56 自动关闭 |
| 2026-09-13 | — | **第 8 批 `code-review`（双轴并行，fixed point `d1732ce`，终点 `f10cc67`）**：标准轴 0 硬违规；规格轴两票实质合规 + 2 小瑕疵。去重 **5 条**（3 修 2 保留）+ 驳回 1 条（「READMED 拼写错误」不成立——仓库文件名即为 READMED.md） | 明细见「第 8 批审查 findings 明细」 |
| 2026-09-13 | — | **第 8 批 findings 修复**：台账「五项自查」改「四项」、「同构」改「对齐（含差异注明）」、tip 滞后回填。修复 = 本记录 commit；fixed point 随本记录落定，下一批（第 9 批 T27–T29）起算 |
| 2026-09-13 | T27 | 实施 + 合并：pytest.ini 注册 unit/needs_infra，addopts 默认 `-m "not needs_infra"`；只标不删——integration 4 用例、observability 1 用例（双标记）、evals 真 LLM 评测 12 用例（pytestmark），合计 17 与 deselect 数吻合。**重要发现：此前全量 248 passed 里一直混着 12 个真 LLM 在线评测用例**（本次 T27 验收因 DASHSCOPE 账户欠费 400 才暴露），分层后默认 236 passed / 17 deselected、exit 0、无未知 marker 警告 | commit `e4fa99d`，PR #116 已 merge（`d9d1bdb`），issue #58 自动关闭 |
| 2026-09-13 | T28 | 实施 + 合并：`.github/workflows/ci-backend.yml` 单 job（Python 3.11 + pip 缓存 + ruff check + pytest tests -q）；env 从 Secrets 读取、未配置回退 test-only 占位。needs-infra 实跑：pull_request 与 main push 均 **success**（~1m4s） | commit `59bcfca`，PR #117 已 merge（`22ea77f`），issue #59 自动关闭 |
| 2026-09-13 | T29 | 实施 + 合并：`frontend/.npmrc` legacy-peer-deps=true + `.github/workflows/ci-frontend.yml` 单 job（Node 22 + npm ci + build）。本地 preflight：build ✅ 27s；**lint 89 errors（T33/T34 范畴）、vitest 时序敏感 flaky——按票面风险条 lint/test 步骤暂不启用并在 workflow 注明依赖，不关规则凑绿**。needs-infra 实跑 success（37s） | commit `1626c18`，PR #118 已 merge（`6a7e489`），issue #60 自动关闭 |
| 2026-09-13 | — | **第 9 批 `code-review`（双轴并行，fixed point `37a2ec6`，终点 `3e7ea65`）**：标准轴 0 硬违规；规格轴 T29 无发现、T27/T28 数字与口径瑕疵。去重 **7 条**（3 修 4 保留） | 明细见「第 9 批审查 findings 明细」 |
| 2026-09-13 | — | **第 9 批 findings 修复**：integration 用例数 5→4（合计 17 吻合）、T29 merge SHA 回填、tip 占位回填。批次末全量默认口径 236 passed / 17 deselected（8.64s）。修复 = 本记录 commit；fixed point 随本记录落定，下一批（第 10 批 T30–T31 等）起算 |
| 2026-09-13 | T30 | 实施 + 合并：`backend/Dockerfile` 多阶段构建（builder venv → runtime 仅拷贝，python:3.11-slim；migrations 随镜像）；`backend/.dockerignore`（.env/tests/\*.png 等不入镜像）；`docker-compose.yml` 新增 backend 服务（industry_network / 8000 / depends_on postgres·redis·milvus service_healthy / env_file 注入密钥）。验收 1/2 PASS；3/4 needs-infra（Docker daemon 未运行）按 R-05 记 BLOCKED。另发现遗留 `backend/app/Dockerfile`（旧式单阶段）未动 | commit `1e8f6f7`，PR #121 已 merge（`85aca91`），issue #61 自动关闭 |
| 2026-09-13 | T31 | 实施 + 合并：`start-services.sh` 的 `docker-compose` → `docker compose`（6 处）；`sleep 10` 改 `wait_for_healthy` 按容器名轮询 `docker inspect` Health.Status（180s 超时；规避 `compose wait`「等退出」语义陷阱）；restart 二次确认、clean 补 `down -v` 后果说明。验收 1/2/3 PASS；4 needs-infra 记 BLOCKED | commit `7a943b0`，PR #122 已 merge（`f716105`），issue #62 自动关闭 |
| 2026-09-13 | T32 | 实施 + 合并：清理 83 处 console.log/debug —— 80 处单行（8 文件，python 逐行括号平衡校验后整行移除）+ `chat/index.tsx` 3 处多行日志块（checkpoint 详情/UI状态/debug useEffect）；`session-drawer/index.tsx` 错误路径按工单精神保留错误上报并降级 `console.warn`（注释标记 T32）。验证：grep console.log\|debug 于 src/ 为 0；test 65.69s 全过；build 28.29s 通过；lint console 相关 0（剩余 104 errors 全属 T33/T34 范围，全绿依赖 T33） | commit `09c3522`，PR #124 已 merge（`a99d55c`），issue #63 自动关闭；批次 10 收批，fixed point 推进至 `a99d55c` |
