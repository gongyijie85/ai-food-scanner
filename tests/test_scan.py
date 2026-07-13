"""扫描页相关单元测试

覆盖：统一图片上传入口的校验与识别路径
"""

import io
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pages.scan import _scan_validate_and_recognize


class FakeUploadedFile:
    """模拟 Streamlit UploadedFile 对象."""

    def __init__(self, name, size, content=b"fake image bytes"):
        self.name = name
        self.size = size
        self._buffer = io.BytesIO(content)

    def seek(self, pos):
        self._buffer.seek(pos)

    def read(self, size=-1):
        return self._buffer.read(size)


class StopTriggered(Exception):
    """模拟 Streamlit st.stop() 中断脚本执行."""


class TestUnifiedUploadValidation:
    """测试统一上传入口的校验与识别路径."""

    def _patch_stop(self, monkeypatch):
        """把 st.stop 替换为抛出 StopTriggered，方便测试断言."""
        monkeypatch.setattr(
            "pages.scan.st.stop", lambda: (_ for _ in ()).throw(StopTriggered())
        )

    def test_oversize_file_shows_error_and_stops(self, monkeypatch):
        """超过 5MB 时提示并停止，不继续识别."""
        errors = []
        monkeypatch.setattr("pages.scan.st.error", errors.append)
        self._patch_stop(monkeypatch)

        oversized = FakeUploadedFile("big.jpg", 6 * 1024 * 1024)
        with pytest.raises(StopTriggered):
            _scan_validate_and_recognize(oversized, "fake-api-key", [])

        assert any("5MB" in msg for msg in errors)

    def test_missing_api_key_shows_error_and_stops(self, monkeypatch):
        """未配置 API key 时提示并停止."""
        errors = []
        monkeypatch.setattr("pages.scan.st.error", errors.append)
        self._patch_stop(monkeypatch)

        uploaded = FakeUploadedFile("test.jpg", 1024)
        with pytest.raises(StopTriggered):
            _scan_validate_and_recognize(uploaded, "", [])

        assert any("API 密钥" in msg for msg in errors)
