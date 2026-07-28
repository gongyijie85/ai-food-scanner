"""utils/history.py 会话隔离相关测试."""

import json
import os

import streamlit as st

from utils import history


class TestSessionIsolation:
    def test_different_sessions_have_isolated_history(self, tmp_path, monkeypatch):
        """不同会话保存的历史记录应互相隔离，互不可见."""
        monkeypatch.setattr(history, "_DATA_DIR", str(tmp_path))

        monkeypatch.setattr(st, "session_state", {})
        history.save_history({"product_name": "会话A的产品", "score": 90})

        monkeypatch.setattr(st, "session_state", {})
        result_b = history.load_history()

        assert result_b == []

    def test_same_session_sees_its_own_history(self, tmp_path, monkeypatch):
        """同一会话内保存的记录应能读回."""
        monkeypatch.setattr(history, "_DATA_DIR", str(tmp_path))
        monkeypatch.setattr(st, "session_state", {})

        history.save_history({"product_name": "会话B的产品", "score": 80})
        result = history.load_history()

        assert len(result) == 1
        assert result[0]["product_name"] == "会话B的产品"

    def test_history_files_are_written_per_session_id(self, tmp_path, monkeypatch):
        """磁盘上应生成以 session_id 命名的独立文件."""
        monkeypatch.setattr(history, "_DATA_DIR", str(tmp_path))
        monkeypatch.setattr(st, "session_state", {})

        history.save_history({"product_name": "测试", "score": 70})
        session_id = history._get_session_id()

        expected_path = os.path.join(str(tmp_path), f"history_{session_id}.json")
        assert os.path.exists(expected_path)
        with open(expected_path, encoding="utf-8") as f:
            data = json.load(f)
        assert data[0]["product_name"] == "测试"

    def test_add_history_writes_both_summary_and_full_snapshot_isolated(
        self, tmp_path, monkeypatch
    ):
        """add_history 应同时写入摘要与完整快照，且均按会话隔离."""
        monkeypatch.setattr(history, "_DATA_DIR", str(tmp_path))
        monkeypatch.setattr(st, "session_state", {})

        history.add_history(
            {"product_name": "测试", "score": 60, "type": "food", "additives": []}
        )

        assert len(history.load_history()) == 1
        assert len(history.load_history_full()) == 1
        assert history.load_history_full()[0]["product_name"] == "测试"

    def test_public_load_functions_expose_working_clear(self):
        """load_history/load_history_full 应暴露可调用的 .clear()（app.py 演示模式依赖此接口）."""
        # 这两个调用不应抛出 AttributeError（回归测试：曾因 @st.cache_data 装饰在
        # 私有函数上，导致公开包装函数缺少 .clear() 属性）。
        history.load_history.clear()
        history.load_history_full.clear()
