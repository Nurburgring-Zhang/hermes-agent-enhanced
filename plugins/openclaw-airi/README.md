# OpenClaw AirI Digital Human Plugin

Advanced digital human plugin featuring Live2D integration, real-time lip-sync, and emotion control.

## Features

- **Live2D Integration**: Full Live2D Cubism SDK support via WebGL (pixi-live2d-display)
- **Lip-Sync**: Real-time phoneme extraction from audio and mouth shape animation
- **Emotion Control**: Dynamic emotion mapping with smooth transitions
- **Physics Simulation**: Live2D physics (breathing, hair, accessories)
- **Eye Tracking**: Optional mouse/point tracking for eye movement
- **Web Interface**: HTML5/WebSocket-based interactive display
- **REST API**: HTTP endpoints for programmatic control
- **Works out of the box**: Includes sample Live2D model (Haru)

## Architecture

```
┌─────────────────┐     WebSocket     ┌─────────────────┐
│   Hermes Plugin │◄────────────────► │  Web Frontend   │
│   (Python)      │                  │  (Live2D JS)    │
└────────┬────────┘                  └─────────────────┘
          │ HTTP
          ▼
┌─────────────────┐
│   Local Server  │
│  (aiohttp)      │
└─────────────────┘
```

The plugin:
1. Starts a local web server serving the Live2D web page
2. Runs a WebSocket server for real-time control
3. Exposes REST endpoints for commands
4. Handles audio analysis for lip-sync
5. Manages model state (expressions, poses, motions)

## Installation

1. Place plugin in `~/.hermes/plugins/openclaw-airi/`
2. Install dependencies: `pip install -r requirements.txt`
3. Place Live2D model in `./assets/` (example included)
4. Enable: `/plugin_enable openclaw-airi`
5. Start: `/plugin_start openclaw-airi`

The plugin will start the web server automatically if configured.

## Usage

### Hermes Commands

```
/airi_start_web      # Start web server
/airi_stop_web       # Stop web server
/airi_open           # Open web UI in browser
/airi_set_expression <emotion>  # Set emotion: happy, sad, angry, neutral, shy
/airi_set_pose <pose_name>     # Set model pose
/airi_say "text" [audio_file]  # Speak text with lip-sync
/airi_look_at <x> <y>          # Look at point (0-1 normalized)
/airi_status           # Get plugin status
```

### HTTP API

```bash
# Get status
curl http://localhost:8080/api/status

# Set expression
curl -X POST http://localhost:8080/api/expression \
  -H "Content-Type: application/json" \
  -d '{"expression": "happy", "duration": 0.5}'

# Say text with lip-sync
curl -X POST http://localhost:8080/api/say \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, world!", "speed": 1.0}'

# Set pose
curl -X POST http://localhost:8080/api/pose \
  -H "Content-Type: application/json" \
  -d '{"pose": "Idle_01"}'

# Look at point
curl -X POST http://localhost:8080/api/look_at \
  -H "Content-Type: application/json" \
  -d '{"x": 0.5, "y": 0.5}'
```

### WebSocket

Connect to `ws://localhost:8081/` and send JSON messages:

```json
{
  "type": "expression",
  "value": "happy",
  "duration": 0.5
}
```

Message types:
- `expression`: Change expression
- `pose`: Change pose
- `say`: Speak text
- `look_at`: Eye tracking
- `motion`: Play motion
- `emotion`: Set emotion state (affects expression mapping)

## Lip-Sync Mechanism

The plugin extracts phonemes from audio using:

1. **Audio analysis**: Using librosa to compute MFCCs and formants
2. **Phoneme classification**: Pre-trained model maps audio features to phonemes
3. **Viseme mapping**: Phonemes map to Live2D mouth shapes (A, E, I, O, U, etc.)
4. **Smoothing**: Temporal smoothing prevents jittery animation
5. **Real-time update**: Sends mouth parameters via WebSocket

To use lip-sync:
```python
await plugin.execute("say",
    text="Hello!",
    audio_file="/path/to/audio.wav",  # Optional, generates if not provided
    voice="female"
)
```

The plugin can synthesize speech (if TTS configured) or use provided audio.

## Emotion & Expression System

Expressions are Live2D built-in expressions (e.g., f01, f02). Emotions are higher-level states:

| Emotion   | Expression | Description          |
|-----------|------------|----------------------|
| neutral   | f00        | Default, calm        |
| happy     | f01        | Smiling, joyful      |
| sad       | f02        | Frown, teary         |
| angry     | f03        | Furrowed brows       |
| shy       | f04        | Blushing, look down  |
| surprised | f05        | Wide eyes            |

Emotion changes smoothly interpolate between expressions.

The emotion can be set directly or triggered by TTS tone (if integrated).

## Live2D Model Requirements

Place your Live2D model in `./assets/`. The model must be in Cubism 3/4 format:

```
assets/
└── your_model/
    └── your_model.model3.json   (or .model.json for Cubism 2)
```

The plugin expects:
- Model JSON configuration
- Texture images (PNG)
- Physics settings (optional)
- Moc3 file (binary model)
- Motion/Expression definitions

**Sample model**: Haru greeter is included by default.

## Web Interface

Open `http://localhost:8080/` in your browser to see the digital human.

Features:
- Interactive mouse tracking (eyes follow cursor)
- Click to trigger random motion
- Speech bubble for TTS output
- Control panel for expression/pose
- Debug overlay (FPS, expressions)

## API Reference

### Plugin Actions

- `start_web`: Start web/WebSocket servers
- `stop_web`: Stop servers
- `set_expression(expression, duration=0.5)`: Change expression
- `set_pose(pose_name)`: Change pose
- `say(text, audio_file=None, voice=None, speed=1.0)`: Text-to-speech with lip-sync
- `set_emotion(emotion, intensity=1.0)`: Set emotion state
- `look_at(x, y, immediate=False)`: Direct gaze direction (0-1)
- `add_motion(group, name)`: Add motion to queue
- `clear_motions()`: Clear motion queue
- `get_status()`: Get current state
- `trigger(event_name)`: Trigger custom event

### Hooks Emitted

- `ai.after_generate`: When AI completes a response (if integrated)
- `message.receive`: On incoming text (for auto-reactions)

## TTS Integration

AirI supports multiple TTS backends (if configured):

- **Edge TTS** (free, no API key)
- **OpenAI TTS**
- **Azure TTS**
- **Local Coqui TTS**

Configure TTS in config:

```yaml
tts:
  backend: edge  # edge, openai, azure, coqui
  voice: "en-US-JennyNeural"  # for Edge
  # OpenAI specific
  openai_api_key: ""
  openai_model: "tts-1"
```

## Performance

- Target: 60 FPS rendering (vsync)
- Lip-sync: 30 FPS updates
- Memory: ~150MB for model + runtime
- CPU: Low (mostly GPU for rendering)
- Bandwidth: <1Mbps for WebSocket

## Troubleshooting

**Model not loading**: Check `model_path` and file permissions

**Web page blank**: Check browser console for CORS or JS errors

**Lip-sync jittery**: Increase smoothing in config

**High CPU**: Reduce motion FPS or disable random motion

**WebSocket connection refused**: Ensure ports are free and server running

## Dependencies

- `websockets`: WebSocket server
- `aiohttp`: HTTP API server
- `numpy`: Audio processing
- `librosa`: Music/audio analysis
- `soundfile`: Audio file I/O
- Pillow: Image processing (for UI)

## Extending

Create custom expressions in your Live2D model using Cubism Editor, then add to emotion mapping in config:

```yaml
emotion_mapping:
  excited: f06
```

## License

MIT
