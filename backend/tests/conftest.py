"""conftest.py — 测试基础设施配置。

条件兼容：Python 3.8+ 使用内置 AsyncMock，Python 3.7 使用自定义实现。
"""

import sys

import pytest

if sys.version_info >= (3, 8):
    from unittest.mock import AsyncMock
else:
    from unittest.mock import MagicMock

    class AsyncMock(MagicMock):
        async def __call__(self, *args, **kwargs):
            return super().__call__(*args, **kwargs)

        def __await__(self):
            future = self.__call__()
            return future.__await__()


__all__ = ["AsyncMock"]
