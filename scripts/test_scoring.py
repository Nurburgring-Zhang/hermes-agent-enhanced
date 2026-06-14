#!/usr/bin/env python3
"""Tests for ai_sixdim_scorer + hermes_ai_scoring — scoring system."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import ai_sixdim_scorer as sixdim
import hermes_ai_scoring as hasc


# ========== Fixtures ==========

@pytest.fixture
def sample_item():
    return {
        "id": 12345,
        "title": "OpenAI发布GPT-5: AI进入AGI时代",
        "content": "OpenAI刚刚发布了GPT-5模型，性能大幅提升，采用全新架构...",
        "source": "ithome",
        "platform": "ithome",
        "author": "测试作者",
    }


# ========== Tests for ai_sixdim_scorer (sixdim) ==========

class TestSixdimScoreItem:
    def test_score_item_returns_dict(self, sample_item):
        result = sixdim.score_item(sample_item)
        assert isinstance(result, dict)
        assert "scarcity" in result
        assert "impact" in result
        assert "tech_depth" in result
        assert "timeliness" in result
        assert "preference" in result
        assert "credibility" in result
        assert "total" in result
        assert "reasoning" in result

    def test_total_is_capped_at_100(self, sample_item):
        result = sixdim.score_item(sample_item)
        assert result["total"] <= 100

    def test_total_reasonable_for_ai_item(self, sample_item):
        result = sixdim.score_item(sample_item)
        # AI + ithome + recent should give a decent score
        assert result["total"] > 20

    def test_credibility_ithome_is_8(self, sample_item):
        result = sixdim.score_item(sample_item)
        assert result["credibility"] == 8

    def test_preference_high_for_ai_keywords(self, sample_item):
        result = sixdim.score_item(sample_item)
        assert result["preference"] >= 7

    def test_tech_depth_for_ai_content(self, sample_item):
        result = sixdim.score_item(sample_item)
        assert result["tech_depth"] >= 6

    def test_openai_impact(self, sample_item):
        result = sixdim.score_item(sample_item)
        assert result["impact"] >= 10

    def test_scarcity_baseline(self, sample_item):
        result = sixdim.score_item(sample_item)
        assert result["scarcity"] >= 5

    def test_timeliness_default_mid(self, sample_item):
        result = sixdim.score_item(sample_item)
        assert result["timeliness"] >= 5

    def test_weibo_credibility_is_4(self):
        item = {"id": 1, "title": "test", "content": "", "source": "weibo", "platform": "weibo"}
        result = sixdim.score_item(item)
        assert result["credibility"] == 4

    def test_arxiv_credibility_is_9(self):
        item = {"id": 1, "title": "test", "content": "", "source": "arxiv", "platform": "arxiv"}
        result = sixdim.score_item(item)
        assert result["credibility"] == 9

    def test_exclusive_keyword_boosts_scarcity(self):
        item = {"id": 1, "title": "独家首发: 重大突破", "content": "A" * 300, "source": "test"}
        result = sixdim.score_item(item)
        assert result["scarcity"] >= 18

    def test_reuters_exclusive(self):
        item = {"id": 1, "title": "Breaking: Reuters exclusive", "content": "Reuters exclusive report", "source": "test"}
        result = sixdim.score_item(item)
        assert result["scarcity"] >= 18

    def test_byd_impact(self):
        item = {"id": 1, "title": "比亚迪宣布全系可搭载天神之眼", "content": "行业里程碑事件", "source": "test"}
        result = sixdim.score_item(item)
        assert result["impact"] >= 18

    def test_tech_depth_multiple_details(self):
        item = {"id": 1, "title": "新GPU架构突破",
                "content": "2nm工艺 HBM4内存 张量核心 架构升级 神经网络加速 TOPS 100 TFLOPS",
                "source": "test"}
        result = sixdim.score_item(item)
        assert result["tech_depth"] >= 12

    def test_arxiv_tech_depth(self):
        item = {"id": 1, "title": "A New LLM Architecture",
                "content": "Abstract: We propose a new transformer variant with attention mechanism..." * 10,
                "source": "arxiv"}
        result = sixdim.score_item(item)
        assert result["tech_depth"] >= 10

    def test_reasoning_json(self, sample_item):
        result = sixdim.score_item(sample_item)
        reasoning = json.loads(result["reasoning"])
        assert "scarcity_reason" in reasoning
        assert "impact_reason" in reasoning
        assert "summary" in reasoning

    def test_importance_score_derived(self, sample_item):
        result = sixdim.score_item(sample_item)
        assert result["importance_score"] == result["total"] / 10.0

    def test_id_preserved(self, sample_item):
        result = sixdim.score_item(sample_item)
        assert result["id"] == sample_item["id"]

    def test_photography_low_timeliness(self):
        item = {"id": 1, "title": "2024年摄影器材榜中榜", "content": "2024年回顾...", "source": "test"}
        result = sixdim.score_item(item)
        assert result["timeliness"] <= 3


class TestSixdimHelperFunctions:
    def test_get_scarcity_reason_high(self):
        reason = sixdim.get_scarcity_reason(25, "独家首发", "test")
        assert "高独家性" in reason

    def test_get_impact_reason_high(self):
        reason = sixdim.get_impact_reason(22, "test title", "breaking news")
        assert "高影响力" in reason

    def test_get_tech_depth_reason_high(self):
        reason = sixdim.get_tech_depth_reason(15, "architecture paper", "arxiv")
        assert "技术深度高" in reason

    def test_get_timeliness_reason_high(self):
        reason = sixdim.get_timeliness_reason(10, "today news")
        assert "极高时效性" in reason

    def test_get_preference_reason_high(self):
        reason = sixdim.get_preference_reason(9, "AI breakthrough")
        assert "高度偏好匹配" in reason

    def test_get_credibility_reason_high(self):
        reason = sixdim.get_credibility_reason(9, "ithome")
        assert "高可信度" in reason

    def test_get_summary_format(self):
        summary = sixdim.get_summary("Test title here", 75, 15, 20, 12)
        assert "75" in summary
        assert "Test" in summary

    def test_article_with_date_pattern(self):
        item = {"id": 1, "title": "Test", "content": "2026年5月29日，重大事件发生", "source": "test"}
        result = sixdim.score_item(item)
        assert result["timeliness"] >= 7


# ========== Tests for hermes_ai_scoring (hasc) ==========

class TestHascTimeliness:
    def test_no_date_returns_5(self):
        assert hasc.score_timeliness(None) == 5

    def test_recent_24h_returns_10(self):
        now = datetime.now().isoformat()
        assert hasc.score_timeliness(now) == 10

    def test_invalid_date_returns_5(self):
        assert hasc.score_timeliness("not-a-date") == 5

    def test_old_date_returns_1(self):
        old = (datetime.now().replace(year=2020)).isoformat()
        assert hasc.score_timeliness(old) == 1


class TestHascSourceCredibility:
    def test_offical_source(self):
        assert hasc.score_source_credibility("github", "") == 10
        assert hasc.score_source_credibility("openai", "") == 10

    def test_first_hand_source(self):
        assert hasc.score_source_credibility("twitter", "") == 8

    def test_media_source(self):
        assert hasc.score_source_credibility("36kr", "") == 6

    def test_unknown_source(self):
        assert hasc.score_source_credibility("unknown_blog", "") == 3

    def test_none_source(self):
        assert hasc.score_source_credibility(None, None) == 3


class TestHascPreferenceRule:
    def test_no_weights_returns_5(self):
        result = hasc.score_preference_rule("title", "content", {})
        assert result == 5

    def test_matching_keyword_boosts(self):
        weights = {"ai": 15, "llm": 12}
        result = hasc.score_preference_rule("AI and LLM breakthrough", "", weights)
        assert result > 5

    def test_no_match_returns_0(self):
        weights = {"basketball": 15}
        result = hasc.score_preference_rule("AI breakthrough", "", weights)
        assert result == 0

    def test_score_capped_at_10(self):
        weights = {"ai": 99}
        result = hasc.score_preference_rule("ai ai ai ai ai", "", weights)
        assert result <= 10


class TestHascParseAiResponse:
    def test_parse_valid_json(self):
        text = '[{"id": 1, "scarcity": 10, "impact": 15, "tech_depth": 8}]'
        result = hasc.parse_ai_response(text)
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_parse_with_markdown_codeblock(self):
        text = '```json\n[{"id": 1, "scarcity": 10}]\n```'
        result = hasc.parse_ai_response(text)
        assert len(result) == 1

    def test_parse_nested_scores(self):
        text = '{"scores": [{"id": 1, "scarcity": 10}]}'
        result = hasc.parse_ai_response(text)
        assert len(result) == 1

    def test_parse_invalid_returns_empty(self):
        result = hasc.parse_ai_response("not json at all")
        assert result == []

    def test_parse_empty_string(self):
        assert hasc.parse_ai_response("") == []

    def test_parse_with_id_order_match(self):
        items = [{"id": 100}, {"id": 200}]
        text = '[{"scarcity": 10}, {"scarcity": 20}]'
        result = hasc.parse_ai_response(text, items=items)
        assert result[0]["id"] == 100
        assert result[1]["id"] == 200

    def test_parse_extract_json_from_text(self):
        text = 'Here are the scores: [{"id": 1, "scarcity": 10}] End.'
        result = hasc.parse_ai_response(text)
        assert len(result) == 1


class TestHascApplyRulesFallback:
    def test_returns_dict(self):
        item = {"id": 1, "title": "test", "content": "", "source": "test", "platform": "test"}
        result = hasc.apply_rules_for_fallback(item, {})
        assert isinstance(result, dict)
        assert "total" in result
        assert result["total"] > 0

    def test_github_tech_depth_boost(self):
        item = {"id": 1, "title": "test repo", "content": "", "source": "github", "platform": "github"}
        result = hasc.apply_rules_for_fallback(item, {"code": 10})
        assert result["tech_depth"] >= 16

    def test_arxiv_scarcity_boost(self):
        item = {"id": 1, "title": "test paper", "content": "", "source": "arxiv", "platform": "arxiv"}
        result = hasc.apply_rules_for_fallback(item, {})
        assert result["tech_depth"] >= 18

    def test_exclusive_keyword_scarcity(self):
        item = {"id": 1, "title": "独家首次披露内部消息", "content": "", "source": "test"}
        result = hasc.apply_rules_for_fallback(item, {})
        assert result["scarcity"] >= 20

    def test_impact_keywords(self):
        item = {"id": 1, "title": "行业变革全球里程碑事件", "content": "", "source": "test"}
        result = hasc.apply_rules_for_fallback(item, {})
        assert result["impact"] >= 20

    def test_tech_keywords(self):
        item = {"id": 1, "title": "新架构算法框架模型训练", "content": "", "source": "test"}
        result = hasc.apply_rules_for_fallback(item, {})
        assert result["tech_depth"] >= 14


class TestHascGenerateAiScoringPrompt:
    def test_empty_items_returns_empty(self):
        assert hasc.generate_ai_scoring_prompt([], {}) == ""

    def test_prompt_contains_item_details(self):
        items = [{"id": 1, "title": "Test Title", "content": "Test Content",
                  "source": "test", "platform": "test", "author": "author"}]
        prompt = hasc.generate_ai_scoring_prompt(items, {})
        assert "Test Title" in prompt
        assert "Test Content" in prompt
        assert "## 条目 #1" in prompt

    def test_prompt_contains_scoring_criteria(self):
        items = [{"id": 1, "title": "T", "content": "C", "source": "s", "platform": "p", "author": "a"}]
        prompt = hasc.generate_ai_scoring_prompt(items, {"ai": 15})
        assert "稀缺性" in prompt
        assert "影响力" in prompt
        assert "ai" in prompt

    def test_prompt_json_output_format(self):
        items = [{"id": 1, "title": "T", "content": "C", "source": "s", "platform": "p", "author": "a"}]
        prompt = hasc.generate_ai_scoring_prompt(items, {})
        assert "scarcity" in prompt
        assert "impact" in prompt
        assert "tech_depth" in prompt

    def test_prompt_includes_pref_hints(self):
        items = [{"id": 1, "title": "T", "content": "C", "source": "s", "platform": "p", "author": "a"}]
        prompt = hasc.generate_ai_scoring_prompt(items, {"ai": 15.0, "llm": 12.0})
        assert "ai" in prompt
        assert "llm" in prompt


class TestHascLoadKeywordWeights:
    def test_no_db_returns_empty(self, monkeypatch):
        monkeypatch.setattr(hasc.Path, "exists", lambda self: False)
        assert hasc.load_keyword_weights() == {}

    def test_db_exception_returns_empty(self, monkeypatch):
        monkeypatch.setattr(hasc.Path, "exists", lambda self: True)
        with patch.object(hasc, "sqlite3") as mock_sqlite:
            mock_sqlite.connect.side_effect = Exception("error")
            result = hasc.load_keyword_weights()
            assert result == {}

    def test_load_returns_dict(self, monkeypatch):
        monkeypatch.setattr(hasc.Path, "exists", lambda self: True)
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchall.return_value = [("ai", 15), ("llm", 10)]
        with patch.object(hasc, "sqlite3") as mock_sqlite:
            mock_sqlite.connect.return_value = mock_conn
            result = hasc.load_keyword_weights()
            assert result == {"ai": 15.0, "llm": 10.0}


class TestHascGetPendingItems:
    def test_returns_list(self, monkeypatch):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = None
        mock_conn.execute.return_value = mock_cur
        mock_cur.fetchall.return_value = []
        mock_cur.description = [("id",), ("title",)]

        with patch.object(hasc, "sqlite3") as mock_sqlite:
            mock_sqlite.connect.return_value = mock_conn
            result = hasc.get_pending_items(limit=5, min_content_len=0)
            assert isinstance(result, list)


class TestHascSaveScoresToDb:
    def test_empty_scores_returns_0(self):
        assert hasc.save_scores_to_db([]) == 0

    def test_saves_scores(self):
        mock_conn = MagicMock()
        scores = [{"id": 1, "scarcity": 10, "impact": 15, "tech_depth": 8,
                   "timeliness": 5, "preference": 7, "credibility": 6}]
        with patch.object(hasc, "sqlite3") as mock_sqlite:
            mock_sqlite.connect.return_value = mock_conn
            result = hasc.save_scores_to_db(scores)
            assert result == 1
