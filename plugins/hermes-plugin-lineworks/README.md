# Hermes LINE WORKS Platform Plugin

Hermes Agent gateway platform plugin for **LINE WORKS** (Works Mobile), aligned with the npm package [`@unayung/lineworks@0.5.5`](https://www.npmjs.com/package/@unayung/lineworks).

This is a Hermes-native Python plugin, not the OpenClaw TypeScript package.

## Features

- inbound LINE WORKS bot webhooks at `/lineworks/webhook`
- `X-WORKS-Signature` HMAC-SHA256 verification
- service-account JWT bearer auth via `https://auth.worksmobile.com/oauth2/v2.0/token`
- access-token cache with refresh skew + single-flight lock per account
- inbound text, image, file, sticker, location, postback normalization
- image/file download into local temp files so Hermes vision/document tools can see them
- outbound text, image URL, local image upload, file upload
- rich outbound directives compatible with npm 0.5.5:
  - `[[flex: <altText> ||| <JSON>]]`
  - `[[location: <title> | <address> | <lat> | <lng>]]`
  - `[[quick_replies: Label, More > https://example.com, Payload > data:x=1]]`
- multi-account config compatible with the OpenClaw plugin style
- optional group mention gate
- optional sender profile enrichment via Directory API (`user.profile.read`)
- Hermes tools for official LINE WORKS REST APIs:
  - `lineworks_calendar` — list/create calendar events (`calendar`, `calendar.read`)
  - `lineworks_task` — list/create/update/complete/reopen tasks (`task`, `task.read`)
  - `lineworks_drive` — list folders, download, create upload URL, upload files (`file`, `file.read`)

## Install

Local checkout:

```bash
hermes plugins install /absolute/path/to/hermes-plugin-lineworks
hermes gateway restart
```

From GitHub once published:

```bash
hermes plugins install https://github.com/Unayung/hermes-plugin-lineworks.git
hermes gateway restart
```

For pip distribution, this package exposes the Hermes entry point:

```toml
[project.entry-points."hermes_agent.plugins"]
lineworks = "lineworks_platform"
```

## LINE WORKS Developer Console

In <https://developers.worksmobile.com/console/>:

1. create an app
2. issue a Service Account and download the PKCS#8 PEM private key
3. grant scopes:
   - `bot` — send messages
   - `bot.read` — download bot attachments
   - `user.profile.read` — optional, sender profile enrichment
   - `calendar`, `calendar.read` — calendar tool
   - `task`, `task.read` — task tool
   - `file`, `file.read` — Drive tool
4. create a bot and copy Bot ID + Bot Secret
5. enable callback events, at minimum:
   - `message.text`
   - `message.image`
   - `message.file` optional
   - `message.sticker`, `message.location`, `postback` optional
6. set callback URL:

```text
https://<your-gateway-host>/lineworks/webhook
```

Hermes must be publicly reachable: VPS reverse proxy, Cloudflare Tunnel, Tailscale Funnel, or ngrok.

## Configure Hermes

Minimal `~/.hermes/config.yaml`:

```yaml
gateway:
  platforms:
    lineworks:
      enabled: true
      extra:
        port: 3981
        client_id: "<app client ID>"
        client_secret: "<app client secret>"
        service_account: "<uuid>.serviceaccount@<domain>"
        private_key_file: "/home/you/.hermes/keys/lineworks.pem"
        bot_id: "<bot ID>"
        bot_secret: "<bot secret>"
        domain_id: "<domain ID>"          # optional
        dm_policy: "pairing"              # open | allowlist | pairing | disabled
        group_policy: "allowlist"         # open | allowlist | disabled
        group_require_mention: true
        bot_mention_handle: "Hermes"
        sender_profile_enrichment: true
```

CamelCase aliases from the npm/OpenClaw config are also accepted (`clientId`, `privateKeyFile`, `groupRequireMention`, etc.).

Env fallback:

```bash
LINEWORKS_CLIENT_ID=...
LINEWORKS_CLIENT_SECRET=...
LINEWORKS_SERVICE_ACCOUNT=...
LINEWORKS_PRIVATE_KEY_FILE=/home/you/.hermes/keys/lineworks.pem
LINEWORKS_BOT_ID=...
LINEWORKS_BOT_SECRET=...
LINEWORKS_DOMAIN_ID=...
LINEWORKS_PORT=3981
```

`private_key_file` is strongly preferred. Inline PEMs inside YAML/JSON love to get mangled. ask me how i know. actually don't.

## Multiple accounts

```yaml
gateway:
  platforms:
    lineworks:
      enabled: true
      extra:
        port: 3981
        accounts:
          main:
            client_id: "..."
            client_secret: "..."
            service_account: "..."
            private_key_file: "/home/you/.hermes/keys/main.pem"
            bot_id: "..."
            bot_secret: "..."
          support:
            client_id: "..."
            client_secret: "..."
            service_account: "..."
            private_key_file: "/home/you/.hermes/keys/support.pem"
            bot_id: "..."
            bot_secret: "..."
            webhook_path: "/lineworks/support/webhook"
```

## Send targets

Inbound messages use Hermes chat IDs:

- DMs: `user:<lineworks-user-id>`
- groups/channels: `channel:<lineworks-channel-id>`

Examples:

```text
send_message(target="lineworks:user:abc123", message="hello")
send_message(target="lineworks:channel:room123", message="hello group")
```

## Agent tools

After the plugin is loaded, Hermes registers these tool calls:

```text
lineworks_calendar(action="list", user_id="...", start="2026-05-01T00:00:00+09:00", end="2026-05-31T23:59:59+09:00")
lineworks_calendar(action="create", user_id="...", event={...})
lineworks_task(action="list", user_id="...", status="TODO")
lineworks_task(action="create", user_id="...", task={...})
lineworks_task(action="complete", task_id="...")
lineworks_drive(action="list", user_id="...", file_id="root")
lineworks_drive(action="download", user_id="...", file_id="...", output_path="/tmp/file")
lineworks_drive(action="upload", user_id="...", parent_file_id="root", file_path="/tmp/file.pdf")
```

Calendar list follows LINE WORKS' 31-day window limit. Drive download handles the 302/`Location` flow; upload creates an upload URL then posts multipart `FileData` to storage.

## Development / verification

```bash
PYTHONPATH=/home/unayung/.hermes/hermes-agent:. python -m pytest tests -q
python -m pip wheel . -w /tmp/hermes-plugin-lineworks-dist --no-deps
```

Current verification:

- `9 passed`
- wheel builds: `hermes_plugin_lineworks-0.5.5-py3-none-any.whl`
- Hermes plugin scan detects `('lineworks', 'platform', 'lineworks', '/home/unayung/Projects/hermes-plugin-lineworks')` when scanning a plugins root/parent directory

## Known gaps vs OpenClaw npm 0.5.5

Hermes platform plugins do not expose the exact OpenClaw ChannelPlugin SDK surface, so these are not 1:1 ports yet:

- user OAuth consent routes / token store (only needed for endpoints that reject service-account access)
- mail higher-level tools
- `[[mail_send: ...]]` directive execution
- Thinking ack delayed placeholder message

The core messaging channel is aligned: auth, webhook verification, multi-account, inbound media, sender profile enrichment, rich outbound directives, and attachment upload/download.
