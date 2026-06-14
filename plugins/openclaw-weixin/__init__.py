"""
OpenClaw Weixin Plugin - Hermes Channel Adapter
Complete implementation with multi-account management, message handling, and group support.
"""

import asyncio
import json
import logging
import os
import queue
import re
import threading
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from hermes.plugins.plugin_system import Plugin, PluginConfig, PluginManifest

logger = logging.getLogger(__name__)


# ============ Data Structures ============

@dataclass
class WeChatAccount:
    """WeChat account configuration."""
    id: str
    name: str
    backend: str
    auto_login: bool = False
    qr_path: str = "./qr.png"
    qr_callback: str | None = None
    status: str = "inactive"  # inactive, logging_in, active, error
    session_path: str = "./session.pkl"
    extra: dict[str, Any] = None

    def __post_init__(self):
        if self.extra is None:
            self.extra = {}


@dataclass
class WeChatMessage:
    """Unified message structure."""
    msg_id: str
    msg_type: str  # text, image, voice, file, video, location, card
    account_id: str
    from_user: str
    to_user: str
    content: str
    raw_content: Any
    is_group: bool
    group_id: str | None = None
    sender_nickname: str | None = None
    timestamp: datetime
    file_path: str | None = None
    file_url: str | None = None
    location: dict[str, float] | None = None  # lat, lon

    def to_dict(self) -> dict[str, Any]:
        """Serialise to dictionary."""
        return {
            "msg_id": self.msg_id,
            "msg_type": self.msg_type,
            "account_id": self.account_id,
            "from_user": self.from_user,
            "to_user": self.to_user,
            "content": self.content,
            "is_group": self.is_group,
            "group_id": self.group_id,
            "sender_nickname": self.sender_nickname,
            "timestamp": self.timestamp.isoformat(),
            "file_path": self.file_path,
            "file_url": self.file_url,
            "location": self.location
        }


class Backend(ABC):
    """Abstract backend interface."""

    @abstractmethod
    async def login(self, account: WeChatAccount, qr_callback=None) -> bool:
        """Login to WeChat."""

    @abstractmethod
    async def logout(self) -> bool:
        """Logout."""

    @abstractmethod
    async def send_message(self, to_user: str, message: str, msg_type: str = "text", file_path: str = None) -> bool:
        """Send a message."""

    @abstractmethod
    async def get_contacts(self) -> list[dict[str, Any]]:
        """Get all contacts."""

    @abstractmethod
    async def get_groups(self) -> list[dict[str, Any]]:
        """Get all groups."""

    @abstractmethod
    async def get_messages(self, limit: int = 100) -> list[WeChatMessage]:
        """Get recent messages."""

    @abstractmethod
    async def start_listening(self) -> None:
        """Start listening for incoming messages."""

    @abstractmethod
    async def stop_listening(self) -> None:
        """Stop listening."""

    @abstractmethod
    def is_logged_in(self) -> bool:
        """Check if logged in."""

    @abstractmethod
    def get_qr_code(self) -> str | None:
        """Get QR code path (if generated)."""


class ItchatBackend(Backend):
    """itchat-based backend."""

    def __init__(self):
        self.itchat = None
        self.logged_in = False
        self.account: WeChatAccount | None = None
        self.message_queue = asyncio.Queue()
        self._listening = False
        self._thread: threading.Thread | None = None
        self._login_event = threading.Event()
        self._qr_code_path: str | None = None

    def _load_itchat(self):
        """Lazy load itchat."""
        if self.itchat is None:
            import itchat
            self.itchat = itchat

    async def login(self, account: WeChatAccount, qr_callback=None) -> bool:
        """Login using itchat."""
        self.account = account
        self._load_itchat()

        def do_login():
            try:
                # Login with QR
                self.itchat.auto_login(
                    hotReload=True,
                    statusStorageDir=account.session_path,
                    qrCallback=self._qr_callback if qr_callback else None
                )
                self._login_event.set()
            except Exception as e:
                logger.error(f"itchat login failed: {e}")
                self._login_event.set()

        # Run login in a separate thread (itchat is blocking)
        self._thread = threading.Thread(target=do_login, daemon=True)
        self._thread.start()

        # Wait for login
        await asyncio.sleep(1)

        # Check periodically
        for _ in range(account.extra.get("login_attempts", 30)):
            if self._login_event.is_set():
                break
            await asyncio.sleep(1)

        self.logged_in = True
        return True

    def _qr_callback(self, uuid, status, qrcode):
        """QR callback from itchat."""
        self._qr_code_path = f"qrcode_{uuid}.png"
        logger.info(f"QR code generated: {self._qr_code_path}")

    async def logout(self) -> bool:
        """Logout."""
        if self.itchat and self.logged_in:
            self.itchat.logout()
            self.logged_in = False
        return True

    async def send_message(self, to_user: str, message: str, msg_type: str = "text", file_path: str = None) -> bool:
        """Send message via itchat."""
        if not self.logged_in:
            logger.error("Not logged in")
            return False

        try:
            if msg_type == "text":
                self.itchat.send(message, toUserName=to_user)
            elif msg_type == "image" and file_path:
                self.itchat.send_image(file_path, toUserName=to_user)
            elif msg_type == "file" and file_path:
                self.itchat.send_file(file_path, toUserName=to_user)
            elif msg_type == "video" and file_path:
                self.itchat.send_video(file_path, toUserName=to_user)
            else:
                logger.warning(f"Unsupported message type or missing file: {msg_type}")
                return False

            logger.info(f"Message sent to {to_user}")
            return True
        except Exception as e:
            logger.error(f"Send message failed: {e}")
            return False

    async def get_contacts(self) -> list[dict[str, Any]]:
        """Get all contacts."""
        if not self.logged_in:
            return []
        friends = self.itchat.get_friends(update=True)
        return [{"UserName": f["UserName"], "NickName": f["NickName"]} for f in friends]

    async def get_groups(self) -> list[dict[str, Any]]:
        """Get all groups."""
        if not self.logged_in:
            return []
        groups = self.itchat.get_chatrooms(update=True)
        return [
            {
                "UserName": g["UserName"],
                "NickName": g["NickName"],
                "MemberCount": g.get("MemberCount", 0)
            }
            for g in groups
        ]

    async def get_messages(self, limit: int = 100) -> list[WeChatMessage]:
        """Get recent messages from queue."""
        messages = []
        try:
            while not self.message_queue.empty() and len(messages) < limit:
                msg = self.message_queue.get_nowait()
                messages.append(msg)
        except asyncio.QueueEmpty:
            pass
        return messages

    async def start_listening(self) -> None:
        """Start listening with itchat message handler."""
        if not self.logged_in:
            logger.error("Must be logged in to start listening")
            return

        @self.itchat.msg_register(self.itchat.content.TEXT)
        def text_handler(msg):
            self._handle_message(msg, "text")

        @self.itchat.msg_register([self.itchat.content.PICTURE, self.itchat.content.RECORDING])
        def media_handler(msg):
            msg_type = "image" if msg["Type"] == "Picture" else "voice"
            self._handle_message(msg, msg_type)

        @self.itchat.msg_register(self.itchat.content.ATTACHMENT)
        def file_handler(msg):
            self._handle_message(msg, "file")

        @self.itchat.msg_register(self.itchat.content.SHARING)
        def sharing_handler(msg):
            self._handle_message(msg, "link")

        @self.itchat.msg_register(self.itchat.content.NOTE)
        def note_handler(msg):
            self._handle_message(msg, "note")

        self._listening = True

        # Run itchat in a thread
        def run_itchat():
            self.itchat.run()

        self._thread = threading.Thread(target=run_itchat, daemon=True)
        self._thread.start()

        logger.info("itchat listening started")

    async def stop_listening(self) -> None:
        """Stop listening."""
        self._listening = False
        if self.itchat:
            self.itchat.logout()
        if self._thread and self._thread.is_alive():
            # Itchat will exit on logout
            pass

    def is_logged_in(self) -> bool:
        return self.logged_in

    def get_qr_code(self) -> str | None:
        return self._qr_code_path

    def _handle_message(self, msg, msg_type: str):
        """Handle incoming message from itchat."""
        # This runs in itchat's thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            message = WeChatMessage(
                msg_id=msg.get("MsgId", str(hash(msg))),
                msg_type=msg_type,
                account_id=self.account.id if self.account else "unknown",
                from_user=msg.get("FromUserName", ""),
                to_user=msg.get("ToUserName", ""),
                content=msg.get("Text", ""),
                raw_content=msg,
                is_group=msg.get("isAt", False) or msg.get("IsAt", False),
                sender_nickname=msg.get("ActualNickName") or msg.get("NickName", ""),
                timestamp=datetime.now()
            )

            # Handle file downloads
            if msg_type in ["image", "voice", "file", "video"]:
                try:
                    import os
                    cache_dir = self.account.extra.get("file_cache_dir", "./file_cache") if self.account else "./file_cache"
                    os.makedirs(cache_dir, exist_ok=True)

                    filename = msg["FileName"]
                    filepath = os.path.join(cache_dir, filename)
                    msg.download(filepath)
                    message.file_path = filepath
                    message.file_url = f"file://{filepath}"
                except Exception as e:
                    logger.error(f"Failed to download file: {e}")

            # Put into queue
            loop.run_until_complete(self.message_queue.put(message))

            # Emit event
            loop.run_until_complete(
                self.account.manager.event_bus.publish(
                    "message.receive",
                    source="openclaw-weixin",
                    data=message.to_dict()
                )
            ) if self.account and hasattr(self.account, "manager") else None

        finally:
            loop.close()


class WxautoBackend(Backend):
    """wxauto-based backend (Windows)."""

    def __init__(self):
        self.wx = None
        self.logged_in = False
        self.account: WeChatAccount | None = None
        self.message_queue = asyncio.Queue()
        self._listening = False
        self._thread: threading.Thread | None = None
        self._last_messages: list[WeChatMessage] = []

    async def login(self, account: WeChatAccount, qr_callback=None) -> bool:
        """Login using wxauto."""
        try:
            from wxauto import WeChat
            self.wx = WeChat()
            self.account = account
            self.logged_in = True
            logger.info("wxauto login successful")
            return True
        except Exception as e:
            logger.error(f"wxauto login failed: {e}")
            return False

    async def logout(self) -> bool:
        """Logout."""
        self.logged_in = False
        if self.wx:
            self.wx = None
        return True

    async def send_message(self, to_user: str, message: str, msg_type: str = "text", file_path: str = None) -> bool:
        """Send message via wxauto."""
        if not self.logged_in or not self.wx:
            logger.error("Not logged in or wx not initialized")
            return False

        try:
            if msg_type == "text":
                self.wx.SendMsg(message, who=to_user)
            elif msg_type == "image" and file_path:
                self.wx.SendFiles(file_path, who=to_user)
            else:
                logger.warning(f"Unsupported message type: {msg_type}")
                return False

            logger.info(f"Message sent to {to_user}")
            return True
        except Exception as e:
            logger.error(f"Send message failed: {e}")
            return False

    async def get_contacts(self) -> list[dict[str, Any]]:
        """Get all contacts."""
        if not self.logged_in:
            return []
        try:
            friends = self.wx.GetFriendLists()
            return [{"NickName": f} for f in friends]
        except Exception as e:
            logger.error(f"Get contacts failed: {e}")
            return []

    async def get_groups(self) -> list[dict[str, Any]]:
        """Get all groups."""
        if not self.logged_in:
            return []
        try:
            chats = self.wx.GetChatList()
            groups = [c for c in chats if c.get("IsGroup", False)]
            return groups
        except Exception as e:
            logger.error(f"Get groups failed: {e}")
            return []

    async def get_messages(self, limit: int = 100) -> list[WeChatMessage]:
        """Get recent messages."""
        if not self.logged_in:
            return []

        try:
            messages = self.wx.GetListenMessage()
            result = []

            for msg in messages[:limit]:
                msg_type = msg.get("type", "text")
                content = msg.get("content", "")
                sender = msg.get("sender", "")
                chat = msg.get("chat", "")

                is_group = msg.get("is_group", False)

                result.append(WeChatMessage(
                    msg_id=str(hash(msg)),
                    msg_type=msg_type,
                    account_id=self.account.id if self.account else "unknown",
                    from_user=sender,
                    to_user=chat,
                    content=content,
                    raw_content=msg,
                    is_group=is_group,
                    group_id=chat if is_group else None,
                    sender_nickname=sender,
                    timestamp=datetime.now()
                ))

            return result
        except Exception as e:
            logger.error(f"Get messages failed: {e}")
            return []

    async def start_listening(self) -> None:
        """Start listening with wxauto."""
        if not self.logged_in:
            return

        def listen_loop():
            while self._listening:
                try:
                    messages = self.wx.GetListenMessage()
                    for msg in messages:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                        wmsg = WeChatMessage(
                            msg_id=str(hash(msg)),
                            msg_type=msg.get("type", "text"),
                            account_id=self.account.id if self.account else "unknown",
                            from_user=msg.get("sender", ""),
                            to_user=msg.get("chat", ""),
                            content=msg.get("content", ""),
                            raw_content=msg,
                            is_group=msg.get("is_group", False),
                            group_id=msg.get("chat") if msg.get("is_group") else None,
                            sender_nickname=msg.get("sender", ""),
                            timestamp=datetime.now()
                        )

                        loop.run_until_complete(self.message_queue.put(wmsg))
                        loop.run_until_complete(
                            self.account.manager.event_bus.publish(
                                "message.receive",
                                source="openclaw-weixin",
                                data=wmsg.to_dict()
                            )
                        ) if self.account and hasattr(self.account, "manager") else None

                        loop.close()
                except Exception as e:
                    logger.error(f"Listen loop error: {e}")

        self._listening = True
        self._thread = threading.Thread(target=listen_loop, daemon=True)
        self._thread.start()
        logger.info("wxauto listening started")

    async def stop_listening(self) -> None:
        """Stop listening."""
        self._listening = False
        if self._thread and self._thread.is_alive():
            # Thread will exit on its own
            pass

    def is_logged_in(self) -> bool:
        return self.logged_in

    def get_qr_code(self) -> str | None:
        """wxauto doesn't use QR."""
        return None


# ============ Main Plugin ============

class WeixinPlugin(Plugin):
    """Complete WeChat plugin for Hermes."""

    def __init__(self, manifest: PluginManifest, config: PluginConfig):
        super().__init__(manifest, config)
        self.accounts: dict[str, WeChatAccount] = {}
        self.backends: dict[str, Backend] = {}
        self._lock = asyncio.Lock()
        self._message_filters: list[re.Pattern] = []
        self._auto_reply_enabled = False
        self._auto_reply_prefix = ""
        self._blocked_users: set = set()
        self._blocked_groups: set = set()
        self._trusted_users: set = set()

    async def init(self) -> None:
        """Initialize plugin and load accounts."""
        await super().init()
        await self._load_config()
        await self._load_accounts()

        # Load backends
        for backend_name in self.config.config.get("backends", ["itchat"]):
            try:
                if backend_name == "itchat":
                    backend = ItchatBackend()
                elif backend_name == "wxauto":
                    backend = WxautoBackend()
                else:
                    logger.warning(f"Unknown backend: {backend_name}")
                    continue

                self.backends[backend_name] = backend
                logger.info(f"Backend loaded: {backend_name}")
            except Exception as e:
                logger.error(f"Failed to load backend {backend_name}: {e}")

        logger.info(f"Weixin plugin initialized with {len(self.accounts)} accounts")

    async def start(self) -> None:
        """Start plugin and auto-login configured accounts."""
        await super().start()

        # Auto-login accounts that have auto_login enabled
        for account in self.accounts.values():
            if account.auto_login:
                try:
                    await self.connect(account.id)
                except Exception as e:
                    logger.error(f"Auto-login failed for {account.id}: {e}")

        logger.info("Weixin plugin started")

    async def stop(self) -> None:
        """Stop plugin and disconnect all accounts."""
        for account_id in list(self.accounts.keys()):
            try:
                await self.disconnect(account_id)
            except Exception as e:
                logger.error(f"Error disconnecting {account_id}: {e}")

        await super().stop()
        logger.info("Weixin plugin stopped")

    async def _load_config(self):
        """Load configuration settings."""
        self._auto_reply_enabled = self.config.config.get("auto_reply", False)
        self._auto_reply_prefix = self.config.config.get("auto_reply_prefix", "@Bot")
        self._blocked_users = set(self.config.config.get("blocked_users", []))
        self._blocked_groups = set(self.config.config.get("blocked_groups", []))

        # Compile message filter regex
        filter_pattern = self.config.config.get("message_filter", "")
        if filter_pattern:
            try:
                self._message_filters.append(re.compile(filter_pattern))
            except re.error as e:
                logger.error(f"Invalid message filter regex: {e}")

    async def _load_accounts(self):
        """Load accounts from configuration."""
        accounts_file = self.config.config.get("accounts_file", "accounts.json")
        accounts_path = Path(accounts_file)

        if not accounts_path.exists():
            logger.warning(f"Accounts file not found: {accounts_file}")
            return

        try:
            with open(accounts_path) as f:
                data = json.load(f)

            for acc_data in data.get("accounts", []):
                account = WeChatAccount(
                    id=acc_data["id"],
                    name=acc_data["name"],
                    backend=acc_data["backend"],
                    auto_login=acc_data.get("auto_login", False),
                    qr_path=acc_data.get("qr_path", "./qr.png"),
                    qr_callback=acc_data.get("qr_callback"),
                    session_path=acc_data.get("session_path", "./session.pkl"),
                    extra={**acc_data.get("extra", {}), "file_cache_dir": self.config.config.get("file_cache_dir", "./file_cache")}
                )
                self.accounts[account.id] = account

            logger.info(f"Loaded {len(self.accounts)} accounts")

        except Exception as e:
            logger.error(f"Failed to load accounts: {e}")

    async def _save_accounts(self):
        """Save accounts to configuration."""
        accounts_file = self.config.config.get("accounts_file", "accounts.json")
        accounts_path = Path(accounts_file)

        data = {
            "accounts": [
                {
                    "id": acc.id,
                    "name": acc.name,
                    "backend": acc.backend,
                    "auto_login": acc.auto_login,
                    "qr_path": acc.qr_path,
                    "qr_callback": acc.qr_callback,
                    "session_path": acc.session_path,
                    "status": acc.status,
                    "extra": {k: v for k, v in acc.extra.items() if k != "manager"}
                }
                for acc in self.accounts.values()
            ]
        }

        try:
            with open(accounts_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save accounts: {e}")

    def _get_backend(self, account_id: str) -> Backend | None:
        """Get backend for account."""
        account = self.accounts.get(account_id)
        if not account:
            return None
        return self.backends.get(account.backend)

    def _should_process_message(self, msg: WeChatMessage) -> bool:
        """Check if message should be processed."""
        # Filter by user/group
        if msg.is_group:
            if msg.group_id in self._blocked_groups:
                return False
        elif msg.from_user in self._blocked_users:
            return False

        # Apply regex filters
        for pattern in self._message_filters:
            if pattern.search(msg.content):
                return False

        return True

    async def connect(self, account_id: str) -> bool:
        """Connect (login) a WeChat account."""
        async with self._lock:
            if account_id not in self.accounts:
                logger.error(f"Account {account_id} not found")
                return False

            account = self.accounts[account_id]
            backend = self._get_backend(account_id)

            if not backend:
                logger.error(f"Backend {account.backend} not available")
                return False

            if account.status in ["logging_in", "active"]:
                logger.warning(f"Account {account_id} already connecting or connected")
                return True

            account.status = "logging_in"
            qr_path = account.qr_path

            try:
                success = await backend.login(account, qr_callback=qr_path)
                if success:
                    account.status = "active"
                    await backend.start_listening()
                    logger.info(f"Account {account_id} connected successfully")
                else:
                    account.status = "error"
                    logger.error(f"Account {account_id} failed to connect")
                return success
            except Exception as e:
                logger.error(f"Connect error for {account_id}: {e}")
                account.status = "error"
                return False

    async def disconnect(self, account_id: str) -> bool:
        """Disconnect a WeChat account."""
        async with self._lock:
            if account_id not in self.accounts:
                logger.warning(f"Account {account_id} not found")
                return False

            account = self.accounts[account_id]
            backend = self._get_backend(account_id)

            if backend and account.status in ["logging_in", "active"]:
                try:
                    await backend.stop_listening()
                    await backend.logout()
                except Exception as e:
                    logger.error(f"Error during disconnect: {e}")

            account.status = "inactive"
            await self._save_accounts()
            logger.info(f"Account {account_id} disconnected")
            return True

    async def send(self, to_user: str, message: str, msg_type: str = "text", file_path: str = None, account_id: str = None) -> bool:
        """Send a message."""
        # Select account
        if account_id:
            if account_id not in self.accounts:
                logger.error(f"Account {account_id} not found")
                return False
        else:
            # Use first active account
            active_accounts = [aid for aid, acc in self.accounts.items() if acc.status == "active"]
            if not active_accounts:
                logger.error("No active accounts available")
                return False
            account_id = active_accounts[0]

        account = self.accounts[account_id]
        backend = self._get_backend(account_id)

        if not backend or not account.status == "active":
            logger.error(f"Account {account_id} not active")
            return False

        try:
            return await backend.send_message(to_user, message, msg_type, file_path)
        except Exception as e:
            logger.error(f"Send failed: {e}")
            return False

    async def receive(self, account_id: str = None, limit: int = 100) -> list[dict[str, Any]]:
        """Receive pending messages."""
        messages = []

        if account_id:
            if account_id not in self.accounts:
                logger.error(f"Account {account_id} not found")
                return []
            account_ids = [account_id]
        else:
            account_ids = [aid for aid, acc in self.accounts.items() if acc.status == "active"]

        for aid in account_ids:
            account = self.accounts[aid]
            backend = self._get_backend(aid)
            if backend and account.status == "active":
                try:
                    backend_messages = await backend.get_messages(limit)
                    for msg in backend_messages:
                        if self._should_process_message(msg):
                            messages.append(msg.to_dict())
                except Exception as e:
                    logger.error(f"Receive error for {aid}: {e}")

        return messages[len(messages)-limit:] if len(messages) > limit else messages

    async def disconnect(self, account_id: str) -> bool:
        """Alias for disconnect."""
        return await self.disconnect(account_id)

    # ============ Action Methods ============

    async def list_accounts(self) -> list[dict[str, Any]]:
        """List all accounts with status."""
        result = []
        for acc in self.accounts.values():
            result.append({
                "id": acc.id,
                "name": acc.name,
                "backend": acc.backend,
                "status": acc.status,
                "auto_login": acc.auto_login
            })
        return result

    async def get_contacts(self, account_id: str) -> list[dict[str, Any]]:
        """Get contacts for an account."""
        if account_id not in self.accounts:
            raise ValueError(f"Account {account_id} not found")
        backend = self._get_backend(account_id)
        if not backend:
            raise ValueError(f"Backend not available for {account_id}")
        return await backend.get_contacts()

    async def get_groups(self, account_id: str) -> list[dict[str, Any]]:
        """Get groups for an account."""
        if account_id not in self.accounts:
            raise ValueError(f"Account {account_id} not found")
        backend = self._get_backend(account_id)
        if not backend:
            raise ValueError(f"Backend not available for {account_id}")
        return await backend.get_groups()

    async def toggle_auto_reply(self, enabled: bool = None) -> bool:
        """Toggle auto-reply."""
        if enabled is None:
            self._auto_reply_enabled = not self._auto_reply_enabled
        else:
            self._auto_reply_enabled = enabled
        logger.info(f"Auto-reply {'enabled' if self._auto_reply_enabled else 'disabled'}")
        return self._auto_reply_enabled

    async def add_blocked_user(self, user_id: str) -> None:
        """Block a user."""
        self._blocked_users.add(user_id)

    async def remove_blocked_user(self, user_id: str) -> bool:
        """Remove a user from block list."""
        if user_id in self._blocked_users:
            self._blocked_users.remove(user_id)
            return True
        return False

    async def set_message_filter(self, pattern: str) -> bool:
        """Set message filter regex."""
        try:
            self._message_filters = []
            if pattern:
                self._message_filters.append(re.compile(pattern))
            logger.info(f"Message filter set: {pattern or 'none'}")
            return True
        except re.error as e:
            logger.error(f"Invalid regex: {e}")
            return False

    async def get_qr_code(self, account_id: str) -> str | None:
        """Get QR code path for login."""
        if account_id not in self.accounts:
            return None
        account = self.accounts[account_id]
        backend = self._get_backend(account_id)
        if backend and account.status == "logging_in":
            return backend.get_qr_code()
        return None

    def get_tools(self) -> list[dict[str, Any]]:
        """Return tool definitions."""
        return [{
            "name": "weixin_send",
            "description": "Send a WeChat message via connected account",
            "parameters": {
                "type": "object",
                "properties": {
                    "to_user": {
                        "type": "string",
                        "description": "Recipient (username or group)"
                    },
                    "message": {
                        "type": "string",
                        "description": "Message content"
                    },
                    "msg_type": {
                        "type": "string",
                        "enum": ["text", "image", "voice", "file", "video"],
                        "description": "Message type",
                        "default": "text"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to file (for non-text messages)"
                    },
                    "account_id": {
                        "type": "string",
                        "description": "Account to use (default: first active)"
                    }
                },
                "required": ["to_user", "message"]
            }
        }, {
            "name": "weixin_login",
            "description": "Login (connect) a WeChat account",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "string",
                        "description": "Account ID to login"
                    }
                },
                "required": ["account_id"]
            }
        }, {
            "name": "weixin_receive",
            "description": "Receive pending WeChat messages",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "string",
                        "description": "Account ID (default: all active)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max messages to return",
                        "default": 100
                    }
                }
            }
        }, {
            "name": "weixin_list_accounts",
            "description": "List all configured WeChat accounts",
            "parameters": {"type": "object", "properties": {}}
        }]

    async def execute(self, action: str, **kwargs) -> Any:
        """Execute actions."""
        actions = {
            "connect": self.connect,
            "disconnect": self.disconnect,
            "send": self.send,
            "receive": self.receive,
            "list_accounts": self.list_accounts,
            "get_contacts": self.get_contacts,
            "get_groups": self.get_groups,
            "toggle_auto_reply": self.toggle_auto_reply,
            "add_blocked_user": self.add_blocked_user,
            "remove_blocked_user": self.remove_blocked_user,
            "set_message_filter": self.set_message_filter,
            "get_qr_code": self.get_qr_code
        }

        if action not in actions:
            raise ValueError(f"Unknown action: {action}")

        method = actions[action]
        return await method(**kwargs)

    async def health_check(self) -> dict[str, Any]:
        """Return plugin health status."""
        status = await super().health_check()
        status["accounts"] = len(self.accounts)
        status["active_accounts"] = sum(1 for acc in self.accounts.values() if acc.status == "active")
        status["backends_loaded"] = list(self.backends.keys())
        status["auto_reply"] = self._auto_reply_enabled
        return status
