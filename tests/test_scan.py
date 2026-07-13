"""扫描页相关单元测试

覆盖：_resolve_uploaded_input 互斥选择逻辑
"""

import io
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pages.scan import _resolve_uploaded_input


class FakeUploadedFile:
    """模拟 Streamlit UploadedFile / camera_input 返回对象."""

    def __init__(self, name, size):
        self.name = name
        self.size = size
        self._buffer = io.BytesIO(b"fake image bytes")

    def seek(self, pos):
        self._buffer.seek(pos)

    def read(self, size=-1):
        return self._buffer.read(size)


class TestResolveUploadedInput:
    """测试 _resolve_uploaded_input 在 camera_input 与 file_uploader 之间的选择逻辑."""

    def test_none_returns_none(self):
        """两者都为空时返回 None."""
        assert _resolve_uploaded_input(None, None) is None

    def test_camera_wins_over_file(self):
        """camera 和 file 同时存在时优先返回 camera."""
        camera = FakeUploadedFile("camera.jpg", 1024)
        file_obj = FakeUploadedFile("album.jpg", 2048)
        selected = _resolve_uploaded_input(camera, file_obj)
        assert selected is camera

    def test_file_used_when_camera_none(self):
        """只有 file 时返回 file."""
        file_obj = FakeUploadedFile("album.jpg", 2048)
        selected = _resolve_uploaded_input(None, file_obj)
        assert selected is file_obj

    def test_camera_used_when_file_none(self):
        """只有 camera 时返回 camera."""
        camera = FakeUploadedFile("camera.jpg", 1024)
        selected = _resolve_uploaded_input(camera, None)
        assert selected is camera


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
