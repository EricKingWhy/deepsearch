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
| `main` 当前 tip（2026-09-13 核实，本地＝远端） | `2047a7728c3679908f4907faa30433442b3767a0` |
| 当前批次 | 1 |
| 当前 fixed point（上一批审查结束 commit） | `9342913` |
| 当前分支前缀 | `ticket/T<编号>-` |
| 合并目标 | 本地 `main` 分支（merge commit，不用 squash） |
| 总 ticket 数 | 40 |
| 已完成 | 0 |
| 决策票待裁决 | T18、T19、T20、T37 |

## 批次审查记录

| 批次 | 覆盖 ticket | fixed point（起点） | 审查 commit（终点） | findings 数 | 修复 commit | 状态 |
|------|------------|--------------------|--------------------|------------|------------|------|
| 1 | T01–T03 | `9342913` | — | — | — | PENDING |

## ticket 明细

状态取值：`TODO` / `DOING` / `DONE` / `BLOCKED` / `CANCELLED`

| ID | 标题 | Issue | 状态 | 分支 | Commit | PR | 验收 | 批次 | 批次审查 |
|----|------|-------|------|------|--------|----|------|------|---------|
| T01 | 移除 dr_g.py 硬编码 API Key | — | TODO | — | — | — | — | 1 | PENDING |
| T02 | JWT 密钥必填并在启动时校验 | — | TODO | — | — | — | — | 1 | PENDING |
| T03 | document_router 上传安全加固 | — | TODO | — | — | — | — | 1 | PENDING |
| T04 | document_router 增加鉴权 | — | TODO | — | — | — | — | 2 | PENDING |
| T05 | chat / search / news 路由补充鉴权 | — | TODO | — | — | — | — | 2 | PENDING |
| T06 | 收紧 CORS 配置 | — | TODO | — | — | — | — | 2 | PENDING |
| T07 | docker-compose 明文口令改为环境变量注入 | — | TODO | — | — | — | — | 3 | PENDING |
| T08 | 修复 Scout 本地知识库检索的集合名不匹配 | — | TODO | — | — | — | — | 3 | PENDING |
| T09 | 修复 text2sql SQL 校验可被 UNION SELECT 绕过 | — | TODO | — | — | — | — | 3 | PENDING |
| T10 | text2sql 使用只读数据库账号兜底 | — | BLOCKED | — | — | — | 等待用户创建只读角色 | 4 | PENDING |
| T11 | 清除裸 except 并补日志 | — | TODO | — | — | — | — | 4 | PENDING |
| T12 | 收敛数据库连接池与会话生命周期 | — | TODO | — | — | — | — | 4 | PENDING |
| T13 | 显式标注 LangGraph 运行时路径为有意保留 | — | TODO | — | — | — | — | 5 | PENDING |
| T14 | 显式标注 V1 ReAct 编排为保留的备选路线 | — | TODO | — | — | — | — | 5 | PENDING |
| T15 | 抽离 serialize_event | — | TODO | — | — | — | — | 5 | PENDING |
| T16 | 修复文档与代码漂移 | — | TODO | — | — | — | — | 6 | PENDING |
| T17 | 新增架构总览文档 | — | TODO | — | — | — | — | 6 | PENDING |
| T18 | requirements.txt 去重与依赖分区 | — | BLOCKED | — | — | — | 等待用户裁决锁定策略 | 6 | PENDING |
| T19 | 决策票：alembic 去留 | — | BLOCKED | — | — | — | 等待用户裁决 | — | — |
| T20 | 决策票：chat/index.tsx 是否拆分 | — | BLOCKED | — | — | — | 等待用户裁决 | — | — |
| T21 | 新增 LICENSE | — | TODO | — | — | — | — | 7 | PENDING |
| T22 | 新增 CONTRIBUTING.md | — | TODO | — | — | — | — | 7 | PENDING |
| T23 | 新增 .editorconfig | — | TODO | — | — | — | — | 7 | PENDING |
| T24 | 新增 issue 与 PR 模板 | — | TODO | — | — | — | — | 8 | PENDING |
| T25 | 新增 CHANGELOG.md 并初始化版本号 | — | TODO | — | — | — | — | 8 | PENDING |
| T26 | 新增后端 ruff 配置 | — | TODO | — | — | — | — | 8 | PENDING |
| T27 | 后端测试分层：无基础设施单测可独立运行 | — | TODO | — | — | — | — | 9 | PENDING |
| T28 | 新增 CI：后端 pytest | — | TODO | — | — | — | — | 9 | PENDING |
| T29 | 新增 CI：前端 lint + vitest + build | — | TODO | — | — | — | — | 9 | PENDING |
| T30 | 新增 backend/Dockerfile 并接入 compose | — | TODO | — | — | — | — | 10 | PENDING |
| T31 | start-services.sh 现代化 | — | TODO | — | — | — | — | 10 | PENDING |
| T32 | 清理 console.log 残留 | — | TODO | — | — | — | — | 10 | PENDING |
| T33 | eslint 启用 no-explicit-any 并收敛 store 层 any | — | TODO | — | — | — | — | 11 | PENDING |
| T34 | vite 构建分包 + 路由懒加载 | — | TODO | — | — | — | — | 11 | PENDING |
| T35 | ECharts 真正拆包 | — | TODO | — | — | — | — | 11 | PENDING |
| T36 | 清理注释死代码 | — | TODO | — | — | — | — | 12 | PENDING |
| T37 | 决策票：前端 JWT 存储方式 | — | BLOCKED | — | — | — | 等待用户裁决 | — | — |
| T38 | 清除 print 调试残留 | — | TODO | — | — | — | — | 12 | PENDING |
| T39 | 补 text2sql.validate_sql 单元测试 | — | TODO | — | — | — | — | 12 | PENDING |
| T40 | 补 security 鉴权单元测试 | — | TODO | — | — | — | — | 13 | PENDING |

## 执行日志

> append-only。每完成一张 ticket 追加一行。

| 时间 | ticket | 动作 | 结果 |
|------|--------|------|------|
| 2026-09-13 | — | 基线整理：工作树入库、协议落盘、PRD 与 ticket 定义写入 `docs/hardening/` | 基线 commit `9342913` |
| 2026-09-13 | — | 推送 `main` 时发现 `git status -sb` 报 `[gone]`、`origin/main` 不可解析。核实本地＝远端＝`2047a77`，对象与历史完整，确认为远程跟踪引用被清扫的良性现象。修正文档：所有审查基准改为显式 commit SHA，并新增 `LOOP-PROTOCOL.md` §9 引用可用性说明 | 文档修正 commit（见下） |
