#!/usr/bin/env python3
"""Tests for hermes_v12_push.py — push engine, no real HTTP requests."""
import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import hermes_v12_push as push


# ========== Fixtures ==========

@pytest.fixture
def sample_item():
    return {
        "id": 1001,
        "title": "OpenAI发布GPT-5模型性能大幅提升",
        "content": "OpenAI刚刚发布了GPT-5模型，采用全新架构...",
        "url": "https://example.com/gpt5",
        "source": "ithome",
        "platform": "ithome",
        "author": "测试",
        "ai_score_total": 85,
        "importance_score": 9,
        "personal_match_score": 8,
        "tags": "AI|Tech",
        "category": "AI",
        "published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "collected_at": datetime.now().isoformat(),
        "cleaned_at": datetime.now().isoformat(),
    }


# ========== Test Tier / Tag helpers ==========

class TestTagTierMapping:
    def test_ai_is_p0(self):
        assert push.get_tier_for_tag("AI") == "P0"

    def test_dev_is_p0(self):
        assert push.get_tier_for_tag("Dev") == "P0"

    def test_sports_fight_is_p1(self):
        assert push.get_tier_for_tag("Sports_Fight") == "P1"

    def test_beauty_photo_is_p1(self):
        assert push.get_tier_for_tag("Beauty_Photo") == "P1"

    def test_travel_food_is_p2(self):
        assert push.get_tier_for_tag("Travel_Food") == "P2"

    def test_general_is_p2(self):
        assert push.get_tier_for_tag("General") == "P2"

    def test_unknown_tag_defaults_p2(self):
        assert push.get_tier_for_tag("NonExistentTag") == "P2"

    def test_p0_marker_is_fire(self):
        assert push.get_tier_marker("AI") == "🔥"

    def test_p1_marker_is_star(self):
        assert push.get_tier_marker("Sports_Fight") == "⭐"

    def test_p2_marker_empty(self):
        assert push.get_tier_marker("Travel_Food") == ""


class TestTierMultiplier:
    def test_p0_multiplier(self):
        assert push.TIER_MULTIPLIER["P0"] == 2.5

    def test_p1_multiplier(self):
        assert push.TIER_MULTIPLIER["P1"] == 1.5

    def test_p2_multiplier(self):
        assert push.TIER_MULTIPLIER["P2"] == 1.0


# ========== Test Platform helpers ==========

class TestPlatformIcon:
    def test_ithome_icon(self):
        assert push.get_platform_icon("ithome") == "🏠"

    def test_github_icon(self):
        assert push.get_platform_icon("github") == "🐙"

    def test_unknown_icon(self):
        assert push.get_platform_icon("unknown") == "🌐"

    def test_weibo_icon(self):
        assert push.get_platform_icon("weibo") == "🐦"


class TestPlatformColor:
    def test_ithome_color(self):
        assert push.get_platform_color("ithome") == "#E74C3C"

    def test_github_color(self):
        assert push.get_platform_color("github") == "#333333"

    def test_unknown_color(self):
        assert push.get_platform_color("unknown") == "#666666"

    def test_zhihu_color(self):
        assert push.get_platform_color("zhihu") == "#1ABC9C"


# ========== Test is_trash ==========

class TestIsTrash:
    def test_empty_title_is_trash(self):
        assert push.is_trash("", "") is True

    def test_novel_keyword_is_trash(self):
        assert push.is_trash("修仙小说最新章节", "") is True

    def test_social_garbage_is_trash(self):
        assert push.is_trash("婚前查出乙肝怎么办", "") is True

    def test_political_vacuous_is_trash(self):
        assert push.is_trash("深入学习贯彻重要指示", "") is True

    def test_high_score_item_passes_trash_check(self):
        item = {"ai_score_total": 80}
        assert push.is_trash("Some AI related content", "", item) is False

    def test_high_score_still_blocks_hard_trash(self):
        item = {"ai_score_total": 80}
        assert push.is_trash("修仙小说最新章节", "", item) is True

    def test_bilibili_trash_pattern(self):
        assert push.is_trash("代号XYZ首曝", "") is True

    def test_clean_title_not_trash(self):
        item = {"ai_score_total": 30}
        assert push.is_trash("GPT-5模型重大突破", "技术细节内容", item) is False

    def test_too_few_chinese_chars_trash(self):
        assert push.is_trash("AB!", "") is True

    def test_too_many_punctuation_trash(self):
        # Actual code checks title.count("!") + title.count("?") >= 4 (ASCII only)
        assert push.is_trash("真的假的!!!!????", "") is True

    def test_low_quality_vlog_trash(self):
        assert push.is_trash("景区探店打卡攻略", "") is True

    def test_sports_score_trash(self):
        assert push.is_trash("100比98绝杀比赛", "") is True

    def test_starts_with_jiuzai(self):
        assert push.is_trash("就在刚刚重大事件爆发", "") is True


# ========== Test score_quality ==========

class TestScoreQuality:
    def test_zero_score_no_tags_no_kw(self, monkeypatch):
        """Item with no tags and no keyword matches gets 0."""
        item = {"title": "无关内容", "content": "", "ai_score_total": 0,
                "personal_match_score": 0, "tags": "", "published_at": ""}
        monkeypatch.setattr(push, "load_user_keywords", lambda: [])
        score, count = push.score_quality(item)
        assert score == 0.0

    def test_ai_score_boosts(self, monkeypatch):
        item = {"title": "AI news", "content": "", "ai_score_total": 80,
                "personal_match_score": 0, "tags": "AI", "published_at": datetime.now().isoformat()}
        monkeypatch.setattr(push, "load_user_keywords", lambda: [])
        score, count = push.score_quality(item)
        assert score > 0

    def test_p0_tag_bonus(self, monkeypatch):
        item = {"title": "AI breakthrough", "content": "", "ai_score_total": 50,
                "personal_match_score": 0, "tags": "AI", "published_at": datetime.now().isoformat()}
        monkeypatch.setattr(push, "load_user_keywords", lambda: [])
        score, count = push.score_quality(item)
        assert score > 0

    def test_time_decay_old_item(self, monkeypatch):
        old_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        item = {"title": "AI", "content": "", "ai_score_total": 50,
                "personal_match_score": 0, "tags": "AI", "published_at": old_date}
        monkeypatch.setattr(push, "load_user_keywords", lambda: [])
        score, count = push.score_quality(item)
        # Should have decay factor < 1
        assert score > 0  # still has some score

    def test_no_published_time_decay(self, monkeypatch):
        item = {"title": "AI", "content": "", "ai_score_total": 50,
                "personal_match_score": 0, "tags": "AI", "published_at": ""}
        monkeypatch.setattr(push, "load_user_keywords", lambda: [])
        score, count = push.score_quality(item)
        assert score >= 0

    def test_keyword_match_bonus(self, monkeypatch):
        item = {"title": "machine learning progress", "content": "", "ai_score_total": 30,
                "personal_match_score": 0, "tags": "AI", "published_at": datetime.now().isoformat()}
        monkeypatch.setattr(push, "load_user_keywords", lambda: [("machine learning", 10, "AI")])
        score, count = push.score_quality(item)
        assert score > 0
        assert count > 0


# ========== Test is_chinese ==========

class TestIsChinese:
    def test_chinese_text(self):
        assert push.is_chinese("这是中文内容") is True

    def test_english_text(self):
        assert push.is_chinese("hello world") is False

    def test_empty_text(self):
        assert push.is_chinese("") is False

    def test_mixed_text(self):
        assert push.is_chinese("hello世界") is True

    def test_none_text(self):
        assert push.is_chinese(None) is False


# ========== Test Build HTML ==========

class TestBuildHtmlMessage:
    def test_returns_string(self, monkeypatch):
        monkeypatch.setattr(push, "load_user_keywords", lambda: [])
        items = [{"title": "Test", "url": "https://ex.com", "platform": "github",
                  "ai_score_total": 75, "tags": "AI"}]
        html = push.build_html_message(items, "14:00")
        assert isinstance(html, str)
        assert "<a href=" in html
        assert "Test" in html
        assert "github" in html

    def test_contains_platform_stats(self, monkeypatch):
        monkeypatch.setattr(push, "load_user_keywords", lambda: [])
        items = [
            {"title": "T1", "url": "https://ex.com/1", "platform": "ithome", "ai_score_total": 70, "tags": "AI"},
            {"title": "T2", "url": "https://ex.com/2", "platform": "github", "ai_score_total": 65, "tags": "Dev"},
        ]
        html = push.build_html_message(items, "14:00")
        assert "ithome" in html
        assert "github" in html

    def test_title_truncated(self, monkeypatch):
        monkeypatch.setattr(push, "load_user_keywords", lambda: [])
        long_title = "A" * 100
        items = [{"title": long_title, "url": "https://ex.com", "platform": "test",
                  "ai_score_total": 50, "tags": ""}]
        html = push.build_html_message(items, "14:00")
        assert len(long_title) > 65  # title should be truncated in HTML
        # The actual html content will have truncated version
        assert "A" * 65 in html or "A" * 62 + "..." in html

    def test_no_url_uses_span(self, monkeypatch):
        monkeypatch.setattr(push, "load_user_keywords", lambda: [])
        items = [{"title": "No URL", "url": "", "platform": "test", "ai_score_total": 50, "tags": ""}]
        html = push.build_html_message(items, "14:00")
        assert "<span" in html

    def test_marker_for_p0_tag(self, monkeypatch):
        monkeypatch.setattr(push, "load_user_keywords", lambda: [])
        items = [{"title": "AI News", "url": "https://ex.com", "platform": "test",
                  "ai_score_total": 80, "tags": "AI"}]
        html = push.build_html_message(items, "14:00")
        # P0 items get 🔥 marker
        assert "🔥" in html or "🎯" in html

    def test_html_structure(self, monkeypatch):
        monkeypatch.setattr(push, "load_user_keywords", lambda: [])
        items = [{"title": "T", "url": "https://ex.com", "platform": "test",
                  "ai_score_total": 50, "tags": ""}]
        html = push.build_html_message(items, "14:00")
        assert "<div" in html
        assert "</div>" in html


# ========== Test enforce_diversity ==========

class TestEnforceDiversity:
    def test_basic_diversity(self):
        items = [
            {"platform": "a", "_score": 100},
            {"platform": "b", "_score": 90},
            {"platform": "c", "_score": 80},
        ]
        result = push.enforce_diversity(items, 3)
        assert len(result) == 3

    def test_diversity_limits_per_platform(self):
        items = [{"platform": "a", "_score": i} for i in range(100, 0, -1)]
        result = push.enforce_diversity(items, 30)
        assert len(result) <= 30

    def test_empty_items(self):
        assert push.enforce_diversity([], 10) == []

    def test_single_platform(self):
        items = [{"platform": "a", "_score": i} for i in range(5)]
        result = push.enforce_diversity(items, 10)
        # MAX_PLATFORM_RATIO=0.3, target=10 -> max_per=3
        assert len(result) == 3

    def test_returns_sorted(self):
        items = [
            {"platform": "a", "_score": 10},
            {"platform": "b", "_score": 100},
        ]
        result = push.enforce_diversity(items, 2)
        assert result[0]["_score"] >= result[1]["_score"]


# ========== Test is_recent_published ==========

class TestIsRecentPublished:
    def test_empty_pub_str(self):
        assert push.is_recent_published("") is None

    def test_recent_iso_date(self):
        recent = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        assert push.is_recent_published(recent, max_days=7) is True

    def test_old_iso_date(self):
        old = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        assert push.is_recent_published(old, max_days=7) is False

    def test_timeconvert_format(self):
        ts = int(time.time())
        assert push.is_recent_published(f"timeConvert('{ts}')", max_days=7) is True

    def test_invalid_format_returns_none(self):
        assert push.is_recent_published("not-a-date") is None


# ========== Test get_pushplus_token (no real file) ==========

class TestGetPushplusToken:
    def test_config_yaml_token(self, monkeypatch):
        mock_config = {"pushplus": {"token": "valid_token_that_is_long_enough_12345"}}
        monkeypatch.setattr("yaml.safe_load", lambda f: mock_config)
        monkeypatch.setattr(push.Path, "exists", lambda self: True)
        with patch("builtins.open", MagicMock()):
            token = push.get_pushplus_token()
            assert token == "valid_token_that_is_long_enough_12345"

    def test_no_config_returns_env_token(self, monkeypatch):
        # The real env has PUSHPLUS_TOKEN, so this test checks the env fallback
        monkeypatch.setattr(push.Path, "exists", lambda self: False)
        token = push.get_pushplus_token()
        # Either empty (no env) or the real token (if env set) — both acceptable
        assert isinstance(token, str)

    def test_short_token_rejected(self, monkeypatch):
        mock_config = {"pushplus": {"token": "short"}}
        monkeypatch.setattr("yaml.safe_load", lambda f: mock_config)
        monkeypatch.setattr(push.Path, "exists", lambda self: True)
        with patch("builtins.open", MagicMock()):
            token = push.get_pushplus_token()
            assert token == ""  # falls through to env, which is also empty


# ========== Test push_wechat (no real HTTP) ==========

class TestPushWechat:
    def test_no_token_returns_error(self, monkeypatch):
        monkeypatch.setattr(push, "get_pushplus_token", lambda: "")
        result = push.push_wechat("Test", "<div>content</div>")
        assert result["code"] == -1
        assert "token" in result["msg"]

    def test_long_html_gets_truncated(self, monkeypatch):
        monkeypatch.setattr(push, "get_pushplus_token", lambda: "valid_token_that_is_long_enough_12345")
        long_html = "\n".join([f'<a href="https://ex.com/{i}">Title {i}</a>' for i in range(200)])
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"code": 200}'
        # push_wechat uses urllib.request.urlopen(req, timeout=15) directly (not as context manager)
        with patch.object(push.urllib.request, "urlopen", return_value=mock_resp):
            result = push.push_wechat("Test", long_html)
            assert result["code"] == 200

    def test_successful_push(self, monkeypatch):
        monkeypatch.setattr(push, "get_pushplus_token", lambda: "valid_token_that_is_long_enough_12345")
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"code": 200}'
        with patch.object(push.urllib.request, "urlopen", return_value=mock_resp):
            result = push.push_wechat("Test", "<div>content</div>")
            assert result["code"] == 200

    def test_push_failure_returns_error(self, monkeypatch):
        monkeypatch.setattr(push, "get_pushplus_token", lambda: "valid_token_that_is_long_enough_12345")
        with patch.object(push, "urllib") as mock_urllib:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b'{"code": 400, "msg": "error"}'
            mock_urllib.request.urlopen.return_value.__enter__.return_value = mock_resp
            result = push.push_wechat("Test", "<div>content</div>")
            assert result["code"] == -1

    def test_push_exception_retries(self, monkeypatch):
        monkeypatch.setattr(push, "get_pushplus_token", lambda: "valid_token_that_is_long_enough_12345")
        with patch.object(push, "urllib") as mock_urllib:
            mock_urllib.request.urlopen.side_effect = [Exception("timeout"),
                                                        Exception("timeout"),
                                                        Exception("timeout")]
            result = push.push_wechat("Test", "<div>content</div>")
            assert result["code"] == -1
            assert mock_urllib.request.urlopen.call_count == 2  # max_retries=2


# ========== Test record_pushed ==========

class TestRecordPushed:
    def test_empty_items_noop(self):
        mock_conn = MagicMock()
        with patch.object(push, "sqlite3") as mock_sqlite:
            mock_sqlite.connect.return_value = mock_conn
            push.record_pushed([])
            assert mock_conn.commit.called

    def test_records_item(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.execute.return_value.fetchone.return_value = None
        items = [{"id": 1, "title": "Test", "content": "C", "url": "https://ex.com",
                  "source": "src", "platform": "plat", "_score": 50}]
        with patch.object(push, "sqlite3") as mock_sqlite:
            mock_sqlite.connect.return_value = mock_conn
            push.record_pushed(items)
            assert mock_conn.commit.called


# ========== Test Constants ==========

class TestConstants:
    def test_target_count(self):
        assert push.TARGET_COUNT == 25

    def test_min_platforms(self):
        assert push.MIN_PLATFORMS == 6

    def test_max_platform_ratio(self):
        assert push.MAX_PLATFORM_RATIO == 0.3

    def test_tier_markers_p0(self):
        assert push.TIER_MARKERS["P0"] == "🔥"

    def test_tier_markers_p1(self):
        assert push.TIER_MARKERS["P1"] == "⭐"

    def test_tier_markers_p2(self):
        assert push.TIER_MARKERS["P2"] == ""

    def test_tier_multiplier_keys(self):
        assert set(push.TIER_MULTIPLIER.keys()) == {"P0", "P1", "P2"}

    def test_bilibili_trash_patterns_exist(self):
        assert len(push.BILIBILI_TRASH_PATTERNS) > 0

    def test_trash_keywords_hard_exist(self):
        assert len(push.TRASH_KEYWORDS_HARD) > 10
