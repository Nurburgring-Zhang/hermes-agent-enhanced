# OpenClaw Weixin Plugin

WeChat channel adapter for Hermes with multi-account support.

## Features

- **Multiple Backend Support**: itchat (all platforms), wxauto (Windows)
- **Multi-Account**: Manage multiple WeChat accounts
- **Message Types**: Text, image, voice, file, video, location, card
- **Group & Private**: Full support for both group and individual chats
- **Auto-Reply**: Simple keyword or mention-based auto-reply
- **Message Filtering**: Skip unwanted messages via regex
- **File Handling**: Download and cache media files
- **Event Hooks**: Emit events for incoming messages

## Installation

1. Place plugin in `~/.hermes/plugins/openclaw-weixin/`
2. Install dependencies: `pip install -r requirements.txt`
3. Create accounts file (see below)
4. Enable: `/plugin_enable openclaw-weixin`
5. Start: `/plugin_start openclaw-weixin`

## Account Configuration

Create `accounts.json` in the plugin directory:

```json
{
  "accounts": [
    {
      "id": "personal",
      "name": "Personal Account",
      "backend": "itchat",
      "auto_login": true,
      "qr_path": "./qr.png",
      "qr_callback": null,
      "status": "inactive"
    }
  ]
}
```

Fields:
- `id`: Unique account identifier
- `name`: Display name
- `backend`: "itchat" or "wxauto"
- `auto_login`: Auto-login on plugin start
- `qr_path`: Where to save QR code for scanning
- `qr_callback`: Optional URL to send QR to
- `status`: Current status (inactive, logging_in, active, error)

## Usage

### Scrape QR Code and login
```
# Login with QR code (QR saved to file)
/weixin_login <account_id>
```

### Check status
```
/weixin_status
```

### Send message
```
/weixin_send <to_username> <message> [--account <id>]
```

### Group operations
```
/weixin_groups          # List all groups
/weixin_group_members <group_id>
```

### Auto-reply toggle
```
/weixin_autoreply [on|off]
```

## Channel Interface

The plugin implements the Hermes channel interface:

```python
plugin = manager.get_plugin("openclaw-weixin")

# Connect account
await plugin.execute("connect", account_id="personal")

# Send message
await plugin.execute("send",
    to_user="username",
    message="Hello!",
    msg_type="text"
)

# Receive messages (returns list)
messages = await plugin.execute("receive", account_id="personal", limit=10)

# Disconnect
await plugin.execute("disconnect", account_id="personal")
```

## Message Types Supported

- `text`: Plain text
- `image`: Image (with file path or URL)
- `voice`: Voice message (audio file)
- `file`: General file attachment
- `video`: Video file
- `location`: Geographic location
- `card`: Contact card/vCard

## Event Hooks

The plugin emits these events:

- `message.receive`: When a message is received
  - Event data: `{"account_id", "msg_type", "from_user", "content", "is_group", "raw"}`

## Message Flow

1. **Receive**: WeChat backend receives message
2. **Filter**: Apply regex filter if configured
3. **Parse**: Extract content and metadata
4. **Emit**: Publish `message.receive` event
5. **Auto-Reply**: If enabled and matching criteria, send reply
6. **Cache**: Store file attachments in cache directory

## Dependencies

- `itchat`: Cross-platform Web WeChat protocol (may be unstable)
- `wxauto`: Windows native WeChat protocol (requires WeChat installed)
- `aiohttp`: Async HTTP for file transfers
- `Pillow`: Image processing

## Troubleshooting

**QR code timeout**: Increase `qr_timeout` in config

**Login failed**: Ensure you have WeChat app and are not banned. Web WeChat may be restricted.

**wxauto not working**: Requires Windows + WeChat desktop app. Run as same user.

**No messages received**: Check `auto_reply` and `message_filter` settings.

**Files not downloading**: Check `file_cache_dir` permissions.

## Security Notes

- Account credentials are stored in plain text - secure your server
- QR codes are saved to disk - secure the directory
- Be cautious with auto-reply to avoid spam
- Understand WeChat's terms of service

## License

MIT
