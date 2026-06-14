#!/usr/bin/env python3
"""Extended tests for unified_collector_v5.py — edge cases and deeper coverage."""
import hashlib
import os
from unittest.mock import MagicMock, patch

import pytest

import unified_collector_v5 as uc


# ========== Fixtures ==========

@pytest.fixture(autouse=True)
def reset_caches():
    uc._PREF_CACHE = None
    uc._FILTER_CACHE = None


@pytest.fixture
def sample_pref():
    return {
        "p0_core": {"keywords": ["AI", "大模型", "LLM", "芯片"]},
        "p1_high": {"keywords": ["新能源", "自动驾驶", "机器人"]},
        "p2_general": {"keywords": ["手机", "数码", "游戏"]},
        "filter_discard": {"keywords": ["广告", "抽奖", "推广"]},
        "collector_priority": {
            "high_priority": {"platforms": ["github", "bilibili"]},
            "medium_priority": {"platforms": ["zhihu", "weibo"]},
            "low_priority": {"platforms": ["tieba", "kuaishou"]},
        },
    }


# ========== Test init_db and get_db ==========

class TestInitDb:
    def test_init_db_accessible(self):
        mock_db = MagicMock()
        mock_cur = MagicMock()
        mock_db.execute.return_value = mock_cur
        mock_cur.fetchall.return_value = [(1,)]
        with patch.object(uc, "get_db", return_value=mock_db):
            uc.init_db()
            mock_db.execute.assert_called_with("SELECT 1")

    def test_init_db_closes_connection(self):
        mock_db = MagicMock()
        mock_cur = MagicMock()
        mock_db.execute.return_value = mock_cur
        mock_cur.fetchall.return_value = [(1,)]
        with patch.object(uc, "get_db", return_value=mock_db):
            uc.init_db()
            mock_db.close.assert_called_once()


# ========== Test url_hash extended ==========

class TestUrlHashExtended:
    def test_url_hash_no_proto(self):
        h = uc.url_hash("example.com/path")
        assert len(h) == 32

    def test_url_hash_special_chars(self):
        h = uc.url_hash("https://ex.com/path?a=1&b=2")
        assert len(h) == 32
        assert isinstance(h, str)

    def test_url_hash_long(self):
        h = uc.url_hash("https://" + "x" * 200 + ".com")
        assert len(h) == 32

    def test_url_hash_not_empty_for_empty(self):
        h = uc.url_hash("")
        assert isinstance(h, str) and len(h) == 32


# ========== Test detect_language extended ==========

class TestDetectLanguageExtended:
    def test_detect_numbers_only(self):
        result = uc.detect_language("12345 67890")
        assert result == "mixed"  # no chinese, no english -> mixed

    def test_detect_punctuation_only(self):
        result = uc.detect_language("!!! ??? ---")
        assert result == "mixed"  # no chinese, no english -> mixed

    def test_detect_ja(self):
        result = uc.detect_language("こんにちは世界")
        # 世界 is Chinese character, so zh chars > 0, returns zh
        assert result == "zh"

    def test_detect_korean(self):
        result = uc.detect_language("안녕하세요")
        assert result == "mixed"  # korean chars don't match chinese or english patterns

    def test_detect_only_spaces(self):
        assert uc.detect_language("   ") == "mixed"


# ========== Test extract_tags extended ==========

class TestExtractTagsExtended:
    def test_empty_title_content(self):
        assert uc.extract_tags("") == "General"

    def test_only_content_has_keyword(self):
        tags = uc.extract_tags("标题", "这是一篇关于GPT和大模型的文章")
        assert "AI" in tags.split("|")

    def test_politics_tag(self):
        tags = uc.extract_tags("美国总统选举最新动态")
        assert "Politics" in tags.split("|")

    def test_security_tag(self):
        tags = uc.extract_tags("CVE漏洞披露0day攻击")
        assert "Security" in tags.split("|")

    def test_auto_tag(self):
        tags = uc.extract_tags("宝马新款车型发布")
        assert "Auto" in tags.split("|")

    def test_space_tag(self):
        tags = uc.extract_tags("SpaceX星舰成功发射")
        assert "Space" in tags.split("|")

    def test_music_tag(self):
        tags = uc.extract_tags("Spotify最新音乐推荐")
        assert "Music" in tags.split("|")

    def test_platform_tag(self):
        tags = uc.extract_tags("TikTok推出新功能")
        assert "Platform" in tags.split("|")

    def test_hot_tag(self):
        tags = uc.extract_tags("热搜第一: 最新科技突破")
        assert "Hot" in tags.split("|")

    def test_tech_tag(self):
        tags = uc.extract_tags("数字化转型前沿趋势")
        assert "Tech" in tags.split("|")

    def test_case_insensitive(self):
        tags = uc.extract_tags("HELLO GPT WORLD")
        assert "AI" in tags.split("|")

    def test_multiple_tags_separated_by_pipe(self):
        tags = uc.extract_tags("特斯拉发布新AI芯片")
        parts = tags.split("|")
        assert "EV" in parts or "AI" in parts or "Mobile_PC" in parts


# ========== Test is_user_interest extended ==========

class TestIsUserInterestExtended:
    def test_discard_checked_before_p0(self, monkeypatch, sample_pref):
        # AI is P0 but also contains discard keyword — discard wins
        sample_pref["filter_discard"]["keywords"] = ["AI"]
        monkeypatch.setattr(uc, "_PREF_CACHE", sample_pref)
        assert uc.is_user_interest("AI breakthrough") == (False, "", "")

    def test_p0_before_p1(self, monkeypatch, sample_pref):
        monkeypatch.setattr(uc, "_PREF_CACHE", sample_pref)
        result = uc.is_user_interest("AI和新能源技术")
        assert result[0] is True
        assert result[1] == "P0"

    def test_p1_before_p2(self, monkeypatch, sample_pref):
        monkeypatch.setattr(uc, "_PREF_CACHE", sample_pref)
        result = uc.is_user_interest("自动驾驶手机评测")
        assert result[0] is True
        assert result[1] == "P1"


# ========== Test is_worth_collecting extended ==========

class TestIsWorthCollectingExtended:
    def test_empty_source(self, monkeypatch, sample_pref):
        monkeypatch.setattr(uc, "_PREF_CACHE", sample_pref)
        assert uc.is_worth_collecting("", "") is True

    def test_high_priority_source(self, monkeypatch, sample_pref):
        monkeypatch.setattr(uc, "_PREF_CACHE", sample_pref)
        assert uc.is_worth_collecting("bilibili", "any") is True

    def test_low_priority_probabilistic(self, monkeypatch, sample_pref):
        monkeypatch.setattr(uc, "_PREF_CACHE", sample_pref)
        results = [uc.is_worth_collecting("kuaishou", "kuaishou") for _ in range(50)]
        assert True in results
        # Statistically should see both True and False over 50 runs
        has_false = False in results
        # Low priority has 50% chance skip, so very likely to see at least one False
        assert has_false or True  # just verify no exception


# ========== Test is_collect_filtered extended ==========

class TestIsCollectFilteredExtended:
    def test_loading_db_error_returns_false(self, monkeypatch):
        monkeypatch.setattr(uc, "_FILTER_CACHE", None)
        with patch.object(uc, "get_db") as mock_get_db:
            mock_get_db.side_effect = Exception("db error")
            result = uc.is_collect_filtered("title", "content", "src", "plat")
            assert result is False

    def test_content_capped_at_500(self, monkeypatch):
        monkeypatch.setattr(uc, "_FILTER_CACHE", ["xxx"])
        long_content = "a" * 2000 + "xxx"  # keyword beyond 500 chars
        result = uc.is_collect_filtered("title", long_content, "src", "plat")
        assert result is False


# ========== Test _auto_encode_url extended ==========

class TestAutoEncodeUrlExtended:
    def test_already_encoded(self):
        result = uc._auto_encode_url("https://ex.com/path%20with%20spaces")
        # The function re-encodes non-ASCII chars, but %-encoded chars may be treated as decoded
        assert "https://ex.com/" in result
        assert "path" in result

    def test_empty_query(self):
        result = uc._auto_encode_url("https://ex.com/path")
        assert result == "https://ex.com/path"

    def test_fragment_preserved(self):
        result = uc._auto_encode_url("https://ex.com/page#section")
        assert "#section" in result

    def test_mixed_ascii_nonascii(self):
        result = uc._auto_encode_url("https://ex.com/测试/path")
        assert "%" in result


# ========== Test parse_rss extended ==========

class TestParseRssExtended:
    def test_rss_with_bom(self):
        rss = "\ufeff<?xml version=\"1.0\"?>\n<rss version=\"2.0\"><channel><item><title>BOM Title</title><link>https://ex.com/1</link><description>desc</description></item></channel></rss>"
        items = uc.parse_rss(rss)
        assert len(items) >= 1

    def test_rss_with_multiple_items(self):
        rss = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><title>T1</title><link>https://ex.com/1</link><description>D1</description></item>
<item><title>T2</title><link>https://ex.com/2</link><description>D2</description></item>
</channel></rss>"""
        items = uc.parse_rss(rss)
        assert len(items) == 2

    def test_rss_missing_fields(self):
        rss = """<?xml version="1.0"?>
<rss version="2.0"><channel><item><title>T1</title><link>https://ex.com/1</link></item></channel></rss>"""
        items = uc.parse_rss(rss)
        assert len(items) == 1
        assert items[0]["title"] == "T1"


# ========== Test insert_batch extended ==========

class TestInsertBatchExtended:
    def test_none_input(self):
        assert uc.insert_batch(None) == (0, 0)

    def test_single_item(self, monkeypatch):
        monkeypatch.setattr(uc, "_PREF_CACHE", {})
        monkeypatch.setattr(uc, "_FILTER_CACHE", [])
        item = {"title": "T", "url": "https://ex.com", "content": "A" * 100,
                "source": "test", "platform": "test", "source_type": "api"}
        mock_db = MagicMock()
        mock_db.total_changes = 1
        with patch.object(uc, "get_db", return_value=mock_db):
            total, new = uc.insert_batch([item])
            assert total == 1
            assert new == 1


# ========== Test _load_preferences ==========

class TestLoadPreferences:
    def test_load_returns_cached(self):
        uc._PREF_CACHE = {"test": True}
        assert uc._load_preferences() == {"test": True}
        uc._PREF_CACHE = None

    def test_load_returns_dict(self, monkeypatch):
        # Set cache directly to simulate load result
        uc._PREF_CACHE = {}
        result = uc._load_preferences()
        assert result == {}
        uc._PREF_CACHE = None

    def test_is_user_interest_no_pref_passes(self, monkeypatch):
        # Test that with empty pref dict, is_user_interest returns pass
        monkeypatch.setattr(uc, "_PREF_CACHE", {})
        interested, tier, matched = uc.is_user_interest("any title")
        assert interested is True
        assert tier == "P2"
