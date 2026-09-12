# 执行循环协议（LOOP-PROTOCOL）

> **本文件是流程的唯一权威来源。优先级高于仓库内其它任何流程说明（含 `CLAUDE.md`、`AGENTS.md`、历史会话中的约定）。**
> 与其它文档冲突时，以本文件为准。

---

## 0. 强制前置动作（防漂移）

在开始任何 ticket 之前，**必须先重读本文件**，不得凭记忆或摘要推断流程。

触发「强制重读」的情形（满足任意一条即触发）：

- (a) 不确定当前循环走到哪一步；
- (b) 不记得批量审查的 fixed point，或当前批次边界；
- (c) 上下文刚被压缩 / 摘要 / 换会话。

**重读是每个 ticket 的第一个动作，不是可选项。** 找不到状态时，先读 `docs/hardening/TRACKER.md` 恢复，禁止猜测式继续施工。

---

## 1. 循环总览

```
ticket 1 ─┐
ticket 2 ─┼─→ 批量审查(第1批) ─→ 修复 findings ─→ 推进 fixed point
ticket 3 ─┘
ticket 4 ─┐
ticket 5 ─┼─→ 批量审查(第2批) ─→ 修复 findings ─→ 推进 fixed point
ticket 6 ─┘
...
全部 ticket 完成 ─→ 最终全量审查(fixed point = main) ─→ 修复 ─→ 结束
```

全流程**自动执行，无需逐票向用户确认**。仅当出现以下情况才停下来问用户：

1. **规格实质冲突** —— PRD / ticket 之间互相矛盾，且无法从现有材料推断取舍；
2. **架构分叉** —— 需要改变模块边界、公开接口契约、数据模型，或删除/替换整条技术路线。

「停下来问」的正确形式：给出 2–3 个候选方案 + 各自代价 + 你的推荐，等用户裁决。

---

## 2. 单 ticket 执行

1. 执行 `/implement` 完成当前 ticket。
   **跳过 `/implement` 自带的收尾 `/code-review`** —— 本流程改为批量审查，避免同一票双审。
2. ticket 完成后**自行 commit**：
   - **测试全绿才 commit**，测试不绿就继续修，不得提交；
   - commit message 描述**工程事实**（做了什么、为什么），不要写「优化」「改进」这类空话；
   - 遵守第 6 节的提交与合并规范。
3. 在 `docs/hardening/TRACKER.md` 追加一行记录（见第 7 节字段表）。

### 验收口径

- **每张 ticket 优先设计成不依赖基础设施（Postgres / Redis / Milvus / ES）即可验证。**
  优先顺序：纯函数单测 → mock 单测 → 前端 vitest → 构建 / lint / 静态断言脚本。
- 确实需要跨服务才能验证的 ticket，在 ticket 里打 `needs-infra` 标记，并写明需要启动哪些容器。
- **禁止把「人工检查」当作验收方式。** 验收必须是可执行的命令 + 可判定的输出。
- 需要用户本人在第三方后台操作（吊销密钥、建数据库只读账号等）的 ticket，打 `needs-human` 标记，写清操作步骤，**不要跳过、不要假装完成**。

### 决策票

带 `needs-decision` 标记的 ticket（大重构 / 技术路线替换）**不自动执行**：

- 把票留在 `BLOCKED` 状态，在 TRACKER 记录「等待用户裁决」；
- 用户明确批准后才执行；
- 同一批次里其它非决策票正常推进，不要因为一张决策票卡住整批。

---

## 3. 批量审查（每 3 个 ticket 一次）

1. 每完成 **3 个 ticket**，对这批 ticket 的**累计 diff** 跑一次 `/code-review`。
   - 批大小由执行者按 ticket 体量决定，可在 **2–4** 之间浮动；
   - 遇到依赖链断点等自然分界可提前收批，但一批不得超过 4 张；
   - **fixed point = 上一批审查结束时的 commit**（第一批的 fixed point = 基线 commit）。
2. findings 分级处理：
   - **一眼能定位的** → 直接最小修复 + 跑测试，**不停顿、不询问**；
   - **真正疑难的**（无法稳定复现 / 间歇性 / 回归） → 才用 `/diagnosing-bugs` 先定位根因再修。
3. 修复后**不重跑全量 review**：跑测试 + 自查 diff 确认 finding 已消除即可。
   **仅当修复触及架构或契约时**，才做增量复查（只复查上一轮的 findings）。
4. 确认无误后 commit 修复，并把 TRACKER 中本批审查状态推进到该修复 commit，进入下一批。

---

## 4. 总门禁（全部 ticket 完成后）

1. 对整条分支跑一次**最终全量 `/code-review`**，**fixed point = `main`**。
2. findings 全部按第 3 节第 2、3 条的方式修复并验证后，任务才算结束。
3. 结束前确认 TRACKER 中不存在 `BLOCKED`（除用户明确驳回的决策票）或未验证项。

---

## 5. 提交与合并规范

- **每张 ticket 一条分支**：`ticket/T<编号>-<短横线短描述>`，例如 `ticket/T13-remove-hardcoded-keys`。
- 分支上提交完成后**开 PR 并合并到 `main`**（`gh pr create` + `gh pr merge --merge`）。
- **禁止直接 push 到 `main`**（基线整理 commit 除外）。
- 合并方式用 merge commit，**不要 squash** —— 保留 commit 粒度是本项目的明确目标。
- commit message 使用中文正文 + 英文类型前缀，例如：
  `fix(scout): 本地检索按 kb 集合名检索，修复 DeepResearch 搜不到用户文档`

---

## 6. 密钥与敏感信息红线（不可违反）

- **严禁**把任何真实密钥、Token、口令写入被 git 跟踪的文件（含 PRD、ticket、issue 正文、commit message、日志输出、截图）。
- 代码中的密钥一律通过 `os.getenv` / `os.environ` 读取，**不留默认值兜底**。
- 需要密钥的功能验证，从 `backend/.env`（已被 gitignore）读取，不要把值打印到终端或写入文件。
- 往 GitHub 推送前自查：`git grep -nE "(sk-[A-Za-z0-9]{20,}|Bearer [A-Za-z0-9]{20,})"`，命中即停下处理。
- 已知遗留风险（用户已确认暂不处理）：`backend/app/service/dr_g.py` 的历史密钥存在于 `ccbb38a` 提交历史中。**新增提交不得再引入任何密钥。**

---

## 7. TRACKER 字段

`docs/hardening/TRACKER.md` 每个 ticket 一行，字段固定：

| 字段 | 含义 |
|------|------|
| `ID` | ticket 编号，如 `T13` |
| `标题` | 与 issue 标题一致 |
| `Issue` | GitHub issue 编号 |
| `状态` | `TODO` / `DOING` / `DONE` / `BLOCKED` / `CANCELLED` |
| `分支` | 分支名 |
| `Commit` | 该 ticket 的 commit SHA（短） |
| `PR` | PR 编号 |
| `验收` | 实际执行的验收命令 + 结果（`PASS` / `FAIL`） |
| `批次` | 所属审查批次编号 |
| `批次审查` | `PENDING` / `REVIEWED@<commit>` / `FIXED@<commit>` |

---

## 8. 交接说明（给后续接手的 AI）

1. 读 `docs/hardening/LOOP-PROTOCOL.md`（本文件）→ 2. 读 `docs/hardening/prd.md` → 3. 读 `docs/hardening/TRACKER.md` 恢复进度 → 4. 从 TRACKER 里第一个 `TODO` 且非 `BLOCKED` 的 ticket 继续。

ticket 的完整定义在 `docs/hardening/tickets/T<编号>-*.md`，与 GitHub issue 一一对应。
**本地 ticket 文件是权威定义（source of truth）**，issue 是它的镜像；两者不一致时以本地文件为准，并把 issue 同步过来。
