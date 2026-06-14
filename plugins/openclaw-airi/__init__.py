"""
OpenClaw AirI Digital Human Plugin - Hermes Plugin
Complete Live2D integration with lip-sync, emotion control, and web interface.
"""

import asyncio
import base64
import json
import logging
import os
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False

import aiohttp
from aiohttp import web
from hermes.plugins.plugin_system import Plugin, PluginConfig, PluginManifest
from websockets.server import serve as websocket_serve

logger = logging.getLogger(__name__)


# ============ Data Structures ============

class Expression(Enum):
    """Built-in Live2D expressions."""
    NEUTRAL = "f00"
    HAPPY = "f01"
    SAD = "f02"
    ANGRY = "f03"
    SHY = "f04"
    SURPRISED = "f05"


@dataclass
class EmotionState:
    """Current emotion state."""
    primary: str = "neutral"
    intensity: float = 1.0
    secondary: str | None = None
    blend: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class LipSyncFrame:
    """Lip-sync data frame."""
    phoneme: str  # a, e, i, o, u, etc.
    weight: float = 1.0
    timestamp: float = 0.0


@dataclass
class Motion:
    """Motion data."""
    group: str
    name: str
    file: str
    fade_in: float = 0.5
    fade_out: float = 0.5
    repeat: bool = False
    priority: int = 0


@dataclass
class ModelState:
    """Current model state."""
    expression: str = "f00"
    pose: str = "Idle_01"
    emotion: EmotionState = field(default_factory=EmotionState)
    mouth_openness: float = 0.0
    mouth_form: str = "a"
    eye_x: float = 0.5
    eye_y: float = 0.5
    head_x: float = 0.0
    head_y: float = 0.0
    body_x: float = 0.0
    breathing: float = 0.0
    blinking: bool = False
    last_update: datetime = field(default_factory=datetime.now)


# ============ Lip-Sync Engine ============

class LipSyncEngine:
    """Analyze audio for lip-sync phoneme detection."""

    # Simple phoneme to viseme mapping for Live2D
    PHONEME_TO_VISEME = {
        # Vowels
        "a": "a", "æ": "a", "ɑ": "a", "ɒ": "a",
        "e": "e", "ɛ": "e", "eɪ": "e",
        "i": "i", "ɪ": "i", "iː": "i",
        "o": "o", "ɔ": "o", "oʊ": "o",
        "u": "u", "ʊ": "u", "uː": "u",
        # Consonants (simplified)
        "p": "closed", "b": "closed",
        "m": "closed", "n": "neutral",
        "f": "f_v", "v": "f_v",
        "θ": "th", "ð": "th",
        "s": "s_z", "z": "s_z",
        "ʃ": "sh", "ʒ": "sh",
        "t": "neutral", "d": "neutral",
        "k": "a", "g": "a", "ŋ": "a",
        "l": "neutral", "r": "e",
        "w": "u", "j": "i",
        "h": "neutral", "ɸ": "closed"
    }

    VISEME_WEIGHTS = {
        "a": [1.0, 0.0, 0.0, 0.0, 0.0],
        "e": [0.0, 1.0, 0.0, 0.0, 0.0],
        "i": [0.0, 0.0, 1.0, 0.0, 0.0],
        "o": [0.0, 0.0, 0.0, 1.0, 0.0],
        "u": [0.0, 0.0, 0.0, 0.0, 1.0],
        "neutral": [0.2, 0.2, 0.2, 0.2, 0.2],
        "closed": [0.8, 0.1, 0.0, 0.1, 0.1],
        "f_v": [0.0, 0.5, 0.1, 0.4, 0.0],
        "th": [0.4, 0.0, 0.0, 0.4, 0.2],
        "s_z": [0.0, 0.2, 0.2, 0.5, 0.1],
        "sh": [0.0, 0.1, 0.0, 0.6, 0.3]
    }

    def __init__(self, sampling_rate: int = 16000, hop_length: int = 512):
        self.sampling_rate = sampling_rate
        self.hop_length = hop_length
        self.phoneme_cache: dict[str, list[LipSyncFrame]] = {}

    def analyze_audio(self, audio_data: np.ndarray, sr: int) -> list[LipSyncFrame]:
        """
        Analyze audio and produce lip-sync frames.
        Args:
            audio_data: Audio samples (mono)
            sr: Sample rate
        Returns:
            List of lip-sync frames with timestamps
        """
        if not LIBROSA_AVAILABLE:
            logger.error("librosa is required for lip-sync")
            return []

        try:
            # Resample if needed
            if sr != self.sampling_rate:
                audio_data = librosa.resample(audio_data, orig_sr=sr, target_sr=self.sampling_rate)

            # Extract MFCC features
            mfcc = librosa.feature.mfcc(
                y=audio_data,
                sr=self.sampling_rate,
                n_mfcc=13,
                hop_length=self.hop_length
            )

            # Delta features (velocity)
            mfcc_delta = librosa.feature.delta(mfcc)

            # Combine features
            features = np.vstack([mfcc, mfcc_delta])

            # Simple energy-based silence detection
            energy = librosa.feature.rms(y=audio_data, hop_length=self.hop_length)[0]
            is_speech = energy > np.median(energy) * 0.5

            # Detect vowel-like regions (formant analysis)
            # Simplified: use spectral rolloff as proxy
            rolloff = librosa.feature.spectral_rolloff(
                y=audio_data,
                sr=self.sampling_rate,
                hop_length=self.hop_length
            )[0]

            frames = []
            frame_time = self.hop_length / self.sampling_rate

            for i in range(features.shape[1]):
                time_offset = i * frame_time

                if not is_speech[i]:
                    # Closed mouth / silence
                    frames.append(LipSyncFrame(
                        phoneme="closed",
                        weight=0.0,
                        timestamp=time_offset
                    ))
                    continue

                # Simple vowel detection based on spectral rolloff and energy
                # In production, use a proper phoneme classifier (e.g. Praat or Wav2Vec2)
                normalized_rolloff = rolloff[i] / self.sampling_rate

                # Heuristic phoneme selection
                phoneme = self._detect_phoneme_heuristic(features[:, i], normalized_rolloff)

                frames.append(LipSyncFrame(
                    phoneme=phoneme,
                    weight=1.0,
                    timestamp=time_offset
                ))

            # Smooth phoneme transitions
            frames = self._smooth_frames(frames, window=3)

            logger.info(f"Lip-sync analysis: {len(frames)} frames, duration={len(audio_data)/self.sampling_rate:.2f}s")
            return frames

        except Exception as e:
            logger.error(f"Lip-sync analysis failed: {e}")
            return []

    def _detect_phoneme_heuristic(self, features: np.ndarray, rolloff: float) -> str:
        """Heuristic phoneme detection (simplified)."""
        # Use first few MFCCs to approximate vowel quality
        # MFCC 2-4 correspond to vowel formants

        f2 = features[2] if len(features) > 2 else 0
        f3 = features[3] if len(features) > 3 else 0

        # Very rough vowel space mapping
        # High F2 -> front vowels (i, e)
        # Low F2 -> back vowels (a, o, u)

        f2_norm = (f2 + 20) / 40  # rough normalisation

        if rolloff < 0.15:
            return "a"  # low rolloff = back vowel
        if rolloff < 0.25:
            if f2_norm > 0.6:
                return "i"
            return "u"
        if rolloff < 0.35:
            if f2_norm > 0.5:
                return "e"
            return "o"
        return "a"  # default

    def _smooth_frames(self, frames: list[LipSyncFrame], window: int = 3) -> list[LipSyncFrame]:
        """Apply simple temporal smoothing."""
        if len(frames) < window:
            return frames

        smoothed = []
        half = window // 2

        for i, frame in enumerate(frames):
            # Collect surrounding frames
            start = max(0, i - half)
            end = min(len(frames), i + half + 1)
            window_frames = frames[start:end]

            # Majority vote for phoneme
            phoneme_counts = {}
            for wf in window_frames:
                p = wf.phoneme
                phoneme_counts[p] = phoneme_counts.get(p, 0) + 1

            # Get most common phoneme
            dominant_phoneme = max(phoneme_counts.items(), key=lambda x: x[1])[0]

            smoothed.append(LipSyncFrame(
                phoneme=dominant_phoneme,
                weight=frame.weight,
                timestamp=frame.timestamp
            ))

        return smoothed

    def phoneme_to_mouth_param(self, phoneme: str) -> tuple[float, float, str]:
        """
        Convert phoneme to Live2D mouth parameters.
        Returns (mouth_openness, mouth_form, viseme)
        """
        viseme = self.PHONEME_TO_VISEME.get(phoneme, "neutral")
        weights = self.VISEME_WEIGHTS.get(viseme, self.VISEME_WEIGHTS["neutral"])

        # Map viseme weights to mouth parameters
        # Live2D mouth typically uses ParamAngleX and ParamAngleY
        # Simplified mapping to 5 mouth shapes
        openness = weights[0] * 1.0 + weights[1] * 0.8 + weights[2] * 0.3 + weights[3] * 0.6 + weights[4] * 0.2
        form = weights[4] * 0.5 - weights[0] * 0.5

        return openness, form, viseme


# ============ Web Server & WebSocket ============

class WebInterface:
    """Web server and WebSocket for Live2D frontend."""

    HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AirI Digital Human</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            overflow: hidden;
            margin: 0;
            padding: 0;
        }}
        #canvas-container {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        canvas {{
            max-width: 100%;
            max-height: 100%;
        }}
        #controls {{
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(255,255,255,0.9);
            padding: 15px 25px;
            border-radius: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
            display: flex;
            gap: 10px;
            z-index: 100;
        }}
        .btn {{
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }}
        .btn:hover {{
            background: #764ba2;
            transform: scale(1.05);
        }}
        #status {{
            position: absolute;
            top: 10px;
            left: 10px;
            color: white;
            font-size: 12px;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
            z-index: 100;
        }}
        #speech-bubble {{
            position: absolute;
            top: 10%;
            left: 50%;
            transform: translateX(-50%);
            background: white;
            padding: 15px 25px;
            border-radius: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            max-width: 80%;
            display: none;
            z-index: 100;
            animation: fadein 0.3s, fadeout 0.3s 2.7s;
        }}
        @keyframes fadein {{ from {{opacity: 0; transform: translate(-50%, -10px);}} to {{opacity: 1; transform: translate(-50%, 0);}} }}
        @keyframes fadeout {{ from {{opacity: 1;}} to {{opacity: 0;}} }}
    </style>
</head>
<body>
    <div id="status">Connecting...</div>
    <div id="speech-bubble"></div>
    <div id="canvas-container">
        <canvas id="live2d-canvas"></canvas>
    </div>
    <div id="controls">
        <button class="btn" onclick="setExpression('neutral')">Neutral</button>
        <button class="btn" onclick="setExpression('happy')">Happy</button>
        <button class="btn" onclick="setExpression('sad')">Sad</button>
        <button class="btn" onclick="triggerMotion()">Motion</button>
        <button class="btn" onclick="sendSay('Hello!')">Test Speech</button>
    </div>

    <!-- Load pixi.js and pixi-live2d-display -->
    <script src="https://cdn.jsdelivr.net/npm/pixi.js@6.5.10/dist/browser/pixi.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/pixi-live2d-display@0.4.0/dist/index.min.js"></script>

    <script>
        const ws = new WebSocket('ws://localhost:8081/');
        let app = null;
        let model = null;
        let currentExpression = 'f00';
        let mouthInterval = null;

        ws.onopen = () => {{
            console.log('WebSocket connected');
            document.getElementById('status').textContent = 'Connected';
            initLive2D();
        }};

        ws.onmessage = (event) => {{
            const data = JSON.parse(event.data);
            console.log('WS:', data);
            handleMessage(data);
        }};

        ws.onclose = () => {{
            document.getElementById('status').textContent = 'Disconnected - retrying...';
            setTimeout(() => location.reload(), 3000);
        }};

        function handleMessage(data) {{
            switch(data.type) {{
                case 'init':
                    loadModel(data.model_path);
                    break;
                case 'expression':
                    setExpression(data.value, data.duration);
                    break;
                case 'pose':
                    setPose(data.value);
                    break;
                case 'say':
                    showSpeech(data.text);
                    startLipSync(data.frames || []);
                    break;
                case 'look_at':
                    lookAt(data.x, data.y, data.immediate);
                    break;
                case 'emotion':
                    setEmotion(data.value, data.intensity);
                    break;
            }}
        }};

        async function initLive2D() {{
            // Wait for PIXI and Live2D to be ready
            await PIXI.live2d.Live2DModel.from;

            app = new PIXI.Application({{
                view: document.getElementById('live2d-canvas'),
                backgroundAlpha: 0,
                resizeTo: window,
                autoDensity: true,
                resolution: window.devicePixelRatio || 1,
            }});

            // Request model from server
            ws.send(JSON.stringify({{type: 'get_model'}}));
        }}

        async function loadModel(modelPath) {{
            try {{
                model = await PIXI.live2d.Live2DModel.from(modelPath);
                model.scale.set(0.5);
                model.x = app.screen.width / 2;
                model.y = app.screen.height * 0.8;
                model.anchor.set(0.5, 0.5);
                app.stage.addChild(model);

                enableEyeTracking();
                enableRandomMotion();

                document.getElementById('status').textContent = 'Model loaded';
            }} catch (err) {{
                console.error('Failed to load model:', err);
                document.getElementById('status').textContent = 'Model load error';
            }}
        }}

        function setExpression(expr, duration = 0.5) {{
            if (!model) return;
            const exprMap = {{
                'neutral': 0, 'happy': 1, 'sad': 2, 'angry': 3, 'shy': 4, 'surprised': 5
            }};
            const idx = exprMap[expr] ?? 0;
            model.expressionManager.setExpression(idx, undefined, undefined, duration);
            currentExpression = expr;
        }}

        function setPose(poseName) {{
            if (!model || !model.internalModel.motionManager) return;
            const mgr = model.internalModel.motionManager;
            const group = poseName.split('_')[0];
            // Simplified - would need proper definition lookup
            model.motion(poseName);
        }}

        function startLipSync(frames) {{
            if (mouthInterval) clearInterval(mouthInterval);
            if (!frames.length) return;

            // Map phonemes to mouth parameters
            const PHONEME_MAP = {{
                'a': [1.0, 0.0], 'e': [0.8, 0.3], 'i': [0.3, 0.8],
                'o': [0.6, -0.3], 'u': [0.2, -0.8], 'neutral': [0.3, 0.0]
            }};

            let frameIdx = 0;
            mouthInterval = setInterval(() => {{
                if (frameIdx >= frames.length) {{
                    clearInterval(mouthInterval);
                    setMouth(0.3, 0.0);  // neutral
                    return;
                }}
                const f = frames[frameIdx++];
                const [open, form] = PHONEME_MAP[f.phoneme] || PHONEME_MAP['neutral'];
                setMouth(open * f.weight, form);
            }}, 50); // 20 FPS
        }}

        function setMouth(openness, form) {{
            if (!model) return;
            try {{
                model.internalModel.mouthManager.setOpenValue(openness);
                model.internalModel.mouthManager.setForm(form);
            }} catch (e) {{
                // Some models don't have mouth manager
            }}
        }}

        function lookAt(x, y, immediate = false) {{
            if (!model) return;
            const targetX = (x - 0.5) * 2 * 30;  // +/- 30 degrees
            const targetY = (0.5 - y) * 2 * 30;
            model.lookAt(targetX, targetY);
        }}

        function enableEyeTracking() {{
            document.addEventListener('mousemove', (e) => {{
                if (!model) return;
                const rect = app.view.getBoundingClientRect();
                const x = (e.clientX - rect.left) / rect.width;
                const y = (e.clientY - rect.top) / rect.height;
                lookAt(x, y, false);
            }});
        }}

        function setEmotion(emotion, intensity = 1.0) {{
            // Map emotion to expression
            const emotionExpr = {{
                'happy': 'f01', 'sad': 'f02', 'angry': 'f03',
                'neutral': 'f00', 'shy': 'f04', 'surprised': 'f05'
            }};
            const expr = emotionExpr[emotion] || currentExpression;
            if (expr !== currentExpression) {{
                setExpression(emotion, 0.3);
            }}
        }}

        function showSpeech(text) {{
            const bubble = document.getElementById('speech-bubble');
            bubble.textContent = text;
            bubble.style.display = 'block';
            setTimeout(() => {{
                bubble.style.display = 'none';
            }}, 3000);
        }}

        function sendSay(text) {{
            ws.send(JSON.stringify({{type: 'say', text: text}}));
        }}

        function triggerMotion() {{
            if (!model) return;
            // Random motion
            const motions = ['Idle_01', 'Idle_02', 'TapBody'];
            const random = motions[Math.floor(Math.random() * motions.length)];
            model.motion(random);
        }}

        function enableRandomMotion() {{
            setInterval(() => {{
                if (Math.random() < 0.3) triggerMotion();
            }}, 5000);
        }}
    </script>
</body>
</html>
"""

    def __init__(self, host: str = "127.0.0.1", web_port: int = 8080, ws_port: int = 8081):
        self.host = host
        self.web_port = web_port
        self.ws_port = ws_port
        self.model_path: str | None = None
        self._web_app: web.Application | None = None
        self._web_runner: web.AppRunner | None = None
        self._web_site: web.TCPSite | None = None
        self._ws_server = None
        self._clients: list[any] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._lip_sync_engine = LipSyncEngine()

    async def start(self, model_path: str) -> bool:
        """Start web server and WebSocket."""
        try:
            self.model_path = model_path

            # Create web app
            self._web_app = web.Application()
            self._web_app.router.add_get("/", self._handle_index)
            self._web_app.router.add_get("/api/status", self._handle_status)
            self._web_app.router.add_post("/api/expression", self._handle_expression)
            self._web_app.router.add_post("/api/pose", self._handle_pose)
            self._web_app.router.add_post("/api/say", self._handle_say)
            self._web_app.router.add_post("/api/look_at", self._handle_look_at)
            self._web_app.router.add_get("/assets/{path:.*}", self._handle_asset)

            # Start web server
            self._web_runner = web.AppRunner(self._web_app)
            await self._web_runner.setup()
            self._web_site = web.TCPSite(self._web_runner, self.host, self.web_port)
            await self._web_site.start()
            logger.info(f"Web server started at http://{self.host}:{self.web_port}")

            # Start WebSocket server in background
            self._running = True
            self._thread = threading.Thread(target=self._run_ws_server, daemon=True)
            self._thread.start()
            logger.info(f"WebSocket server started on ws://{self.host}:{self.ws_port}")

            return True
        except Exception as e:
            logger.error(f"Failed to start web interface: {e}")
            return False

    def _run_ws_server(self):
        """Run WebSocket server in thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def handler(websocket, path):
            self._clients.append(websocket)
            try:
                async for message in websocket:
                    data = json.loads(message)
                    response = await self._handle_ws_message(data)
                    if response:
                        await websocket.send(json.dumps(response))
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            finally:
                if websocket in self._clients:
                    self._clients.remove(websocket)

        try:
            self._ws_server = loop.run_until_complete(
                websocket_serve(handler, self.host, self.ws_port)
            )
            loop.run_forever()
        except Exception as e:
            logger.error(f"WebSocket server error: {e}")
        finally:
            loop.close()

    async def stop(self):
        """Stop servers."""
        self._running = False

        if self._web_site:
            await self._web_site.stop()
        if self._web_runner:
            await self._web_runner.cleanup()

        if self._ws_server:
            loop = asyncio.get_event_loop()
            self._ws_server.close()
            await self._ws_server.wait_closed()

        logger.info("Web interface stopped")

    # ============ HTTP Handlers ============

    async def _handle_index(self, request):
        """Serve main page."""
        return web.Response(text=self.HTML_TEMPLATE, content_type="text/html")

    async def _handle_status(self, request):
        """Status API."""
        return web.json_response({
            "status": "running",
            "model_path": self.model_path,
            "clients_connected": len(self._clients),
            "timestamp": datetime.now().isoformat()
        })

    async def _handle_expression(self, request):
        """Set expression API."""
        data = await request.json()
        expr = data.get("expression", "neutral")
        duration = data.get("duration", 0.5)

        exp_map = {
            "neutral": "f00", "happy": "f01", "sad": "f02",
            "angry": "f03", "shy": "f04", "surprised": "f05"
        }
        code = exp_map.get(expr, "f00")

        await self._broadcast({"type": "expression", "value": code, "duration": duration})
        return web.json_response({"ok": True})

    async def _handle_pose(self, request):
        """Set pose API."""
        data = await request.json()
        pose = data.get("pose", "Idle_01")
        await self._broadcast({"type": "pose", "value": pose})
        return web.json_response({"ok": True})

    async def _handle_say(self, request):
        """Say text with lip-sync."""
        data = await request.json()
        text = data.get("text", "")
        audio_file = data.get("audio_file")

        # Generate audio if not provided (would use TTS)
        frames = []
        if text and LIBROSA_AVAILABLE:
            # Simple: generate dummy lip-sync frames from text length
            # In production, use actual TTS + audio analysis
            duration = len(text) * 0.1  # rough estimate
            fps = 20
            num_frames = int(duration * fps)

            for i in range(num_frames):
                # Create phoneme-like sequence from text syllables (simplified)
                idx = (i * 2) % len(text)
                char = text[idx].lower()
                phoneme = "a" if char in "aeiou" else "neutral"
                frames.append({
                    "phoneme": phoneme,
                    "weight": 1.0,
                    "timestamp": i / fps
                })

        await self._broadcast({
            "type": "say",
            "text": text,
            "frames": frames
        })

        return web.json_response({"ok": True})

    async def _handle_look_at(self, request):
        """Look at point."""
        data = await request.json()
        x = data.get("x", 0.5)
        y = data.get("y", 0.5)
        immediate = data.get("immediate", False)

        await self._broadcast({
            "type": "look_at",
            "x": x,
            "y": y,
            "immediate": immediate
        })
        return web.json_response({"ok": True})

    async def _handle_asset(self, request):
        """Serve static assets."""
        path = request.match_info["path"]
        asset_dir = Path("./assets")
        file_path = asset_dir / path

        if file_path.exists():
            return web.FileResponse(file_path)
        raise web.HTTPNotFound()

    # ============ WebSocket ============

    async def _handle_ws_message(self, data: dict[str, Any]) -> dict[str, Any] | None:
        """Handle incoming WebSocket message."""
        msg_type = data.get("type")

        if msg_type == "get_model":
            return {
                "type": "init",
                "model_path": self.model_path or "./assets/haru/haru_greeter_t03.model3.json"
            }

        # Broadcast to all other clients
        await self._broadcast(data, exclude=data.get("_client"))
        return None

    async def _broadcast(self, data: dict[str, Any], exclude=None):
        """Broadcast message to all WebSocket clients."""
        if not self._clients:
            return

        message = json.dumps(data)
        tasks = []
        for client in self._clients:
            if client != exclude:
                try:
                    tasks.append(client.send(message))
                except:
                    pass

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


# ============ Main Plugin ============

class AirIPlugin(Plugin):
    """Main AirI digital human plugin."""

    def __init__(self, manifest: PluginManifest, config: PluginConfig):
        super().__init__(manifest, config)
        self.state = ModelState()
        self.web_interface: WebInterface | None = None
        self.lip_sync_engine = LipSyncEngine()
        self._motion_queue: list[Motion] = []
        self._running = False
        self._lock = asyncio.Lock()
        self._emotion_callbacks: list[Callable] = []

    async def init(self) -> None:
        """Initialize plugin."""
        await super().init()
        self._load_config()
        logger.info("AirI plugin initialized")

    def _load_config(self):
        """Load configuration."""
        self.model_path = self.config.config.get("model_path", "./assets/haru/haru_greeter_t03.model3.json")
        self.web_port = self.config.config.get("web_port", 8080)
        self.ws_port = self.config.config.get("websocket_port", 8081)
        self.host = self.config.config.get("host", "127.0.0.1")
        self.auto_start_web = self.config.config.get("auto_start_web", True)
        self.lip_sync_enabled = self.config.config.get("lip_sync_enabled", True)

        # Expression mapping
        emotion_mapping = self.config.config.get("emotion_mapping", {
            "happy": "f01",
            "sad": "f02",
            "angry": "f03",
            "neutral": "f00"
        })
        self.emotion_mapping = emotion_mapping

        self.default_expression = self.config.config.get("default_expression", "f00")
        self.default_pose = self.config.config.get("default_pose", "Idle_01")

        # Animation settings
        self.animation_speed = self.config.config.get("animation_speed", 1.0)
        self.breathing_enabled = self.config.config.get("breathing_enabled", True)
        self.eye_tracking_enabled = self.config.config.get("eye_tracking_enabled", True)

    async def start(self) -> None:
        """Start plugin and web interface."""
        await super().start()

        self.web_interface = WebInterface(
            host=self.host,
            web_port=self.web_port,
            ws_port=self.ws_port
        )

        if self.auto_start_web:
            success = await self.web_interface.start(self.model_path)
            if success:
                logger.info(f"AirI web interface started at http://{self.host}:{self.web_port}")
            else:
                logger.error("Failed to start web interface")

        self._running = True
        logger.info("AirI plugin started")

    async def stop(self) -> None:
        """Stop plugin."""
        self._running = False
        if self.web_interface:
            await self.web_interface.stop()
        await super().stop()
        logger.info("AirI plugin stopped")

    # ============ Actions ============

    async def start_web(self) -> dict[str, Any]:
        """Start web interface."""
        if self.web_interface and not self._running:
            success = await self.web_interface.start(self.model_path)
            if success:
                self._running = True
                return {"status": "started", "url": f"http://{self.host}:{self.web_port}"}
        return {"status": "failed", "error": "Already running or error"}

    async def stop_web(self) -> dict[str, Any]:
        """Stop web interface."""
        if self.web_interface:
            await self.web_interface.stop()
            self._running = False
            return {"status": "stopped"}
        return {"status": "not_running"}

    async def set_expression(self, expression: str, duration: float = 0.5) -> bool:
        """Set expression."""
        if self.web_interface:
            expr = self.emotion_mapping.get(expression, self.default_expression)
            await self.web_interface._broadcast({
                "type": "expression",
                "value": expr,
                "duration": duration
            })
            self.state.expression = expr
            logger.info(f"Expression set: {expression} ({expr})")
            return True
        return False

    async def set_pose(self, pose: str) -> bool:
        """Set pose."""
        if self.web_interface:
            await self.web_interface._broadcast({
                "type": "pose",
                "value": pose
            })
            self.state.pose = pose
            logger.info(f"Pose set: {pose}")
            return True
        return False

    async def say(self, text: str, audio_file: str = None, voice: str = None, speed: float = 1.0) -> bool:
        """
        Speak text with lip-sync.
        Args:
            text: Text to speak
            audio_file: Optional pre-generated audio file
            voice: Voice selection (if TTS available)
            speed: Speech speed
        """
        if not self.web_interface:
            return False

        frames = []
        if self.lip_sync_enabled and LIBROSA_AVAILABLE and audio_file:
            # Analyze actual audio file
            try:
                y, sr = sf.read(audio_file)
                if len(y.shape) > 1:
                    y = np.mean(y, axis=1)  # stereo to mono
                frames = self.lip_sync_engine.analyze_audio(y, sr)
                # Convert to serialisable format
                frames = [{"phoneme": f.phoneme, "weight": f.weight, "timestamp": f.timestamp} for f in frames]
            except Exception as e:
                logger.error(f"Lip-sync audio analysis failed: {e}")

        await self.web_interface._broadcast({
            "type": "say",
            "text": text,
            "frames": frames,
            "speed": speed
        })

        logger.info(f"Speaking: {text[:50]}...")
        return True

    async def set_emotion(self, emotion: str, intensity: float = 1.0) -> bool:
        """Set emotion state."""
        self.state.emotion = EmotionState(
            primary=emotion,
            intensity=intensity,
            timestamp=datetime.now()
        )

        if self.web_interface:
            await self.web_interface._broadcast({
                "type": "emotion",
                "value": emotion,
                "intensity": intensity
            })

        # Trigger callbacks
        for cb in self._emotion_callbacks:
            try:
                await cb(emotion, intensity)
            except:
                pass

        logger.info(f"Emotion set: {emotion} (intensity={intensity})")
        return True

    async def look_at(self, x: float, y: float, immediate: bool = False) -> bool:
        """
        Set look-at direction.
        Args:
            x, y: Normalized coordinates (0-1)
            immediate: Skip smoothing
        """
        if self.web_interface:
            await self.web_interface._broadcast({
                "type": "look_at",
                "x": x,
                "y": y,
                "immediate": immediate
            })
            self.state.eye_x = x
            self.state.eye_y = y
            return True
        return False

    async def add_motion(self, group: str, name: str, file: str = None, **kwargs) -> bool:
        """Add motion to queue."""
        motion = Motion(
            group=group,
            name=name,
            file=file or f"{group}/{name}.motion3.json",
            **kwargs
        )
        self._motion_queue.append(motion)
        self._motion_queue.sort(key=lambda m: -m.priority)

        if self.web_interface:
            await self.web_interface._broadcast({
                "type": "motion",
                "group": group,
                "name": name
            })

        logger.info(f"Motion queued: {group}/{name}")
        return True

    async def clear_motions(self) -> None:
        """Clear motion queue."""
        self._motion_queue.clear()

    async def get_status(self) -> dict[str, Any]:
        """Get current plugin status."""
        return {
            "running": self._running,
            "model_path": self.model_path,
            "web_url": f"http://{self.host}:{self.web_port}" if self._running else None,
            "websocket_url": f"ws://{self.host}:{self.ws_port}" if self._running else None,
            "state": {
                "expression": self.state.expression,
                "pose": self.state.pose,
                "emotion": self.state.emotion.primary,
                "emotion_intensity": self.state.emotion.intensity,
                "mouth_openness": self.state.mouth_openness,
                "eye_position": {"x": self.state.eye_x, "y": self.state.eye_y}
            },
            "queue_size": len(self._motion_queue)
        }

    async def trigger(self, event_name: str, **kwargs) -> bool:
        """Trigger custom event."""
        if self.web_interface:
            await self.web_interface._broadcast({
                "type": "event",
                "event": event_name,
                "data": kwargs
            })
            return True
        return False

    async def on_emotion_change(self, callback: Callable) -> None:
        """Register emotion change callback."""
        self._emotion_callbacks.append(callback)

    async def execute(self, action: str, **kwargs) -> Any:
        """Execute actions."""
        actions = {
            "start_web": self.start_web,
            "stop_web": self.stop_web,
            "set_expression": self.set_expression,
            "set_pose": self.set_pose,
            "say": self.say,
            "set_emotion": self.set_emotion,
            "look_at": self.look_at,
            "add_motion": self.add_motion,
            "clear_motions": self.clear_motions,
            "get_status": self.get_status,
            "trigger": self.trigger,
            "on_emotion_change": self.on_emotion_change
        }

        if action not in actions:
            raise ValueError(f"Unknown action: {action}")

        method = actions[action]
        return await method(**kwargs)

    def get_tools(self) -> list[dict[str, Any]]:
        """Return tool definitions."""
        return [{
            "name": "airi_say",
            "description": "Make AirI speak with lip-sync animation",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to speak"},
                    "voice": {"type": "string", "description": "Voice identifier"},
                    "speed": {"type": "number", "description": "Speech speed", "default": 1.0}
                },
                "required": ["text"]
            }
        }, {
            "name": "airi_set_expression",
            "description": "Set AirI's expression",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "enum": ["neutral", "happy", "sad", "angry", "shy", "surprised"],
                        "description": "Expression to set"
                    },
                    "duration": {"type": "number", "description": "Transition duration in seconds", "default": 0.5}
                },
                "required": ["expression"]
            }
        }, {
            "name": "airi_set_emotion",
            "description": "Set AirI's emotional state",
            "parameters": {
                "type": "object",
                "properties": {
                    "emotion": {"type": "string", "description": "Emotion state"},
                    "intensity": {"type": "number", "description": "Intensity 0-1", "default": 1.0}
                },
                "required": ["emotion"]
            }
        }, {
            "name": "airi_look_at",
            "description": "Make AirI look at a point",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "number", "description": "X position (0-1 normalized)"},
                    "y": {"type": "number", "description": "Y position (0-1 normalized)"},
                    "immediate": {"type": "boolean", "description": "Skip smoothing"}
                },
                "required": ["x", "y"]
            }
        }, {
            "name": "airi_get_status",
            "description": "Get AirI current status",
            "parameters": {"type": "object", "properties": {}}
        }]

    async def health_check(self) -> dict[str, Any]:
        """Return plugin health status."""
        status = await super().health_check()
        status["running"] = self._running
        status["model_path"] = self.model_path
        status["lip_sync"] = self.lip_sync_enabled
        status["active_connections"] = len(self.web_interface._clients) if self.web_interface else 0
        return status
