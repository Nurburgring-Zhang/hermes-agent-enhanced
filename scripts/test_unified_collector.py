#!/usr/bin/env python3
"""Tests for unified_collector_v5.py — focus on data processing, no real HTTP."""
import json
import hashlib
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest

# Module under test
import unified_collector_v5 as uc


# ========== Fixtures ==========

@pytest.fixture(autouse=True)
def reset_caches():
    """Reset module-level caches between tests."""
    uc._PREF_CACHE = None
    uc._FILTER_CACHE = None
    yield


@pytest.fixture
def sample_pref():
    """Sample collector_preferences.json content."""
    return {
        "p0_core": {"keywords": ["AI", "大模型", "LLM", "芯片"]},
        "p1_high": {"keywords": ["新能源", "自动驾驶", "机器人"]},
        "p2_general": {"keywords": ["手机", "数码", "游戏"]},
        "filter_discard": {"keywords": ["广告", "抽奖", "推广"]},
        "collector_priority": {
            "high_priority": {"platforms": ["github", "bilibili"]},
            "medium_priority": {"platforms": ["zhihu", "weibo"]},
            "low_priority": {"platforms": ["tieba", "kuaishou"]},
        }
    }


@pytest.fixture
def sample_item():
    return {
        "title": "GPT-5发布: AI进入AGI时代",
        "content": "OpenAI刚刚发布了GPT-5模型，性能大幅提升...",
        "url": "https://example.com/gpt5",
        "source": "ithome",
        "platform": "ithome",
        "author": "test",
        "author_id": "123",
        "source_type": "api",
        "hot_score": 5000,
        "view_count": 10000,
        "like_count": 500,
        "collect_count": 200,
        "comment_count": 100,
        "share_count": 50,
        "published_at": "2026-06-14 10:00:00",
        "category_tags": "AI|Tech",
    }


# ========== Test url_hash ==========

class TestUrlHash:
    def test_url_hash_consistency(self):
        h1 = uc.url_hash("https://example.com")
        h2 = uc.url_hash("https://example.com")
        assert h1 == h2
        assert len(h1) == 32

    def test_url_hash_differs(self):
        h1 = uc.url_hash("https://example.com/a")
        h2 = uc.url_hash("https://example.com/b")
        assert h1 != h2

    def test_url_hash_sha256(self):
        expected = hashlib.sha256(b"test").hexdigest()[:32]
        assert uc.url_hash("test") == expected

    def test_url_hash_empty(self):
        h = uc.url_hash("")
        assert len(h) == 32

    def test_url_hash_unicode(self):
        h = uc.url_hash("https://例子.测试/路径")
        assert len(h) == 32
        assert isinstance(h, str)


# ========== Test detect_language ==========

class TestDetectLanguage:
    def test_detect_zh(self):
        assert uc.detect_language("今天天气真好") == "zh"

    def test_detect_en(self):
        assert uc.detect_language("hello world this is a test") == "en"

    def test_detect_mixed(self):
        # "hello世界" -> 5 english, 2 chinese -> en, not mixed
        result = uc.detect_language("hello世界")
        assert result in ("en", "mixed")

    def test_detect_empty(self):
        assert uc.detect_language("") == "unknown"

    def test_detect_none(self):
        assert uc.detect_language(None) == "unknown"

    def test_detect_equal_count(self):
        # equal chinese and english chars
        assert uc.detect_language("a你我b他c") == "mixed"


# ========== Test extract_tags ==========

class TestExtractTags:
    def test_ai_tag(self):
        tags = uc.extract_tags("GPT-5发布!大模型时代")
        assert "AI" in tags.split("|")

    def test_ev_tag(self):
        tags = uc.extract_tags("特斯拉FSD自动驾驶升级")
        assert "EV" in tags.split("|")

    def test_military_tag(self):
        tags = uc.extract_tags("中国航母编队南海演习")
        assert "Military_Intl" in tags.split("|")

    def test_sports_fight_tag(self):
        tags = uc.extract_tags("张伟丽UFC卫冕成功")
        assert "Sports_Fight" in tags.split("|")

    def test_dev_tag(self):
        tags = uc.extract_tags("Python 3.13发布，性能提升")
        assert "Dev_OpenSource" in tags.split("|")

    def test_robot_tag(self):
        tags = uc.extract_tags("人形机器人Optimus最新进展")
        assert "Robot" in tags.split("|")

    def test_default_general(self):
        tags = uc.extract_tags("无关无意义内容xxx")
        assert tags == "General"

    def test_multiple_tags(self):
        tags = uc.extract_tags("AI芯片公司发布新GPU", "详细技术架构介绍")
        parts = tags.split("|")
        assert "AI" in parts
        assert "Mobile_PC" in parts or "Tech" in parts

    def test_tags_from_content(self):
        tags = uc.extract_tags("标题", "这是关于deepseek大模型的技术文章")
        parts = tags.split("|")
        assert "AI" in parts

    def test_photo_art_tag(self):
        tags = uc.extract_tags("最新索尼相机人像摄影评测")
        assert "Photo_Art" in tags.split("|") or "Beauty_Photo" in tags.split("|")

    def test_game_tag(self):
        tags = uc.extract_tags("原神新版本更新内容")
        assert "Game" in tags.split("|")

    def test_science_tag(self):
        tags = uc.extract_tags("量子计算最新突破研究")
        assert "Science" in tags.split("|") or "AI" in tags.split("|")

    def test_history_tag(self):
        tags = uc.extract_tags("故宫文物修复传统工艺")
        assert "History_Culture" in tags.split("|")

    def test_movie_tag(self):
        tags = uc.extract_tags("好莱坞大片即将上映")
        assert "Movie_Video" in tags.split("|")

    def test_travel_food_tag(self):
        tags = uc.extract_tags("境外游攻略热门景点")
        assert "Travel_Food" in tags.split("|")

    def test_music_tag(self):
        tags = uc.extract_tags("Spotify推出新音乐推荐算法")
        # may also get AI or Tech
        parts = tags.split("|")
        assert "Music" in parts or "AI" in parts or "Tech" in parts


# ========== Test is_user_interest ==========

class TestIsUserInterest:
    def test_no_pref_returns_pass(self, monkeypatch):
        monkeypatch.setattr(uc, "_PREF_CACHE", {})
        assert uc.is_user_interest("anything") == (True, "P2", "")

    def test_discard_matched(self, monkeypatch, sample_pref):
        monkeypatch.setattr(uc, "_PREF_CACHE", sample_pref)
        assert uc.is_user_interest("注册抽奖送大礼") == (False, "", "")

    def test_p0_matched(self, monkeypatch, sample_pref):
        monkeypatch.setattr(uc, "_PREF_CACHE", sample_pref)
        result = uc.is_user_interest("大模型突破性进展")
        assert result[0] is True
        assert result[1] == "P0"

    def test_p1_matched(self, monkeypatch, sample_pref):
        monkeypatch.setattr(uc, "_PREF_CACHE", sample_pref)
        result = uc.is_user_interest("自动驾驶技术新突破")
        assert result[0] is True
        assert result[1] == "P1"

    def test_p2_matched(self, monkeypatch, sample_pref):
        monkeypatch.setattr(uc, "_PREF_CACHE", sample_pref)
        result = uc.is_user_interest("新款手机评测")
        assert result[0] is True
        assert result[1] == "P2"

    def test_no_match_returns_false(self, monkeypatch, sample_pref):
        monkeypatch.setattr(uc, "_PREF_CACHE", sample_pref)
        assert uc.is_user_interest("股票行情走势分析") == (False, "", "")

    def test_content_also_checked(self, monkeypatch, sample_pref):
        monkeypatch.setattr(uc, "_PREF_CACHE", sample_pref)
        result = uc.is_user_interest("无关标题", "芯片技术深度分析")
        assert result[0] is True
        assert result[1] == "P0"


# ========== Test is_worth_collecting ==========

class TestIsWorthCollecting:
    def test_no_pref_returns_true(self, monkeypatch):
        monkeypatch.setattr(uc, "_PREF_CACHE", {})
        assert uc.is_worth_collecting("test", "test") is True

    def test_high_priority_true(self, monkeypatch, sample_pref):
        monkeypatch.setattr(uc, "_PREF_CACHE", sample_pref)
        assert uc.is_worth_collecting("github", "github") is True

    def test_medium_priority_true(self, monkeypatch, sample_pref):
        monkeypatch.setattr(uc, "_PREF_CACHE", sample_pref)
        assert uc.is_worth_collecting("zhihu", "zhihu") is True

    def test_low_priority_sometimes(self, monkeypatch, sample_pref):
        monkeypatch.setattr(uc, "_PREF_CACHE", sample_pref)
        # Run multiple times; should sometimes be True, sometimes False
        results = {uc.is_worth_collecting("tieba", "tieba") for _ in range(20)}
        # At least one True and one False possible
        assert True in results

    def test_unknown_platform_true(self, monkeypatch, sample_pref):
        monkeypatch.setattr(uc, "_PREF_CACHE", sample_pref)
        assert uc.is_worth_collecting("unknown_platform", "unknown_platform") is True

    def test_platform_in_high(self, monkeypatch, sample_pref):
        monkeypatch.setattr(uc, "_PREF_CACHE", sample_pref)
        assert uc.is_worth_collecting("some_other", "bilibili") is True


# ========== Test is_collect_filtered ==========

class TestIsCollectFiltered:
    def test_empty_title_content_returns_false(self, monkeypatch):
        monkeypatch.setattr(uc, "_FILTER_CACHE", [])
        assert uc.is_collect_filtered("", "", "src", "plat") is False

    def test_filter_cache_empty_returns_false(self, monkeypatch):
        monkeypatch.setattr(uc, "_FILTER_CACHE", [])
        assert uc.is_collect_filtered("test title", "content", "src", "plat") is False

    def test_keyword_matched_returns_true(self, monkeypatch):
        monkeypatch.setattr(uc, "_FILTER_CACHE", ["badword", "spam"])
        assert uc.is_collect_filtered("this has badword in it", "", "src", "plat") is True

    def test_no_match_returns_false(self, monkeypatch):
        monkeypatch.setattr(uc, "_FILTER_CACHE", ["badword", "spam"])
        assert uc.is_collect_filtered("clean title", "clean content", "src", "plat") is False

    def test_case_insensitive(self, monkeypatch):
        monkeypatch.setattr(uc, "_FILTER_CACHE", ["badword"])
        assert uc.is_collect_filtered("BadWord in title", "", "src", "plat") is True

    def test_content_searched(self, monkeypatch):
        monkeypatch.setattr(uc, "_FILTER_CACHE", ["spammy"])
        assert uc.is_collect_filtered("title", "this contains spammy content", "src", "plat") is True


# ========== Test insert_raw_item (data processing logic) ==========

class TestInsertRawItem:
    def test_missing_url_returns_false(self, monkeypatch):
        item = {"title": "test"}
        assert uc.insert_raw_item(item) is False

    def test_missing_title_returns_false(self, monkeypatch):
        item = {"url": "https://example.com"}
        assert uc.insert_raw_item(item) is False

    def test_match_type_updates_tags(self, monkeypatch):
        item = {"url": "https://ex.com", "title": "t", "source_type": "match", "category_tags": "AI|Tech"}
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = ("Old",)
        mock_db.total_changes = 1
        with patch.object(uc, "get_db", return_value=mock_db):
            result = uc.insert_raw_item(item)
            assert result is True
            # Should call UPDATE
            update_calls = [c for c in mock_db.execute.call_args_list if "UPDATE" in str(c)]
            assert len(update_calls) > 0

    def test_uninteresting_item_dropped(self, monkeypatch, sample_item):
        monkeypatch.setattr(uc, "_PREF_CACHE", {"filter_discard": {"keywords": ["GPT"]}})
        monkeypatch.setattr(uc, "_FILTER_CACHE", [])
        assert uc.insert_raw_item(sample_item) is False

    def test_filtered_item_dropped(self, monkeypatch, sample_item):
        monkeypatch.setattr(uc, "_PREF_CACHE", {})
        monkeypatch.setattr(uc, "_FILTER_CACHE", ["GPT"])
        assert uc.insert_raw_item(sample_item) is False

    def test_short_content_dropped(self, monkeypatch, sample_item):
        monkeypatch.setattr(uc, "_PREF_CACHE", {})
        monkeypatch.setattr(uc, "_FILTER_CACHE", [])
        short = dict(sample_item, content="short")
        assert uc.insert_raw_item(short) is False

    def test_short_content_ok_for_short_sources(self, monkeypatch, sample_item):
        monkeypatch.setattr(uc, "_PREF_CACHE", {})
        monkeypatch.setattr(uc, "_FILTER_CACHE", [])
        short = dict(sample_item, content="short", platform="weibo")
        mock_db = MagicMock()
        mock_db.total_changes = 1
        with patch.object(uc, "get_db", return_value=mock_db):
            assert uc.insert_raw_item(short) is True

    def test_successful_insert(self, monkeypatch):
        monkeypatch.setattr(uc, "_PREF_CACHE", {})
        monkeypatch.setattr(uc, "_FILTER_CACHE", [])
        # Content must have >=80 effective chars (after removing punctuation/special chars)
        item = {
            "title": "GPT-5发布: AI进入AGI时代",
            "content": "OpenAI刚刚发布了GPT5模型性能大幅提升采用全新Transformer架构" * 3,
            "url": "https://example.com/gpt5",
            "source": "ithome",
            "platform": "ithome",
            "author": "test",
            "author_id": "123",
            "source_type": "api",
            "hot_score": 5000,
            "view_count": 10000,
            "like_count": 500,
            "collect_count": 200,
            "comment_count": 100,
            "share_count": 50,
            "published_at": "2026-06-14 10:00:00",
            "category_tags": "AI|Tech",
        }
        mock_conn = MagicMock()
        mock_conn.total_changes = 1
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = []
        mock_conn.execute.return_value = mock_cur
        with patch.object(uc, "get_db", return_value=mock_conn):
            assert uc.insert_raw_item(item) is True

    def test_insert_exception_returns_false(self, monkeypatch, sample_item):
        monkeypatch.setattr(uc, "_PREF_CACHE", {})
        monkeypatch.setattr(uc, "_FILTER_CACHE", [])
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("DB error")
        with patch.object(uc, "get_db", return_value=mock_db):
            assert uc.insert_raw_item(sample_item) is False

    def test_blog_platform_content_filter(self, monkeypatch):
        monkeypatch.setattr(uc, "_PREF_CACHE", {})
        monkeypatch.setattr(uc, "_FILTER_CACHE", [])
        item = {
            "title": "Test Blog",
            "url": "https://blog.csdn.net/test",
            "content": "A" * 100,  # < 150
            "source": "csdn",
            "platform": "csdn",
            "source_type": "api",
        }
        assert uc.insert_raw_item(item) is False

    def test_title_too_short_and_content_short(self, monkeypatch):
        monkeypatch.setattr(uc, "_PREF_CACHE", {})
        monkeypatch.setattr(uc, "_FILTER_CACHE", [])
        item = {
            "title": "AB",  # < 6 effective chars
            "url": "https://ex.com/test",
            "content": "short content under 100 chars",
            "source": "test",
            "platform": "test",
            "source_type": "api",
        }
        assert uc.insert_raw_item(item) is False


# ========== Test _auto_encode_url ==========

class TestAutoEncodeUrl:
    def test_ascii_url_unchanged(self):
        url = "https://example.com/path/file.html"
        assert uc._auto_encode_url(url) == url

    def test_non_ascii_encoded(self):
        result = uc._auto_encode_url("https://例子.com/路径")
        assert "%" in result

    def test_chinese_query_params(self):
        result = uc._auto_encode_url("https://example.com/search?q=中文")
        assert "%" in result or result == "https://example.com/search?q=中文"


# ========== Test insert_batch ==========

class TestInsertBatch:
    def test_empty_list(self):
        assert uc.insert_batch([]) == (0, 0)

    def test_batch_success(self, monkeypatch):
        monkeypatch.setattr(uc, "_PREF_CACHE", {})
        monkeypatch.setattr(uc, "_FILTER_CACHE", [])
        items = [
            {"title": "T1", "url": f"https://ex.com/{i}", "content": "A" * 100,
             "source": "test", "platform": "test", "source_type": "api"}
            for i in range(5)
        ]
        mock_db = MagicMock()
        mock_db.total_changes = 1
        with patch.object(uc, "get_db", return_value=mock_db):
            total, new = uc.insert_batch(items)
            assert total == 5
            assert new == 5


# ========== Test parse_rss (no real HTTP) ==========

class TestParseRss:
    def test_parse_rss_basic(self):
        rss = """<?xml version="1.0"?>
<rss version="2.0">
<channel>
<item>
<title>Test Article</title>
<link>https://example.com/article</link>
<description>This is a test description</description>
<pubDate>Mon, 14 Jun 2026 10:00:00 GMT</pubDate>
</item>
</channel>
</rss>"""
        items = uc.parse_rss(rss)
        assert len(items) == 1
        assert items[0]["title"] == "Test Article"
        assert items[0]["url"] == "https://example.com/article"

    def test_parse_rss_empty_xml(self):
        assert uc.parse_rss("") == []

    def test_parse_rss_invalid_xml(self):
        assert uc.parse_rss("not xml at all") == []

    def test_parse_rss_no_items(self):
        rss = '<?xml version="1.0"?><rss version="2.0"><channel><title>Empty</title></channel></rss>'
        assert uc.parse_rss(rss) == []

    def test_parse_rss_cdata_stripped(self):
        rss = """<?xml version="1.0"?>
<rss version="2.0">
<channel>
<item>
<title><![CDATA[CDATA Title]]></title>
<link>https://ex.com/1</link>
<description>desc</description>
</item>
</channel>
</rss>"""
        items = uc.parse_rss(rss)
        assert len(items) == 1
        assert items[0]["title"] == "CDATA Title"
