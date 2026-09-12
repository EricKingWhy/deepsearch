# AGENTS.md

本文件面向所有在本仓库工作的 AI 编码助手（Claude Code / Codex / Cursor / WorkBuddy 等）。

## 🔴 第一优先级：执行循环协议

**动手之前必须先读 [`docs/hardening/LOOP-PROTOCOL.md`](docs/hardening/LOOP-PROTOCOL.md)。**

该文件是流程的唯一权威来源，优先级高于本文件、`CLAUDE.md` 以及任何历史会话中的约定。它规定了：

- 每个 ticket 开工前的**强制重读**动作（防止上下文压缩后凭记忆漂移）；
- 单 ticket 的执行 / 提交 / 记录方式；
- 每 3 个 ticket 一次的**批量代码审查**机制与 fixed point 推进规则；
- 全部完成后的**最终全量审查**门禁；
- 分支、PR、commit message 规范；
- **密钥红线**（严禁把真实密钥写入任何被跟踪的文件）。

## 📋 当前项目上下文

- **PRD / 需求**：`docs/hardening/prd.md`
- **进度追踪**：`docs/hardening/TRACKER.md`（恢复状态先读这个）
- **ticket 定义**：`docs/hardening/tickets/T<编号>-*.md`（权威定义，GitHub issue 是镜像）
- **项目概览与架构**：`CLAUDE.md`
- **启动与配置**：`READMED.md`

## ⚙️ 常用命令

```bash
# 基础设施
./start-services.sh start          # 启动 PG / Redis / Milvus / ES / MinIO
./start-services.sh status

# 后端
cd backend && python app/app_main.py                 # :8000
cd backend && pytest tests -q                        # 单元测试
cd backend && ruff check app                         # 静态检查

# 前端
cd frontend && npm run dev                            # :5183
cd frontend && npm run lint
cd frontend && npm run test                           # vitest
cd frontend && npm run build
```

## 🚫 硬性约束

1. **不得**把真实密钥 / Token / 口令写入任何被 git 跟踪的文件（PRD、ticket、issue、commit message、日志、截图一律包括）。
2. **不得**直接 push 到 `main`（基线整理 commit 除外）。每张 ticket 走独立分支 + PR。
3. **不得**把「人工检查」当作验收方式。验收必须是可执行命令 + 可判定输出。
4. 遇到规格冲突或架构分叉 → 停下来问用户，给出候选方案 + 代价 + 推荐，不要自行拍板。
