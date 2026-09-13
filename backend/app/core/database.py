# Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
# 未经授权，禁止转售或仿制。

"""数据库连接和会话管理"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


def _require_env(name: str) -> str:
    """读取必需的环境变量；缺失时显式失败并指出变量名。

    刻意**不提供默认值**：历史默认值是公开可知的弱口令（形如 `postgres` + 数字后缀），
    一旦兜底，compose 忘记注入变量时应用会静默连上同一个弱口令的库 ——
    既看不出配置缺失，也把弱口令固化进部署。
    """
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"缺少必需的环境变量 {name}。请参照仓库根目录的 .env.example 配置后重试，"
            f"不要把真实口令写入受版本控制的文件。"
        )
    return value


# 从环境变量获取数据库配置
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
# 口令必填：本行在**导入期**执行，因此缺失会让应用在启动阶段就终止，
# 而不是等到第一次建连才暴露（与 core.security 的 JWT 校验同一风格）。
POSTGRES_PASSWORD = _require_env("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB", "industry_assistant")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """获取数据库会话的依赖函数"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
