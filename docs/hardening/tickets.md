# ticket 定义（source of truth）

> 本文件是 ticket 的**权威定义**，GitHub issue 是它的镜像。两者不一致时以本文件为准。
> 执行流程见 [`LOOP-PROTOCOL.md`](LOOP-PROTOCOL.md)，需求与非目标见 [`prd.md`](prd.md)。
> 进度见 [`TRACKER.md`](TRACKER.md)。

## 通用约定

- **文件路径**均相对仓库根目录。
- **「最小改法」是硬约束**：优先复用仓库已有实现与标准库，不引入新依赖，不新增抽象层。
- **验收**必须可执行。禁止「人工检查」。
- **标记含义**：`needs-infra`＝验收需容器；`needs-human`＝需用户本人在第三方后台操作；`needs-decision`＝需用户裁决后才执行（不进入自动循环）。
- **禁止触碰**：`prd.md` §2.2 的 NG-2 / NG-3 所列实现。

---

# 阶段 1 · 安全（P0）

## T01 — 移除 dr_g.py 硬编码 API Key

- **类型**：security　**阶段**：1　**依赖**：无　**标记**：无

### 背景

`backend/app/service/dr_g.py:29-30` 使用 `os.getenv(..., "<真实密钥>")` 的写法：环境变量缺失时会**静默回退到硬编码的真实密钥**，导致密钥随源码进入公开仓库（事实 F-01）。

只要兜底值存在，任何一次「本地忘了配 .env」的运行都会继续使用这批密钥，且无法通过删除提交历史根治（用户已决定暂不吊销，见 NG-4 / R-01）。

**执行期范围扩张（2026-09-13 记录）**：按「修根因不修症状」原则对全仓做同类扫描后，发现同一缺陷还有 3 处真实凭据，上一轮审计因正则只匹配 `sk-` 前缀而漏检：

| 位置 | 泄露内容 |
|------|---------|
| `backend/app/service/config.py:20` | RAGFlow `api_key` |
| `backend/app/service/config.py:21` | RAGFlow `default_dataset_id` |
| `backend/app/service/config.py:22` | Serper `api_key`（40 位十六进制） |

三者与其他泄漏点属于**同一类缺陷**，合并到本票一次修净；拆票会留下仍在公开仓库中的有效凭据。

同时发现一处**潜在真实 bug**：`dr_g.py` 的 `SEARCH_API_KEY` 默认值内嵌了 `"Bearer "` 前缀，而其余代码（`scout.py:1080`、`news_collection_service.py:62`、`document_service.py:20`）的统一约定是**环境变量存裸密钥、调用处拼前缀**。本地 `.env` 正是按裸密钥存放，因此 `websearch()` 发出的 `Authorization` 头**缺少 Bearer 前缀**，属鉴权格式错误。本票一并修正。

**不在本票范围**：`backend/app/core/database.py:14` 的 `POSTGRES_PASSWORD` 默认值 `postgres123`。它是「弱口令」缺陷，与 T07 的主题同类，且改为导入期必填会影响测试收集，归 T07 处理。

### 改什么

1. `dr_g.py`：删除 `SEARCH_API_KEY` / `LLM_API_KEY` 两个模块常量，改为 `get_search_api_key()` / `get_llm_api_key()` 访问器；缺失即抛 `RuntimeError`。
2. `dr_g.py`：`websearch()` 与 `qwen_llm()` 两个**模块级函数**改为调用访问器（它们无法访问实例属性），并为 `Authorization` 补上 `Bearer ` 前缀。
3. `dr_g.py` 构造函数：`search_api_key or get_search_api_key()`，保持「显式传入优先」的既有语义。
4. `config.py`：`api_key` / `default_dataset_id` / `serper_api_key` 的默认值改为空字符串。
5. `document_service.py`：`DocumentService.__init__` 在 `api_key` 为空时显式抛 `ValueError` 并指出变量名（避免退化为含义不明的 401）。
6. `backend/.env.example`：补充 `API_BASE_URL` / `API_KEY` / `DEFAULT_DATASET_ID` 三项，并为 `BOCHA_API_KEY` 注明「只填裸密钥，不带 Bearer 前缀」。
7. 新增 `backend/tests/service/test_dr_g_config.py` 回归测试。

### 最小改法

- 用模块级访问器函数，**不要**新建配置类 / 配置框架 —— 只涉及 2 个密钥。
- `LLM_BASE_URL` 的默认值是公开地址，保留不动。
- 消费方 `chat_router.py:22-33`、`document_router.py:26-30` 都在**请求期依赖函数内**读取配置（非导入期），因此移除默认值不影响应用启动 —— 已核实。
- 密钥读取一律 `os.environ`，**不留任何默认值兜底**。

### 验收

```bash
# 1) 静态断言：相关文件不再出现密钥/凭据字面量
cd backend && ! grep -nE 'sk-[A-Za-z0-9]{16,}|ragflow-[A-Za-z0-9]{10,}' \
  app/service/dr_g.py app/service/config.py app/service/document_service.py

# 2) 全仓凭据命中数归零
git grep -nE 'sk-[A-Za-z0-9]{20,}' -- . ':!frontend/node_modules' | wc -l   # 期望 0
git grep -nE 'ragflow-[A-Za-z0-9]{10,}' | wc -l                            # 期望 0

# 3) 行为回归测试（pytest 形式，CI 使用）
cd backend && .venv/Scripts/python.exe -m pytest tests/service/test_dr_g_config.py -v

# 4) Bearer 前缀专项
cd backend && .venv/Scripts/python.exe -m pytest tests/service/test_dr_g_config.py -k bearer -v
```

预期：命令 1/2 无输出；命令 3/4 全部通过（含 `test_missing_env_raises_runtime_error`、
`test_websearch_prefixes_bearer` 等）。

**3.5) 无 pytest 环境下的等价验收**（本机 venv 未就绪时使用，见 `LOOP-PROTOCOL.md` §11）：

用 `importlib.util.spec_from_file_location` 直接加载 `app/service/dr_g.py`，绕过包
`__init__` 的重依赖链，用任一具备 `requests` / `openai` 的解释器执行等价行为断言：
缺变量抛 `RuntimeError` 且信息含变量名、配置后可原样读取、模块不再导出旧常量。

**本票实际执行结果：4 项全 PASS。** 命令 3/4 的 pytest 形式化运行因 venv 依赖未就绪，
记为待办 **P-02**（`TRACKER.md`），**未伪造 PASS**。

### 风险

- **不要**因为「缺变量会报错」而重新引入兜底值 —— 那等于撤销本票。
- `backend/app/service/__init__.py:10` 也 import 了 `dr_g`，检查链路是否受影响。
- **R-01 依然未闭合**：本票只阻止后续泄露，已进入 `ccbb38a` 提交历史的 5 个凭据仍可被任何人读到，服务商侧的吊销需用户本人操作。


---

## T02 — JWT 密钥必填并在启动时校验

- **类型**：security　**阶段**：1　**依赖**：无　**标记**：无

### 背景

`backend/app/core/security.py:13` 的 `JWT_SECRET_KEY` 默认值是 `"your-super-secret-key-change-in-production"`（事实 F-06）。若生产环境未覆盖该变量，任何人都能用公开可知的密钥伪造合法 Token。

### 改什么

1. `JWT_SECRET_KEY` 无默认值；未配置时在**应用启动阶段**就报错并终止，而不是等到第一次签发 Token 才暴露。
2. 增加最短长度校验（建议 ≥ 32 字符），拒绝弱值。
3. **（实施补充）** 历史默认值本身有 43 个字符，**仅靠长度校验拦不住**，因此额外维护一份
   「公开已知弱值」拒绝名单。实施时实测发现本机 `backend/.env` 正是沿用了该默认值 ——
   也就是说这是一处**真实存在的漏洞**，而非理论风险（已随本票轮换为强随机值，见下）。

### 最小改法

- 在 `security.py` 读取 `os.environ["JWT_SECRET_KEY"]`，缺失或长度不足时抛 `RuntimeError`。
- 增加 `KNOWN_WEAK_SECRET_KEYS` 名单，命中历史默认值时同样拒绝（长度校验的漏洞补丁）。
- 在 `app_main.py` 的应用启动逻辑中触发一次该校验（import 或显式调用皆可），确保「启动即失败」。
- **不要**引入 `pydantic-settings` 等配置框架 —— 单个变量不值得。
- 同步更新 `backend/.env.example`，把占位符改成明确的强随机示例说明（如 `# 生成方式: python -c "import secrets;print(secrets.token_urlsafe(48))"`），并把示例值留空。
- **附带操作（不进版本库）**：轮换本机 `backend/.env` 中沿用的历史默认值；`.env` 已 gitignore，备份写入 `.runlogs/`。

### 验收

```bash
# 1) 缺变量时启动失败
cd backend && env -u JWT_SECRET_KEY python -c "
import sys; sys.path.insert(0,'.')
from app.core import security
" 2>&1 | grep -q "JWT_SECRET_KEY" && echo "OK: 缺变量被拒绝"

# 2) 弱值被拒绝
cd backend && JWT_SECRET_KEY=short python -c "
import sys; sys.path.insert(0,'.')
from app.core import security
" 2>&1 | grep -qiE "长度|弱|too short" && echo "OK: 弱值被拒绝"

# 3) 强值可正常导入
cd backend && JWT_SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(48))") python -c "
import sys; sys.path.insert(0,'.')
from app.core import security
print('OK: 强值通过')
"
```

预期：三行 `OK` 全部打印。

### 风险

- 本票会让**未配置 `.env` 的本地环境无法启动** —— 这是预期行为，需在 commit message 中写明。
- 检查 `backend/tests/` 中是否有依赖旧默认值的用例，若有需同步更新（属于本票范围）。

---

## T03 — document_router 上传安全加固

- **类型**：security　**阶段**：1　**依赖**：无　**标记**：无

### 背景

`backend/app/router/document_router.py:66` 使用 `f"/tmp/{file.filename}"` 落盘（事实 F-02）。上传文件名由客户端完全控制，`../../` 形式可写出 `/tmp` 之外；同时该接口无大小与类型限制。

### 改什么

1. 落盘文件名改为服务端生成（UUID + 规范化后的扩展名），**不使用**客户端提供的文件名作为路径。
2. 增加扩展名白名单（与 `attachment_router.py:148` 的既有做法保持一致）。
3. 增加单文件大小上限，超限返回 4xx 并给出可读错误。
4. 原始文件名若需保留（入库展示用），仅作为**数据字段**存入数据库，不作为文件路径。

### 最小改法

- 复用 `attachment_router.py:148` 的 **uuid 命名思路**，**不要**新写一套生成逻辑。
- **⚠️ 但不要照抄它的拼接方式**：该处是 `f"{uuid.uuid4()}_{file.filename}"`，
  仍然把**客户端文件名**放进了路径 —— `os.path.join(UPLOAD_DIR, "uuid_../../x")` 依旧可以穿越出去。
  本票的正确形式是 `<uuid><规范化扩展名>`，客户端文件名**一个字符都不进路径**。
- 扩展名白名单沿用项目已支持的文档类型集合，不要发明新格式。
- 大小上限取一个常量即可，不必做成可配置项。
- 纯逻辑（净化 / 白名单 / 限长读取）抽到 `core/upload_security.py`，使 CI 无需基础设施即可验证。

### 验收

```bash
# 1) 路径穿越被净化
#    注意：`app/core/__init__.py` 会连带导入 security，自 T02 起**必须提供 JWT_SECRET_KEY** 才能导入。
cd backend && JWT_SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(48))") python - <<'PY'
import sys; sys.path.insert(0, 'app')
from core.upload_security import safe_filename as fn
for bad in ["../../etc/passwd", "..\\..\\win.ini", "a/b/c.txt"]:
    out = fn(bad)
    assert "/" not in out and "\\" not in out and ".." not in out, f"未净化: {bad} -> {out}"
print("OK: 路径穿越被净化")
PY

# 2) 类型白名单 / 大小上限 / 边界（21 用例，不依赖基础设施）
#    由 (2) 覆盖「非法扩展名被拒绝」与「大文件返回 413」两项
cd backend && pytest tests/router/test_document_upload.py -q -k document_upload
```

预期：打印 `OK: 路径穿越被净化`，`pytest` 全绿。

> **⚠️ 实施修正（2026-09-13，已实测）**
>
> 1. 原验收写的 `from app.router import document_router` **实际不可执行**：该路由会连带引入
>    milvus / ES / docmind（实测缺 `tinytag` 即失败），不满足「无基础设施即可验证」。
>    故把纯逻辑抽到 `core/upload_security.py`（本票允许的必要重构），验收改为直接测该模块。
> 2. 原 `sys.path.insert(0, '.')` 解析不到 `service` / `core`：项目约定是 **`backend/app` 进
>    `sys.path`**（见 `tests/conftest.py`），已修正为 `insert(0, 'app')`。
> 3. `pytest tests -q -k document_upload` 会被**其它无关测试模块**的收集错误中断
>    （10 个 collection error，属 T27「测试分层」的范畴），故验收改为指定具体文件路径。

### 风险

- 若难以为路由抽出纯函数，可先把净化逻辑提成模块级函数（**这是本票允许的必要重构**），再测该函数。
- 不要改动 `/tmp` 作为存储位置的既有决定（另有 ticket 关注存储策略，本期不做）。

---

## T04 — document_router 增加鉴权

- **类型**：security　**阶段**：1　**依赖**：无　**标记**：无

### 背景

`backend/app/router/document_router.py` 全文件无鉴权依赖（事实 F-03），任何未登录请求都能调用文档上传与检索接口。

### 改什么

1. 为该路由下所有**写操作与检索类**端点补 `Depends(get_current_user_required)`。
2. 若存在确实需要匿名的健康检查类端点，保持匿名并在代码中注明理由。

### 最小改法

- 复用 `backend/app/router/research_router.py:144` 的既有写法：`current_user: User = Depends(get_current_user_required)`。
- 可在 router 级别通过 `dependencies=[...]` 一次性挂载，避免逐端点重复。**注意**：需先确认该路由下所有端点都应鉴权，否则逐个挂更安全。
- **不要**自建鉴权中间件。

### 验收

```bash
# 1) 未带 Token 请求被拒（真实请求 → 401）
# 注：T04 时本命令为 `-k document_auth`（当时 10 passed）；第 2 批审查把该测试文件
# 并入 tests/router/test_router_auth.py 后，改为下述命令（document 路由含在其中）。
cd backend && pytest tests -q -k router_auth

# 2) 全文件鉴权依赖计数 > 0
cd backend && grep -c "get_current_user_required\|get_current_user" app/router/document_router.py

# 3) 前端调用链已注入 Token（见风险 R-02）
grep -rn "auth" frontend/src/api/request/plugins/auth.ts | head
```

预期：`pytest` 全绿（10 passed）；计数 = 2；前端统一注入存在。

> **⚠️ 实施修正（2026-09-13，已实测）**
>
> 1. **原验收 #3 的路径不存在**：`frontend/src/api/request/auth.ts` 在仓库中查无此文件。
>    真实的统一注入点是 `frontend/src/api/request/plugins/auth.ts`，已修正路径。该文件是
>    **无条件的 axios 请求拦截器**（无 URL 白名单），命中即写入 `Authorization: Bearer <token>`，
>    因此覆盖 `/documents` 链路。
> 2. **R-02 结论：该链路前端无调用方。** 全仓搜索 `documents/upload|list|delete|retrieve`，
>    前端源码命中 **0 处**（前端知识库走 `/knowledge-bases/...`，属另一路由）。因此本票
>    **不需要改前端**。真正的「既有匿名调用方」是两处文档示例：
>    `backend/README.md` 与 `READMED.md` 的 `/documents/upload` curl 示例，已补
>    `Authorization: Bearer <你的Token>` 头，避免文档里的命令在改动后失效。
> 3. **router 级挂依赖的安全性已确认**：该文件共 4 个端点
>    （`/upload`、`/list`、`/delete`、`/retrieve`），**全部为文档数据操作，无匿名 / 健康检查端点**，
>    故 router 级挂载不会误伤任何应当匿名访问的接口。
> 4. **测试基建修正（后续所有 router 类测试共用，含 T05）**：
>    - `tests/conftest.py` 的 `service` 占位包原先不含顶层名字，导致
>      `from service import DocumentService, ServiceConfig` 在**收集期** `ImportError`。
>      已改为按需从轻量子模块（`service.config` / `service.document_service`）取名字挂到占位包上，
>      仍**不执行** `service/__init__.py` 的重型链。
>    - `service.docmind_service` 实测导入耗时约 **48s**（拉起 docmind / llama-index），
>      已在 conftest 注入轻量替身；替身**故意抛 `NotImplementedError`** 而非伪造成功，
>      以防真实解析调用被静默吞掉。
>    - 不能把 `APIRouter` 直接交给 `TestClient`（FastAPI 0.141 会报
>      `AssertionError: fastapi_middleware_astack not found`），测试改为用**最小 `FastAPI` 应用**
>      挂载被测 router。该写法不引入 DB / Redis 依赖。
> 5. **第 2 批审查后的调整（2026-09-13）**：T04 的 `tests/router/test_document_auth.py`
>    与 T05 新增的 `tests/router/test_router_auth.py` 是同一套断言的两次实现（审查发现
>    「重复代码」）。已把 document 路由并入后者的 `ROUTER_MODULES` 参数表并删除原文件；
>    同时把「源码字符串匹配」断言换成结构化断言
>    `APIRouter.dependencies`（`Depends.dependency`），不再受代码格式化影响。
>    历史事实保留：T04 当时的 `pytest -k document_auth` 确为 **10 passed**。

### 风险

- **R-02**：前端若未对这条链路注入 `Authorization`，鉴权后会 401。必须在同一 ticket 内核查 `frontend/src/api/request/auth.ts` 的统一注入覆盖到该接口，覆盖不到就在本票内补齐。
- 若存在既有的匿名调用方（如脚本、定时任务）会受影响，需在 commit message 中列出。

---

## T05 — chat / search / news 路由补充鉴权

- **类型**：security　**阶段**：1　**依赖**：T04　**标记**：无

### 背景

`chat_router.py`、`search_router.py`、`news_router.py` 三个路由均无鉴权依赖（事实 F-04），与 `research_router` 的鉴权现状不一致。

### 改什么

1. 逐端点确认是否应鉴权，默认**应鉴权**。
2. 对确需匿名的端点（如公开新闻列表）保留匿名，并在代码中写明理由。

### 最小改法

- 复制 T04 采用的同一模式，保持四个路由写法一致。
- 先跑一次端点清单（`grep -n "@router\." app/router/*.py`）再逐个决策，避免漏端点。

### 验收

```bash
# 1) 三个路由的鉴权依赖计数均 > 0（或匿名端点有显式注明）
cd backend && for f in chat_router search_router news_router; do
  echo -n "$f: "; grep -c "get_current_user" app/router/$f.py
done

# 2) 未授权访问回归测试
cd backend && pytest tests -q -k "auth or unauthorized"

# 3) 未授权端点的旁路检查
cd backend && grep -n "Depends(get_current_user" app/router/chat_router.py app/router/search_router.py app/router/news_router.py
```

预期：计数均 ≥ 1；测试全绿；grep 有命中。

> **⚠️ 实施修正（2026-09-13，已实测）**
>
> 1. **端点清单与实测**：三个路由共 **13 个端点**（chat 4 + search 1 + news 8），
>    全部未带 Token 时返回 `401 {"detail":"无法验证凭据"}`，即依赖解析先于 body 校验，
>    空 body 也会先被鉴权拦下。
> 2. **匿名端点判定：一个都没有，三个路由全部挂 router 级。** 判定依据是**实测前端无匿名调用方**：
>    - `frontend/src/router/routes.tsx` 里**只有 `/login` 是匿名的**：其余全部挂在 `/` 之下，
>      而该父路由被 `AuthGuard` 包裹（未登录即 `Navigate to="/login"`，
>      见 `components/auth-guard/index.tsx`）。注意 `/404` 虽然标了 `pure: true`，
>      但它作为 `routes` 数组成员同样处于 `AuthGuard` 子树内 —— 也受守卫。
>      `/chat`、`/news`、`/bidding` 自然也在受保护子树内。
>    - `/search/web` 在 `frontend/src` 中**命中 0 处**（也没有 `api/search.ts`）。
>    - 登录页只调用 `api.auth.login` / `api.auth.register`，不会在登录前触碰这三个路由。
>    - 仓库内无脚本 / 定时任务调用这三个路由（唯一命中是 `backend/README.md` 的两条 curl 示例）。
>    → 因此**不存在「公开落地页依赖匿名检索」的场景**，不构成风险条所述的架构分叉，无需停下问用户。
> 3. **`news_router` 端点数是 8 不是 9**（`/list`、`/bidding/list`、`/stats`、`/collect`、
>    `/scheduler/status`、`/check`、`/industries`、`/industries/{industry_id}`）。
>    其中 `/collect` 是**触发采集的写操作**、`/scheduler/status` 与 `/check` 是运维诊断，
>    本就最该鉴权，因此没有理由为「公开新闻列表」保留匿名。
> 4. **`backend/README.md` 的两条 curl 示例**（`/chat/session`、`/chat/completion`）已补
>    `Authorization: Bearer <你的Token>` 头，避免文档里的命令在改动后失效。
> 5. **conftest 扩展**：T05 的测试需要导入这三个路由，而它们还用到 `WebSearchService`、
>    `ChatService`、`SessionService` 这三个 `service` 顶层名字；已把 T04 的「按需挂顶层名字」
>    做法改为显式的 `_SERVICE_PUBLIC_NAMES` 映射，仍不执行重型 `service/__init__.py`。

### 风险

- 搜索接口若被前端公开落地页调用，加鉴权会影响未登录用户 —— 若存在该场景，**保留匿名并写明理由**，不要为了「统一」而破坏产品行为（属架构分叉，需停下来问用户）。

---

## T06 — 收紧 CORS 配置

- **类型**：security　**阶段**：1　**依赖**：无　**标记**：无

### 背景

`backend/app/app_main.py:83-89` 同时设置 `allow_origins=["*"]` 与 `allow_credentials=True`（事实 F-05）。该组合被浏览器规范禁止，`Access-Control-Allow-Origin` 不会返回 `*`，凭据请求实际失效；同时通配的来源在生产环境中是不可接受的。

### 改什么

1. 允许来源改为从环境变量读取的**显式白名单**（逗号分隔）。
2. 仅当来源为通配（开发模式）时，强制 `allow_credentials=False`，并在启动日志中给出警告。
3. 生产环境若来源列表为空，启动即失败（与 T02 同一风格）。

### 最小改法

- 在 `app_main.py` 内解析一个环境变量，按是否含 `*` 分两条分支构造参数，10 行以内。
- **不要**新建 CORS 配置模块。
- 同步在 `backend/.env.example` 增加该变量及注释。

### 验收

```bash
# 1) 通配 + credentials 的组合不再同时出现
cd backend && ! grep -Pzo 'allow_origins=\["\*"\][\s\S]{0,200}?allow_credentials=True' app/app_main.py

# 2) 断言逻辑：通配时 credentials 必为 False（纯逻辑，不依赖基础设施）
cd backend && python - <<'PY'
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location("cors", pathlib.Path("app/core/cors.py"))
cors = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cors)
assert cors.build_cors_kwargs("*")["allow_credentials"] is False
assert cors.build_cors_kwargs("https://a.com,https://b.com")["allow_origins"] == ["https://a.com", "https://b.com"]
print("OK: CORS 参数构造正确")
PY

# 2b) 回归测试（更完整：含「生产环境留空即启动失败」等用例）
cd backend && pytest tests/core/test_cors_config.py

# 3) .env.example 已列出变量
grep -n "CORS" backend/.env.example
```

预期：命令 1 无输出；命令 2 打印 `OK`（并输出一条通配警告）；命令 2b `14 passed`；命令 3 有命中。

> **⚠️ 实施修正（2026-09-13，已实测）**
>
> 1. **原验收 #2 实际不可执行**，已替换为上面的形式。两个原因：
>    ① `from app.app_main import build_cors_kwargs` 会连带导入**全部路由与数据库引擎**
>    （实测直接报 `ModuleNotFoundError: No module named 'observability'`，因为 `app_main`
>    假定 `backend/app` 在 `sys.path` 上）；
>    ② 即便换成 `from core.cors import ...`，也会触发 `core/__init__.py` → `core.security`
>    的导入期 JWT 校验，在没有 `.env` 的机器上直接 `RuntimeError`。
>    故改用 §11.3 记录的 `importlib` 按**文件路径**加载，绕过整条包导入链。
> 2. **偏离「不要新建 CORS 配置模块」的说明**：本票把纯函数放进 `app/core/cors.py`。
>    这不是新建「配置体系」，而是与本仓 `core/upload_security.py` 同一做法的**纯逻辑抽离**
>    （该文件同样为满足「无基础设施即可验证」而独立成模块，见 T03）。
>    `app_main.py` 侧的改动仍满足「10 行以内」——实际只有 2 行
>    （一行 import + 一行 `app.add_middleware(CORSMiddleware, **build_cors_kwargs())`）。
> 3. **R-03 已实测闭合：前端不依赖凭据，通配 + `credentials=False` 不影响本地联调。**
>    依据：`frontend/src` 全量搜索 `withCredentials` **命中 0 处**（axios 未开启凭据），
>    登录态走 `Authorization: Bearer` 头。因此开发环境退回 `*` 并禁用凭据后，
>    浏览器会正常返回 `Access-Control-Allow-Origin: *`，请求仍然放行。
>    **故不构成架构分叉，无需停下问用户。**
>    （另：`frontend/.env` 的 `VITE_API_BASE=http://localhost:8000/` 确为绝对地址，
>    跨域确实生效，所以这项核对是必要的而不是形式化。）
> 4. `.env.example` 中新增 `CORS_ALLOW_ORIGINS` 段并**留空**：非生产环境留空退回 `*`，
>    生产环境（`ENV=production`）留空则启动失败 —— 迫使生产部署显式给出白名单。

### 风险

- **R-03**：收紧后本地前端 :5183 → 后端 :8000 的跨域请求需靠「开发模式通配 + credentials=False」放行。若前端确实依赖 credentials，需改为显式白名单并带上 `http://localhost:5183`。若无法确定，属架构分叉 → 停下来问用户。

---

## T07 — docker-compose 明文口令改为环境变量注入

- **类型**：security　**阶段**：1　**依赖**：无　**标记**：无

### 背景

`docker-compose.yml:11` 的 `POSTGRES_PASSWORD: postgres123` 与 `:71-72` 的 MinIO `minioadmin/minioadmin` 明文写入受版本控制的文件（事实 F-07）。

**T01 执行期追加（2026-09-13）**：同一弱口令在应用侧还有第二处底座 —— `backend/app/core/database.py:14` 的 `POSTGRES_PASSWORD` 默认值同样是 `postgres123`。两处必须一起处理，否则应用会在 compose 未注入变量时静默回落到同一个弱口令。

### 改什么

1. `docker-compose.yml`：口令改为 `${POSTGRES_PASSWORD}` / `${MINIO_ROOT_USER}` / `${MINIO_ROOT_PASSWORD}` 形式。
2. 仓库根目录新增 `.env.example`（供 docker compose 读取），列出这些变量及生成说明。
3. `backend/app/core/database.py:14`：`POSTGRES_PASSWORD` 移除默认值，缺失时显式失败并指出变量名（与 T01 的访问器风格一致）。
4. 确认顶层 `.env` 已被 `.gitignore` 覆盖。

### 最小改法

- 只改口令类字段，**不要**顺手重排 compose 文件结构。
- 复用 `docker compose` 原生的 `.env` 读取能力，**不要**引入 `env_file` 之外的机制。
- `database.py` 的改动**必须**同步处理测试环境：`backend/tests/conftest.py` 需为 `POSTGRES_PASSWORD` 等提供测试安全值，否则无基础设施的单元测试会在导入阶段失败（与 T27 联动，属本票范围）。

### 验收

```bash
# 1) compose 中不再出现明文口令
! grep -nE "postgres123|minioadmin" docker-compose.yml

# 2) 应用侧不再有弱口令默认值
cd backend && ! grep -nE 'postgres123' app/core/database.py

# 3) 单元测试在无基础设施环境下不被本票破坏
#    注：原文写的 `backend/.venv/Scripts/python.exe` 是**损坏环境**（见协议 §11 与待办 P-01），
#    可用解释器为 C:/Users/王浩宇/.workbuddy/binaries/python/envs/deepsearch/Scripts/python.exe
cd backend && <可用venv>/Scripts/python.exe -m pytest tests -q -m "not integration"

# 4) 顶层 .env 已被忽略
git check-ignore -v .env && echo "OK: 顶层 .env 被忽略"

# 5) 示例文件已提供
grep -nE "POSTGRES_PASSWORD|MINIO_ROOT" .env.example

# 6) compose 配置可解析
docker compose config --quiet
```

预期：命令 1/2 无输出；命令 3 全绿；命令 4 打印 `OK`；命令 5 有命中；命令 6 在 Docker 可用时通过。

> **⚠️ 实施修正（2026-09-13，已实测）**
>
> 1. **执行期范围扩张（同类缺陷一次修净）**：按「修根因不修症状」做全仓扫描后，同一明文口令
>    另有 **4 处受版本控制的副本**，均并入本票 —— 拆票会留下仍在公开仓库里的弱口令
>    （与 T01 的处理原则一致）：
>
>    | 位置 | 内容 |
>    |------|------|
>    | `backend/docker-compose-base.yml:37-38` | MinIO `minioadmin/minioadmin`（**不在原 ticket 清单里**） |
>    | `backend/.env.example:59` | `POSTGRES_PASSWORD=postgres123` |
>    | `READMED.md`（6 处） | 文档正文直接给出 `postgres123` / `minioadmin` |
>    | `start-services.sh:62` | 启动完成提示打印 `admin/minioadmin` |
>
> 2. **必须同时改 Milvus 的 MinIO 凭据（原 ticket 未提）**：Milvus 需要凭据才能读写 MinIO，
>    而两个 compose 的 `milvus` 服务此前**没有设置**凭据，靠「MinIO 默认口令恰好也是
>    `minioadmin`」才连得上。只改 MinIO 不改 Milvus，会让轮换口令后的向量库**静默不可写**。
>    故在两个 compose 的 milvus 服务补 `MINIO_ACCESS_KEY_ID` / `MINIO_SECRET_ACCESS_KEY`，
>    与 minio 服务取同一组变量。
> 3. **变量名用 `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`**（ticket 指定）。原 compose 的
>    `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` 是 MinIO 的已废弃别名，现行镜像用 ROOT_* 命名。
> 4. **原验收 #3 的 venv 路径不可用**：`backend/.venv/Scripts/python.exe` 是损坏环境
>    （见协议 §11 与待办 P-01）。已改为可用解释器路径；并加 `-m "not integration"`，
>    因为全量跑必然含 1 条需真实 Postgres 的 `@pytest.mark.integration` 用例（见 P-10）。
> 5. **原文风险条需修正**：「旧卷仍可用（环境变量只影响新初始化）」**不完整** —— 卷确实保留
>    旧口令，但**应用/客户端**改用新口令后就连不上。正确做法是二选一：把 `.env` 填回旧口令，
>    或在容器内 `ALTER USER`／`docker compose down -v` 重建（**会丢数据**）。
>    该说明已写入根目录 `.env.example`、`backend/.env.example` 与 `READMED.md`。
> 6. **未改本机 `backend/.env`**：其中 `POSTGRES_PASSWORD` 仍是旧弱口令，与**既有数据卷匹配**。
>    轮换本机口令要动数据库卷，属破坏性操作，留给用户决定（见下方风险）。
> 7. **验收 #6 已实测通过**：`docker compose config --quiet` → `exit=0`（会打印
>    「POSTGRES_PASSWORD / MINIO_ROOT_* 未设置，默认为空串」的 warning，这正是有意的响亮失败）。
> 8. **未加「拒绝已知弱口令」的校验**（与 T02 的 `KNOWN_WEAK_SECRET_KEYS` 不同）：本票只要求
>    「移除默认值 + 缺失即失败」。若再加弱口令拒绝名单，会对用旧卷的存量环境造成额外破坏，
>    超出本票范围。

### 风险

- 已存在的本地数据卷使用旧口令初始化，改口令后**旧卷仍可用**（环境变量只影响新初始化）。需在 commit message 中写明这一点，避免误导。
- 若顶层 `.env` 未被忽略，属**安全缺陷**，必须在本票内补进 `.gitignore`。

---

# 阶段 2 · 正确性（P1）

## T08 — 修复 Scout 本地知识库检索的集合名不匹配

- **类型**：bug　**阶段**：2　**依赖**：无　**标记**：needs-infra

### 背景

`backend/app/service/deep_research_v2/agents/scout.py:1031` 硬编码 `collection_name="knowledge_base"`，但用户上传的文档入到 `kb_{知识库名}`（`knowledge_router.py:93`，见事实 F-08 与 `docs/RAG架构分析.md` 第二节）。

**后果**：DeepResearch 流程内的「本地知识库搜索」实际上搜不到任何用户上传的文档，这是一个用户可感知的功能缺陷。

### 改什么

将硬编码集合名改为按知识库检索。仓库已具备两种现成能力：

- **方案 A（推荐）**：改用 `retrieval_service.retrieve_content` / `retrieve_from_knowledge_base` —— 它们已经正确地使用 `kb_{name}`（见 `docs/RAG架构分析.md` 关键文件索引）。
- **方案 B**：遍历该用户的 `kb_*` 集合分别检索后合并排序。

### 最小改法

优先方案 A：Scout 不该自己拼集合名，**改用已经正确的现成服务**。这是最小且最不易回归的改法。

若 Scout 的调用上下文拿不到 `kb_name`（`service.py` 的 `research()` 已接收 `kb_name` 参数），把 `kb_name` 透传到 Scout，而不是在 Scout 内部猜。

**不要**新建检索服务、不要引入查询路由层。

### 验收

```bash
# 1) 不再存在硬编码的公共集合名
cd backend && ! grep -n '"knowledge_base"' app/service/deep_research_v2/agents/scout.py

# 2) 单元测试：Scout 使用 kb 前缀集合名（mock milvus_service，无需真实 Milvus）
cd backend && pytest tests/service/deep_research_v2 -q -k "local_search or collection"

# 3) needs-infra：端到端验证（需 Milvus + Postgres）
docker compose up -d milvus postgres
# 上传一个文档到知识库 kb_demo 后，发起 v2 研究并确认事件流中出现来自该文档的 chunk
```

预期：命令 1 无输出；命令 2 全绿；命令 3 在基础设施可用时确认命中。

### 风险

- **R-05**：命令 3 需要 Milvus + Postgres，Docker 未运行时该步记 `BLOCKED`，但命令 1、2 必须 PASS。**不得**因为端到端未跑就伪造 PASS。
- 若 Scout 支持「不指定知识库」的全局检索语义，改法需保留该语义 —— 此时遍历 `kb_*` 更稳妥。若两种语义的取舍不确定，属架构分叉 → 停下来问用户。

---

## T09 — 修复 text2sql SQL 校验可被 UNION SELECT 绕过

- **类型**：bug　**阶段**：2　**依赖**：无　**标记**：无

### 背景

`backend/app/service/text2sql_service.py:210-242` 用黑名单做校验：`FORBIDDEN` 含 `'UNION ALL SELECT'`，但 `UNION` 本身在 `ALLOWED` 中（事实 F-09）。因此 `SELECT ... UNION SELECT ...` 形式可通过校验。

### 改什么

1. 明确校验策略：**允许列表**（只放行 `SELECT` 起始的语句）优于黑名单。
2. 至少补齐 `UNION` 相关的绕过形式。
3. 校验逻辑保持为**纯函数**，便于单测（T39 会补测试）。

### 最小改法

- 在现有 `validate_sql` 内收紧：以「语句必须以 `SELECT` 或 `WITH` 开头」+「禁止出现 `UNION`」为主判据，黑名单降为辅助。
- **不要**引入 SQL 解析库 —— 本票是收紧校验，不是重写解析器。
- 顺带清理 `'--'` 与 `FORBIDDEN` 中的重复检查。

### 验收

```bash
# 1) 纯函数回归测试（本票必须新增，见 T39 可扩展）
cd backend && python - <<'PY'
import sys; sys.path.insert(0,'.')
from app.service.text2sql_service import validate_sql  # 按实际导出名替换
cases_bad = [
    "SELECT 1 UNION SELECT 2",
    "SELECT 1 UNION ALL SELECT 2",
    "SELECT * FROM t; DROP TABLE t",
    "DELETE FROM t",
    "UPDATE t SET a=1",
]
for sql in cases_bad:
    assert not validate_sql(sql), f"FAIL 未拦截: {sql}"
assert validate_sql("SELECT id, name FROM users WHERE id = 1"), "FAIL 误拦合法查询"
print("OK: UNION 绕过已封堵")
PY

# 2) 既有测试未回归
cd backend && pytest tests -q -k text2sql
```

预期：打印 `OK`；既有测试全绿。

### 风险

- 收紧后可能误拦前端已有能力（例如多表联合查询确实是产品需求）。若 `UNION` 是**有意支持**的查询形式，则本票目标应改为「用只读账号兜底（T10）」而非禁止 `UNION` —— 这属架构分叉，需停下来问用户。**先核实前端是否会生成含 `UNION` 的查询。**

### 实施修正（2026-09-13，T09 实测后）

1. **风险条已核实，不构成架构分叉**：`ALLOWED_KEYWORDS` 在全仓**无任何使用点**（死配置，`UNION` 在其中只是表面），text2sql 的 prompt 无任何鼓励 UNION / 联合查询的指引，前端 `frontend/src` 无 UNION 相关查询生成逻辑 → UNION 不是有意支持的能力，按主方案全禁。
2. **实施范围**：`validate_sql` 主判据改为「以 `SELECT` 或 `WITH` 开头 + 禁止任何形式的 `UNION`」（黑名单降为辅助）；`FORBIDDEN_KEYWORDS` 移除 `'--'`（专门的注释检查已覆盖，报错语义更明确）与 `'UNION ALL SELECT'`（被 UNION 全禁覆盖）；`ALLOWED_KEYWORDS` 同步移除 `'UNION'`（该列表本身仍未参与校验，整体清理不在本票范围）。
3. **验收 #1 的脚本需修正路径**：原脚本 `sys.path.insert(0,'.')` 假设 `from app.service...`，与项目约定（`backend/app` 在 `sys.path`，`from service.text2sql_service import ...`）不符；`validate_sql` 是 `Text2SQLService` 的实例方法而非模块级函数。实际执行改为 `sys.path.insert(0,'app')` + 实例化后调用，断言内容不变，输出 `OK: UNION 绕过已封堵`。

---

## T10 — text2sql 使用只读数据库账号兜底

- **类型**：bug　**阶段**：2　**依赖**：T09　**标记**：needs-human

### 背景

`backend/app/service/text2sql_service.py:386` 使用 `text(sql)` 直连数据库（事实 F-10）。应用层的 SQL 校验（T09）终究是**解析式防御**，任何一处漏判都会直接作用在主库上。

**唯一根治手段**：让 text2sql 使用一个只有 `SELECT` 权限的数据库账号，使得即使 SQL 校验被绕过，数据库层面也会拒绝写操作。

### 改什么

1. 新增只读数据库角色，仅授予目标表的 `SELECT` 权限。
2. text2sql 的引擎/会话使用该角色（独立连接串，从环境变量读取）。
3. `backend/.env.example` 增加对应变量。

### 最小改法

- 复用 `backend/app/core/database.py` 的引擎构造方式，只是换连接串；**不要**新建数据库抽象层。
- 若无法独立引擎，退一步：在 `execute_sql` 前设置 `SET TRANSACTION READ ONLY`，也可阻断写操作。优先做前者，后者作为备选。

### 验收

**需要用户完成后半部分（本票为 `needs-human`）：**

```bash
# 1) 用户在 Postgres 中执行（示例，实际库名/表名以部署为准）
#    CREATE ROLE text2sql_ro LOGIN PASSWORD '<强随机>';
#    GRANT CONNECT ON DATABASE <db> TO text2sql_ro;
#    GRANT USAGE ON SCHEMA public TO text2sql_ro;
#    GRANT SELECT ON ALL TABLES IN SCHEMA public TO text2sql_ro;

# 2) 验证只读角色无法写
psql "$TEXT2SQL_DATABASE_URL" -c "CREATE TABLE _probe(x int);"
#    预期：ERROR: permission denied for schema public

# 3) 验证只读角色可读
psql "$TEXT2SQL_DATABASE_URL" -c "SELECT 1;"
#    预期：成功

# 4) 应用侧使用只读连接串
grep -n "TEXT2SQL" backend/.env.example
```

预期：命令 2 报权限错误；命令 3 成功；命令 4 有命中。

### 风险

- **必须**由用户本人执行数据库角色创建（本 AI 不应获得生产库的管理凭据）。
- 若本地 Docker 未运行，命令 2/3 可延后 —— 但**不得**因此把本票标为 DONE，应记 `BLOCKED` 并注明等待用户操作。

---

## T11 — 清除裸 except 并补日志

- **类型**：bug　**阶段**：2　**依赖**：无　**标记**：无

### 背景

7 处使用裸 `except:`（事实 F-11），会捕获 `KeyboardInterrupt` / `SystemExit`，导致 Ctrl-C 无法中断长任务，且吞掉真实异常。

位置：`deep_research_v2/graph.py:511`、`dr_g.py:370`、`news_collection_service.py:619/643/694`、`smart_analyzer.py:224/276/327`。

### 改什么

每处改为 `except Exception as e:`，并至少记录一次日志（`logger.warning` / `logger.exception`，视上下文选择）。

### 最小改法

- 逐处替换，**不改变**原有控制流（原本 `except: pass` 的仍保持继续执行，只是多了日志）。
- `dr_g.py` 属 NG-3 保留实现 —— 允许改 `except`，**不允许**删函数。
- **不要**顺手重构这些文件里的其它逻辑。

### 验收

```bash
# 1) 目标文件不再有裸 except
cd backend && ! grep -nE "except\s*:" app/service/deep_research_v2/graph.py app/service/dr_g.py app/service/news_collection_service.py app/service/smart_analyzer.py

# 2) 全仓裸 except 计数（允许 residual=0）
cd backend && grep -rnE "except\s*:" app/ | wc -l

# 3) 既有测试未回归
cd backend && pytest tests -q
```

预期：命令 1 无输出；命令 2 输出 `0`；命令 3 全绿。

### 风险

- 若某处原本依赖捕获 `BaseException`（极少见），改后行为会变。逐处读上下文确认，**不要**无脑替换。

---

## T12 — 收敛数据库连接池与会话生命周期，统一 schema 初始化入口

- **类型**：bug　**阶段**：2　**依赖**：无　**标记**：无

### 背景

`backend/app/core/database.py:19` 未设置任何连接池参数（事实 F-12）；`app_main.py:43` 在启动时执行 `create_all`，与 `backend/migrations/` 的手写 SQL 并存（事实 F-13），两条 schema 来源存在漂移风险。

### 改什么

1. 引擎增加 `pool_pre_ping=True`（防止连接被中间件断开后报错）与 `pool_recycle`（小于数据库侧空闲超时）。
2. `pool_size` / `max_overflow` 显式设置，取当前并发需求下的保守值。
3. `create_all` 改为仅在显式开发开关下执行；默认不执行，避免与迁移 SQL 打架。

### 最小改法

- 参数直接写在 `create_engine` 调用里，常量就地定义。
- 开关沿用环境变量判断，**不要**引入配置框架（与 T02 一致）。
- 手写迁移的执行方式保持原样，本票**不**建立迁移体系（NG-7）。

### 验收

```bash
# 1) 连接池参数已设置
cd backend && grep -nE "pool_pre_ping|pool_recycle|pool_size" app/core/database.py

# 2) 默认不执行 create_all（未开开关时不调用）
cd backend && python - <<'PY'
import sys, inspect; sys.path.insert(0,'.')
from app.core import database
src = inspect.getsource(database)
assert "pool_pre_ping" in src, "FAIL: 未设置 pool_pre_ping"
print("OK: 连接池参数存在")
PY

# 3) 既有测试未回归
cd backend && pytest tests -q
```

预期：命令 1 有命中；命令 2 打印 `OK`；命令 3 全绿。

### 风险

- `pool_size` 取值过大可能耗尽 Postgres 连接数。取保守值并在 commit message 中说明依据。
- 关闭 `create_all` 后，若某人依赖它自动建表会失败。需在 `READMED.md` 的启动章节补充「迁移 SQL 如何执行」的说明（属本票范围）。

---

# 阶段 3 · 可接手性（P1）

## T13 — 显式标注 LangGraph 运行时路径为有意保留

- **类型**：docs　**阶段**：3　**依赖**：无　**标记**：无

### 背景

`deep_research_v2/graph.py` 的 `_build_langgraph`（`:214`）、6 个 `_*_node`（`:251-292`）、`_run_with_langgraph`（`:372`）在当前主路径下不可达（事实 F-14）。但用户明确说明这是**有意保留**的并行实现，未来要在「手写异步状态机」与「LangGraph 运行时」之间做选择（NG-2）。

**风险**：任何接手者看到「无调用点」都会判定为死代码并删除。必须用显式标注阻止这件事。

### 改什么

1. 在 `graph.py` 模块 docstring 中说明：本模块同时维护**两条执行路径**，当前生效的是手写异步状态机，LangGraph 路径为预留实现。
2. 在 `_build_langgraph`、`_run_with_langgraph`、`LANGGRAPH_AVAILABLE` 定义处加行内注释，写明保留理由，并指向本 PRD 的 NG-2。
3. 把 `:366` 处被注释掉的调用点，改为带明确说明的注释（说明如何启用 LangGraph 路径）。

### 最小改法

**纯注释与文档改动，不改任何可执行代码。** 不新增开关、不调整 `requirements.txt`。

### 验收

```bash
# 1) 标注存在且指向 NG-2
cd backend && grep -n "NG-2" app/service/deep_research_v2/graph.py
cd backend && grep -nE "有意保留|预留|不得删除" app/service/deep_research_v2/graph.py | head

# 2) 确认本票未删除任何实现（diff 中不得有删除的函数）
git log -1 --diff-filter=D --name-only -- backend/app/service/deep_research_v2/graph.py

# 3) 语法与测试未受影响
cd backend && python -c "import sys;sys.path.insert(0,'.');import app.service.deep_research_v2.graph;print('OK')"
cd backend && pytest tests -q -k deep_research_v2
```

预期：命令 1 有命中；命令 2 无输出（未删除文件）；命令 3 打印 `OK` 且测试全绿。

### 风险

- **最容易犯的错**：顺手把「不可达」的代码删掉。本票的验收第 2 条就是防这个。

---

## T14 — 显式标注 V1 ReAct 编排为保留的备选路线

- **类型**：docs　**阶段**：3　**依赖**：无　**标记**：无

### 背景

`dr_g.py`（791 行）、`react_controller.py`（951 行）、`tool_executor.py`（661 行）合计 2403 行，仅当显式传 `version=v1` 时可达（事实 F-15）。用户明确说明这是**有意保留**的备选路线（NG-3）。

### 改什么

1. 三个模块的 docstring 顶部写明：这是 V1 ReAct 研究路线，由 `POST /research/stream` 的 `version=v1` 触发，**有意保留**，禁止当死代码删除。
2. 在 `research_router.py` 的 `version` 字段旁注明两条路线的分工与默认值（`"v2"`）。
3. 在 `CLAUDE.md` 的架构章节补充一句两条路线的关系，避免接手者只看前端调用就误判。

### 最小改法

**纯注释与文档改动。** 不改路由逻辑、不改 `requirements.txt`、不标记 `@deprecated`。

### 验收

```bash
# 1) 三个模块均有保留说明
cd backend && for f in dr_g react_controller tool_executor; do
  echo -n "$f: "; grep -cE "有意保留|备选路线|不得删除" app/service/$f.py
done

# 2) 路由处有路线说明
grep -n "version" backend/app/router/research_router.py | head -5

# 3) CLAUDE.md 已更新
grep -n "V1\|v1" CLAUDE.md | head -5

# 4) 未删除任何实现
git log -1 --diff-filter=D --name-only -- backend/app/service/dr_g.py backend/app/service/react_controller.py backend/app/service/tool_executor.py
```

预期：命令 1 三个计数均 ≥ 1；命令 2/3 有命中；命令 4 无输出。

### 风险

- 同 T13：不要顺手删。

---

## T15 — 抽离 serialize_event，解除 research_router 对 dr_g 的隐式依赖

- **类型**：refactor　**阶段**：3　**依赖**：无　**标记**：无

### 背景

`backend/app/router/research_router.py:18` 仅为一个序列化函数就 `from service.dr_g import serialize_event`（事实 F-16），使「V2 主路径」的路由反向依赖「V1 备选路线」的模块。这既模糊了模块边界，也让 V1 无法被独立理解。

### 改什么

1. 把 `serialize_event` 抽到**中立的公共位置**（如 `backend/app/core/serialization.py` 或 `app/service/serialization.py`，取与现有目录习惯最接近的一个）。
2. `dr_g.py` 与 `research_router.py` 都改为从新位置导入；`dr_g.py` 可保留一个同名转发以兼容其它调用方（若有）。
3. 全部调用点改指向。

### 最小改法

- **移动，不重写**。函数体逐字保留。
- 先跑 `grep -rn "serialize_event" backend/` 找全调用点，一次改完（避免只改路由、漏了其它调用方 —— 这是典型的「只修症状」错误）。
- 不新增依赖、不改函数签名。

### 验收

```bash
# 1) 新位置存在该函数
cd backend && grep -rn "def serialize_event" app/

# 2) research_router 不再从 dr_g 导入
cd backend && ! grep -n "from service.dr_g import" app/router/research_router.py

# 3) 全仓无遗留的旧导入路径（除有意保留的转发）
cd backend && grep -rn "from service.dr_g import\|from .dr_g import" app/ | grep -v "serialize_event"

# 4) 行为未变
cd backend && pytest tests -q
```

预期：命令 1 有唯一命中；命令 2 无输出；命令 3 无输出；命令 4 全绿。

### 风险

- 若存在 `service/__init__.py` 的再导出，需一并更新（`service/__init__.py:10` 导出了 `ResearchService`，检查是否也导出 `serialize_event`）。
- 这是本阶段唯一动到可执行代码的票 —— 务必跑全量 `pytest`。

---

## T16 — 修复文档与代码漂移

- **类型**：docs　**阶段**：3　**依赖**：无　**标记**：无

### 背景

三处文档与实现不符：`READMED.md:385,391` 的 langfuse 版本与开关默认值（事实 F-17）；`knowledge_router.py:76` / `docmind_service.py:258` 注释仍写 ES（事实 F-18）；`READMED.md:3` 宣称「知识图谱」但无对应模块（事实 F-19）。

### 改什么

1. `READMED.md` 中的 langfuse 版本改为与 `backend/requirements.txt` 实际一致；`LANGFUSE_ENABLED` 的默认值与主链路开关（`OBSERVABILITY_TRACING_ENABLED`）的关系写清楚。
2. 清理「ES 存储 / ES 索引」注释，改为 Milvus（保留历史迁移说明一句话即可，不要留误导）。
3. 「知识图谱」宣称：核实前端确有知识图谱组件（`knowledge-graph.tsx` 存在），而后端无对应模块 —— 明确写成「前端基于研究结果渲染的关系视图」，不暗示存在独立图谱后端。

### 最小改法

只改文案。**不做**功能补齐（NG-1）。

### 验收

```bash
# 1) 文档中的版本与实际依赖一致
grep -n "langfuse" READMED.md | head
grep -n "langfuse" backend/requirements.txt

# 2) 过时注释已清理
cd backend && grep -rn "ES 存储\|ES 索引" app/ | wc -l

# 3) 知识图谱描述已澄清
grep -n "知识图谱" READMED.md
```

预期：命令 1 两处版本号一致；命令 2 输出 `0`；命令 3 的表述与前端实现相符。

### 风险

- 不要为了「让文档好看」而承诺不存在的功能 —— 本票方向是**收窄宣称**，不是扩写。

---

## T17 — 新增架构总览文档

- **类型**：docs　**阶段**：3　**依赖**：T13、T14　**标记**：无

### 背景

项目有 `CLAUDE.md`（开发指引）与 `docs/RAG架构分析.md`（检索专题），但**没有**一份能让接手者一次看懂「有哪些执行路线、各自入口、数据如何流动」的总览（事实 F-14/F-15 的根因）。

### 改什么

新增 `docs/architecture.md`，内容限定为：

1. **两条研究路线**：V2（`service/deep_research_v2/`，默认）与 V1（`dr_g.py` + `react_controller.py` + `tool_executor.py`，`version=v1`），各自的入口、触发条件与状态管理方式。
2. **V2 内部流程**：六类 agent 的顺序与职责，以及「手写异步状态机 + `asyncio.Queue` → SSE」的数据通路。
3. **RAG 数据流**：上传 → DocMind 解析 → `chunk_text` → 向量化 → Milvus `kb_*` → 检索。指向 `docs/RAG架构分析.md` 而不复制其内容。
4. **基础设施依赖矩阵**：哪个功能依赖哪个服务（Postgres / Redis / Milvus / ES / MinIO）。
5. **目录导航**：`backend/app/` 与 `frontend/src/` 下每个顶层目录一句话职责。

### 最小改法

- **一个文件**。不建 `docs/architecture/` 目录、不拆多个文档。
- 内容以「接手者能否据此定位改动点」为唯一标准，不写历史沿革、不写设计动机散文。
- 明确标注 NG-2 / NG-3 两处「有意保留」，并回链 `prd.md`。

### 验收

```bash
# 1) 文件存在且覆盖五个规定小节
test -f docs/architecture.md && grep -nE "^## " docs/architecture.md

# 2) 明确标注了 "有意保留"
grep -n "有意保留" docs/architecture.md

# 3) 目录导航覆盖实际存在的顶层目录
cd backend && ls app/ | head -20

# 4) 未触碰可执行代码
git log -1 --name-only | grep -v "^docs/" | grep -vE "^(commit|Author|Date|$)" || echo "OK: 仅改动 docs/"
```

预期：命令 1 列出 ≥ 5 个小节；命令 2 有命中；命令 4 打印 `OK`。

### 风险

- **容易退化成散文**。约束：每节不超过 15 行，能画表格就用表格。

---

## T18 — requirements.txt 去重与依赖分区

- **类型**：refactor　**阶段**：3　**依赖**：无　**标记**：needs-decision

### 背景

`langfuse` 在 `backend/requirements.txt:28` 与 `:69` 重复声明，且版本约束不一致（`>=4.0.0` vs `>=4.0.0,<5.0.0`，事实 F-20）。全文件混用 `>=` 而不锁次要版本，构建不可复现。

### 改什么

1. **去重**（无争议，必须做）：合并 `langfuse` 两行，取更严格的约束。
2. 按用途分区注释（LLM / 搜索 / 数据库 / 可观测性 / Web 框架 / 工具），便于接手者理解每个依赖为何存在。
3. **【需裁决】**是否引入版本锁定（`pip-tools` / `pip freeze` 生成 `requirements.lock`）。

### 最小改法

- 只做去重与分区注释，**不删除**任何依赖 —— 特别注意 `langgraph` 与 `alembic`：
  - `langgraph`：**不得删除**（NG-2）。
  - `alembic`：由 T19 决策票处理，本票不动。

### 验收

```bash
# 1) 无重复依赖声明
cd backend && awk -F'[<>=!]' '/^[a-zA-Z]/{gsub(/ /,"",$1); print tolower($1)}' requirements.txt | sort | uniq -d
# 预期：无输出

# 2) 关键依赖仍在
cd backend && grep -cE "^(langgraph|langfuse|alembic)" requirements.txt

# 3) 依赖仍可解析（不需要安装）
cd backend && python -m pip install --dry-run -r requirements.txt 2>&1 | tail -3 || echo "（离线环境跳过）"
```

预期：命令 1 无输出；命令 2 输出 `3`；命令 3 无解析错误。

### 决策点（需用户裁决）

- **选项 A（推荐）**：不锁版本，只去重与分区。理由：当前无构建不可复现的实际事故，锁定会带来升级维护成本（YAGNI）。
- **选项 B**：引入 `requirements.lock`（`pip-compile` 生成），CI 与部署均使用锁文件。理由：需要严格可复现构建时值得。
- **代价**：B 需要为每次依赖变更多跑一步，并新增一个工具依赖。

### 风险

- 依赖去重后需确认 `langfuse` 实际被 `import` 的模块仍可用（`backend/app/observability/` 相关）。

---

## T19 — 决策票：alembic 去留

- **类型**：refactor　**阶段**：3　**依赖**：T12　**标记**：needs-decision

### 背景

`backend/requirements.txt:10` 声明 `alembic>=1.12.0`，但仓库无 `alembic.ini` / `env.py`，`backend/migrations/` 是手写 SQL（事实 F-21）。这是一个「声称在用、实际没用」的依赖。

### 待裁决选项

| 选项 | 内容 | 代价 |
|------|------|------|
| **A（推荐）** | 删除 `alembic` 依赖，保留手写 SQL，并在 `READMED.md` 写清「迁移如何执行」 | 未来需要版本化迁移时得重新引入 |
| **B** | 真正引入 alembic：`alembic init`、把 `migrations/` 的 SQL 转成版本化 revision、接入 CI 做 `alembic upgrade head` 校验 | 一次性工作量较大；与 `create_all` 的边界需要重新定义（T12 已收窄） |
| **C** | 保持不变，只在 `requirements.txt` 加注释说明「预留未使用」 | 依赖继续漂移，接手者仍会困惑 |

### 本票不自动执行

等待用户裁决后，再按所选选项拆出可执行的实施步骤。

### 验收（按所选选项不同）

- 选 A：`! grep -n "alembic" backend/requirements.txt`（删除后应为空），且 `READMED.md` 含迁移执行说明。
- 选 B：`alembic upgrade head` 在干净数据库上成功执行，且 CI 含该步骤。
- 选 C：`requirements.txt` 中含明确注释。

### 风险

- 选 B 时，`app_main.py` 的 `create_all`（T12 已改为默认关闭）与 alembic 的职责边界必须一次说清，否则会出现两套 schema 来源 —— 这正是本票要解决的问题。

---

## T20 — 决策票：chat/index.tsx 是否拆分

- **类型**：refactor　**阶段**：3　**依赖**：无　**标记**：needs-decision

### 背景

`frontend/src/pages/chat/index.tsx` 为 1953 行，含 12 个 `useEffect` 与 13 个 `useMemo`（事实 F-22）。这是仓库最大的单文件，任何改动都要先读懂近 2000 行。

### 待裁决选项

| 选项 | 内容 | 代价 |
|------|------|------|
| **A（推荐）** | 暂不拆分。先做低风险清理（T32 清理 console.log、T36 清理死代码），观察是否仍有必要 | 文件继续超大，但零回归风险 |
| **B** | 按职责拆为 4–6 个模块：消息流渲染 / SSE 消费与事件分发 / 研究详情与工具栏 / 会话状态与副作用 | 属大重构，浏览器行为回归风险高，需要 Playwright 端到端拦截 |
| **C** | 只抽出**纯逻辑**（SSE 事件解析、状态归约）到 hooks 与 utils，UI 渲染留在原文件 | 收益小于 B，风险也小于 B，但会留下一个「半拆」的中间态 |

### 本票不自动执行

若用户选 B 或 C，需先补该文件的 Playwright 覆盖再动手（`frontend/e2e/` 已有 `deep-research-outline-approval.spec.ts` 可扩展）。

### 验收（按所选选项不同）

- 选 A：`wc -l frontend/src/pages/chat/index.tsx` 记录基线值，`npm run test` 全绿。
- 选 B/C：拆分后 `wc -l` 主文件显著下降，`npm run test` 与 `npm run test:e2e` 全绿。

### 风险

- 该文件承载深研 SSE 流式消费，拆分时极易引入**竞态与双重订阅**回归。若选 B/C，必须先建立端到端保护网。

---

# 阶段 4 · 工程化底座

## T21 — 新增 LICENSE

- **类型**：chore　**阶段**：4　**依赖**：无　**标记**：无

### 背景

仓库为 PUBLIC 但无 LICENSE（事实 F-24）。无许可证意味着默认保留全部权利，他人（含协作者与依赖使用者）在法律上无权使用、修改或分发。

### 改什么

新增仓库根目录 `LICENSE`。

### 最小改法

采用 MIT（最宽松、最常用）。若用户有其它偏好需先裁决 —— **若用户未指定，默认 MIT，并在 commit message 中注明可随时更换**。

### 验收

```bash
test -f LICENSE && head -3 LICENSE
grep -q "MIT" LICENSE && echo "OK: MIT"
```

预期：文件存在，头部含 MIT 许可文本。

### 风险

- 许可证属法律事项。若该项目涉及雇主或学校权益，用户需自行确认是否有权选择 MIT。**本票只做默认选择，不构成法律建议。**

---

## T22 — 新增 CONTRIBUTING.md

- **类型**：chore　**阶段**：4　**依赖**：T26　**标记**：无

### 背景

无贡献指南（事实 F-24）。接手者（AI 或人）需要知道代码风格、测试要求、提交规范才能安全改动。

### 改什么

新增 `CONTRIBUTING.md`，内容限定：

1. 环境准备（指向 `READMED.md`，不重复其内容）。
2. 分支与提交规范（与 `LOOP-PROTOCOL.md` §5 一致，**不要**另立一套）。
3. 代码风格：后端 `ruff check`、前端 `eslint` + `prettier`。
4. 测试要求：改代码必须带验证；验收必须可执行（指向 `prd.md` §7）。
5. **密钥红线**：不得提交任何密钥（重复 `AGENTS.md` 的硬性约束，因为这是最容易被违反的一条）。

### 最小改法

**一个文件、一屏以内**。不写「欢迎贡献」这类客套话。

### 验收

```bash
test -f CONTRIBUTING.md
grep -nE "^## " CONTRIBUTING.md
grep -n "密钥" CONTRIBUTING.md
```

预期：文件存在；含 ≥ 4 个小节；含密钥约束。

### 风险

- 与 `LOOP-PROTOCOL.md` 重复的部分要回链而不是复制，避免两份规范漂移。

---

## T23 — 新增 .editorconfig

- **类型**：chore　**阶段**：4　**依赖**：无　**标记**：无

### 背景

无 `.editorconfig`（事实 F-24）。同一仓库混有 Python（4 空格）与前端（2 空格），且当前工作区存在 LF/CRLF 混用（`git add` 时出现多处 `LF will be replaced by CRLF` 警告）。

### 改什么

新增 `.editorconfig`，覆盖 Python / TypeScript / JSON / YAML / Markdown。

### 最小改法

一个文件。使用 `root = true`，为不同扩展名设置 `indent_size` 与 `charset` / `end_of_line`。**不要**在本票内统一换行符（那会产生巨大 diff）；只建立约定，交由前端已有的 prettier 与后端 ruff 逐步收敛。

### 验收

```bash
test -f .editorconfig && grep -n "root = true" .editorconfig
grep -nE "\[.*\.(py|ts|tsx)\]" .editorconfig
```

预期：文件存在；声明了 `root = true`；覆盖 py 与 ts/tsx。

### 风险

- 若把 `end_of_line = crlf` 设为全局默认，会在 Linux CI 上引发 lint 差异。**建议保持 `lf`**，Windows 侧由 `core.autocrlf` 处理。

---

## T24 — 新增 issue 与 PR 模板

- **类型**：chore　**阶段**：4　**依赖**：无　**标记**：无

### 背景

无 `.github/` 目录（事实 F-23/F-24）。issue 由 AI 创建、PR 由 AI 提交，但没有强制字段会导致信息缺失。

### 改什么

新增：

- `.github/ISSUE_TEMPLATE/task.md`（任务类）
- `.github/ISSUE_TEMPLATE/bug_report.md`（缺陷类）
- `.github/PULL_REQUEST_TEMPLATE.md`

### 最小改法

模板字段与 `docs/hardening/tickets.md` 的 ticket 结构对齐（背景 / 事实依据 / 改什么 / 验收 / 风险），这样 issue 与 ticket 天然同构，减少两处维护。

PR 模板必须包含：**验收命令与实际输出**、**是否触碰 NG-2/NG-3**、**是否引入密钥**。

### 验收

```bash
ls -1 .github/ISSUE_TEMPLATE/ .github/PULL_REQUEST_TEMPLATE.md
grep -n "验收" .github/PULL_REQUEST_TEMPLATE.md
grep -n "密钥" .github/PULL_REQUEST_TEMPLATE.md
```

预期：文件均存在；PR 模板含验收与密钥检查项。

### 风险

- 模板一旦建立会被 GitHub 自动应用，字段过多会降低填写意愿。保持 3–5 个必填项。

---

## T25 — 新增 CHANGELOG.md 并初始化版本号

- **类型**：chore　**阶段**：4　**依赖**：无　**标记**：无

### 背景

无 `CHANGELOG.md`，前端 `package.json` 的 `version` 为 `0.0.0`，后端无版本号（事实 F-24）。

### 改什么

1. 新增 `CHANGELOG.md`，采用 Keep a Changelog 格式，记录本次硬化的条目。
2. 前端 `package.json` 版本 `0.0.0` → `0.1.0`。
3. 后端在 `backend/app/__init__.py`（或既有合适位置）定义 `__version__ = "0.1.0"`。

### 最小改法

- CHANGELOG 只写已发生的事实，**不要**预留未完成的版本小节。
- 两侧版本号必须一致（验收会检查）。

### 验收

```bash
node -e "console.log(require('./frontend/package.json').version)"   # 期望 0.1.0
cd backend && python -c "import sys;sys.path.insert(0,'.');import app;print(app.__version__)"  # 期望 0.1.0
head -12 CHANGELOG.md
```

预期：两侧版本均为 `0.1.0`；CHANGELOG 头部含 Unreleased 或 0.1.0 小节。

### 风险

- 版本号初始化会与后续 ticket 的条目产生先后顺序问题：**建议本票在阶段 4 末尾执行**，或在 CHANGELOG 中标注「本条目前的内容为本次硬化计划的汇总，逐票条目在合并时追加」。

---

## T26 — 新增后端 ruff 配置

- **类型**：chore　**阶段**：4　**依赖**：无　**标记**：无

### 背景

`backend/requirements.txt:79` 列出了 `ruff`，但无 `ruff.toml` / `pyproject.toml`，也没有 pre-commit（事实 F-25）。也就是说 ruff 装了但从未被配置或执行。

### 改什么

1. 新增 `backend/ruff.toml`：设定 `line-length`（建议 100，与现有多数文件风格接近）、`target-version`（与 `pyproject`/README 声明的 Python 3.10 一致）、`select` 规则集。
2. 首次运行 `ruff check --fix` 时**只接受无风险修复**；对无法自动修的问题，将其规则暂时 `ignore` 并在配置中注明原因（不要一次性引入上百条违规）。

### 最小改法

- **先以最小规则集起步**（如 `E9,F63,F7,F82` —— 只抓语法错误与未定义名），确保 `ruff check` 一次就能绿。
- 不要在本票里格式化全仓（会淹没后续 diff）。格式化交给独立动作。
- **不要**同时引入 black —— ruff 已覆盖格式化。

### 验收

```bash
cd backend && ruff check app tests
# 预期：All checks passed!（退出码 0）

cd backend && cat ruff.toml | head -20
```

预期：命令无违规输出；配置文件存在。

### 风险

- 若把规则集开得过大导致大量违规，会诱使执行者「修改代码去迎合 lint」从而超出本票范围。**规则集小、`check` 通过**是本票唯一的硬指标。

---

## T27 — 后端测试分层：无基础设施单测可独立运行

- **类型**：chore　**阶段**：4　**依赖**：无　**标记**：无

### 背景

`backend/tests/conftest.py` 只设了 `sys.path` 与 `ENV=test`，没有 DB/Redis/Milvus fixture（事实 F-30）。`backend/tests/` 中有依赖外部服务的用例（如 `integration/test_checkpoint_approval_postgres.py`），导致「跑测试」必须先把整套中间件起起来 —— 这是 CI 无法落地（事实 F-23）的直接原因。

### 改什么

1. 在 `backend/pytest.ini`（或 `pyproject.toml` 的 `[tool.pytest.ini_options]`）注册 marker：`unit`、`integration`、`needs_infra`。
2. `conftest.py` 增加 `--no-infra` 选项（或 `-m "not needs_infra"` 语义的默认行为），使默认 `pytest tests` **跳过**需要基础设施的用例。
3. 把现有依赖外部服务的测试标注为 `@pytest.mark.needs_infra`。

### 最小改法

- 用 pytest 原生 marker，**不要**自建测试框架或 fixture 工厂。
- 标注时逐个文件确认：能用 mock 隔离的（如 checkpoint 逻辑）优先改为 mock，**确实必须连真库的**才标 `needs_infra`。
- 本票**不写**新测试（新测试分别在 T39/T40 与各功能票里）。

### 验收

```bash
# 1) 无基础设施下默认跑通
cd backend && pytest tests -q
# 预期：全绿（跳过 needs_infra），退出码 0

# 2) 跳过数量可见
cd backend && pytest tests -q --collect-only -m "not needs_infra" | tail -3

# 3) marker 已注册，无 warning
cd backend && pytest tests -q 2>&1 | grep -i "PytestUnknownMarkWarning" && echo "FAIL: marker 未注册" || echo "OK: 无未注册 marker"
```

预期：命令 1 退出码 0；命令 3 打印 `OK`。

### 风险

- **不要**为了让测试通过而删除既有用例 —— 只能标记或补 mock。
- 若某些用例无法在不连库的情况下构造，保留为 `needs_infra` 并在 TRACKER 中标注，**不得**删除。

---

## T28 — 新增 CI：后端 pytest

- **类型**：ci　**阶段**：4　**依赖**：T27、T26　**标记**：needs-infra

### 背景

仓库零 CI（事实 F-23）。后端测试在 T27 之后已可无基础设施运行，具备上 CI 的条件。

### 改什么

新增 `.github/workflows/ci-backend.yml`：

1. `actions/setup-python`，版本与 `READMED.md` 声明的 3.10+ 一致（建议 3.11）。
2. 安装 `backend/requirements.txt`（缓存 pip）。
3. 注入测试所需的环境变量（**从 GitHub Secrets 读取，不得写死在 workflow 文件中**；本阶段仅需满足 T02 的 `JWT_SECRET_KEY` 等）。
4. 运行 `ruff check`（T26）与 `pytest tests -q`（T27）。

### 最小改法

- **一个 workflow、一个 job**，不拆矩阵、不做多平台。
- 不引入 docker-compose 服务容器（`needs-infra` 用例已被 T27 跳过）。
- 触发条件：`push` 到 `main` 与所有 `pull_request`。

### 验收

```bash
# 1) workflow 文件存在且语法合法
test -f .github/workflows/ci-backend.yml
python -c "import yaml,sys;yaml.safe_load(open('.github/workflows/ci-backend.yml'));print('OK: YAML 合法')" 2>/dev/null || node -e "console.log('（无 yaml 模块，改用 gh 校验）')"

# 2) 无明文密钥
! grep -nE "sk-[A-Za-z0-9]{16,}" .github/workflows/ci-backend.yml

# 3) needs-infra：推送后查看运行结果（需 gh 已认证）
gh run list --workflow=ci-backend.yml --limit 3
gh run watch $(gh run list --workflow=ci-backend.yml --limit 1 --json databaseId -q '.[0].databaseId')
```

预期：命令 1 合法；命令 2 无命中；命令 3 中该次运行结论为 `success`。

### 风险

- **R-05**：命令 3 需要实际推送并等待 CI，属 `needs-infra`。若推送被推迟，本票记 `BLOCKED`，但命令 1/2 必须 PASS。
- 若 T02 之后本地 `.env` 缺失会导致 import 失败，CI 中的环境变量注入必须完整，否则 CI 一启动就红。

---

## T29 — 新增 CI：前端 lint + vitest + build

- **类型**：ci　**阶段**：4　**依赖**：无　**标记**：needs-infra

### 背景

前端具备完整的工具链（`eslint`、`vitest`、`playwright`、`husky`），但从不自动执行（事实 F-23）。

### 改什么

新增 `.github/workflows/ci-frontend.yml`：

1. `actions/setup-node`，Node 版本与 `frontend/package.json` 的 engines 声明或 `vite` 要求一致。
2. 安装依赖时必须带 `--legacy-peer-deps`（React 19 + Ant Design 5 的 peer 冲突，见 `READMED.md`），或先补 `.npmrc`。
3. 运行 `npm run lint`、`npm run test`、`npm run build`。

### 最小改法

- **优先补 `.npmrc`（`legacy-peer-deps=true`）而不是在 workflow 里加 flag** —— 这样本地 CI 与开发环境行为一致，且 `npm ci` 也能用。若采用此做法，本票包含 `.npmrc` 的新增。
- 一个 workflow、一个 job。
- **不接** Playwright 端到端（需要浏览器与后端，属 `needs-infra`，另议）。

### 验收

```bash
# 1) workflow 文件存在
test -f .github/workflows/ci-frontend.yml
grep -nE "npm run (lint|test|build)" .github/workflows/ci-frontend.yml

# 2) 本地三条命令均通过（preflight，不需要 CI 运行）
cd frontend && npm run lint && npm run test && npm run build

# 3) 若采用 .npmrc 方案，确认已新增
test -f frontend/.npmrc && cat frontend/.npmrc
```

预期：命令 1 有命中；命令 2 三条均成功；命令 3 视方案而定。

### 风险

- `npm run lint` 当前可能已有违规（如 T33/T34 涉及的 `console.log` 与 `any`）。**必须先在本地跑一遍**：若已红，则在对应 ticket（T32/T33）完成后再启用该步骤，并在本票内把该步骤标注为「依赖 T33 完成」。**不得**通过关闭规则来让 CI 变绿。

---

## T30 — 新增 backend/Dockerfile 并接入 compose

- **类型**：ci　**阶段**：4　**依赖**：T12、T26　**标记**：needs-infra

### 背景

后端无 `Dockerfile`，`docker-compose.yml` 只编排中间件，后端跑在宿主机；可观测性栈通过 `host.docker.internal:8000` 抓指标（事实 F-26），在非 Docker Desktop 环境不可用。

### 改什么

1. 新增 `backend/Dockerfile`，**多阶段**构建（builder 装依赖 → runtime 仅拷贝虚拟环境与代码），基础镜像用 `python:3.11-slim`。
2. `docker-compose.yml` 增加 `backend` 服务，加入既有 `industry_network`，暴露 8000，依赖中间件的 healthcheck。
3. 增加 `.dockerignore`（至少排除 `__pycache__`、`.pytest_cache`、`tests`、`.env`、`*.png`）。

### 最小改法

- 复用 `docker-compose.yml` 中既有服务的网络与健康检查写法。
- **不要**引入 k8s / helm / 多环境 compose（YAGNI）。
- 密钥通过 `env_file: backend/.env` 注入，**不得**写进 compose 文件。

### 验收

```bash
# 1) 文件存在
test -f backend/Dockerfile && test -f .dockerignore

# 2) compose 可解析
docker compose config --quiet && echo "OK: compose 合法"

# 3) needs-infra：真实构建并启动
docker build -t deepsearch-backend:dev backend
docker compose up -d backend
curl -sf http://localhost:8000/hello && echo "OK: 健康检查通过"

# 4) 镜像内无密钥
docker run --rm deepsearch-backend:dev sh -c 'test ! -f /app/.env && echo "OK: 未打包 .env"'
```

预期：命令 1/2 通过；命令 3/4 在 Docker 可用时通过。

### 风险

- **R-05**：Docker 未运行时命令 3/4 记 `BLOCKED`。命令 1/2 必须 PASS。
- 多阶段构建容易漏拷 `backend/migrations/` 或 `app/config/` 等资源目录 —— 构建后必须实际 curl 一次健康检查，不能只看 build 成功。

---

## T31 — start-services.sh 现代化

- **类型**：chore　**阶段**：4　**依赖**：T07　**标记**：needs-infra

### 背景

`start-services.sh:47` 使用旧式 `docker-compose`（README 用 `docker compose`），`:50` 在 `start` 后仅 `sleep 10` 而不等待 healthcheck（事实 F-27）。在有 healthcheck 的前提下仍用固定 sleep，会在慢机器上产生「脚本说启动成功、实际服务未就绪」的假成功。

### 改什么

1. `docker-compose` → `docker compose`。
2. `start` 改为先 `up -d` 再 `docker compose wait`（或轮询 `docker compose ps` 的 health 状态），确认全部 healthy 后才输出成功。
3. `clean` / `restart` 等破坏性动作增加**二次确认**（`down -v` 会删数据卷）。

### 最小改法

- 保持 bash，**不要**顺手改成 PowerShell（`observability/manage.ps1` 已覆盖 Windows 侧）。
- 只改这三处，不重排脚本结构。

### 验收

```bash
# 1) 无旧式命令
! grep -n "docker-compose" start-services.sh

# 2) 等待 healthcheck 而非固定 sleep
grep -nE "compose wait|health" start-services.sh

# 3) 语法合法
bash -n start-services.sh && echo "OK: 语法合法"

# 4) needs-infra：真实执行
bash start-services.sh start && bash start-services.sh status
```

预期：命令 1 无输出；命令 2 有命中；命令 3 打印 `OK`；命令 4 在 Docker 可用时全部服务 healthy。

### 风险

- `docker compose wait` 在部分 compose 版本上语义为「等待容器退出」而非「等待 healthy」，**必须核实当前版本行为**并选择正确的等待方式（轮询 `ps` 更稳妥）。写错会直接导致脚本挂死。

---

# 阶段 5 · 前端质量

## T32 — 清理 console.log 残留

- **类型**：refactor　**阶段**：5　**依赖**：无　**标记**：无

### 背景

前端约 30 处 `console.log` 残留，`chat/index.tsx` 最密集（事实 F-32），生产包会把这些调试输出带上线。

### 改什么

清理 `console.log` / `console.debug`；保留 `console.warn` / `console.error`（用于真实错误上报）。

重点位置：`frontend/src/pages/chat/index.tsx`、`frontend/src/api/news.ts:100-156`、`frontend/src/store/industry.ts:134/149/159/165`、`frontend/src/pages/chat/component/research-detail/index.tsx:113-120`、`frontend/src/layout/nav.tsx:31/45`。

### 最小改法

- **先全量定位**：`grep -rn "console\.log" frontend/src`，逐处判断是调试残留还是有意保留。
- **不要**引入 logger 封装库或 `vite-plugin-remove-console`（YAGNI）。若确实需要开关式日志，用已有依赖（`ahooks` 无此能力，则用一个 30 行的 `devLog` 工具函数）—— **优先直接删**。
- **不要**在本票内动 `any`（属 T33）。

### 验收

```bash
# 1) 目标文件已无 console.log
cd frontend && grep -rn "console\.log" src/ | wc -l

# 2) 构建与测试通过
cd frontend && npm run test && npm run build

# 3) lint 通过
cd frontend && npm run lint
```

预期：命令 1 输出 `0`；命令 2/3 通过。

### 风险

- 若某处 `console.log` 实为前端与后端联调的唯一诊断手段，删除会降低可观测性。**判断标准**：该日志是否在 `error-toast` 或既有 diagnostics 面板已有等价信息 —— 有则删。

---

## T33 — eslint 启用 no-explicit-any 并收敛 store 层 any

- **类型**：refactor　**阶段**：5　**依赖**：无　**标记**：无

### 背景

前端 59 处 `any`，`eslint.config.js` 未启用 `no-explicit-any`，因此不会被拦截（事实 F-32）。主要集中区：`store/session.ts:38/50/64/78`、`router/routes.tsx:30`、`store/device.ts:21`、各 page 的 `catch (error: any)`。

### 改什么

1. 在 `eslint.config.js` 启用 `@typescript-eslint/no-explicit-any`（先设 `warn`，本票收敛完成后再由 T35 或后续票提升为 `error`，视 diff 规模决定）。
2. 收敛**优先区**：Valtio store 层（`store/`）与 `router/`，因为这些是全局状态与路由的契约面，`any` 在此危害最大。
3. `catch (error: any)` 统一改为 `catch (error: unknown)` + 类型守卫（项目已有 `ResponseError` 类型，`frontend/src/api/request/` 下可见）。

### 最小改法

- **不要**一次收敛 59 处（diff 过大、审查成本高）。本票只收敛 store 层 + router，其余在票内以 `eslint-disable` 以外的形式**留待后续**（记入 TRACKER 作为已知残留）。
- 复用项目已有的 `ResponseError` 与 `session.ts` 中已定义的类型，**不要**新建类型体系。

### 验收

```bash
# 1) store 层与 router 无显式 any
cd frontend && grep -rn ": any\|as any" src/store/ src/router/ | wc -l

# 2) 规则已启用
cd frontend && grep -n "no-explicit-any" eslint.config.js

# 3) lint 与测试通过
cd frontend && npm run lint && npm run test
```

预期：命令 1 输出 `0`；命令 2 有命中；命令 3 通过。

### 风险

- 若把规则设为 `error` 而全仓仍有 50+ 处 `any`，CI 会立刻变红。**本票必须用 `warn`**，并在 commit message 中写明「待收敛后再提升为 error」。

---

## T34 — vite 构建分包 + 路由懒加载

- **类型**：refactor　**阶段**：5　**依赖**：无　**标记**：无

### 背景

`frontend/vite.config.ts` 无 `build` 配置（事实 F-33），`router/routes.tsx:8-17` 全部静态 `import`（事实 F-34）。结果：单包体积大，首屏加载即拉取全部页面与图表库。

### 改什么

1. `vite.config.ts` 增加 `build.rollupOptions.output.manualChunks`，至少拆出 `echarts`、`antd`、`react` 三个 vendor chunk。
2. `router/routes.tsx` 改为 `React.lazy` + `Suspense`，并为 Suspense 提供**中文**加载态（与项目现有文案风格一致）。
3. 不要开启 `sourcemap`（生产环境不需要，且会显著增大产物）。

### 最小改法

- 只拆最重的 3 个 chunk，**不要**做自动分包策略调优。
- 懒加载只作用于路由级页面，**不要**顺手拆分组件内部。
- 复用项目既有的 loading 组件（若有），不要新写。

### 验收

```bash
# 1) 配置已存在
grep -nE "manualChunks|rollupOptions" frontend/vite.config.ts

# 2) 路由已懒加载
grep -nE "React.lazy|lazy\(" frontend/src/router/routes.tsx

# 3) 构建产物确实分包
cd frontend && npm run build && ls -1 dist/assets | grep -E "echarts|antd|react" | head

# 4) 测试通过
cd frontend && npm run test
```

预期：命令 1/2 有命中；命令 3 产出含 echarts / antd / react 的独立 chunk 文件；命令 4 通过。

### 风险

- 懒加载后首屏会出现加载态闪烁，**不要**通过取消懒加载来解决 —— 应调整 Suspense fallback。
- 若 `manualChunks` 拆得过细会产生大量小 chunk 反而变慢。只拆三个。

---

## T35 — ECharts 真正拆包

- **类型**：refactor　**阶段**：5　**依赖**：T34　**标记**：无

### 背景

`chart/index.tsx:23` 已经用了动态 `import('echarts')`，但 `knowledge-graph.tsx:7` 与 `process-report.tsx:8` **静态**引入 `echarts-for-react`（该库依赖完整 `echarts`），导致动态导入失效、echarts 仍进主包（事实 F-35）。

### 改什么

把 `knowledge-graph.tsx` 与 `process-report.tsx` 改为懒加载（`React.lazy` + `Suspense`），使其与 `chart/index.tsx` 的动态导入策略一致。

### 最小改法

- 只改这两个组件的引入方式，**不改**组件内部实现。
- 懒加载的 fallback 使用与 T34 相同的中文加载态（复用同一处）。

### 验收

```bash
# 1) 两个组件不再被静态引入
cd frontend && grep -rn "knowledge-graph\|process-report" src/ --include="*.tsx" | grep -v "^src/pages/chat/component/knowledge-graph" | head

# 2) 主包不含 echarts（构建后检查 chunk 归属）
cd frontend && npm run build && node -e "
const fs=require('fs');const d='dist/assets';
const main=fs.readdirSync(d).find(f=>/^index-.*\.js$/.test(f));
const s=fs.readFileSync(d+'/'+main,'utf8');
if(/echarts/i.test(s)) { console.log('FAIL: echarts 仍在主包'); process.exit(1) }
console.log('OK: 主包不含 echarts');
"

# 3) 测试与 e2e 通过
cd frontend && npm run test
```

预期：命令 2 打印 `OK`；命令 3 通过。

### 风险

- 若 `echarts-for-react` 与动态 `import('echarts')` 的实例不共享，可能出现「图表不渲染」或「主题丢失」。**必须**在浏览器中实际打开一个含图表的页面验证（可用 `agent-browser` 技能截图），不能只靠构建通过。

---

## T36 — 清理注释死代码

- **类型**：refactor　**阶段**：5　**依赖**：T32　**标记**：无

### 背景

`frontend/src/pages/chat/index.tsx` 含约 128 行注释代码；`api/request/error-toast.ts:11-24` 的 `NETWORK_ERROR_MAP` 除 429 外全部被注释（事实 F-32）。

### 改什么

1. `chat/index.tsx` 中被注释掉的**代码块**（非解释性注释）删除。若其中有未来要用的片段，改为在 PR 描述中保留，不留在源码里。
2. `error-toast.ts:11-24`：要么补全映射（若产品确实需要区分这些网络错误），要么删除注释并把 429 之外的处理明确为「统一兜底」。**默认后者**（YAGNI）。

### 最小改法

- 只删注释，**不改**可执行逻辑。
- 解释「为什么」的注释一律保留；只删「被注释掉的代码」。
- 先 `grep -c "^\s*//" frontend/src/pages/chat/index.tsx` 记录基线，便于验收对比。

### 验收

```bash
# 1) 注释行数下降（与基线对比）
cd frontend && grep -cE "^\s*//" src/pages/chat/index.tsx

# 2) error-toast 中不再有大段注释映射
cd frontend && grep -cE "^\s*//" src/api/request/error-toast.ts

# 3) 行为未变
cd frontend && npm run test && npm run lint
```

预期：命令 1 的计数显著低于基线；命令 3 通过。

### 风险

- 误删解释性注释会丢失关键上下文。**逐段确认**是否在解释非显而易见的设计决策。

---

## T37 — 决策票：前端 JWT 存储方式

- **类型**：refactor　**阶段**：5　**依赖**：无　**标记**：needs-decision

### 背景

`frontend/src/api/request/auth.ts` 将 JWT 存入 `localStorage`。该方式对 XSS 完全无防护：任意一次 XSS 即可窃取 Token。项目当前没有 CSP 头（未在 `backend/app/app_main.py` 或前端配置中发现）。

### 待裁决选项

| 选项 | 内容 | 代价 |
|------|------|------|
| **A（推荐）** | 暂不改存储方式，改为**加防护**：后端补 `Content-Security-Policy` 响应头；`localStorage` 的读取集中到单一模块（便于将来替换） | 零功能风险；不根治 XSS 窃取 |
| **B** | 改为 httpOnly Cookie：需要后端新增 Cookie 签发与校验、引入 CSRF 防护（SameSite + token）、改造前端不再读取 Token | 涉及鉴权契约变更，属架构分叉；改动面覆盖前后端 |
| **C** | 保持现状，仅在 `docs/architecture.md` 与 `CONTRIBUTING.md` 中登记风险 | 零成本，风险持续 |

### 本票不自动执行

选 B 需先与用户确认鉴权契约变更范围。

### 验收（按所选选项不同）

- 选 A：响应头含 `Content-Security-Policy`；`localStorage` 的访问点收敛到一处（`grep -rn "localStorage" frontend/src` 仅命中该模块）。
- 选 B：登录后 Token 不出现在任何 JS 可读位置；带 Cookie 的请求通过 CSRF 校验。
- 选 C：文档中有风险登记条目。

### 风险

- 选 B 会破坏所有已登录用户的会话，需要一次强制重新登录。必须提前告知用户。

---

# 阶段 6 · 后端质量

## T38 — 清除 print 调试残留

- **类型**：refactor　**阶段**：6　**依赖**：无　**标记**：无

### 背景

多处使用 `print` 而非 logger（事实 F-36）：`chat_service_v2.py:42-117`（整片）、`knowledge_router.py:463/468/470`、`redis_client.py:43-103`、`embedding_service.py:52/119`、`llm_config.py:16-207`。

**为什么这是问题**：`backend/app/observability/logging.py` 已建立 JSON 结构化日志并投递到 Elasticsearch。`print` 的输出不进该链路，等于在可观测性体系里开了个洞。

### 改什么

逐处把 `print` 换成模块级 `logger`（`logger.info` / `debug` / `warning`，按原语义选择），保留原有信息内容。

### 最小改法

- 每个文件检查是否已有 `logger = logging.getLogger(__name__)`，有则直接用，无则补一行。
- **不要**新建日志封装（`observability/logging.py` 已存在）。
- **不要**顺手改业务逻辑。

### 验收

```bash
# 1) 目标文件已无 print
cd backend && grep -rn "^\s*print(" app/service/chat_service_v2.py app/router/knowledge_router.py app/core/redis_client.py app/service/embedding_service.py app/config/llm_config.py | wc -l

# 2) 全仓 print 残留计数
cd backend && grep -rn "^\s*print(" app/ | wc -l

# 3) 测试通过
cd backend && pytest tests -q
```

预期：命令 1/2 输出 `0`（或仅剩脚本目录下的合法输出）；命令 3 全绿。

### 风险

- `app/scripts/` 下的脚本用 `print` 做 CLI 输出是**合理的**，不要清理（除非同时改成 `logging` 并配置 console handler）。
- `llm_config.py:16-207` 的 print 可能承载启动期的配置自检信息，改成 `logger.info` 后需确认日志级别未把它过滤掉（否则会丢失配置可见性）。

---

## T39 — 补 text2sql.validate_sql 单元测试

- **类型**：test　**阶段**：6　**依赖**：T09　**标记**：无

### 背景

`backend/tests/` 中 text2sql **零测试**（事实 F-31），而它是唯一直接拼接并执行用户输入到数据库的模块 —— 风险与测试覆盖严重不匹配。

### 改什么

新增 `backend/tests/service/test_text2sql_validate.py`，针对 `validate_sql` 这一**纯函数**构建用例矩阵：

1. **拒绝**：`DELETE` / `UPDATE` / `INSERT` / `DROP` / `TRUNCATE` / `ALTER`；`UNION SELECT` 与 `UNION ALL SELECT`；多语句（`; DROP`）；注释绕过（`--`、`/* */`）；空语句与非字符串输入。
2. **放行**：普通 `SELECT`、带 `WHERE` / `JOIN` / `GROUP BY` / 子查询的 `SELECT`、`WITH ... SELECT`。
3. **边界**：超长 SQL、大小写混写（`select` / `SeLeCt`）。

### 最小改法

- 用 `pytest.mark.parametrize`，**不要**建测试基类或 fixture 工厂。
- 纯函数测试，**不连数据库**（确保在 T27 的 `--no-infra` 口径下也能跑）。
- 若 `validate_sql` 当前不可直接导入（嵌套在类里），最小重构为模块级函数 —— 这是本票允许的必要重构。

### 验收

```bash
cd backend && pytest tests/service/test_text2sql_validate.py -v
# 预期：全部通过，且用例数 >= 15

cd backend && pytest tests -q
# 预期：全绿（不因本票新增用例而变红）
```

预期：新测试文件全绿，用例数 ≥ 15。

### 风险

- **不要**为了让测试通过而放宽 `validate_sql` 的校验范围 —— 测试应暴露缺陷，而不是迎合实现。若发现真实漏洞，记录下来并开新 ticket（或若与 T09 同源，回到 T09 一起修）。

---

## T40 — 补 security 鉴权单元测试

- **类型**：test　**阶段**：6　**依赖**：T02、T05　**标记**：无

### 背景

`backend/app/core/security.py` 承载 JWT 签发与校验，是全部鉴权的信任根，但**零测试**（事实 F-31）。T02 刚强化了密钥校验，正是需要测试护栏的时刻。

### 改什么

新增 `backend/tests/core/test_security.py`：

1. 签发 → 校验的往返（正确密钥）。
2. 篡改签名 → 校验失败。
3. 过期 Token → 校验失败。
4. 使用另一密钥签发的 Token → 校验失败。
5. 弱密钥 / 缺失密钥 → 配置阶段即失败（对应 T02）。
6. `get_current_user_required` 在缺失 / 格式错误的 `Authorization` 头下的行为。

### 最小改法

- 用 `monkeypatch.setenv` 注入测试密钥（**测试里使用明显的假值**，如 `"test-only-" + "x"*40`，绝不使用真实密钥）。
- 不引入 `freezegun` 等新依赖 —— 过期用例通过签发一个 `expires_delta` 为负数的 Token 实现。
- 不连数据库：对用户查询部分使用 mock。

### 验收

```bash
cd backend && pytest tests/core/test_security.py -v
# 预期：全部通过，用例数 >= 6

# 确认测试中无真实密钥
cd backend && ! grep -nE "sk-[A-Za-z0-9]{16,}" tests/core/test_security.py && echo "OK: 测试无真实密钥"

cd backend && pytest tests -q
```

预期：新测试全绿；无真实密钥；全量测试全绿。

### 风险

- 鉴权测试若依赖真实数据库查询用户，会变成 `needs_infra`。**必须**用 mock 隔离，否则违背 T27 建立的分层。

---

## T41 — 合并三处上传实现，消除 attachment / knowledge 路由的路径穿越（决策票）

- **类型**：security　**阶段**：1　**依赖**：T03　**标记**：`needs-decision`

> ✅ **裁决结果（2026-09-13）**：用户选定 **方案 A** —— 只统一**代码实现**，白名单各自保留。
> 已实施并合并（commit / PR 见 `TRACKER.md`）。**零行为变更**：三份白名单的成员集合
> 由 `tests/router/test_upload_paths.py` 用 AST 断言锁定，任何一处被改动都会失败。

> 来源：第 1 批 `code-review` 的两条**独立** findings —— 标准轴的「Duplicated Code / 未并轨」，
> 与规格轴的「T03 白名单未与 `attachment_router` 对齐」。两条指向同一处根因。

### 背景

T03 把「安全的上传落盘」抽到了 `core/upload_security.py`，但**只有 `document_router` 接上了它**。
另外两个上传入口仍是同一类漏洞，客户端文件名照样进路径：

- `backend/app/router/attachment_router.py:148` —— `unique_filename = f"{uuid.uuid4()}_{file.filename}"`
- `backend/app/router/knowledge_router.py:327` —— `file_path = os.path.join(UPLOAD_DIR, f"{kb_uuid}_{file.filename}")`

`os.path.join(UPLOAD_DIR, "uuid_../../x")` 依旧能穿越出 `UPLOAD_DIR`。此外三处各有
`ALLOWED_EXTENSIONS` 与 `get_file_extension` 的**副本**，已经开始漂移（见下方裁决点）。

### 改什么

> **已按用户裁决（方案 A）执行，下列第 1 条随之收窄** —— 原第 1 条写「把 `ALLOWED_EXTENSIONS`
> 一起收拢，三个路由共用一份」，但方案 A 明确「只统一**实现**（净化 / 落盘名 / 限长读取），
> **各路由的白名单成员集合保持不变**」。实际执行的是：把**工具函数**（`safe_filename` /
> `ensure_supported_extension` / `read_upload_with_limit`）并轨到 `core/upload_security.py`，
> `ALLOWED_EXTENSIONS` 仍各自保留在路由文件里。

1. 把 `get_file_extension` 的**逻辑**收拢进 `core/upload_security.py`（即 `ensure_supported_extension`），
   三个路由共用一份；**`ALLOWED_EXTENSIONS` 成员集合按方案 A 各自保留，不做并轨**。
2. `attachment_router` / `knowledge_router` 改用 `safe_filename()`，删除「客户端文件名进路径」的写法。
3. 两个入口补单文件大小上限（复用 `read_upload_with_limit`）。

### 🔴 需要用户裁决

**白名单是否并轨** —— 三者不一致，并轨会**放宽**文档上传的类型，而放宽后的类型能否被下游
docmind 正确处理**未知**：

| 路由 | 当前白名单 |
|------|-----------|
| `document_router` | `pdf, docx, xlsx, xls, txt` |
| `attachment_router` / `knowledge_router` | `pdf, docx, doc, txt, md, html, xlsx, xls, pptx, ppt,` 图片、代码 |

- **方案 A（推荐）**：只统一**代码实现**，白名单各自保留 —— 零行为变更，只堵路径穿越。
- **方案 B**：统一为 attachment 的集合 —— 行为变更，需先验证 docmind 兼容性。
- **方案 C**：定义一个更小的「文档类」统一子集 —— 需要新定义，收益不明。

### 验收

```bash
cd backend && pytest tests/router -q -k "upload"
# 断言：三个路由的落盘名都不含客户端文件名；非法扩展名 400；超限 413
```

### 风险

- 属**跨路由行为变更**，故标 `needs-decision`，**不进入自动循环**，等用户裁决后再执行。

---

## 附：ticket 统计

| 阶段 | 编号 | 数量 |
|------|------|------|
| 1 · 安全（P0） | T01–T07 | 7 |
| 2 · 正确性（P1） | T08–T12 | 5 |
| 3 · 可接手性（P1） | T13–T20 | 8 |
| 4 · 工程化底座 | T21–T31 | 11 |
| 5 · 前端质量 | T32–T37 | 6 |
| 6 · 后端质量 | T38–T40 | 3 |
| 追加 · 安全（第 1 批审查衍生） | T41 | 1 |
| **合计** | | **41** |

**其中决策票（`needs-decision`，不进入自动循环）**：T18、T19、T20、T37、T41 —— 共 5 张。
**`needs-human`**：T10 —— 1 张。
**`needs-infra`**：T07（部分）、T08、T28、T29、T30、T31 —— 6 张。
