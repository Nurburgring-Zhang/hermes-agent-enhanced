# OpenClaw SuperIntelligence Plugin

Advanced AI orchestration with multi-model collaboration, self-optimizing feedback loops, and performance monitoring.

## Features

- **Multi-Model Collaboration**: Combine multiple LLMs for superior reasoning
- **Strategy-Based Synthesis**: Consensus, voting, cascade, parallel strategies
- **Self-Critique & Iteration**: Automatic refinement loops for high-stakes queries
- **Performance Optimization**: Dynamic routing based on quality/cost metrics
- **Adaptive Temperature**: Adjust generation parameters based on task
- **Comprehensive Metrics**: Track latency, cost, quality, success rate
- **Intelligent Caching**: Reduce costs with smart response caching
- **Tool Augmentation**: Seamless integration with Hermes plugins (web search, etc.)
- **Fallback System**: Automatic fallback if primary model fails

## Architecture

```
┌─────────────┐
│   Query     │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│   Strategy Router   │
│   (voting/consensus)│
└──────┬──────────────┘
       │
       ├──────────────┬──────────────┐
       ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Model 1     │ │ Model 2     │ │ Model N     │
│ (GPT-4)     │ │ (Claude)    │ │ (Local)     │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │
       └───────────────┴───────────────┘
                       │
                       ▼
           ┌─────────────────────┐
           │   Synthesis Engine  │
           │  (combine/compare)  │
           └──────────┬──────────┘
                      │
                      ▼
           ┌─────────────────────┐
           │   Quality Check    │
           │  (confidence > ?)  │
           └──────────┬──────────┘
                      │
            ┌─────────┴─────────┐
            ▼                   ▼
      ┌───────────┐      ┌───────────┐
      │  Return   │      │  Iterate  │
      │  Result   │      │  & improve│
      └───────────┘      └───────────┘
```

## Installation

1. Place plugin in `~/.hermes/plugins/openclaw-superintelligence/`
2. Install dependencies: `pip install -r requirements.txt`
3. Configure models in `config.yaml`
4. Enable: `/plugin_enable openclaw-superintelligence`
5. Start: `/plugin_start openclaw-superintelligence`

## Configuration

### Model Setup

Edit `config.yaml` to add your models:

```yaml
models:
  - id: "gpt4"
    name: "GPT-4 Turbo"
    provider: "openrouter"
    model: "gpt-4-turbo-preview"
    api_key: "sk-..."  # Or set OPENROUTER_API_KEY env var
    temperature: 0.7
    max_tokens: 4096
    weight: 1.0
    enabled: true

  - id: "claude3"
    name: "Claude 3 Opus"
    provider: "anthropic"
    model: "claude-3-opus"
    api_key: "sk-..."
    temperature: 0.5
    max_tokens: 4096
    weight: 1.1
    enabled: true

  - id: "local"
    name: "Local Llama"
    provider: "local"
    endpoint: "http://localhost:11434/api/generate"
    model: "llama2:70b"
    temperature: 0.8
    weight: 0.9
    enabled: true
```

**Providers**:
- `openrouter`: Via OpenRouter API (many models)
- `openai`: Direct OpenAI API
- `anthropic`: Direct Anthropic Claude API
- `local`: Ollama or custom endpoint
- `custom`: Fully custom API format

### Strategy Selection

- **voting**: Each model votes, pick best answer (default)
- **consensus**: Iterative refinement until agreement (slower, higher quality)
- **cascade**: Fast model first, expensive if confidence low
- **parallel**: All at once, synthesize result

## Usage

### Hermes Commands

```
/superintel_chat <prompt>          # Generate response
/superintel_optimize <task>       # Optimize for specific task
/superintel_status                # View performance metrics
/superintel_models                # List configured models
/superintel_enable <model_id>     # Enable/disable model
/superintel_benchmark <queries>   # Benchmark all models
/superintel_feedback <response_id> <rating>:<comments>  # Provide feedback
```

### API

```python
plugin = manager.get_plugin("openclaw-superintelligence")

# Simple chat (uses strategy)
response = await plugin.execute("chat",
    prompt="Explain quantum computing",
    context=[],
    max_iterations=2,
    required_models=["gpt4", "claude3"]
)

# Optimize for specific task
result = await plugin.execute("optimize",
    task="code_generation",
    prompt="Write a Python function...",
    constraints={"max_tokens": 1000, "style": "functional"}
)

# Get metrics
metrics = await plugin.execute("get_metrics")
print(f"Avg latency: {metrics['avg_latency']}s")
print(f"Best model: {metrics['best_model']}")
```

### Tools

The plugin exposes tools for integration:

```json
{
  "name": "superintel_chat",
  "description": "Generate response using multi-model collaboration",
  "parameters": {
    "prompt": "string",
    "context": "array (conversation history)",
    "strategy": "string (override strategy)",
    "max_iterations": "integer",
    "required_models": "array of model IDs"
  }
}
```

## Collaboration Strategies

### Voting
1. Send prompt to all enabled models (parallel)
2. Score each response for quality, coherence, completeness
3. Pick the best response (or synthesize from top 3)

### Consensus
1. Send prompt to all models
2. Identify disagreements
3. Send differences back for debate
4. Iterate until consensus or max iterations

### Cascade
1. Send to fastest/cheapest model first
2. If confidence < threshold, send to better model
3. Continue until quality threshold met or all models tried

### Parallel (Synthesis)
1. Get responses from all models simultaneously
2. Extract unique insights from each
3. Combine into comprehensive answer with citations

## Self-Critique Loop

When `enable_self_critique: true` and `max_iterations > 0`:

1. Generate initial response
2. Critique: "Are there errors? What's missing?"
3. Generate improved response addressing critique
4. Repeat up to `max_iterations` or until satisfied

Example flow:
```
Iteration 1: Initial answer (±100 words)
Critique: Missing recent events, needs citations
Iteration 2: Updated answer with sources
Critique: Still vague on specifics
Iteration 3: Comprehensive, detailed answer
Confidence: 0.82 → Return
```

## Performance Optimization

### Dynamic Routing
The plugin tracks:
- **Latency**: Response time per model
- **Cost**: Token cost per request
- **Quality**: Subjectively scored from user feedback
- **Success Rate**: Completion without error

Based on `auto_optimize: true`, the plugin:
- Adjusts model weights (higher weight = more requests)
- May disable consistently poor performers
- Adjusts temperature to balance creativity/coherence
- Chooses optimal strategy based on request type

### Adaptive Temperature
If `temperature_adjustment: adaptive`:
- High-priority/complex queries → lower temperature (more focused)
- Creative tasks → higher temperature
- Balanced by request pattern analysis

### Caching
- Use semantic similarity (embeddings) to match previous queries
- Cache duration: `cache_ttl` (default 1 hour)
- Cost savings: Up to 60% for repeated queries

## Quality Control

### Confidence Scoring
Each response gets a confidence score (0-1) based on:
- Model's self-assessed certainty (if available)
- Consistency across multiple models (for voting/consensus)
- Length/completeness
- Presence of uncertainty markers

If `min_confidence_threshold` not met → iterate or fallback.

### Self-Evaluation
Models can be prompted to rate their own answers. The plugin aggregates these scores for routing.

## Metrics & Monitoring

The plugin collects extensive metrics:

```json
{
  "total_requests": 1520,
  "total_cost": 12.45,
  "avg_latency": 2.3,
  "success_rate": 0.994,
  "strategy_usage": {"voting": 1200, "cascade": 320},
  "model_performance": {
    "gpt4": {"requests": 800, "avg_latency": 1.8, "quality": 0.92, "weight": 1.05},
    "claude3": {"requests": 720, "avg_latency": 2.1, "quality": 0.89, "weight": 1.0}
  },
  "cache_hit_rate": 0.34,
  "iteration_stats": {"avg_iterations": 1.2, "iterations_breakdown": {"1": 1100, "2": 380, "3": 40}}
}
```

Metrics are saved to `metrics_file` (JSON) and available via `/superintel_status`.

### Metrics Hooks
The plugin emits events:
- `ai.before_generate`: Before querying models
- `ai.after_generate`: After response synthesis
- `ai.tool_use`: When using auxiliary tools

## Integration with Other Plugins

SuperIntelligence automatically uses other Hermes plugins as tools:

- **web_search**: For current information
- **openclaw-weixin**: For user context
- **Any tool-exposing plugin**: Via tool calls

When a query requires external information, the plugin:
1. Detects need (e.g., "What's the weather today?")
2. Calls relevant tool
3. Incorporates result into response

Configuration:
```yaml
enable_tool_augmentation: true
```

## Cost Management

### Cost Tracking
Every model call is tracked by:
- Provider and model ID
- Tokens used (input + output)
- Cost per token (from config)

Total cost per request summed across all models.

### Cost Controls
- `max_cost_per_request`: Abort if estimated cost exceeds
- Disable expensive models automatically if budget exceeded
- Prefer cheaper models when quality delta small

### Optimization
`auto_optimize: true` gradually:
- Increases weight for high-quality, low-cost models
- Decreases weight for low-quality or expensive models
- May temporarily disable models if consistently poor

## Troubleshooting

**All models failing**: Check API keys and network connectivity

**High latency**: Reduce `concurrency_limit` (default 4) or enable cascade strategy

**Poor quality**: Enable more capable models, adjust temperature, or enable self-critique

**High costs**: Enable caching, reduce `max_tokens`, use cheaper models, or use cascade

**No tool calls**: Check `enable_tool_augmentation`, ensure tool plugins are loaded

**Memory errors**: Reduce batch size or enable streaming (future)

## Advanced

### Custom Model Provider

For custom APIs, extend the plugin or use `provider: "custom"` with:

```yaml
custom_endpoint: "http://my-api.com/generate"
custom_headers: {"Authorization": "Bearer ..."}
custom_body_template: '{"prompt": "{{prompt}}", "temperature": {{temperature}}}'
custom_response_path: "result.text"
```

### Feedback Loop

Provide explicit feedback to improve routing:

```bash
/superintel_feedback <response_id> 4:comprehensive and accurate
```

Ratings 1-5 update model performance weights.

### Testing Strategy

```
/superintel_benchmark "set of test queries"
```

Measures quality, latency, cost across all enabled models. Reported in metrics.

## License

MIT
