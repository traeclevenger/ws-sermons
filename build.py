#!/usr/bin/env python3
"""
Build index.html from data/sermons.json.
Run from the ws-sermons repo root: python3 build.py

After deploying the Apps Script web app, paste its URL here:
"""

import json
from pathlib import Path

REPO_DIR = Path(__file__).parent
SERMONS_JSON = REPO_DIR / "data" / "sermons.json"

# Paste your deployed Apps Script web app URL here
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyopzDyAKaarp3KUxtU7JXEvEYdEs_QBLatKMsSHo-IBZ3v9PNaJjd5l5t9JYniOUHwbg/exec"

with open(SERMONS_JSON) as f:
    sermons = json.load(f)

# ── Build SERMONS JS array ─────────────────────────��───────────────────────────
def js_str(s):
    if s is None:
        return "null"
    return json.dumps(str(s))

rows = []
for s in sermons:
    chunks_js = []
    for c in s.get("chunks", []):
        emb = c.get("embedding", [])
        emb_js = f"new Float32Array([{','.join(str(v) for v in emb)}])" if emb else "null"
        chunks_js.append(
            "{"
            f"text:{js_str(c['text'])},"
            f"emb:{emb_js}"
            "}"
        )
    rows.append(
        "{"
        f"date:{js_str(s['date'])},"
        f"title:{js_str(s['title'])},"
        f"speaker:{js_str(s['speaker'])},"
        f"audioUrl:{js_str(s['audio_url'])},"
        f"docUrl:{js_str(s.get('doc_url'))},"
        f"chunks:[{','.join(chunks_js)}]"
        "}"
    )

sermons_js = "const SERMONS = [\n  " + ",\n  ".join(rows) + "\n];"
apps_script_js = f"const APPS_SCRIPT_URL = {js_str(APPS_SCRIPT_URL)};"

# Lightweight index for Claude's catalogue awareness (no embeddings/text)
index_rows = [
    f"{{date:{js_str(s['date'])},title:{js_str(s['title'])},speaker:{js_str(s['speaker'])},audioUrl:{js_str(s['audio_url'])}}}"
    for s in sermons
]
sermon_index_js = "const SERMON_INDEX = [\n  " + ",\n  ".join(index_rows) + "\n];"

print(f"Building index.html with {len(sermons)} sermons, "
      f"{sum(len(s.get('chunks',[])) for s in sermons)} total chunks")
if not APPS_SCRIPT_URL:
    print("  Note: APPS_SCRIPT_URL is empty — configure it in build.py")

# ── HTML template ─────────────────────────────────────────────────────────────
html = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>Westside Sermons</title>
<link rel="icon" type="image/png" href="WS favicon.png">
<style>
  :root {
    --bg: #0d1210; --surface: #141c18; --surface2: #1d2820;
    --accent: #96aa9e; --accent2: #6a7e72;
    --text: #eaedea; --subtext: #7a9082; --border: #2a3830;
    --radius: 14px; --header-h: 96px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; }
  body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; display: flex; flex-direction: column; }

  header {
    background: #fff; border-bottom: 1px solid #d8d8d8;
    padding: 14px 20px 12px; flex-shrink: 0;
    box-shadow: 0 2px 12px rgba(0,0,0,0.12);
    display: flex; align-items: center; justify-content: center;
  }
  .site-logo { height: 80px; width: auto; display: block; }

  .page-title {
    text-align: center; padding: 16px 0 4px;
    font-size: 1.25rem; font-weight: 700; color: var(--accent);
    letter-spacing: 0.03em; flex-shrink: 0;
  }

  .chat-wrap {
    flex: 1; overflow: hidden; display: flex; flex-direction: column;
    max-width: 800px; width: 100%; margin: 0 auto; padding: 0 16px;
  }

  .chat-messages {
    flex: 1; overflow-y: auto; padding: 20px 0 12px;
    display: flex; flex-direction: column; gap: 14px;
  }
  .chat-messages::-webkit-scrollbar { width: 4px; }
  .chat-messages::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

  .msg { display: flex; flex-direction: column; max-width: 82%; }
  .msg.user { align-self: flex-end; align-items: flex-end; }
  .msg.assistant { align-self: flex-start; align-items: flex-start; }
  .msg-bubble {
    padding: 11px 15px; border-radius: 18px; font-size: 0.9rem; line-height: 1.65;
    white-space: pre-wrap; word-break: break-word;
  }
  .msg.user .msg-bubble { background: var(--accent2); color: #fff; border-bottom-right-radius: 4px; }
  .msg.assistant .msg-bubble { background: var(--surface); border: 1px solid var(--border); color: var(--text); border-bottom-left-radius: 4px; }
  .msg-typing .msg-bubble { color: var(--subtext); font-style: italic; }

  .msg-sources { margin-top: 6px; display: flex; flex-wrap: wrap; gap: 4px; }
  .source-chip {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 4px 9px; background: rgba(150,170,158,0.1); border: 1px solid var(--border);
    border-radius: 7px; font-size: 0.74rem; color: var(--accent); text-decoration: none;
    transition: all 0.15s;
  }
  .source-chip:hover { background: rgba(150,170,158,0.2); border-color: var(--accent2); }

  .chat-hint { font-size: 0.72rem; color: var(--subtext); text-align: center; padding: 4px 0 2px; min-height: 1.2em; }

  .chat-input-wrap {
    display: flex; gap: 8px; padding: 10px 0 32px;
    border-top: 1px solid var(--border);
  }
  #askInput {
    flex: 1; padding: 11px 14px; background: var(--surface); border: 1px solid var(--border);
    border-radius: 12px; color: var(--text); font-size: 0.9rem; outline: none;
    transition: border-color 0.2s; resize: none; min-height: 44px; max-height: 140px;
    font-family: inherit; line-height: 1.4;
  }
  #askInput:focus { border-color: var(--accent2); }
  #askInput::placeholder { color: var(--subtext); }
  #askBtn, #newChatBtn {
    width: 44px; height: 44px; flex-shrink: 0; align-self: flex-end;
    border: none; border-radius: 12px; cursor: pointer;
    transition: background 0.15s; display: flex; align-items: center; justify-content: center;
  }
  #askBtn { background: var(--accent2); color: #fff; }
  #askBtn:hover:not(:disabled) { background: var(--accent); }
  #askBtn:disabled { opacity: 0.4; cursor: not-allowed; }
  #newChatBtn { background: var(--surface2); color: var(--subtext); font-size: 1.4rem; line-height: 1; }
  #newChatBtn:hover { background: var(--border); color: var(--text); }

  @media (max-width: 600px) {
    header { padding: 10px 14px; }
    .site-logo { height: 60px; }
    .chat-wrap { padding: 0 12px; }
  }
</style>
</head>
<body>

<header>
  <img src="WS logo.png" alt="Westside church of Christ" class="site-logo">
</header>

<div class="page-title">Sermon Search</div>

<div class="chat-wrap">
  <div class="chat-messages" id="chatMessages"></div>
  <div class="chat-hint" id="chatHint"></div>
  <div class="chat-input-wrap">
    <textarea id="askInput" rows="1" placeholder="Ask about any sermon, or ask what's available…"></textarea>
    <button id="newChatBtn" onclick="newChat()" title="New Conversation">+</button>
    <button id="askBtn" onclick="submitQuestion()" title="Send">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22,2 15,22 11,13 2,9"/></svg>
    </button>
  </div>
</div>

<script>
SERMONS_DATA_PLACEHOLDER
SERMON_INDEX_PLACEHOLDER
APPS_SCRIPT_URL_PLACEHOLDER

const TRANSFORMERS_CDN = 'https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.2';
const EMBED_MODEL = 'Xenova/all-MiniLM-L6-v2';
const SEMANTIC_THRESHOLD = 0.30;
const ASK_TOP_CHUNKS = 8;

let semanticReady = false, semanticLoading = false, embedFn = null;
let conversationHistory = [];

const audioIcon = `<svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><polygon points="5,3 19,12 5,21"/></svg>`;

function esc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function setHint(msg) { document.getElementById('chatHint').textContent = msg; }

function cosineSim(a, b) {
  let dot = 0; for (let i = 0; i < a.length; i++) dot += a[i] * b[i]; return dot;
}

async function loadSemanticModel() {
  if (semanticReady || semanticLoading) return;
  semanticLoading = true;
  setHint('Loading semantic model… (first time only, ~22 MB)');
  try {
    const { pipeline } = await import(`${TRANSFORMERS_CDN}/dist/transformers.min.js`);
    const pipe = await pipeline('feature-extraction', EMBED_MODEL, { quantized: true });
    embedFn = async (text) => {
      const out = await pipe(text, { pooling: 'mean', normalize: true });
      return new Float32Array(out.data);
    };
    semanticReady = true;
    setHint('');
  } catch(e) {
    setHint('Semantic model unavailable — answers may be less precise');
    semanticLoading = false;
  }
}

async function getTopChunks(question) {
  if (!embedFn) return [];
  const queryVec = await embedFn(question);
  const allChunks = [];
  for (const sermon of SERMONS) {
    for (const chunk of sermon.chunks) {
      if (!chunk.emb) continue;
      allChunks.push({
        sim: cosineSim(queryVec, chunk.emb),
        payload: { text: chunk.text, sermon_title: sermon.title, date: sermon.date, speaker: sermon.speaker, audio_url: sermon.audioUrl }
      });
    }
  }
  return allChunks.sort((a, b) => b.sim - a.sim).slice(0, ASK_TOP_CHUNKS).map(x => x.payload);
}

function newChat() {
  conversationHistory = [];
  document.getElementById('chatMessages').innerHTML = '';
  setHint('');
  document.getElementById('askInput').focus();
}

function appendMessage(role, content, sources) {
  const el = document.createElement('div');
  el.className = `msg ${role}`;
  const sourcesHtml = (sources && sources.length)
    ? `<div class="msg-sources">${sources.map(s =>
        `<a class="source-chip" href="${esc(s.audio_url)}" target="_blank" rel="noopener">
          ${audioIcon} ${esc(s.title)} <span style="opacity:0.6">${esc(s.date)}</span>
        </a>`).join('')}</div>`
    : '';
  el.innerHTML = `<div class="msg-bubble">${esc(content)}</div>${sourcesHtml}`;
  document.getElementById('chatMessages').appendChild(el);
  el.scrollIntoView({ behavior: 'smooth', block: 'end' });
  return el;
}

function appendTyping() {
  const el = document.createElement('div');
  el.className = 'msg assistant msg-typing';
  el.innerHTML = '<div class="msg-bubble">Thinking…</div>';
  document.getElementById('chatMessages').appendChild(el);
  el.scrollIntoView({ behavior: 'smooth', block: 'end' });
  return el;
}

async function submitQuestion() {
  const input = document.getElementById('askInput');
  const question = input.value.trim();
  if (!question) return;

  input.value = '';
  input.style.height = 'auto';
  document.getElementById('askBtn').disabled = true;

  appendMessage('user', question);
  conversationHistory.push({ role: 'user', content: question });

  const typingEl = appendTyping();

  try {
    if (!semanticReady) {
      setHint('Loading semantic model…');
      await loadSemanticModel();
      setHint('');
    }
    const chunks = await getTopChunks(question);
    const claudeMessages = conversationHistory.map(m => ({ role: m.role, content: m.content }));

    const res = await fetch(APPS_SCRIPT_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain' },
      body: JSON.stringify({ messages: claudeMessages, chunks, sermonIndex: SERMON_INDEX }),
    });

    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    typingEl.remove();
    appendMessage('assistant', data.answer, data.sources);
    conversationHistory.push({ role: 'assistant', content: data.answer });

  } catch (err) {
    typingEl.remove();
    appendMessage('assistant', `Sorry, something went wrong: ${err.message}`);
  } finally {
    document.getElementById('askBtn').disabled = false;
    input.focus();
  }
}

document.getElementById('askInput').addEventListener('input', function() {
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 140) + 'px';
  if (this.value.trim() && !semanticReady && !semanticLoading) loadSemanticModel();
});

document.getElementById('askInput').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitQuestion(); }
});

document.getElementById('askInput').focus();
</script>
</body>
</html>"""

html = html.replace('SERMONS_DATA_PLACEHOLDER', sermons_js)
html = html.replace('SERMON_INDEX_PLACEHOLDER', sermon_index_js)
html = html.replace('APPS_SCRIPT_URL_PLACEHOLDER', apps_script_js)

out = REPO_DIR / "index.html"
out.write_text(html, encoding="utf-8")
print(f"Written → {out}  ({out.stat().st_size // 1024} KB)")
