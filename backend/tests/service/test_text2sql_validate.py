# Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
# 未经授权，禁止转售或仿制。

"""
T09 回归测试：text2sql SQL 校验封堵 UNION 绕过。

背景（事实 F-09）：旧校验用黑名单，FORBIDDEN 含 'UNION ALL SELECT' 但 UNION
本身在 ALLOWED 中，`SELECT ... UNION SELECT ...` 可绕过校验。

修复口径（ticket T09）：
- 主判据改为允许列表：语句必须以 SELECT 或 WITH 开头，且禁止任何形式的 UNION；
- 黑名单降为辅助兜底；
- 清理 '--'（有专门注释检查）与 'UNION ALL SELECT'（被 UNION 全禁覆盖）的重复项。

`validate_sql` 是纯函数（只依赖类常量），不依赖数据库 / LLM。
"""

import pytest
from service.text2sql_service import Text2SQLService


@pytest.fixture(scope="module")
def service() -> Text2SQLService:
    """不传 db_connection_string，不建 engine、不触网。"""
    return Text2SQLService(
        llm_api_key="test-only-key",
        llm_base_url="http://localhost:9999/v1",
    )


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1 UNION SELECT 2",
        "SELECT 1 UNION ALL SELECT 2",
        "select 1 union select 2",                       # 小写绕过
        "SELECT 1 uNiOn SeLeCt 2",                       # 混合大小写绕过
        "SELECT 1\nUNION\nSELECT 2",                     # 换行分隔绕过
        "SELECT metric_name FROM industry_stats UNION SELECT policy_name FROM policy_data",
        "WITH t AS (SELECT 1) SELECT * FROM t UNION SELECT 2",
    ],
)
def test_union_variants_are_rejected(service, sql):
    ok, msg = service.validate_sql(sql)
    assert not ok, f"未拦截 UNION 变体: {sql!r}"
    assert msg


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM t; DROP TABLE t",
        "SELECT 1; SELECT 2",
        "DELETE FROM t",
        "UPDATE t SET a = 1",
        "INSERT INTO t VALUES (1)",
        "DROP TABLE t",
        "SELECT 1 -- comment",
        "SELECT 1 /* comment */",
        "WITH x AS (DELETE FROM t RETURNING *) SELECT * FROM x",  # PG 数据修改 CTE
        "",
        "   ",
        None,
        "EXEC sp_help",
    ],
)
def test_dangerous_sql_is_rejected(service, sql):
    ok, msg = service.validate_sql(sql)
    assert not ok, f"未拦截危险输入: {sql!r}"
    assert msg


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT id, name FROM users WHERE id = 1",
        "select metric_name, metric_value from industry_stats where year = 2024",
        "SELECT industry_name, SUM(metric_value) AS total FROM industry_stats GROUP BY industry_name ORDER BY total DESC LIMIT 10",
        "SELECT 1;",                                      # 允许末尾分号
        "WITH t AS (SELECT 1 AS v) SELECT v FROM t",      # WITH 开头的 CTE 查询
        "SELECT a FROM t INNER JOIN b ON t.id = b.id WHERE a LIKE '%x%'",
        "SELECT CASE WHEN a > 1 THEN 'high' ELSE 'low' END FROM t",
    ],
)
def test_legitimate_readonly_sql_passes(service, sql):
    ok, msg = service.validate_sql(sql)
    assert ok, f"误拦合法只读查询: {sql!r}（原因: {msg}）"
