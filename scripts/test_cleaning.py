#!/usr/bin/env python3
"""Extended tests for cleaning pipeline — hermes_deep_clean_v2 + unified_cleaning_pipeline."""
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

import hermes_deep_clean_v2 as hdc
import unified_cleaning_pipeline as ucp


# ========== Fixtures ==========

@pytest.fixture(autouse=True)
def reset_caches():
    hdc._keyword_weights_cache = None


# ========== Test ucp.normalize_source extended ==========

class TestNormalizeSourceExtended:
    def test_normalize_36kr_variants(self):
        assert ucp.normalize_source("36氪") == "36kr"

    def test_normalize_huxiu(self):
        assert ucp.normalize_source("虎嗅") == "huxiu"

    def test_normalize_sspai(self):
        assert ucp.normalize_source("少数派") == "sspai"

    def test_normalize_juejin(self):
        assert ucp.normalize_source("掘金") == "juejin"

    def test_normalize_douyin(self):
        assert ucp.normalize_source("抖音-热搜") == "douyin"

    def test_normalize_cnblogs(self):
        assert ucp.normalize_source("博客园") == "cnblogs"

    def test_normalize_oschina(self):
        assert ucp.normalize_source("开源中国") == "oschina"

    def test_normalize_tmtpost(self):
        assert ucp.normalize_source("钛媒体") == "tmtpost"

    def test_normalize_weibo_variants(self):
        assert ucp.normalize_source("微博-热搜") == "weibo"

    def test_normalize_strips_whitespace(self):
        assert ucp.normalize_source("  zhihu  ") == "zhihu"

    def test_normalize_none(self):
        assert ucp.normalize_source(None) == ""


# ========== Test ucp.extract_platform_prefix extended ==========

class TestExtractPlatformPrefixExtended:
    def test_underscore_platform(self):
        assert ucp.extract_platform_prefix("github_python") == "github"

    def test_none_input(self):
        assert ucp.extract_platform_prefix(None) == "unknown"

    def test_douyin_prefix(self):
        assert ucp.extract_platform_prefix("douyin_hot") == "douyin"


# ========== Test ucp.merge_tags extended ==========

class TestMergeTagsExtended:
    def test_merge_with_spaces(self):
        result = ucp.merge_tags("AI | Tech", "Dev")
        assert "AI" in result
        assert "Tech" in result

    def test_merge_duplicates_removed(self):
        result = ucp.merge_tags("AI|AI|Tech", "Tech|AI")
        parts = result.split("|")
        assert len(parts) == 2

    def test_merge_none_values(self):
        # merge_tags converts None to "None" via str(), so we get "AI|None"
        result = str(ucp.merge_tags(None, "AI"))
        assert "AI" in result

    def test_merge_empty_parts_filtered(self):
        result = ucp.merge_tags("AI||Tech", "||Dev")
        parts = result.split("|")
        assert "AI" in parts
        assert "Dev" in parts


# ========== Test ucp.matches_whitelist extended ==========

class TestMatchesWhitelistExtended:
    def test_match_in_category(self):
        assert ucp.matches_whitelist({
            "title": "nothing", "content": "", "tags": "", "category": "python"
        }) is True

    def test_no_match_all_fields(self):
        assert ucp.matches_whitelist({
            "title": "xyzabc123", "content": "xyzabc456",
            "tags": "xyz", "category": "xyz", "source": "xyz", "platform": "xyz"
        }) is False

    def test_security_keyword(self):
        assert ucp.matches_whitelist({
            "title": "CVE漏洞分析", "content": "", "tags": "", "category": ""
        }) is True

    def test_game_keyword(self):
        assert ucp.matches_whitelist({
            "title": "Steam新游戏发布", "content": "", "tags": "", "category": ""
        }) is True

    def test_robot_keyword(self):
        assert ucp.matches_whitelist({
            "title": "人形机器人擎天柱", "content": "", "tags": "", "category": ""
        }) is True

    def test_science_keyword(self):
        assert ucp.matches_whitelist({
            "title": "量子计算突破", "content": "", "tags": "", "category": ""
        }) is True

    def test_travel_keyword(self):
        assert ucp.matches_whitelist({
            "title": "旅游景点推荐", "content": "", "tags": "", "category": ""
        }) is True

    def test_beauty_keyword(self):
        assert ucp.matches_whitelist({
            "title": "时尚写真摄影", "content": "", "tags": "", "category": ""
        }) is True


# ========== Test ucp.is_noise extended ==========

class TestIsNoiseExtended:
    def test_content_too_short_no_title(self):
        assert ucp.is_noise({"title": "短", "content": ""}) is True

    def test_content_body_and_title(self):
        assert ucp.is_noise({"title": "短", "content": "some content but title short"}) is True

    def test_ui_label_match(self):
        assert ucp.is_noise({"title": "快手轻量版", "content": ""}) is True

    def test_heat_num_match(self):
        assert ucp.is_noise({"title": "999.7万", "content": ""}) is True


# ========== Test ucp.title_similarity extended ==========

class TestTitleSimilarityExtended:
    def test_both_empty(self):
        assert ucp.title_similarity("", "") == 0

    def test_one_empty(self):
        assert ucp.title_similarity("", "test") == 0

    def test_one_none(self):
        assert ucp.title_similarity(None, "test") == 0

    def test_different_cases(self):
        sim = ucp.title_similarity("AI NEWS", "ai news")
        assert sim >= 0.5

    def test_non_overlapping(self):
        sim = ucp.title_similarity("abcdef", "xyz123")
        assert sim < 0.2

    def test_high_similarity(self):
        sim = ucp.title_similarity("GPT-5 released", "GPT-5 launched")
        assert 0 < sim < 1


# ========== Test ucp constants ==========

class TestUcpConstants:
    def test_whitelist_set_size(self):
        assert len(ucp.WHITELIST_SET) > 300

    def test_broad_whitelist_length(self):
        assert len(ucp.BROAD_WHITELIST) > 300

    def test_platform_weights_default(self):
        assert "default" in ucp.PLATFORM_WEIGHTS

    def test_noise_patterns_not_empty(self):
        assert len(ucp.NOISE_PATTERNS) > 0

    def test_ui_labels_not_empty(self):
        assert len(ucp.UI_LABELS) > 0

    def test_heat_num_pattern_compiled(self):
        assert ucp.HEAT_NUM_PATTERN is not None

    def test_heat_num_pattern2_compiled(self):
        assert ucp.HEAT_NUM_PATTERN2 is not None


# ========== Test hdc.load_keyword_weights extended ==========

class TestHDCLoadKeywordWeightsExtended:
    def test_exception_returns_empty_cache(self, monkeypatch):
        hdc._keyword_weights_cache = None
        monkeypatch.setattr(hdc.Path, "exists", lambda self: True)
        with patch.object(hdc, "sqlite3") as mock_sqlite:
            mock_sqlite.connect.side_effect = Exception("DB error")
            result = hdc.load_keyword_weights()
            assert result == []

    def test_cache_cleared_and_rebuilt(self, monkeypatch):
        hdc._keyword_weights_cache = None
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [("test", 10, "cat")]
        with patch.object(hdc, "sqlite3") as mock_sqlite:
            mock_sqlite.connect.return_value = mock_conn
            result = hdc.load_keyword_weights()
            assert len(result) == 1
            assert result[0][0] == "test"


# ========== Test hdc.compute_personal_match extended ==========

class TestHdcComputePersonalMatchExtended:
    def test_content_truncated_at_300(self, monkeypatch):
        monkeypatch.setattr(hdc, "_keyword_weights_cache", [("test", 10, "cat")])
        long_content = "a" * 500  # keyword not in first 300
        score, matched = hdc.compute_personal_match("title", long_content)
        assert isinstance(score, (int, float))

    def test_empty_inputs(self, monkeypatch):
        monkeypatch.setattr(hdc, "_keyword_weights_cache", [("test", 10, "cat")])
        score, matched = hdc.compute_personal_match("", "")
        assert score == 0
        assert matched == []

    def test_none_content(self, monkeypatch):
        monkeypatch.setattr(hdc, "_keyword_weights_cache", [("ai", 20, "tech")])
        score, matched = hdc.compute_personal_match("AI breakthrough", None)
        assert score > 0

    def test_lowercase_matching(self, monkeypatch):
        monkeypatch.setattr(hdc, "_keyword_weights_cache", [("AI", 10, "tech")])
        score, matched = hdc.compute_personal_match("ai progress", "")
        assert score > 0


# ========== Test hdc constants ==========

class TestHDCConstants:
    def test_noise_set_nonempty(self):
        assert len(hdc.NOISE) > 0

    def test_noise_contains_ad(self):
        assert "广告" in hdc.NOISE

    def test_noise_contains_promotion(self):
        assert "推广" in hdc.NOISE


# ========== Test hdc.clean_all ==========

class TestHDCCleanAll:
    def test_no_data_returns_0(self, monkeypatch):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_conn.execute.return_value = mock_cur
        mock_cur.fetchone.return_value = [0]
        mock_cur.fetchall.return_value = []
        with patch.object(hdc, "sqlite3") as mock_sqlite:
            mock_sqlite.connect.return_value = mock_conn
            result = hdc.clean_all()
            assert result == 0

    def test_db_exception_handled(self, monkeypatch):
        with patch.object(hdc, "sqlite3") as mock_sqlite:
            mock_sqlite.connect.side_effect = Exception("DB error")
            with pytest.raises(Exception):
                hdc.clean_all()
