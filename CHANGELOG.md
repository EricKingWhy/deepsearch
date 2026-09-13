# Changelog

格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号语义遵循 [SemVer](https://semver.org/lang/zh-CN/)。

> 说明：0.1.0 小节为「质量硬化」计划的汇总；后续条目随 PR 合并逐条追加。

## [0.1.0] - 2026-09-13

### Added

- 架构总览文档 `docs/architecture.md`（两条研究路线 / V2 流程 / RAG 数据流 / 基础设施矩阵 / 目录导航）
- `CONTRIBUTING.md`、`.editorconfig`、MIT `LICENSE`、issue/PR 模板（`.github/`）
- `backend/ruff.toml` 最小规则集（E9/F63/F7/F82），`ruff check` 可执行
- V1 ReAct 三件套与 V2 LangGraph 路径的「有意保留」标注（PRD NG-2/NG-3）
- 后端/前端统一版本号 `0.1.0`（本文件即变更入口）

### Changed

- 数据库连接池参数显式化（pool_size/max_overflow/pool_recycle）；`create_all` 改为 `DB_AUTO_CREATE=1` 显式开关，建表以 `backend/migrations/` 手写 SQL 为准
- `serialize_event` 抽离至 `core/serialization.py`，`research_router` 不再反向依赖 V1 模块
- `requirements.txt` 去重 langfuse（取 `>=4.0.0,<5.0.0`）并按用途分区；alembic 标注「预留未使用」

### Fixed

- text2sql UNION 绕过：`validate_sql` 以 SELECT/WITH 开头判据 + `\bUNION\b` 词边界校验
- Scout 本地知识库集合名不匹配（硬编码 → `retrieval_service` 统一实现）；`kb_name` 透传链修复
- 清除 8 处裸 `except`（改 `except Exception` + 按上下文记日志）
- READMED/代码注释三处文档漂移（langfuse 版本、ES 旧注释、知识图谱宣称）
