# 贡献指南

> 一屏原则：细则一律回链权威文档，本文件不复制其内容，避免两份规范漂移。

## 1. 环境准备

见 [`READMED.md`](./READMED.md)（后端 conda + docker-compose 基础设施；前端 vite）。
架构速览见 [`docs/architecture.md`](./docs/architecture.md)——改动前先定位「改哪个功能动哪个目录」。

## 2. 分支与提交

- 一票一分支一 PR：分支名 = 票号主题（如 `T21-license`）；合并用 merge commit，**不 squash 不 rebase 远端**。
- commit message：`英文类型前缀 + 中文正文`，说明「改了什么、依据哪条票/事实」。细则见
  [`docs/hardening/LOOP-PROTOCOL.md`](./docs/hardening/LOOP-PROTOCOL.md) §5，本文件不另立标准。

## 3. 代码风格

- 后端：`ruff check app tests`（规则集见 [`backend/ruff.toml`](./backend/ruff.toml)，最小集起步、逐步放开）。
- 前端：`npm run lint`（eslint 9）+ prettier；编辑器约定见 [.editorconfig](./.editorconfig)（py 4 空格 / ts 2 空格 / lf）。
- `langgraph` 与 V1 三件套（`dr_g.py` 等）是**有意保留**的备选实现，不得删除（PRD NG-2/NG-3，见 `docs/hardening/prd.md`）。

## 4. 测试与验收

- 改可执行代码必须带验证；全量口径：`cd backend && pytest tests -m "not integration"`。
- 验收命令必须可执行、可复现（标准见 `docs/hardening/prd.md` §7）；纯注释/文档票同样必须 `py_compile` 或跑受影响测试。

## 5. 密钥红线（不可违反）

**不得向仓库提交任何真实密钥**（API key、口令、token）。示例/占位一律用
`test-only-*` 风格假值；敏感配置走 `.env`（已 gitignore）。细则见
[`AGENTS.md`](./AGENTS.md) 与 `docs/hardening/LOOP-PROTOCOL.md` §6。
