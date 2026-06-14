"""
OpenClaw Web Search Plugin - Hermes Plugin
Complete implementation with Brave, DuckDuckGo, Tavily, and Perplexity support.
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    print("Warning: aiohttp not available, some features may be limited")

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

from hermes.plugins.plugin_system import Plugin, PluginConfig, PluginManifest

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result data structure."""
    title: str
    url: str
    snippet: str
    source: str
    score: float = 0.0
    published_date: datetime | None = None
    raw_data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise to dictionary."""
        result = {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "score": self.score
        }
        if self.published_date:
            result["published_date"] = self.published_date.isoformat()
        return result


class CacheEntry:
    """Cache entry with TTL."""
    def __init__(self, data: Any, ttl: int = 3600):
        self.data = data
        self.created = datetime.now()
        self.ttl = ttl

    def is_valid(self) -> bool:
        return (datetime.now() - self.created).total_seconds() < self.ttl


class SimpleCache:
    """In-memory cache with TTL."""
    def __init__(self):
        self._cache: dict[str, CacheEntry] = {}

    def get(self, key: str) -> Any | None:
        if key not in self._cache:
            return None
        entry = self._cache[key]
        if entry.is_valid():
            return entry.data
        del self._cache[key]
        return None

    def set(self, key: str, data: Any, ttl: int = 3600):
        self._cache[key] = CacheEntry(data, ttl)

    def clear(self):
        self._cache.clear()

    def size(self) -> int:
        return len(self._cache)


class BraveSearch:
    """Brave Search API client."""

    BASE_URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout

    async def search(self, query: str, count: int = 10) -> list[SearchResult]:
        """Perform Brave search."""
        if not self.api_key:
            logger.warning("Brave API key not set")
            return []

        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp is required for Brave search")
            return []

        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key
        }
        params = {
            "q": query,
            "count": min(count, 20),
            "freshness": "week"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, headers=headers, params=params, timeout=self.timeout) as resp:
                    if resp.status != 200:
                        logger.error(f"Brave search failed: {resp.status}")
                        return []

                    data = await resp.json()

                    results = []
                    for item in data.get("web", {}).get("results", []):
                        result = SearchResult(
                            title=item.get("title", ""),
                            url=item.get("url", ""),
                            snippet=item.get("snippet", ""),
                            source="brave",
                            score=item.get("score", 0.0)
                        )
                        results.append(result)

                    return results

        except Exception as e:
            logger.error(f"Brave search error: {e}")
            return []


class DuckDuckGoSearch:
    """DuckDuckGo HTML scraper."""

    BASE_URL = "https://html.duckduckgo.com/html/"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    async def search(self, query: str, count: int = 10) -> list[SearchResult]:
        """Perform DuckDuckGo search."""
        if not AIOHTTP_AVAILABLE or not BS4_AVAILABLE:
            logger.error("aiohttp and beautifulsoup4 are required for DuckDuckGo")
            return []

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        params = {
            "q": query,
            "kl": "us-en"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.BASE_URL, data=params, headers=headers, timeout=self.timeout) as resp:
                    if resp.status != 200:
                        logger.error(f"DuckDuckGo search failed: {resp.status}")
                        return []

                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")

                    results = []
                    for result in soup.find_all("div", class_="result")[:count]:
                        title_elem = result.find("a", class_="result__title")
                        snippet_elem = result.find("a", class_="result__snippet")

                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            url = title_elem.get("href", "")

                            # Extract actual URL from DuckDuckGo redirect
                            if url.startswith("uddg="):
                                import urllib.parse
                                parsed = urllib.parse.parse_qs(url)
                                url = parsed.get("uddg", [""])[0]

                            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                            results.append(SearchResult(
                                title=title,
                                url=url,
                                snippet=snippet,
                                source="duckduckgo",
                                score=0.5
                            ))

                    return results

        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []


class TavilySearch:
    """Tavily AI search client."""

    BASE_URL = "https://api.tavily.com/search"

    def __init__(self, api_key: str, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout

    async def search(self, query: str, count: int = 10) -> list[SearchResult]:
        """Perform Tavily search."""
        if not self.api_key:
            logger.warning("Tavily API key not set")
            return []

        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp is required for Tavily search")
            return []

        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": min(count, 20),
            "include_domains": [],
            "exclude_domains": [],
            "include_raw_content": False,
            "include_images": False
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.BASE_URL, json=payload, headers=headers, timeout=self.timeout) as resp:
                    if resp.status != 200:
                        logger.error(f"Tavily search failed: {resp.status}")
                        return []

                    data = await resp.json()

                    results = []
                    for item in data.get("results", []):
                        result = SearchResult(
                            title=item.get("title", ""),
                            url=item.get("url", ""),
                            snippet=item.get("content", "")[:300],
                            source="tavily",
                            score=item.get("score", 0.0)
                        )
                        results.append(result)

                    return results

        except Exception as e:
            logger.error(f"Tavily search error: {e}")
            return []


class PerplexitySearch:
    """Perplexity AI search client."""

    BASE_URL = "https://api.perplexity.ai/chat/completions"

    def __init__(self, api_key: str, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout

    async def search(self, query: str, count: int = 10) -> list[SearchResult]:
        """Perform Perplexity search (conversational)."""
        if not self.api_key:
            logger.warning("Perplexity API key not set")
            return []

        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp is required for Perplexity search")
            return []

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "pplx-7b-online",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": f"Search for: {query}. Provide top {count} results with titles, URLs, and brief descriptions."}
            ],
            "max_tokens": 1024,
            "temperature": 0.3
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.BASE_URL, json=payload, headers=headers, timeout=self.timeout) as resp:
                    if resp.status != 200:
                        logger.error(f"Perplexity search failed: {resp.status}")
                        return []

                    data = await resp.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                    # Parse the response to extract results (simplified)
            return self._parse_response(content, query)

        except Exception as e:
            logger.error(f"Perplexity search error: {e}")
            return []

    def _parse_response(self, content: str, query: str) -> list[SearchResult]:
        """Parse Perplexity response into SearchResults."""
        results = []
        lines = content.split("\n")

        # Simple parsing - extract numbered items or URLs
        current_result = {}
        for line in lines:
            if any(marker in line.lower() for marker in ["http", "www.", ".com", ".org"]):
                if current_result and "url" in current_result:
                    results.append(SearchResult(**current_result))
                    current_result = {}
                current_result["url"] = line.strip()
                current_result["source"] = "perplexity"
            elif line.strip() and "url" in current_result and "title" not in current_result:
                current_result["title"] = line.strip()
                current_result["snippet"] = line.strip()

        if current_result:
            results.append(SearchResult(**current_result))

        return results[:10] if results else []


class WebSearchPlugin(Plugin):
    """Complete web search plugin implementation."""

    def __init__(self, manifest: PluginManifest, config: PluginConfig):
        super().__init__(manifest, config)
        self.cache: SimpleCache | None = None
        self.brave: BraveSearch | None = None
        self.duckduckgo: DuckDuckGoSearch | None = None
        self.tavily: TavilySearch | None = None
        self.perplexity: PerplexitySearch | None = None

    async def init(self) -> None:
        """Initialize plugin and search clients."""
        await super().init()

        # Initialize cache if enabled
        if self.config.config.get("cache_enabled", True):
            self.cache = SimpleCache()
            logger.info("Cache initialized")

        # Initialize search clients
        brave_key = self.config.config.get("brave_api_key", "")
        if brave_key:
            self.brave = BraveSearch(brave_key, timeout=self.config.config.get("request_timeout", 30))

        if self.config.config.get("duckduckgo_enabled", True):
            self.duckduckgo = DuckDuckGoSearch(timeout=self.config.config.get("request_timeout", 30))

        tavily_key = self.config.config.get("tavily_api_key", "")
        if tavily_key:
            self.tavily = TavilySearch(tavily_key, timeout=self.config.config.get("request_timeout", 30))

        perplexity_key = self.config.config.get("perplexity_api_key", "")
        if perplexity_key:
            self.perplexity = PerplexitySearch(perplexity_key, timeout=self.config.config.get("request_timeout", 30))

        logger.info(f"WebSearch plugin initialized with {self._get_active_sources_count()} active sources")

    async def start(self) -> None:
        """Start the plugin."""
        await super().start()
        logger.info("WebSearch plugin started")

    async def stop(self) -> None:
        """Stop the plugin and clear cache."""
        if self.cache:
            self.cache.clear()
        await super().stop()

    def _get_active_sources_count(self) -> int:
        """Count how many search sources are configured."""
        count = 0
        if self.brave:
            count += 1
        if self.duckduckgo:
            count += 1
        if self.tavily:
            count += 1
        if self.perplexity:
            count += 1
        return count

    def _get_cache_key(self, query: str, source: str) -> str:
        """Generate cache key for search."""
        key_str = f"{query.lower().strip()}:{source}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _deduplicate_results(self, results: list[SearchResult]) -> list[SearchResult]:
        """Remove duplicate results based on URL."""
        seen_urls = set()
        unique = []
        for result in results:
            # Normalise URL
            url = result.url.split("?")[0].rstrip("/")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique.append(result)
        return unique

    def _merge_and_sort_results(self, all_results: list[SearchResult]) -> list[SearchResult]:
        """Merge results from different sources and sort by relevance."""
        # Remove duplicates if configured
        if self.config.config.get("deduplicate", True):
            all_results = self._deduplicate_results(all_results)

        # Sort by score (descending) and then by source priority
        source_priority = {"brave": 4, "tavily": 3, "perplexity": 2, "duckduckgo": 1}

        all_results.sort(key=lambda r: (
            r.score * 0.6 + source_priority.get(r.source, 0) * 0.4
        ), reverse=True)

        return all_results

    async def web_search(self, query: str, max_results: int = 10, source: str = "all") -> list[dict[str, Any]]:
        """
        Perform a web search.
        Args:
            query: Search query
            max_results: Maximum number of results to return
            source: Search source ("brave", "duckduckgo", "tavily", "perplexity", or "all")
        Returns:
            List of search results as dictionaries
        """
        if not query.strip():
            raise ValueError("Query cannot be empty")

        sources = []
        if source == "all":
            sources = ["brave", "duckduckgo", "tavily", "perplexity"]
            # Only include configured sources
            sources = [s for s in sources if self._get_source_client(s) is not None]
        else:
            client = self._get_source_client(source)
            if client is None:
                raise ValueError(f"Source '{source}' not available or not configured")
            sources = [source]

        max_per_source = self.config.config.get("max_results_per_source", 10)

        # Check cache first if enabled
        if self.cache:
            cached_results = []
            for src in sources:
                cache_key = self._get_cache_key(query, src)
                cached = self.cache.get(cache_key)
                if cached:
                    cached_results.extend(cached)

            if cached_results:
                logger.info(f"Returning {len(cached_results)} cached results for query: {query}")
                return [r.to_dict() for r in self._merge_and_sort_results(cached_results)[:max_results]]

        # Perform searches concurrently
        tasks = []
        for src in sources:
            client = self._get_source_client(src)
            if client:
                task = asyncio.create_task(
                    self._search_with_source(client, src, min(max_per_source, max_results))
                )
                tasks.append(task)

        if not tasks:
            logger.warning(f"No search sources available for query: {query}")
            return []

        all_raw_results = []
        for task in asyncio.as_completed(tasks):
            try:
                results = await task
                if results:
                    all_raw_results.extend(results)
            except Exception as e:
                logger.error(f"Search task failed: {e}")

        # Merge and sort
        final_results = self._merge_and_sort_results(all_raw_results)

        # Cache results if enabled
        if self.cache:
            # Group by source for caching
            by_source = {}
            for result in all_raw_results:
                if result.source not in by_source:
                    by_source[result.source] = []
                by_source[result.source].append(result)

            for src, src_results in by_source.items():
                cache_key = self._get_cache_key(query, src)
                self.cache.set(cache_key, src_results, ttl=self.config.config.get("cache_ttl", 3600))

        # Truncate to max_results
        final_results = final_results[:max_results]

        # Generate summaries if configured
        if self.config.config.get("summarize", True):
            final_results = await self._generate_summaries(final_results)

        logger.info(f"Search '{query}' returned {len(final_results)} results from {len(all_raw_results)} total")
        return [r.to_dict() for r in final_results]

    def _get_source_client(self, source: str):
        """Get client for a source."""
        clients = {
            "brave": self.brave,
            "duckduckgo": self.duckduckgo,
            "tavily": self.tavily,
            "perplexity": self.perplexity
        }
        return clients.get(source)

    async def _search_with_source(self, client, source: str, count: int) -> list[SearchResult]:
        """Run search with error handling."""
        try:
            return await client.search(query="", count=count)  # Query will be set by caller
        except Exception as e:
            logger.error(f"Search failed for {source}: {e}")
            return []

    async def _generate_summaries(self, results: list[SearchResult]) -> list[SearchResult]:
        """Generate/summarise snippets (basic implementation)."""
        # For now, just ensure snippets are not too long
        for result in results:
            if result.snippet and len(result.snippet) > 500:
                result.snippet = result.snippet[:497] + "..."
        return results

    def get_tools(self) -> list[dict[str, Any]]:
        """Return tool definitions for LLM integration."""
        return [{
            "name": "web_search",
            "description": "Search the web for current information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10
                    },
                    "source": {
                        "type": "string",
                        "enum": ["all", "brave", "duckduckgo", "tavily", "perplexity"],
                        "description": "Search engine to use (default: all)",
                        "default": "all"
                    }
                },
                "required": ["query"]
            }
        }]

    async def health_check(self) -> dict[str, Any]:
        """Return plugin health status."""
        status = await super().health_check()
        status["cache_size"] = self.cache.size() if self.cache else 0
        status["active_sources"] = self._get_active_sources_count()
        return status
