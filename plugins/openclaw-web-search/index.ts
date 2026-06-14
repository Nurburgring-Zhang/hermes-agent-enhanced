import { readFile, access } from "node:fs/promises";
import { execSync } from "node:child_process";
import { homedir, release } from "node:os";
import { join } from "node:path";
import { createPrivateKey, sign as cryptoSign } from "node:crypto";

const WEB_SEARCH_API = "https://ollama.com/api/web_search";
const MAX_RESULTS = 5;
const TIMEOUT_MS = 15_000;

interface KeyPair {
  privateKey: ReturnType<typeof createPrivateKey>;
  pubBase64: string;
}

function isWSL(): boolean {
  return release().toLowerCase().includes("microsoft");
}

function windowsOllamaKeyPath(): string | null {
  try {
    const raw = execSync('cmd.exe /C "echo %USERPROFILE%" 2>/dev/null', {
      encoding: "utf-8",
      timeout: 5000,
    }).trim();
    const posix = raw
      .replace(/\\/g, "/")
      .replace(/^([A-Za-z]):/, (_, d: string) => `/mnt/${d.toLowerCase()}`);
    return join(posix, ".ollama", "id_ed25519");
  } catch {
    return null;
  }
}

let _cachedKeyPath: string | null = null;

async function resolveKeyPath(): Promise<string | null> {
  if (_cachedKeyPath) return _cachedKeyPath;

  const nativePath = join(homedir(), ".ollama", "id_ed25519");

  if (isWSL()) {
    // On WSL, prefer the Windows-side key (registered with ollama.com)
    // and fall back to the native WSL key.
    const winPath = windowsOllamaKeyPath();
    if (winPath) {
      try {
        await access(winPath);
        _cachedKeyPath = winPath;
        return _cachedKeyPath;
      } catch {}
    }
  }

  try {
    await access(nativePath);
    _cachedKeyPath = nativePath;
    return _cachedKeyPath;
  } catch {}

  return null;
}

async function loadKey(): Promise<KeyPair | null> {
  const keyPath = await resolveKeyPath();
  if (!keyPath) return null;
  try {
    const pem = await readFile(keyPath, "utf-8");
    const lines = pem.split("\n").filter((l) => !l.startsWith("-----") && l.trim());
    const der = Buffer.from(lines.join(""), "base64");

    const magic = "openssh-key-v1\0";
    let offset = magic.length;
    const readBuf = (): Buffer => {
      const len = der.readUInt32BE(offset);
      offset += 4;
      const data = der.subarray(offset, offset + len);
      offset += len;
      return data;
    };

    readBuf(); // ciphername
    readBuf(); // kdfname
    readBuf(); // kdfoptions
    offset += 4; // nkeys
    readBuf(); // public key blob (must be read before private section)
    const privBlob = readBuf(); // private section

    // Parse private section: 2x uint32 checkint, keytype, pubkey(32), privkey(64), comment
    let po = 8; // skip checkints
    const readPrivBuf = (): Buffer => {
      const len = privBlob.readUInt32BE(po);
      po += 4;
      const data = privBlob.subarray(po, po + len);
      po += len;
      return data;
    };
    readPrivBuf();
    const pubkey = readPrivBuf();
    const privkey = readPrivBuf();

    const seed = privkey.subarray(0, 32);
    const pkcs8Prefix = Buffer.from("302e020100300506032b657004220420", "hex");
    const pkcs8 = Buffer.concat([pkcs8Prefix, seed]);
    const privateKey = createPrivateKey({ key: pkcs8, format: "der", type: "pkcs8" });

    const keyType = Buffer.from("ssh-ed25519");
    const sshPub = Buffer.alloc(4 + keyType.length + 4 + pubkey.length);
    sshPub.writeUInt32BE(keyType.length, 0);
    keyType.copy(sshPub, 4);
    sshPub.writeUInt32BE(pubkey.length, 4 + keyType.length);
    pubkey.copy(sshPub, 4 + keyType.length + 4);

    return { privateKey, pubBase64: sshPub.toString("base64") };
  } catch {
    return null;
  }
}

async function buildAuthHeader(requestURI: string): Promise<string | null> {
  const key = await loadKey();
  if (!key) return null;
  const payload = Buffer.from(`POST,${requestURI}`);
  const sig = cryptoSign(null, payload, key.privateKey);
  return `Bearer ${key.pubBase64}:${sig.toString("base64")}`;
}

async function executeOllamaWebSearch(
  _toolCallId: string,
  params: { query: string },
  signal?: AbortSignal,
) {
  const query = params.query?.trim();
  if (!query) {
    throw new Error("query parameter is required");
  }

  const url = new URL(WEB_SEARCH_API);
  const ts = Math.floor(Date.now() / 1000).toString();
  url.searchParams.set("ts", ts);

  const requestURI = `${url.pathname}?${url.searchParams.toString()}`;
  const authHeader = await buildAuthHeader(requestURI);
  if (!authHeader) {
    throw new Error(
      "Web search requires authentication. Ensure ~/.ollama/id_ed25519 exists.",
    );
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);
  if (signal) {
    signal.addEventListener("abort", () => controller.abort(), { once: true });
  }

  let response: Response;
  try {
    response = await fetch(url.toString(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: authHeader,
      },
      body: JSON.stringify({ query, max_results: MAX_RESULTS }),
      signal: controller.signal,
    });
  } catch (err) {
    if ((err as Error).name === "AbortError") {
      throw new Error(`Web search timed out after ${TIMEOUT_MS}ms`);
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }

  if (response.status === 401) {
    throw new Error("Web search authentication failed. Your Ollama key may be invalid. Make sure you are signed into ollama with ollama signin");
  }
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`Web search failed (${response.status}): ${body}`);
  }

  const data = (await response.json()) as {
    results: { title: string; url: string; content: string }[];
  };

  if (!data.results?.length) {
    return { content: [{ type: "text" as const, text: `No results for: ${query}` }] };
  }

  const text = data.results
    .map(
      (r, i) =>
        `${i + 1}. ${r.title}\n   ${r.url}\n   ${r.content?.length > 300 ? r.content.slice(0, 300) + "..." : r.content}`,
    )
    .join("\n\n");

  return { content: [{ type: "text" as const, text }] };
}

const ollamaWebSearchPlugin = {
  id: "openclaw-web-search",
  name: "Ollama Web Search",
  description: "Web search via ollama.com API",
  configSchema: { parse: (v: unknown) => v ?? {} },
  register(api: any) {
    api.registerTool({
      name: "ollama_web_search",
      label: "Ollama Web Search",
      description:
        "Search the web for current information using Ollama's search API.",
      parameters: {
        type: "object",
        properties: {
          query: { type: "string", description: "The search query" },
        },
        required: ["query"],
      },
      execute: executeOllamaWebSearch,
    } as any);
  },
};

export default ollamaWebSearchPlugin;
