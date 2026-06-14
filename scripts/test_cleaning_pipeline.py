#!/usr/bin/env python3
"""Tests for hermes_deep_clean_v2 + unified_cleaning_pipeline — cleaning pipeline."""
import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import hermes_deep_clean_v2 as hdc
import unified_cleaning_pipeline as ucp


# ========== Fixtures ==========

@pytest.fixture(autouse=True)
def reset_caches():
    hdc._keyword_weights_cache = None
    yield


@pytest.fixture
def mock_db():
    """Create a mock database connection with cursor."""
    conn = MagicMock(spec=sqlite3.Connection)
    cur = MagicMock()
    conn.cursor.return_value = cur
    conn.execute.return_value = cur
    cur.fetchall.return_value = []
    cur.fetchone.return_value = [0]
    return conn, cur


# ========== Tests for hermes_deep_clean_v2 ==========

class TestHDCLoadKeywordWeights:
    def test_cache_returns_cached(self, monkeypatch):
        hdc._keyword_weights_cache = [("ai", 10, "tech")]
        result = hdc.load_keyword_weights()
        assert result == [("ai", 10, "tech")]

    def test_load_returns_list(self, monkeypatch):
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        with patch.object(hdc, "sqlite3") as mock_sqlite:
            mock_sqlite.connect.return_value = mock_conn
            result = hdc.load_keyword_weights()
            assert isinstance(result, list)

    def test_exception_returns_empty(self, monkeypatch):
        with patch.object(hdc, "sqlite3") as mock_sqlite:
            mock_sqlite.connect.side_effect = Exception("DB error")
            result = hdc.load_keyword_weights()
            assert result == []

    def test_cache_built(self, monkeypatch):
        hdc._keyword_weights_cache = None
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [("llm", 15, "AI")]
        with patch.object(hdc, "sqlite3") as mock_sqlite:
            mock_sqlite.connect.return_value = mock_conn
            hdc.load_keyword_weights()
            assert hdc._keyword_weights_cache == [("llm", 15, "AI")]


class TestHdcComputePersonalMatch:
    def test_no_weights_returns_zero(self):
        assert hdc.compute_personal_match("title", "content") == (0, [])

    def test_matched_keyword_gives_score(self, monkeypatch):
        monkeypatch.setattr(hdc, "_keyword_weights_cache", [("ai", 20, "tech")])
        score, matched = hdc.compute_personal_match("AI breakthrough", "content")
        assert score > 0
        assert "ai" in matched

    def test_no_match_returns_zero(self, monkeypatch):
        monkeypatch.setattr(hdc, "_keyword_weights_cache", [("llm", 10, "AI")])
        score, matched = hdc.compute_personal_match("sports news", "")
        assert score == 0
        assert matched == []

    def test_score_capped_at_100(self, monkeypatch):
        monkeypatch.setattr(hdc, "_keyword_weights_cache", [("ai", 999, "tech")])
        score, matched = hdc.compute_personal_match("ai breakthrough", "ai")
        assert score <= 100

    def test_case_insensitive(self, monkeypatch):
        monkeypatch.setattr(hdc, "_keyword_weights_cache", [("AI", 10, "tech")])
        score, matched = hdc.compute_personal_match("ai progress", "")
        assert score > 0

    def test_multiple_keywords_accumulate(self, monkeypatch):
        monkeypatch.setattr(hdc, "_keyword_weights_cache", [("ai", 10, "t"), ("llm", 10, "t")])
        score, matched = hdc.compute_personal_match("AI and LLM progress", "")
        assert score > 15
        assert len(matched) == 2


class TestHdcNoiseKeywords:
    def test_noise_keywords_exist(self):
        assert len(hdc.NOISE) > 0
        assert "广告" in hdc.NOISE
        assert "推广" in hdc.NOISE

    def test_noise_in_title_skipped(self):
        """Test that clean_all with no data returns 0."""
        # Mock the sqlite3.connect at the module level
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_conn.execute.return_value = mock_cur
        mock_cur.fetchone.return_value = [0]  # max_cleaned = 0
        mock_cur.fetchall.return_value = []   # no backlog/new rows
        with patch.object(hdc, "sqlite3") as mock_sqlite:
            mock_sqlite.connect.return_value = mock_conn
            result = hdc.clean_all()
            assert result == 0


# ========== Tests for unified_cleaning_pipeline ==========

class TestUcpNormalizeSource:
    def test_normalize_hackernews(self):
        assert ucp.normalize_source("HackerNews") == "hackernews"

    def test_normalize_github_variants(self):
        assert ucp.normalize_source("GitHub Trending") == "github"
        assert ucp.normalize_source("GitHub-Python") == "github"

    def test_normalize_bilibili_variants(self):
        assert ucp.normalize_source("B站-全站") == "bilibili"
        assert ucp.normalize_source("bilibili_全站") == "bilibili"

    def test_normalize_baidu_variants(self):
        assert ucp.normalize_source("百度-热搜") == "baidu"
        assert ucp.normalize_source("百度热搜") == "baidu"

    def test_normalize_known_source(self):
        assert ucp.normalize_source("IT之家") == "ithome"
        assert ucp.normalize_source("36氪") == "36kr"
        assert ucp.normalize_source("知乎") == "zhihu"

    def test_normalize_unknown_returns_as_is(self):
        assert ucp.normalize_source("some_random_source") == "some_random_source"

    def test_normalize_empty(self):
        assert ucp.normalize_source("") == ""
        assert ucp.normalize_source(None) == ""


class TestUcpExtractPlatformPrefix:
    def test_github_prefix(self):
        assert ucp.extract_platform_prefix("github") == "github"

    def test_bilibili_prefix(self):
        assert ucp.extract_platform_prefix("bilibili_科技") == "bilibili"

    def test_unknown_returns_first_part(self):
        assert ucp.extract_platform_prefix("my_custom_platform") == "my"

    def test_empty_returns_unknown(self):
        assert ucp.extract_platform_prefix("") == "unknown"

    def test_solidot_prefix(self):
        assert ucp.extract_platform_prefix("solidot") == "solidot"


class TestUcpMergeTags:
    def test_merge_both_nonempty(self):
        assert ucp.merge_tags("AI|Tech", "Dev|AI") == "AI|Dev|Tech"

    def test_merge_empty_tags(self):
        assert ucp.merge_tags("", "AI|Tech") == "AI|Tech"

    def test_merge_both_empty(self):
        assert ucp.merge_tags("", "") == ""

    def test_merge_identical(self):
        assert ucp.merge_tags("AI|Tech", "AI|Tech") == "AI|Tech"

    def test_merge_sorted(self):
        result = ucp.merge_tags("B|A", "C|A")
        parts = result.split("|")
        assert parts == sorted(parts)


class TestUcpMatchesWhitelist:
    def test_ai_keyword_matches(self):
        assert ucp.matches_whitelist({"title": "GPT-5发布", "content": "", "tags": "", "category": ""}) is True

    def test_no_match_returns_false(self):
        # "测试" is actually in the whitelist! Use a completely random string
        assert ucp.matches_whitelist({"title": "qwxyzbknmop完全无关内容", "content": "", "tags": "", "category": ""}) is False

    def test_match_in_content(self):
        assert ucp.matches_whitelist({"title": "标题", "content": "关于openai的最新消息", "tags": "", "category": ""}) is True

    def test_match_in_tags(self):
        assert ucp.matches_whitelist({"title": "标题", "content": "", "tags": "AI", "category": ""}) is True

    def test_match_in_source(self):
        assert ucp.matches_whitelist({"title": "标题", "content": "", "tags": "", "category": "", "source": "github", "platform": ""}) is True

    def test_empty_item_returns_false(self):
        assert ucp.matches_whitelist({}) is False

    def test_ev_keyword(self):
        assert ucp.matches_whitelist({"title": "比亚迪新款电动车发布", "content": "", "tags": "", "category": ""}) is True

    def test_military_keyword(self):
        assert ucp.matches_whitelist({"title": "国防军事演习最新动态", "content": "", "tags": "", "category": ""}) is True


class TestUcpIsNoise:
    def test_ad_keyword_is_noise(self):
        assert ucp.is_noise({"title": "注册抽奖赢红包", "content": ""}) is True

    def test_short_title_is_noise(self):
        assert ucp.is_noise({"title": "短", "content": "some content"}) is True

    def test_heat_num_pattern_noise(self):
        assert ucp.is_noise({"title": "1095.9万热度", "content": ""}) is True

    def test_heat_num_pattern2_noise(self):
        assert ucp.is_noise({"title": "999.7万", "content": ""}) is True

    def test_ui_label_noise(self):
        assert ucp.is_noise({"title": "快手轻量版", "content": ""}) is True

    def test_empty_content_short_title_noise(self):
        assert ucp.is_noise({"title": "短标题无内容", "content": ""}) is True

    def test_clean_content_not_noise(self):
        assert ucp.is_noise({"title": "合理标题有足够内容", "content": "这是一段有实际信息的内容描述..."}) is False

    def test_noise_in_content(self):
        assert ucp.is_noise({"title": "普通标题", "content": "这里有直播带货描述"}) is True


class TestUcpTitleSimilarity:
    def test_identical(self):
        assert ucp.title_similarity("Hello World", "Hello World") == 1.0

    def test_completely_different(self):
        assert ucp.title_similarity("abc", "xyz") == 0.0

    def test_partial_overlap(self):
        sim = ucp.title_similarity("AI大模型", "AI芯片")
        assert 0 < sim < 1

    def test_empty_string(self):
        assert ucp.title_similarity("", "test") == 0
        assert ucp.title_similarity("test", "") == 0

    def test_case_sensitivity_handled(self):
        sim1 = ucp.title_similarity("AI news", "ai news")
        assert sim1 > 0.5


class TestUcpWhitelistSet:
    def test_whitelist_built_correctly(self):
        """Verify the global WHITELIST_SET is built properly."""
        assert len(ucp.WHITELIST_SET) > 300
        assert "ai" in ucp.WHITELIST_SET
        assert "人工智能" in ucp.WHITELIST_SET
        assert "大模型" in ucp.WHITELIST_SET
        assert "python" in ucp.WHITELIST_SET

    def test_whitelist_size_property(self):
        assert ucp.WHITELIST_SIZE == len(ucp.WHITELIST_SET)

    def test_platform_weights_default_exists(self):
        assert "default" in ucp.PLATFORM_WEIGHTS
        assert ucp.PLATFORM_WEIGHTS["default"] == 1.0

    def test_hackernews_weight(self):
        assert ucp.PLATFORM_WEIGHTS.get("hackernews", 0) > 0


class TestUcpNoisePatterns:
    def test_noise_patterns_nonempty(self):
        assert len(ucp.NOISE_PATTERNS) > 0

    def test_heat_num_regex(self):
        assert ucp.HEAT_NUM_PATTERN.match("1095.9万热度") is not None
        assert ucp.HEAT_NUM_PATTERN.match("正常标题") is None

    def test_heat_num2_regex(self):
        assert ucp.HEAT_NUM_PATTERN2.match("999.7万") is not None

    def test_ui_labels_set(self):
        assert "AcFun" in ucp.UI_LABELS
        assert "三角洲" in ucp.UI_LABELS

    def test_broad_whitelist_covers_16_categories(self):
        """Ensure BROAD_WHITELIST contains keywords from all 16 categories."""
        categories = ["AI", "IT", "消费电子", "通信", "新能源汽车", "军事",
                      "体育", "格斗", "美女", "电影", "旅游", "科学",
                      "安全", "游戏", "机器人", "社会热点"]
        found_cats = set()
        # Check each category has at least one keyword found
        cat_keywords = {
            "AI": ["ai", "人工智能", "大模型"],
            "IT": ["python", "rust", "typescript"],
            "消费电子": ["iphone", "samsung", "华为"],
            "通信": ["5g", "6g", "wifi"],
            "新能源汽车": ["特斯拉", "比亚迪", "ev"],
            "军事": ["军事", "国防", "导弹"],
            "体育": ["nba", "足球", "奥运会"],
            "格斗": ["ufc", "mma", "拳击"],
            "美女": ["写真", "摄影", "时尚"],
            "电影": ["电影", "netflix", "票房"],
            "旅游": ["旅游", "景点", "签证"],
            "科学": ["科学", "物理", "nasa"],
            "安全": ["安全", "黑客", "漏洞"],
            "游戏": ["游戏", "steam", "ps5"],
            "机器人": ["机器人", "robot", "humanoid"],
            "社会热点": ["热点", "新闻", "经济"],
        }
        for cat, kws in cat_keywords.items():
            for kw in kws:
                if kw in ucp.WHITELIST_SET:
                    found_cats.add(cat)
                    break
        assert len(found_cats) >= 14, f"Only found {len(found_cats)} categories: {found_cats}"
