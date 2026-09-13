# Copyright © 2026 深圳市深维智见教育科技有限公司 版权所有
# 未经授权，禁止转售或仿制。

"""文件上传安全工具：文件名净化、扩展名校验、大小限制。

**为什么独立成模块**：``router/document_router.py`` 会连带引入 milvus / ES / docmind
等重依赖，导致这些纯粹的上传校验逻辑无法在「无基础设施」的 CI 中验证（见 T27 口径）。
本模块只依赖标准库 + FastAPI，可被单测直接导入。

事实来源：T03 / 事实 F-02 —— 原实现用 ``f"/tmp/{file.filename}"`` 落盘，
文件名完全由客户端控制，``../../`` 片段足以把文件写出 ``/tmp``。
"""

import os
import uuid
from typing import Iterable, Optional

from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST

# 分块读取上传内容时的块大小
READ_CHUNK_BYTES = 1024 * 1024

# 413 的名字在 starlette 新旧版本间改过（REQUEST_ENTITY_TOO_LARGE → CONTENT_TOO_LARGE），
# 而 requirements 只给了 `fastapi>=0.104.0` 这样的下界。为避免绑定某个 starlette 版本，
# 这里直接用数值。
HTTP_413_CONTENT_TOO_LARGE = 413

# 单文件大小上限：三个上传入口（document / attachment / knowledge）共用同一口径。
# 取常量即可，不必做成可配置项。
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def sanitize_extension(filename: Optional[str]) -> str:
    """从客户端文件名中取出扩展名：小写、含点。

    先剥掉客户端可能塞入的目录部分（**同时兼容 POSIX 与 Windows 分隔符**），
    再做扩展名提取。否则 ``..\\..\\x.pdf`` 这类名字在后续拼接路径时仍然危险。
    """
    basename = (filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    return os.path.splitext(basename)[1].lower()


def safe_filename(
    original_filename: Optional[str] = None,
    *,
    extension: Optional[str] = None,
) -> str:
    """生成服务端**完全可控**的落盘文件名：``<uuid><扩展名>``。

    刻意不保留客户端提供的文件名（哪怕只当后缀或前缀）：该字符串不受任何约束，
    ``../`` 片段足以把文件写出目标目录。原始文件名若需展示，请作为**数据字段**入库，
    不要进入路径。

    ``original_filename`` 仅用于推导扩展名（当 ``extension`` 未显式给出时）。
    """
    ext = extension if extension is not None else sanitize_extension(original_filename)
    return f"{uuid.uuid4()}{ext}"


def ensure_supported_extension(filename: Optional[str], allowed: Iterable[str]) -> str:
    """校验扩展名是否在白名单内；不支持时抛 400。

    返回规范化后的扩展名，供调用方直接用于生成落盘文件名。
    """
    extension = sanitize_extension(filename)
    allowed_set = set(allowed)
    if extension not in allowed_set:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=(
                f"不支持的文件类型: {extension or '(无扩展名)'}。"
                f"支持的类型: {', '.join(sorted(allowed_set))}"
            ),
        )
    return extension


async def read_upload_with_limit(upload, max_bytes: int) -> bytes:
    """分块读取上传内容；累计超过 ``max_bytes`` 立即抛 413。

    之所以不写成 ``content = await upload.read()`` 再比长度：那样会把整个文件先读进
    内存，大小校验发生在内存已被占满之后，**挡不住超大文件打爆内存**。
    """
    chunks = []
    total = 0
    while True:
        chunk = await upload.read(READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=HTTP_413_CONTENT_TOO_LARGE,
                detail=f"文件超过大小上限 {max_bytes // (1024 * 1024)} MB",
            )
        chunks.append(chunk)
    return b"".join(chunks)
