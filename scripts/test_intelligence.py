#!/usr/bin/env python3
"""Tests for hermes_intelligence.py — intelligence pipeline (no real HTTP)."""
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

import hermes_intelligence as hi


# ========== Fixtures ==========

@pytest.fixture
def sample_item():
    return {
        "title": "OpenAI发布GPT-5大模型",
        "content": "OpenAI最新发布了GPT-5模型性能大幅提升",
        "url": "https://example.com/gpt5",
        "platform": "ithome",
        "source": "IT之家",
        "author": "test",
        "category": "tech",
        "hot_score": 5000,
        "view_count": 10000,
        "like_count": 500,
        "comment_count": 100,
        "collect_count": 50,
        "share_count": 50,
        "published_at": "2026-06-14 10:00:00",
        "raw_data": "{}",
    }


# ========== Test get_db ==========

class TestGetDb:
    def test_returns_connection_with_row_factory(self):
        with patch.object(hi, "sqlite3") as mock_sqlite:
            mock_conn = MagicMock()
            mock_sqlite.connect.return_value = mock_conn
            conn = hi.get_db()
            assert conn.row_factory == hi.sqlite3.Row


# ========== Test is_noise ==========

class TestIsNoise:
    def test_no_noise(self):
        assert hi.is_noise("AI大模型突破", "技术深度分析") is False

    def test_single_noise_kw_not_enough(self):
        # Use words that match at most 1 NOISE_KW keyword
        assert hi.is_noise("一个普通科技新闻", "这是关于技术的内容分析") is False

    def test_two_noise_kw_is_noise(self):
        assert hi.is_noise("明星娱乐八卦", "粉丝综艺") is True

    def test_content_also_checked(self):
        assert hi.is_noise("普通标题", "游戏主播娱乐八卦") is True

    def test_case_insensitive(self):
        assert hi.is_noise("明星 娱乐 新闻", "") is True

    def test_empty_text(self):
        assert hi.is_noise("", "") is False


# ========== Test get_chinese_ratio ==========

class TestGetChineseRatio:
    def test_all_chinese(self):
        assert hi.get_chinese_ratio("这是一段纯中文内容") == 1.0

    def test_all_english(self):
        assert hi.get_chinese_ratio("hello world") == 0.0

    def test_mixed(self):
        r = hi.get_chinese_ratio("hello世界")
        assert 0 < r < 1

    def test_empty_returns_zero(self):
        assert hi.get_chinese_ratio("") == 0.0


# ========== Test evaluate ==========

class TestEvaluate:
    def test_returns_dict_with_keys(self, sample_item):
        result = hi.evaluate(sample_item)
        assert "importance_score" in result
        assert "value_level" in result
        assert "value_reasons" in result
        assert "is_ai_related" in result
        assert "language" in result
        assert "chinese_ratio" in result

    def test_ai_item_scored_high(self, sample_item):
        result = hi.evaluate(sample_item)
        assert result["is_ai_related"] == 1
        assert result["importance_score"] > 0

    def test_non_ai_item(self):
        item = {"title": "普通新闻内容", "content": "一些日常新闻", "platform": "news",
                "hot_score": 100, "like_count": 0, "comment_count": 0}
        result = hi.evaluate(item)
        assert result["is_ai_related"] == 0

    def test_github_platform_bonus(self):
        item = {"title": "AI开源项目发布", "content": "这是一个AI相关项目",
                "platform": "github", "hot_score": 50000, "like_count": 0, "comment_count": 0}
        result = hi.evaluate(item)
        assert result["importance_score"] >= 10

    def test_bilibili_platform_bonus(self):
        item = {"title": "科技视频推荐", "content": "AI相关内容",
                "platform": "bilibili", "hot_score": 10000000, "like_count": 0, "comment_count": 0}
        result = hi.evaluate(item)
        assert result["importance_score"] >= 0

    def test_tech_platform_bonus(self):
        item = {"title": "新技术发布", "content": "",
                "platform": "solidot", "hot_score": 100, "like_count": 0, "comment_count": 0}
        result = hi.evaluate(item)
        assert result["importance_score"] >= 8

    def test_high_value_level(self):
        item = {"title": "AI 大模型 GPT OpenAI Anthropic Google 发布 开源 突破",
                "content": "技术 架构 框架 系统 平台",
                "platform": "github", "hot_score": 50000,
                "like_count": 50000, "comment_count": 5000}
        result = hi.evaluate(item)
        assert result["value_level"] >= 3


# ========== Test clean_dedup ==========

class TestCleanDedup:
    def test_cleans_short_titles(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = []
        with patch.object(hi, "get_db", return_value=mock_conn):
            items = [{"title": "短", "content": "some content"}]
            result = hi.clean_dedup(items)
            assert len(result) == 0

    def test_removes_duplicates(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = []
        with patch.object(hi, "get_db", return_value=mock_conn):
            items = [
                {"title": "重复标题测试内容很长", "content": "content"},
                {"title": "重复标题测试内容很长", "content": "content2"},
            ]
            result = hi.clean_dedup(items)
            assert len(result) == 1

    def test_filters_noise(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = []
        with patch.object(hi, "get_db", return_value=mock_conn):
            items = [{"title": "明星娱乐八卦绯闻", "content": "粉丝综艺节目"}]
            result = hi.clean_dedup(items)
            assert len(result) == 0

    def test_checks_existing_in_db(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = [("existing title here",)]
        with patch.object(hi, "get_db", return_value=mock_conn):
            items = [{"title": "existing title here", "content": "content"}]
            result = hi.clean_dedup(items)
            assert len(result) == 0

    def test_keeps_valid_items(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_cur.fetchall.return_value = []
        with patch.object(hi, "get_db", return_value=mock_conn):
            items = [{"title": "AI技术突破OpenAI发布GPT", "content": "技术细节"}]
            result = hi.clean_dedup(items)
            assert len(result) == 1


# ========== Test build_report ==========

class TestBuildReport:
    def test_empty_items(self):
        report = hi.build_report([])
        assert "#" in report
        assert "0条" in report

    def test_high_value_items(self):
        items = [
            {"title": "OpenAI发布GPT-5", "value_level": 5, "importance_score": 90,
             "source": "ithome", "value_reasons": "关键词: AI,GPT"}
        ]
        report = hi.build_report(items)
        assert "极端" in report or "重要" in report

    def test_medium_value_items(self):
        items = [
            {"title": "中等新闻", "value_level": 3, "importance_score": 30,
             "source": "36kr", "value_reasons": "中等"}
        ]
        report = hi.build_report(items)
        assert "中等" in report

    def test_ai_related_section(self):
        items = [
            {"title": "AI新闻", "value_level": 3, "importance_score": 50,
             "source": "ithome", "is_ai_related": 1, "value_reasons": "AI"}
        ]
        report = hi.build_report(items)
        assert "AI" in report

    def test_date_in_report(self):
        report = hi.build_report([])
        today = datetime.now().strftime("%Y-%m-%d")
        assert today in report


# ========== Test push_wechat (mock) ==========

class TestPushWechat:
    def test_no_token_returns_error(self, monkeypatch):
        monkeypatch.setattr(hi, "PUSHPLUS_TOKEN", "")
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"code": 200}'
        with patch.object(hi.urllib.request, "urlopen", return_value=mock_resp):
            result = hi.push_wechat("Test", "content")
            assert isinstance(result, dict)

    def test_exception_returns_error(self, monkeypatch):
        monkeypatch.setattr(hi, "PUSHPLUS_TOKEN", "token")
        with patch.object(hi, "urllib") as mock_urllib:
            mock_urllib.request.urlopen.side_effect = Exception("timeout")
            result = hi.push_wechat("Test", "content")
            assert result["code"] == -1

    def test_successful_push(self, monkeypatch):
        monkeypatch.setattr(hi, "PUSHPLUS_TOKEN", "valid_token")
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"code": 200, "msg": "ok"}'
        with patch.object(hi.urllib.request, "urlopen", return_value=mock_resp):
            result = hi.push_wechat("Test", "content")
            assert "code" in result


# ========== Test fetchers (mock) ==========

class TestFetchers:
    @staticmethod
    def _mock_urlopen(read_data):
        """Create a mock urlopen that returns given data as context manager."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = read_data
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = None
        return mock_resp

    def test_fetch_bilibili_mocked(self):
        mock_data = {"data": {"list": [
            {"title": "Test视频标题测试", "desc": "描述", "bvid": "BV123",
             "stat": {"view": 1000, "like": 100, "favorite": 50, "reply": 20, "share": 10},
             "owner": {"name": "作者", "mid": 123}, "pubdate": 1700000000,
             "tname": "科技"}
        ]}}
        mock_resp = self._mock_urlopen(json.dumps(mock_data).encode())
        with patch.object(hi.urllib.request, "urlopen", return_value=mock_resp):
            with patch.object(hi.time, "sleep"):
                items = hi.fetch_bilibili()
                assert len(items) > 0

    def test_fetch_weibo_mocked(self):
        mock_data = {"data": {"realtime": [
            {"note": "微博热搜标题测试", "word_scheme": "#热搜#",
             "category": "热搜", "raw_hot": 100, "num": 50}
        ]}}
        mock_resp = self._mock_urlopen(json.dumps(mock_data).encode())
        with patch.object(hi.urllib.request, "urlopen", return_value=mock_resp):
            items = hi.fetch_weibo()
            assert len(items) > 0

    def test_fetch_github_trending_mocked(self):
        mock_data = {"items": [
            {"full_name": "test/repo", "description": "test", "html_url": "https://github.com/test/repo",
             "owner": {"login": "test", "id": 1},
             "stargazers_count": 1000, "forks_count": 100, "open_issues_count": 10,
             "created_at": "2026-01-01T00:00:00Z"}
        ]}
        mock_resp = self._mock_urlopen(json.dumps(mock_data).encode())
        with patch.object(hi.urllib.request, "urlopen", return_value=mock_resp):
            with patch.object(hi.time, "sleep"):
                items = hi.fetch_github_trending()
                assert len(items) > 0

    def test_fetch_solidot_mocked(self):
        rss = ('<?xml version="1.0"?><rss version="2.0"><channel>'
               '<item><title><![CDATA[Solidot Test Article]]></title>'
               '<link>https://test.com</link>'
               '<description><![CDATA[Test desc]]></description>'
               '<pubDate>Mon, 14 Jun 2026 10:00:00 GMT</pubDate></item>'
               '</channel></rss>')
        mock_resp = self._mock_urlopen(rss.encode())
        with patch.object(hi.urllib.request, "urlopen", return_value=mock_resp):
            items = hi.fetch_solidot()
            assert len(items) > 0

    def test_fetch_oschina_mocked(self):
        rss = ('<?xml version="1.0"?><rss version="2.0"><channel>'
               '<item><title><![CDATA[OSC News Test]]></title>'
               '<link>https://oschina.net/news/1</link>'
               '<description><![CDATA[desc]]></description>'
               '<pubDate>Mon, 14 Jun 2026 10:00:00 GMT</pubDate></item>'
               '</channel></rss>')
        mock_resp = self._mock_urlopen(rss.encode())
        with patch.object(hi.urllib.request, "urlopen", return_value=mock_resp):
            items = hi.fetch_oschina()
            assert len(items) > 0

    def test_fetch_ithome_mocked(self):
        html = '<a href="https://www.ithome.com/d/12345.html" class="title">IT之家测试标题科技新闻</a>'
        mock_resp = self._mock_urlopen(html.encode())
        with patch.object(hi.urllib.request, "urlopen", return_value=mock_resp):
            items = hi.fetch_ithome()
            assert len(items) > 0

    def test_fetch_bilibili_short_title_skipped(self):
        mock_data = {"data": {"list": [
            {"title": "短", "desc": "", "bvid": "BV123",
             "stat": {"view": 100, "like": 10, "favorite": 5, "reply": 2, "share": 1},
             "owner": {"name": "a", "mid": 1}, "pubdate": 1700000000,
             "tname": "other"}
        ]}}
        mock_resp = self._mock_urlopen(json.dumps(mock_data).encode())
        with patch.object(hi.urllib.request, "urlopen", return_value=mock_resp):
            with patch.object(hi.time, "sleep"):
                items = hi.fetch_bilibili()
                assert len(items) == 0  # short title filtered


# ========== Test run ==========

class TestRun:
    def test_run_dry_run(self, monkeypatch):
        # Mock all fetchers to return empty
        monkeypatch.setattr(hi, "fetch_bilibili", lambda: [])
        monkeypatch.setattr(hi, "fetch_weibo", lambda: [])
        monkeypatch.setattr(hi, "fetch_github_trending", lambda: [])
        monkeypatch.setattr(hi, "fetch_solidot", lambda: [])
        monkeypatch.setattr(hi, "fetch_oschina", lambda: [])
        monkeypatch.setattr(hi, "fetch_ithome", lambda: [])
        # Should just exit
        hi.run(dry_run=True)

    def test_run_with_items_dry_run(self, monkeypatch):
        items = [{
            "title": "AI大模型最新突破GPT-5发布深度技术分析",
            "content": "内容描述",
            "url": "https://ex.com",
            "platform": "ithome",
            "source": "IT之家",
            "hot_score": 5000,
        }]
        monkeypatch.setattr(hi, "fetch_ithome", lambda: items)
        monkeypatch.setattr(hi, "fetch_bilibili", lambda: [])
        monkeypatch.setattr(hi, "fetch_weibo", lambda: [])
        monkeypatch.setattr(hi, "fetch_github_trending", lambda: [])
        monkeypatch.setattr(hi, "fetch_solidot", lambda: [])
        monkeypatch.setattr(hi, "fetch_oschina", lambda: [])
        hi.run(dry_run=True)

    def test_run_fetcher_exception_handled(self, monkeypatch):
        monkeypatch.setattr(hi, "fetch_ithome", MagicMock(side_effect=Exception("fail")))
        monkeypatch.setattr(hi, "fetch_bilibili", lambda: [])
        monkeypatch.setattr(hi, "fetch_weibo", lambda: [])
        monkeypatch.setattr(hi, "fetch_github_trending", lambda: [])
        monkeypatch.setattr(hi, "fetch_solidot", lambda: [])
        monkeypatch.setattr(hi, "fetch_oschina", lambda: [])
        hi.run(dry_run=True)


# ========== Test save_all ==========

class TestSaveAll:
    def test_saves_items(self):
        mock_conn = MagicMock()
        mock_conn.execute.return_value = MagicMock()
        with patch.object(hi, "get_db", return_value=mock_conn):
            all_items = [{"title": "T", "content": "C", "url": "https://ex.com",
                          "platform": "test", "source": "test"}]
            evaluated = [{"title": "T", "content": "C", "url": "https://ex.com",
                          "source": "test", "platform": "test", "author": "a",
                          "category": "cat", "importance_score": 50, "value_level": 3,
                          "value_reasons": "ok", "is_ai_related": 1, "language": "zh",
                          "chinese_ratio": 1.0, "published_at": None}]
            hi.save_all(all_items, evaluated)
            assert mock_conn.commit.called

    def test_exception_in_insert_handled(self):
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("db error")
        with patch.object(hi, "get_db", return_value=mock_conn):
            all_items = [{"title": "T", "content": "C", "url": "https://ex.com",
                          "platform": "test", "source": "test"}]
            hi.save_all(all_items, [])
            assert mock_conn.commit.called


# ========== Test constants ==========

class TestConstants:
    def test_noise_kw_exists(self):
        assert len(hi.NOISE_KW) > 0
        assert "明星" in hi.NOISE_KW

    def test_high_kw_exists(self):
        assert len(hi.HIGH_KW) > 0
        assert "AI" in hi.HIGH_KW

    def test_db_path(self):
        assert ".hermes" in str(hi.DB_PATH)
        assert "intelligence.db" in str(hi.DB_PATH)

    def test_pushplus_url(self):
        assert "pushplus" in hi.PUSHPLUS_URL

    def test_headers_present(self):
        assert "User-Agent" in hi.HEADERS
