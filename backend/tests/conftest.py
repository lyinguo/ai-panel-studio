"""conftest.py — 测试基础设施配置。

提供 Python 3.7 兼容的 AsyncMock。
"""

import asyncio
from unittest.mock import MagicMock

import pytest


# ============================================================
# Python 3.7 AsyncMock 兼容实现
# ============================================================

class AsyncMock(MagicMock):
    """异步 Mock，支持 await 语法（Python 3.7 兼容）。"""

    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)

    def __await__(self):
        future = self.__call__()
        return future.__await__()
