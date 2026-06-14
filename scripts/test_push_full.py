#!/usr/bin/env python3
"""Comprehensive tests for hermes_v12_push.py — push system full coverage."""
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

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
    }


# ========== Test get_tier_for_tag extended ==========

class TestGetTierForTagExtended:
    def test_military_is_p0(self):
        assert push.get_tier_for_tag("Military") == "P0"

    def test_ev_is_p0(self):
        assert push.get_tier_for_tag("EV") == "P0"

    def test_politics_is_p0(self):
        assert push.get_tier_for_tag("Politics") == "P0"

    def test_security_is_p0(self):
        assert push.get_tier_for_tag("Security") == "P0"

    def test_game_is_p1(self):
        assert push.get_tier_for_tag("Game") == "P1"

    def test_science_is_p1(self):
        assert push.get_tier_for_tag("Science") == "P1"

    def test_music_is_p1(self):
        assert push.get_tier_for_tag("Music") == "P1"

    def test_fashion_is_p2(self):
        assert push.get_tier_for_tag("Fashion") == "P2"

    def test_entertainment_is_p2(self):
        assert push.get_tier_for_tag("Entertainment") == "P2"

    def test_startup_is_p2(self):
        assert push.get_tier_for_tag("Startup") == "P2"

    def test_video_is_p2(self):
        assert push.get_tier_for_tag("Video") == "P2"


# ========== Test get_tier_marker extended ==========

class TestGetTierMarkerExtended:
    def test_military_tag(self):
        assert push.get_tier_marker("Military") == "🔥"

    def test_music_tag(self):
        assert push.get_tier_marker("Music") == "⭐"

    def test_fashion_tag(self):
        assert push.get_tier_marker("Fashion") == ""

    def test_unknown_tag(self):
        assert push.get_tier_marker("UnknownXYZ") == ""


# ========== Test get_platform_icon/color extended ==========

class TestPlatformIconColorExtended:
    def test_bilibili_icon(self):
        assert push.get_platform_icon("bilibili") == "📺"

    def test_douyin_icon(self):
        assert push.get_platform_icon("douyin") == "🎵"

    def test_solidot_icon(self):
        assert push.get_platform_icon("solidot") == "🔧"

    def test_36kr_icon(self):
        assert push.get_platform_icon("36kr") == "📊"

    def test_bilibili_color(self):
        assert push.get_platform_color("bilibili") == "#00A1D6"

    def test_douyin_color(self):
        assert push.get_platform_color("douyin") == "#000000"


# ========== Test is_trash extended ==========

class TestIsTrashExtended:
    def test_empty_title_is_trash(self):
        assert push.is_trash("") is True
        assert push.is_trash(None) is True

    def test_high_score_passes(self):
        item = {"ai_score_total": 80}
        assert push.is_trash("Some normal title about AI and tech", "", item) is False

    def test_hard_trash_blocked_even_high_score(self):
        item = {"ai_score_total": 80}
        assert push.is_trash("修仙小说最新章节", "", item) is True

    def test_bilibili_trash_title(self):
        assert push.is_trash("代号XYZ首曝游戏", "") is True

    def test_political_vacuous(self):
        assert push.is_trash("总书记对经济工作做出重要指示", "") is True

    def test_social_garbage(self):
        assert push.is_trash("婚前查出乙肝父母让分手", "") is True

    def test_sports_score(self):
        assert push.is_trash("铁人三项赛100比98绝杀", "") is True

    def test_low_quality_vlog(self):
        assert push.is_trash("航拍延时摄影打卡景区攻略", "") is True

    def test_clean_title_ok(self):
        item = {"ai_score_total": 30}
        assert push.is_trash("GPT-5模型重大突破技术细节分析", "详细的技术架构分析", item) is False

    def test_high_score_blocks_only_hard(self, monkeypatch):
        monkeypatch.setattr(push, "_SPAM_KEYWORDS_CACHE", [])
        item = {"ai_score_total": 55}
        # NBA is in TRASH_KEYWORDS_HARD but for high-score items only HARD_TRASH subset is checked
        # HARD_TRASH = {"目瑙纵歌", "小说", "修仙", "穿越", "赘婿", "兵王", "末世",
        #               "诡秘", "玄幻", "斗罗", "食人魔", "打赏"}
        # NBA is NOT in HARD_TRASH, so high-score NBA items pass
        assert push.is_trash("NBA篮球赛事分析", "", item) is False


# ========== Test score_quality extended ==========

class TestScoreQualityExtended:
    def test_no_tags_no_kw_no_ai(self, monkeypatch):
        monkeypatch.setattr(push, "load_user_keywords", list)
        item = {"title": "test", "content": "", "ai_score_total": 0,
                "personal_match_score": 0, "tags": "", "published_at": ""}
        score, count = push.score_quality(item)
        assert score >= 0

    def test_p0_tag_with_ai_score(self, monkeypatch):
        monkeypatch.setattr(push, "load_user_keywords", list)
        item = {"title": "AI", "content": "", "ai_score_total": 80,
                "personal_match_score": 0, "tags": "AI",
                "published_at": datetime.now().isoformat()}
        score, count = push.score_quality(item)
        assert score > 20

    def test_p1_tag_without_ai_score(self, monkeypatch):
        monkeypatch.setattr(push, "load_user_keywords", list)
        item = {"title": "Sports", "content": "", "ai_score_total": 0,
                "personal_match_score": 0, "tags": "Sports_Fight",
                "published_at": datetime.now().isoformat()}
        score, count = push.score_quality(item)
        assert score >= 0

    def test_very_old_item_decay(self, monkeypatch):
        monkeypatch.setattr(push, "load_user_keywords", list)
        old_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d %H:%M:%S")
        item = {"title": "AI", "content": "", "ai_score_total": 80,
                "personal_match_score": 0, "tags": "AI", "published_at": old_date}
        score, count = push.score_quality(item)
        assert score > 0  # should still have some score

    def test_missing_published_at_uses_decay(self, monkeypatch):
        monkeypatch.setattr(push, "load_user_keywords", list)
        item = {"title": "AI", "content": "", "ai_score_total": 80,
                "personal_match_score": 0, "tags": "AI", "published_at": ""}
        score, count = push.score_quality(item)
        assert score >= 0


# ========== Test is_chinese extended ==========

class TestIsChineseExtended:
    def test_mixed_numbers(self):
        assert push.is_chinese("hello123世界") is True

    def test_only_numbers(self):
        assert push.is_chinese("123456") is False

    def test_punctuation_only(self):
        assert push.is_chinese("!!!???...") is False

    def test_single_chinese_char(self):
        assert push.is_chinese("中") is True


# ========== Test build_html_message extended ==========

class TestBuildHtmlMessageExtended:
    def test_empty_items(self, monkeypatch):
        monkeypatch.setattr(push, "load_user_keywords", list)
        html = push.build_html_message([], "14:00")
        assert isinstance(html, str)

    def test_no_url_item(self, monkeypatch):
        monkeypatch.setattr(push, "load_user_keywords", list)
        item = {"title": "No URL", "url": "", "platform": "test",
                "ai_score_total": 50, "tags": ""}
        html = push.build_html_message([item], "14:00")
        assert "<span" in html

    def test_tags_displayed(self, monkeypatch):
        monkeypatch.setattr(push, "load_user_keywords", list)
        item = {"title": "AI News", "url": "https://ex.com", "platform": "ithome",
                "ai_score_total": 80, "tags": "AI|Tech"}
        html = push.build_html_message([item], "14:00")
        assert "🔥" in html or "🎯" in html or "AI" in html


# ========== Test enforce_diversity extended ==========

class TestEnforceDiversityExtended:
    def test_exact_platform_count(self):
        items = [{"platform": p, "_score": 100 - i}
                 for i, p in enumerate(["a", "b", "c", "d", "e", "f", "g"])]
        result = push.enforce_diversity(items, 10)
        assert len(result) <= 10

    def test_mixed_scores(self):
        items = [
            {"platform": "a", "_score": 10},
            {"platform": "b", "_score": 100},
            {"platform": "c", "_score": 50},
            {"platform": "a", "_score": 90},
        ]
        result = push.enforce_diversity(items, 3)
        # Platform 'a' has 2 items, MAX_PLATFORM_RATIO=0.3 -> max 0 per platform for target=3 -> 0
        # Actually max_per = max(1, floor(3 * 0.3)) = 1
        assert len(result) <= 3

    def test_returned_sorted_descending(self):
        items = [
            {"platform": "a", "_score": 5},
            {"platform": "b", "_score": 10},
        ]
        result = push.enforce_diversity(items, 2)
        for i in range(len(result) - 1):
            assert result[i]["_score"] >= result[i + 1]["_score"]


# ========== Test is_recent_published extended ==========

class TestIsRecentPublishedExtended:
    def test_future_date(self):
        future = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        result = push.is_recent_published(future, max_days=7)
        assert result is True  # future dates are recent

    def test_exactly_boundary(self):
        boundary = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        result = push.is_recent_published(boundary, max_days=7)
        assert result is True

    def test_slightly_old(self):
        old = (datetime.now() - timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S")
        result = push.is_recent_published(old, max_days=7)
        assert result is False


# ========== Test load_user_keywords ==========

class TestLoadUserKeywords:
    def test_cache_hit(self, monkeypatch):
        push._USER_KW_CACHE = [("test", 10, "cat")]
        push._USER_KW_CACHE_TIME = time.time()
        result = push.load_user_keywords()
        assert result == [("test", 10, "cat")]

    def test_db_error_returns_empty(self, monkeypatch):
        push._USER_KW_CACHE = None
        push._USER_KW_CACHE_TIME = 0
        with patch.object(push, "sqlite3") as mock_sqlite:
            mock_sqlite.connect.side_effect = Exception("error")
            result = push.load_user_keywords()
            assert result == []

    def test_load_from_db(self, monkeypatch):
        push._USER_KW_CACHE = None
        push._USER_KW_CACHE_TIME = 0
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.return_value.fetchall.return_value = [("ai", 20, "AI"), ("llm", 15, "AI")]
        with patch.object(push, "sqlite3") as mock_sqlite:
            mock_sqlite.connect.return_value = mock_conn
            result = push.load_user_keywords()
            assert len(result) == 2


# ========== Test log function ==========

class TestLogFunction:
    def test_log_writes(self, monkeypatch, tmp_path):
        monkeypatch.setattr(push, "PUSH_LOG", tmp_path / "v12_push.log")
        push.log("test message")
        assert (tmp_path / "v12_push.log").exists()


# ========== Test record_pushed ==========

class TestRecordPushedExtended:
    def test_item_already_recorded(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.execute.return_value.fetchone.return_value = [1]
        items = [{"id": 1, "title": "Test", "content": "C", "url": "https://ex.com",
                  "source": "src", "platform": "plat", "_score": 50}]
        with patch.object(push, "sqlite3") as mock_sqlite:
            mock_sqlite.connect.return_value = mock_conn
            push.record_pushed(items)
            assert mock_conn.commit.called


# ========== Test constants ==========

class TestConstantsExtended:
    def test_tag_to_tier_size(self):
        assert len(push.TAG_TO_TIER) > 30

    def test_tier_multiplier_values(self):
        assert push.TIER_MULTIPLIER["P0"] > push.TIER_MULTIPLIER["P1"]
        assert push.TIER_MULTIPLIER["P1"] > push.TIER_MULTIPLIER["P2"]

    def test_platform_icons_count(self):
        assert len(push.PLATFORM_ICONS) > 10

    def test_platform_colors_count(self):
        assert len(push.PLATFORM_COLORS) > 10

    def test_trash_keywords_hard_count(self):
        assert len(push.TRASH_KEYWORDS_HARD) > 20

    def test_bilibili_trash_patterns_count(self):
        assert len(push.BILIBILI_TRASH_PATTERNS) > 5

    def test_category_multiplier_synonym(self):
        assert push.CATEGORY_MULTIPLIER is push.TIER_MULTIPLIER
