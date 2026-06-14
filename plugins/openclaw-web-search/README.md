# OpenClaw Web Search Plugin

Powerful web search plugin with support for multiple search engines.

## Features

- **Multiple Search Engines**: Brave, DuckDuckGo, Tavily, Perplexity
- **Smart Result Processing**: Deduplication, summarization, relevance scoring
- **Caching**: Optional Redis-backed caching for improved performance
- **Configurable**: Fine-tune search behavior via configuration

## Installation

1. Place this plugin in `~/.hermes/plugins/openclaw-web-search/`
2. Install dependencies: `pip install -r requirements.txt`
3. Configure API keys in `config.yaml` (optional for DuckDuckGo)
4. Enable: `/plugin_enable openclaw-web-search`

## Configuration

Edit `config.yaml` to adjust:

- **API Keys**: Add your API keys for Brave, Tavily, or Perplexity
- **duckduckgo_enabled**: Enable/disable DuckDuckGo (no API key needed)
- **cache_enabled**: Enable result caching
- **cache_ttl**: Cache time-to-live in seconds
- **max_results_per_source**: Max results from each engine
- **deduplicate**: Remove duplicate results
- **summarize**: Generate result summaries

## Usage

### CLI Command
```
/web_search <query> [--source <engine>] [--max <count>]
```

### API
```python
from hermes.plugins.plugin_system import PluginManager

manager = PluginManager()
plugin = manager.get_plugin("openclaw-web-search")

results = await plugin.execute("web_search",
    query="Hermes plugin system",
    max_results=10,
    source="brave"  # brave, duckduckgo, tavily, perplexity, or 'all'
)
```

## Tool Schema

The plugin exposes `web_search` tool with parameters:

- `query` (string, required): Search query
- `max_results` (integer, optional, default=10): Maximum results
- `source` (string, optional, default='all'): Search engine(s)

Returns a list of search results with:
- `title`: Result title
- `url`: Link URL
- `snippet`: Description/summary
- `source`: Search engine name
- `score`: Relevance score (0-1)

## Search Engines

### Brave Search
Requires API key. Fast, privacy-focused search with good results.

### DuckDuckGo
No API key required. Privacy-respecting, reliable results.

### Tavily
Requires API key. AI-optimized, provides clean content extraction.

### Perplexity
Requires API key. AI-powered, provides detailed answers.

## Caching

Results are cached by query+source combination. Cache is in-memory by default,
can be extended to Redis or other backends.

## Dependencies

- `aiohttp`: Async HTTP client
- `beautifulsoup4`: HTML parsing
- `lxml`: Fast XML/HTML parser
- `httpx`: HTTP client (fallback)

## Troubleshooting

**No results**: Check API keys and internet connection

**Rate limits**: Each service has rate limits. Enable caching to reduce calls.

**Import errors**: Make sure dependencies are installed.

## License

MIT
