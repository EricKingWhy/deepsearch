# Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
# 未经授权，禁止转售或仿制。

"""
T51 回归测试：DeepScout 的 `source_url` 边界归一（缺陷 P-14）。

背景（生产实测）：提示词把 `extracted_facts[].source_url` 声明为「来源URL」（单值），
但当一条事实有多个来源时大模型会返回**数组**。下游三处都把它当字符串用：

- `process()` / `_supplementary_research()` 的 `sources_count` 做
  `len(set(...))` —— 数组不可哈希，直接抛 `TypeError: unhashable type: 'list'`；
- 该异常从 `process()` 逸出，在 `graph.py` 的 `execute_agent` 里只被记成
  `Task exception was never retrieved`，于是**检索阶段静默死亡**：不发
  `research_step` 完成事件、不发 `search_results`，前端 UI 状态恒为
  `search_results=0, charts=0`，永远进不了结果详情页；
- `graph.py` 的 references 又把该字段当 `url` 用，数组会产出非法链接。

修复口径（ticket T51）：新增模块级 `normalize_source_url()`，在**写入 fact 的边界**
（三处 `extracted_facts` 循环）归一为单个字符串；`sources_count` 聚合处再包一层，
以兼容检查点里可能存在的旧数据。多值取**第一个非空项**（该字段被当链接使用）。

T69 追加（第一步）：事实写入边界已收拢为**唯一构造口** `build_fact_entry` /
`build_data_point`，不变量落在那里。因此原先「数源码里赋值/聚合表达式出现次数」的
两条穿透实现断言（`src.count(...) == 3` / `== 2`）被删除，判据改为
**断言构造口唯一且公共可导入**，不再按调用点数量守。

所有用例均不触网、不依赖 Milvus / LLM。
"""

import asyncio
from pathlib import Path

from service.deep_research_v2.agents.scout import (
    DeepScout,
    build_data_point,
    build_fact_entry,
    normalize_source_url,
)
from service.deep_research_v2.state import create_initial_state

SCOUT_SOURCE_PATH = (
    Path(__file__).resolve().parents[3]
    / "app" / "service" / "deep_research_v2" / "agents" / "scout.py"
)


def _make_scout() -> DeepScout:
    """构造一个不触网的 DeepScout（OpenAI client 仅保存配置，不发请求）。"""
    return DeepScout(
        llm_api_key="test-only-key",
        llm_base_url="http://localhost:9999/v1",
        search_api_key="test-only-key",
    )


def _make_state(**kwargs):
    """phase=researching 的初始状态（含一个待研究章节）。"""
    params = {"search_web": False, "search_local": True, "kb_name": "demo"}
    params.update(kwargs)
    state = create_initial_state("测试查询", "sess-t51", **params)
    state["phase"] = "researching"
    state["outline"] = [{"id": "s1", "title": "章节一", "status": "pending"}]
    return state


async def _noop_local_search(_query, top_k=10, kb_name=None):
    """本地检索桩：返回一条不触网的结果。"""
    return [{
        "url": "local://kb/demo/d1",
        "title": "示例文档",
        "summary": "摘要",
        "site_name": "本地知识库",
        "is_local": True,
    }]


# ---------------------------------------------------------------- 纯函数行为层


def test_plain_string_passes_through_stripped():
    assert normalize_source_url(" https://a.example/1 ") == "https://a.example/1"


def test_list_takes_first_non_empty_item():
    assert normalize_source_url(["https://a.example/1", "https://b.example/2"]) == "https://a.example/1"


def test_list_skips_blank_and_none_candidates():
    assert normalize_source_url(["", None, "   ", "https://c.example/3"]) == "https://c.example/3"


def test_empty_or_all_blank_list_becomes_empty_string():
    assert normalize_source_url([]) == ""
    assert normalize_source_url([None, "", "  "]) == ""
    assert normalize_source_url(None) == ""


def test_tuple_and_non_string_are_normalized():
    assert normalize_source_url(("https://d.example/4",)) == "https://d.example/4"
    assert normalize_source_url(123) == "123"


def test_result_is_always_hashable():
    """归一的核心目的就是让下游 set() 可用 —— 对任意输入都必须可哈希。"""
    for value in (None, "", 12, 3.5, ["a", "b"], [None], ("x",), [["nested"]]):
        assert isinstance(normalize_source_url(value), str)


# ---------------------------------------------------------- 接口层：单一构造口


def test_construction_port_is_single_and_public():
    """结构层：构造口**唯一**（3 → 1 / 2 → 1）且公共可导入。

    这与「不再穿透接口」不矛盾 —— 断言的是**构造口只有一个**（主键铸造点唯一），
    而不是「调用点有几个」；调用点数量已由上面的行为层判据覆盖（键集一致性）。
    """
    assert callable(build_fact_entry)
    assert callable(build_data_point)

    src = SCOUT_SOURCE_PATH.read_text(encoding="utf-8")
    assert src.count('"id": f"fact_{uuid.uuid4().hex[:8]}"') == 1, \
        "fact 主键铸造点应唯一（收拢前的三处手抄构造）"
    assert src.count('"id": f"dp_{uuid.uuid4().hex[:8]}"') == 1, \
        "data_point 主键铸造点应唯一（收拢前的两处手抄构造）"


# ---------------------------------------------------- 行为层：真实 process() 路径


async def test_process_does_not_raise_when_source_url_is_list():
    """P-14 回归（与生产 traceback 同口径）：facts 里 source_url 为数组时不得抛异常。

    修复前：`scout.py` 的 `sources_count` 抛 `TypeError: unhashable type: 'list'`，
    即"检索阶段静默死亡"路径 —— 既拿不到 research_step 完成事件，也拿不到
    search_results 事件，故本用例同时断言这两件事都发生了。

    本用例同时是**聚合侧**的接口级判据：这里直接往 `state["facts"]` 塞入
    数组形态的 fact（模拟检查点旧数据，绕过写入边界），`process()` 的全量
    `sources_count` 聚合必须仍能归一 —— 替代了原先「数源码里聚合表达式出现次数」的断言。
    """
    state = _make_state()
    scout = _make_scout()

    async def _noop_fetch(_state):
        return None

    scout._fetch_stock_data_if_relevant = _noop_fetch

    # 模拟 _research_section 写入两条「source_url 为数组、首项相同」的事实
    async def _fake_section(_state, _section):
        for url_list in (
            ["https://a.example/1", "https://b.example/2"],
            ["https://a.example/1", "https://c.example/3"],
        ):
            _state["facts"].append({
                "id": "fact_x",
                "content": "某条事实",
                "source_url": url_list,
            })

    scout._research_section = _fake_section

    await asyncio.wait_for(scout.process(state), timeout=10)

    completed = [
        m for m in state["messages"]
        if m["type"] == "research_step"
        and isinstance(m["content"], dict)
        and m["content"].get("status") == "completed"
    ]
    assert completed, "检索阶段未发出 research_step 完成事件（修复前的静默死亡路径）"
    # 两条事实首项相同 -> 归一后应去重为 1 个来源，而非把数组当两个键
    assert completed[-1]["content"]["stats"]["sources_count"] == 1
    assert any(m["type"] == "search_results" for m in state["messages"]), \
        "未发出 search_results 事件（前端因此进不了结果详情页）"


# ------------------------------------------------- 边界层：extracted_facts 写入


async def test_fact_written_from_extracted_facts_has_string_source_url():
    """边界层：数组 source_url 经 _research_section 的真实事实循环后落成字符串。"""
    state = _make_state()
    scout = _make_scout()
    scout._execute_local_search = _noop_local_search

    async def _fake_analyze(*_args, **_kwargs):
        return {"extracted_facts": [{
            "content": "某条事实",
            "source_url": ["https://a.example/1", "https://b.example/2"],
            "source_name": "某来源",
        }]}

    scout._analyze_search_results = _fake_analyze

    await asyncio.wait_for(
        scout._research_section(state, {"id": "s1", "title": "章节一", "search_queries": ["q1"]}),
        timeout=10,
    )

    assert state["facts"], "未写入任何事实"
    assert state["facts"][0]["source_url"] == "https://a.example/1"
    assert isinstance(state["facts"][0]["source_url"], str)
