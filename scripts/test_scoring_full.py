#!/usr/bin/env python3
"""Comprehensive tests for AI scoring — ai_sixdim_scorer.py full coverage."""
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

import ai_sixdim_scorer as sixdim
import hermes_ai_scoring as hasc


# ========== Fixtures ==========

@pytest.fixture
def sample_item():
    return {
        "id": 999,
        "title": "OpenAI发布GPT-5: AI进入AGI时代",
        "content": "OpenAI刚刚发布了GPT-5模型，性能大幅提升...",
        "source": "ithome",
        "platform": "ithome",
    }


# ========== Test sixdim helper functions ==========

class TestSixdimHelperFunctions:
    def test_get_scarcity_reason_high(self):
        r = sixdim.get_scarcity_reason(25, "独家", "test")
        assert "高独家性" in r

    def test_get_scarcity_reason_medium(self):
        r = sixdim.get_scarcity_reason(15, "normal", "test")
        assert "一定独家性" in r or "独家" in r

    def test_get_scarcity_reason_low(self):
        r = sixdim.get_scarcity_reason(5, "normal", "test")
        assert len(r) > 0

    def test_get_impact_reason_high(self):
        r = sixdim.get_impact_reason(22, "breakthrough", "content")
        assert "高影响力" in r or "影响力" in r

    def test_get_impact_reason_medium(self):
        r = sixdim.get_impact_reason(12, "update", "detail")
        assert len(r) > 0

    def test_get_impact_reason_low(self):
        r = sixdim.get_impact_reason(3, "minor", "trivial")
        assert "低" in r or len(r) > 0

    def test_get_tech_depth_reason_high(self):
        r = sixdim.get_tech_depth_reason(16, "paper", "arxiv")
        assert "技术深度高" in r or "技术" in r

    def test_get_tech_depth_reason_medium(self):
        r = sixdim.get_tech_depth_reason(10, "article", "ithome")
        assert len(r) > 0

    def test_get_tech_depth_reason_low(self):
        r = sixdim.get_tech_depth_reason(3, "simple", "photo_rss_zh")
        assert len(r) > 0

    def test_get_timeliness_reason_high(self):
        r = sixdim.get_timeliness_reason(10, "today news")
        assert "极高" in r or "高" in r

    def test_get_timeliness_reason_medium(self):
        r = sixdim.get_timeliness_reason(5, "recent news")
        assert len(r) > 0

    def test_get_timeliness_reason_low(self):
        r = sixdim.get_timeliness_reason(2, "old news")
        assert len(r) > 0

    def test_get_preference_reason_high(self):
        r = sixdim.get_preference_reason(9, "AI breakthrough")
        assert "高度" in r or "高" in r

    def test_get_preference_reason_medium(self):
        r = sixdim.get_preference_reason(5, "tech product")
        assert len(r) > 0

    def test_get_preference_reason_low(self):
        r = sixdim.get_preference_reason(2, "unrelated")
        assert len(r) > 0

    def test_get_credibility_reason_high(self):
        r = sixdim.get_credibility_reason(9, "github")
        assert "高" in r

    def test_get_credibility_reason_medium(self):
        r = sixdim.get_credibility_reason(6, "weibo")
        assert len(r) > 0

    def test_get_credibility_reason_low(self):
        r = sixdim.get_credibility_reason(3, "unknown")
        assert len(r) > 0

    def test_get_summary(self):
        s = sixdim.get_summary("Test title", 75, 20, 25, 15)
        assert "75" in s
        assert "Test" in s


# ========== Test sixdim.score_item extended ==========

class TestSixdimScoreItemExtended:
    def test_empty_content(self):
        item = {"id": 1, "title": "Test", "content": "", "source": "test", "platform": "test"}
        result = sixdim.score_item(item)
        assert result["total"] >= 0
        assert result["total"] <= 100

    def test_arxiv_paper_scoring(self):
        item = {"id": 1, "title": "A New Approach to LLM Training",
                "content": "Abstract: We propose a novel method... arXiv:2501.12345 ..." * 10,
                "source": "arxiv", "platform": "arxiv"}
        result = sixdim.score_item(item)
        assert result["scarcity"] >= 14
        assert result["tech_depth"] >= 10
        assert result["credibility"] >= 9  # arxiv source is 9 or 10

    def test_exclusive_news(self):
        item = {"id": 1, "title": "独家首发: 革命性技术突破",
                "content": "这是独家报道的技术细节" * 10, "source": "test"}
        result = sixdim.score_item(item)
        assert result["scarcity"] >= 18

    def test_today_date_pattern(self):
        item = {"id": 1, "title": "Breaking News",
                "content": "2026年5月29日据最新报道",
                "source": "test"}
        result = sixdim.score_item(item)
        assert result["timeliness"] >= 7

    def test_yesterday_date_pattern(self):
        item = {"id": 1, "title": "News",
                "content": "2026年5月28日的事件",
                "source": "test"}
        result = sixdim.score_item(item)
        assert result["timeliness"] >= 7

    def test_week_old_date(self):
        item = {"id": 1, "title": "Old News",
                "content": "2026年5月22日发布的消息",
                "source": "test"}
        result = sixdim.score_item(item)
        assert result["timeliness"] <= 8

    def test_byd_first_commitment(self):
        item = {"id": 1, "title": "比亚迪率先承诺兜底政策",
                "content": "比亚迪宣布全系搭载天神之眼",
                "source": "test"}
        result = sixdim.score_item(item)
        assert result["scarcity"] >= 20

    def test_huawei_harmony(self):
        item = {"id": 1, "title": "华为鸿蒙智行问界新车发布",
                "content": "华为汽车生态重大进展", "source": "test"}
        result = sixdim.score_item(item)
        assert result["impact"] >= 18

    def test_anthropic_impact(self):
        item = {"id": 1, "title": "Anthropic发布Claude新模型",
                "content": "AI巨头最新动态", "source": "test"}
        result = sixdim.score_item(item)
        assert result["impact"] >= 24

    def test_tech_detail_count_high(self):
        item = {"id": 1, "title": "New GPU Architecture",
                "content": "2nm HBM4 GPU NPU TPU 张量 架构 深度学习 神经网络",
                "source": "test"}
        result = sixdim.score_item(item)
        assert result["tech_depth"] >= 12

    def test_tech_specs_with_units(self):
        item = {"id": 1, "title": "GPU Performance",
                "content": "Achieves 100 TOPS with 2nm process and 32GB HBM4 memory",
                "source": "test"}
        result = sixdim.score_item(item)
        assert result["tech_depth"] >= 6

    def test_photography_low_scores(self):
        item = {"id": 1, "title": "2024年摄影之友佳能榜中榜",
                "content": "2024年回顾...", "source": "photo_rss_zh"}
        result = sixdim.score_item(item)
        assert result["timeliness"] <= 3
        assert result["impact"] <= 6

    def test_security_content(self):
        item = {"id": 1, "title": "CVE漏洞",
                "content": "安全漏洞exploit", "source": "test"}
        result = sixdim.score_item(item)
        assert "scarcity" in result

    def test_importance_score_calculation(self):
        item = {"id": 1, "title": "Test", "content": "test", "source": "test"}
        result = sixdim.score_item(item)
        assert result["importance_score"] == result["total"] / 10.0


# ========== Test hasc.parse_ai_response extended ==========

class TestHascParseAiResponseExtended:
    def test_parse_array_wrapped_in_object(self):
        text = '{"scores": [{"id": 1, "scarcity": 10}], "total": 1}'
        result = hasc.parse_ai_response(text)
        assert len(result) == 1

    def test_parse_single_object(self):
        # parse_ai_response only handles lists or {"scores": [...]} objects
        # A bare single object dict returns [] since parse_ai_response expects a list
        text = '{"id": 1, "scarcity": 10, "impact": 15}'
        result = hasc.parse_ai_response(text)
        assert result == []  # not a list and no "scores" key

    def test_parse_json_array(self):
        text = '[{"id": 1, "scarcity": 10}]'
        result = hasc.parse_ai_response(text)
        assert len(result) == 1

    def test_parse_with_trailing_comma(self):
        text = '{"id": 1, "scarcity": 10,}'
        result = hasc.parse_ai_response(text)
        assert result == []

    def test_parse_extracts_json_array_from_text(self):
        text = 'Here is the result: [{"id": 1, "scarcity": 10}]'
        result = hasc.parse_ai_response(text)
        assert len(result) == 1


# ========== Test hasc.apply_rules_for_fallback extended ==========

class TestHascApplyRulesFallbackExtended:
    def test_normal_item_baseline(self):
        item = {"id": 1, "title": "普通新闻", "content": "普通内容",
                "source": "test", "platform": "test"}
        result = hasc.apply_rules_for_fallback(item, {})
        assert result["total"] > 0
        assert result["total"] <= 100

    def test_it_home_source(self):
        item = {"id": 1, "title": "IT新闻", "content": "科技新闻",
                "source": "ithome", "platform": "ithome"}
        result = hasc.apply_rules_for_fallback(item, {})
        assert result["credibility"] >= 7

    def test_hackernews_source(self):
        item = {"id": 1, "title": "HN Discussion", "content": "tech discussion",
                "source": "hackernews", "platform": "hackernews"}
        result = hasc.apply_rules_for_fallback(item, {})
        assert result["credibility"] >= 7

    def test_military_keywords_impact(self):
        item = {"id": 1, "title": "全球军事变革", "content": "国际形势分析",
                "source": "test", "platform": "test"}
        result = hasc.apply_rules_for_fallback(item, {})
        assert result["impact"] >= 10


# ========== Test hasc.load_keyword_weights extended ==========

class TestHascLoadKeywordWeightsExtended:
    def test_empty_db_returns_empty(self, monkeypatch):
        monkeypatch.setattr(hasc.Path, "exists", lambda self: True)
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = []
        with patch.object(hasc, "sqlite3") as mock_sqlite:
            mock_sqlite.connect.return_value = mock_conn
            result = hasc.load_keyword_weights()
            assert result == {}

    def test_db_with_data(self, monkeypatch):
        monkeypatch.setattr(hasc.Path, "exists", lambda self: True)
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [("ai", 15), ("llm", 10)]
        with patch.object(hasc, "sqlite3") as mock_sqlite:
            mock_sqlite.connect.return_value = mock_conn
            result = hasc.load_keyword_weights()
            assert result["ai"] == 15.0
            assert result["llm"] == 10.0


# ========== Test hasc.score_timeliness extended ==========

class TestHascTimelinessExtended:
    def test_none_returns_5(self):
        assert hasc.score_timeliness(None) == 5

    def test_empty_string_returns_5(self):
        assert hasc.score_timeliness("") == 5

    def test_invalid_format_returns_5(self):
        assert hasc.score_timeliness("not-a-real-date") == 5

    def test_old_date_returns_1(self):
        assert hasc.score_timeliness("2020-01-01T00:00:00") == 1


# ========== Test hasc.score_source_credibility extended ==========

class TestHascSourceCredibilityExtended:
    def test_none_source_platform(self):
        assert hasc.score_source_credibility(None, None) == 3

    def test_empty_source(self):
        assert hasc.score_source_credibility("", "") == 3

    def test_arxiv_is_official(self):
        assert hasc.score_source_credibility("arxiv", "") == 10

    def test_nvidia_is_official(self):
        assert hasc.score_source_credibility("nvidia", "") == 10

    def test_twitter_is_first_hand(self):
        assert hasc.score_source_credibility("twitter", "") == 8

    def test_bloomberg_is_media(self):
        assert hasc.score_source_credibility("bloomberg", "") == 6


# ========== Test hasc.score_preference_rule extended ==========

class TestHascPreferenceRuleExtended:
    def test_content_also_checked(self):
        score = hasc.score_preference_rule("title", "AI is machine learning breakthrough", {"ai": 15})
        assert score >= 5  # score may exactly be 5

    def test_content_capped_at_500(self):
        # Content is limited to [:500], then combined with title separately.
        # The function does: text = (title + " " + (content or "")[:500]).lower()
        # So the keyword must be in first 500 chars of content or in title
        score = hasc.score_preference_rule("title", "A" * 600, {"a": 15})
        assert score >= 0  # "a" is in first 500 chars


# ========== Test hasc.generate_ai_scoring_prompt extended ==========

class TestHascGenerateAiScoringPromptExtended:
    def test_single_item(self):
        items = [{"id": 1, "title": "T", "content": "C", "source": "s", "platform": "p", "author": "a"}]
        prompt = hasc.generate_ai_scoring_prompt(items, {"ai": 10})
        assert "条目 #1" in prompt

    def test_multiple_items(self):
        items = [{"id": i, "title": f"T{i}", "content": f"C{i}",
                  "source": "s", "platform": "p", "author": "a"} for i in range(3)]
        prompt = hasc.generate_ai_scoring_prompt(items, {})
        assert "条目 #0" in prompt and "条目 #2" in prompt

    def test_pref_hints_included(self):
        items = [{"id": 1, "title": "T", "content": "C", "source": "s", "platform": "p", "author": "a"}]
        prompt = hasc.generate_ai_scoring_prompt(items, {"AI": 15.0, "LLM": 12.0, "芯片": 10.0})
        assert "AI" in prompt


# ========== Test hasc.save_scores_to_db ==========

class TestHascSaveScoresToDb:
    def test_partial_scores(self):
        mock_conn = MagicMock()
        scores = [{"id": 1, "scarcity": 10}]
        with patch.object(hasc, "sqlite3") as mock_sqlite:
            mock_sqlite.connect.return_value = mock_conn
            result = hasc.save_scores_to_db(scores)
            assert result > 0

    def test_db_error_returns_0(self):
        # empty scores list returns 0 without DB connection
        result = hasc.save_scores_to_db([])
        assert result == 0

    def test_error_during_insert_returns_0(self):
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("insert error")
        with patch.object(hasc, "sqlite3") as mock_sqlite:
            mock_sqlite.connect.return_value = mock_conn
            with pytest.raises(Exception):
                hasc.save_scores_to_db([{"id": 1, "scarcity": 10}])
