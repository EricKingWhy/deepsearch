# Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
# 未经授权，禁止转售或仿制。

"""SSE 事件序列化工具（从 service/dr_g.py 原样抽离，见 tickets.md T15）。

抽离目的：research_router 只需要这一个序列化函数，此前却因此反向依赖
V1 备选路线模块 dr_g，模糊了模块边界。本模块为中立公共位置，无任何重依赖。
"""

import json
import logging
from typing import Any, Dict


def serialize_event(event_data: Dict[str, Any]) -> str:
    """将事件数据序列化为JSON字符串"""
    def json_serializer(obj):
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, Exception):
            return str(obj)
        raise TypeError(f"Type {type(obj)} not serializable")

    try:
        return json.dumps(event_data, default=json_serializer, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Failed to serialize event: {e}")
        return json.dumps({"type": "error", "content": f"Serialization error: {e}"})
