"""扫描页拍得清引导 HTML 单测."""

from components.scan_guide import (
    build_scan_fail_html,
    build_scan_hero_html,
    build_scan_steps_html,
)


class TestScanHero:
    def test_mentions_ingredients_label(self):
        html = build_scan_hero_html()
        assert "配料" in html
        assert "scan-viewfinder" in html


class TestScanSteps:
    def test_three_steps(self):
        html = build_scan_steps_html()
        assert "光线" in html
        assert "平行" in html or "平" in html
        assert "占满" in html or "字要大" in html
        assert html.count("scan-step-card") == 3


class TestScanFail:
    def test_json_fail_not_technical(self):
        html = build_scan_fail_html("json")
        assert "JSON" not in html
        assert "重拍" in html or "三步" in html or "占满" in html
        assert "scan-fail-card" in html

    def test_network_fail(self):
        html = build_scan_fail_html("network")
        assert "网络" in html or "服务" in html

    def test_auth_fail_not_blaming_photo(self):
        html = build_scan_fail_html("auth")
        assert "密钥" in html
        assert "JSON" not in html
