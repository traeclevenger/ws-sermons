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
    --radius: 14px; --header-h: 68px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; height: 100dvh; }
  body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; display: flex; flex-direction: column; }

  header {
    background: #fff; border-bottom: 1px solid #d8d8d8;
    padding: 16px 24px 14px; flex-shrink: 0;
    box-shadow: 0 2px 12px rgba(0,0,0,0.12);
    display: flex; align-items: center; justify-content: flex-start;
  }
  .site-logo { height: 64px; width: auto; display: block; }

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
  .msg-bubble ul { padding-left: 1.4em; margin: 4px 0; }
  .msg-bubble li { margin: 2px 0; }

  .msg-sources { margin-top: 6px; display: flex; flex-wrap: wrap; gap: 4px; }
  .source-chip {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 4px 9px; background: rgba(150,170,158,0.1); border: 1px solid var(--border);
    border-radius: 7px; font-size: 0.74rem; color: var(--accent); text-decoration: none;
    transition: all 0.15s;
  }
  .source-chip:hover { background: rgba(150,170,158,0.2); border-color: var(--accent2); }
  .extra-toggle {
    margin-top: 6px; background: none; border: none; cursor: pointer;
    font-size: 0.75rem; color: var(--subtext); padding: 2px 0;
    display: flex; align-items: center; gap: 4px;
  }
  .extra-toggle:hover { color: var(--accent); }
  .extra-toggle svg { transition: transform 0.2s; }
  .extra-toggle.open svg { transform: rotate(180deg); }
  .extra-body { display: none; }
  .extra-body.open { display: block; }

  .sermon-table { margin-top: 10px; border-collapse: collapse; font-size: 0.82rem; width: 100%; table-layout: auto; }
  .sermon-table th { text-align: left; padding: 5px 10px; color: var(--subtext); border-bottom: 1px solid var(--border); font-weight: 600; white-space: nowrap; }
  .sermon-table td { padding: 5px 10px; border-bottom: 1px solid rgba(42,56,48,0.5); }
  .sermon-table td:first-child { white-space: nowrap; word-break: normal; width: 1%; }
  .sermon-table a { color: var(--accent); text-decoration: none; }
  .sermon-table a:hover { text-decoration: underline; }

  .chat-hint { font-size: 0.72rem; color: var(--subtext); text-align: center; padding: 4px 0 2px; min-height: 1.2em; }

  .chat-input-wrap {
    display: flex; gap: 8px; padding: 10px 0 64px;
    padding-bottom: max(64px, calc(32px + env(safe-area-inset-bottom)));
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
  #askBtn, #newChatBtn, #micBtn {
    width: 44px; height: 44px; flex-shrink: 0; align-self: flex-end;
    border: none; border-radius: 12px; cursor: pointer;
    transition: background 0.15s; display: flex; align-items: center; justify-content: center;
  }
  #askBtn { background: var(--accent2); color: #fff; }
  #askBtn:hover:not(:disabled) { background: var(--accent); }
  #askBtn:disabled { opacity: 0.4; cursor: not-allowed; }
  #newChatBtn { background: var(--surface2); color: var(--subtext); font-size: 1.4rem; line-height: 1; }
  #newChatBtn:hover { background: var(--border); color: var(--text); }
  #micBtn { background: var(--surface2); color: var(--subtext); display: none; }
  #micBtn:hover { background: var(--border); color: var(--text); }
  #micBtn.listening { background: #c0392b; color: #fff; animation: pulse 1s infinite; }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.6; } }

  @media (max-width: 600px) {
    header { padding: 10px 16px; }
    .site-logo { height: 48px; }
    .chat-wrap { padding: 0 12px; }
    .page-title { font-size: 1.35rem; padding: 12px 0 4px; }
    .msg { max-width: 92%; }
    .msg-bubble { font-size: 0.88rem; }
    #askInput { font-size: 1rem; }
  }
</style>
</head>
<body>

<header>
  <img src="WS logo.png" alt="Westside church of Christ" class="site-logo">
</header>

<div class="chat-wrap">
  <div class="chat-messages" id="chatMessages"></div>
  <div class="chat-hint" id="chatHint"></div>
  <div class="chat-input-wrap">
    <textarea id="askInput" rows="1" placeholder="Ask about any sermon, or ask what's available…" data-placeholder-desktop="Ask about any sermon, or ask what's available…" data-placeholder-mobile="Ask about a sermon…"></textarea>
    <button id="micBtn" title="Speak your question">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.91-3c-.49 0-.9.36-.98.85C16.52 14.2 14.47 16 12 16s-4.52-1.8-4.93-4.15c-.08-.49-.49-.85-.98-.85-.61 0-1.09.54-1 1.14.49 3 2.89 5.35 5.91 5.78V19c0 .55.45 1 1 1s1-.45 1-1v-1.08c3.02-.43 5.42-2.78 5.91-5.78.1-.6-.39-1.14-1-1.14z"/></svg>
    </button>
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

function renderMarkdown(text) {
  const lines = esc(text).split('\n');
  const out = [];
  let inList = false;
  for (const line of lines) {
    const bullet = line.match(/^(\s*[-*]|\s*\d+\.)\s+(.*)/);
    if (bullet) {
      if (!inList) { out.push('<ul>'); inList = true; }
      out.push(`<li>${bullet[2]}</li>`);
    } else {
      if (inList) { out.push('</ul>'); inList = false; }
      out.push(line === '' ? '<br>' : `<span>${line}</span><br>`);
    }
  }
  if (inList) out.push('</ul>');
  return out.join('');
}

function setHint(msg) { document.getElementById('chatHint').textContent = msg; }

function toggleExtra(btn) {
  const open = btn.classList.toggle('open');
  btn.nextElementSibling.classList.toggle('open', open);
  const n = btn.dataset.count;
  const label = `${open ? 'Hide' : 'Show'} ${n} sermon${n != 1 ? 's' : ''}`;
  const svg = btn.querySelector('svg').outerHTML;
  btn.innerHTML = label + ' ' + svg;
}

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

  // For follow-up questions, augment the query with the last assistant reply
  const lastAssistant = [...conversationHistory].reverse().find(m => m.role === 'assistant');
  const augmentedQuery = lastAssistant
    ? question + ' ' + lastAssistant.content.slice(0, 300)
    : question;
  const queryVec = await embedFn(augmentedQuery);

  // Score each sermon against question text (weighted heavily) + assistant context (weak signal)
  const questionLower = question.toLowerCase();
  const assistantLower = lastAssistant ? lastAssistant.content.toLowerCase() : '';
  const searchText = questionLower + ' ' + assistantLower;
  const monthNames = ['january','february','march','april','may','june','july','august','september','october','november','december'];
  const sermonScoreMap = new Map();
  const titleScoreQMap = new Map();
  for (const s of SERMONS) {
    const words = s.title.toLowerCase().split(/\s+/).filter(w => w.length > 3);
    // Weight question matches 5x over assistant-context-only matches
    const titleScoreQ = words.length ? words.filter(w => questionLower.includes(w)).length / words.length : 0;
    const titleScoreA = words.length ? words.filter(w => !questionLower.includes(w) && assistantLower.includes(w)).length / words.length : 0;
    const titleScore = titleScoreQ * 1.0 + titleScoreA * 0.2;
    const sermonMonth = monthNames[parseInt(s.date.slice(5,7)) - 1];
    const dateBonus = searchText.includes(sermonMonth) ? 0.25 : 0;
    // Speaker bonus: strong if speaker named in the question, weak if only in assistant context
    const speakerLower = s.speaker.toLowerCase();
    const speakerBonus = questionLower.includes(speakerLower) ? 0.8
      : assistantLower.includes(speakerLower) ? 0.1 : 0;
    const score = titleScore + dateBonus + speakerBonus;
    if (score > 0) sermonScoreMap.set(s.title, score);
    titleScoreQMap.set(s.title, titleScoreQ);
  }

  // Positional reference detection: "the last one", "the first sermon", "that one", etc.
  // Fires when the user's question contains no title words (pronoun/positional reference)
  const noQuestionTitleMatch = [...titleScoreQMap.values()].every(v => v === 0);
  if (noQuestionTitleMatch && assistantLower) {
    // Find sermons mentioned in the last assistant reply, in order of appearance
    const mentioned = SERMONS
      .map(s => ({ title: s.title, pos: assistantLower.indexOf(s.title.toLowerCase()) }))
      .filter(s => s.pos >= 0)
      .sort((a, b) => a.pos - b.pos);
    if (mentioned.length > 0) {
      let target = null;
      if (/\blast\b/i.test(question))        target = mentioned[mentioned.length - 1].title;
      else if (/\bfirst\b/i.test(question))  target = mentioned[0].title;
      else if (/\bthird\b/i.test(question))  target = mentioned[2]?.title;
      else if (/\bsecond\b/i.test(question)) target = mentioned[1]?.title;
      else if (mentioned.length === 1)        target = mentioned[0].title;
      // "that one", "it", "the one" with only 1 sermon in context → same as single mention
      else if (/\b(that|this|the one)\b/i.test(question) && mentioned.length <= 3)
        target = mentioned[mentioned.length - 1].title;
      if (target) sermonScoreMap.set(target, (sermonScoreMap.get(target) || 0) + 1.5);
    }
  }

  const allChunks = [];
  for (const sermon of SERMONS) {
    for (const chunk of sermon.chunks) {
      if (!chunk.emb) continue;
      allChunks.push({
        sim: cosineSim(queryVec, chunk.emb),
        titleMatch: sermonScoreMap.has(sermon.title),
        payload: { text: chunk.text, sermon_title: sermon.title, date: sermon.date, speaker: sermon.speaker, audio_url: sermon.audioUrl }
      });
    }
  }

  // If one sermon is clearly the best match, send ALL its chunks for full outlines/summaries.
  // Use title score as gate, then semantic similarity as tiebreaker within tied groups.
  if (sermonScoreMap.size > 0) {
    // Compute average chunk cosine similarity per title-matched sermon
    const sermonAvgSim = new Map();
    for (const title of sermonScoreMap.keys()) {
      const chunks = allChunks.filter(c => c.payload.sermon_title === title);
      sermonAvgSim.set(title, chunks.reduce((s, c) => s + c.sim, 0) / (chunks.length || 1));
    }
    // Combined score: title match fraction + semantic similarity (weighted 3x)
    const combined = [...sermonScoreMap.entries()]
      .map(([title, tScore]) => ({ title, score: tScore + (sermonAvgSim.get(title) || 0) * 3 }))
      .sort((a, b) => b.score - a.score);
    const topScore = combined[0].score;
    const secondScore = combined[1]?.score ?? 0;
    if (topScore - secondScore >= 0.05) {
      const targetSermon = SERMONS.find(s => s.title === combined[0].title);
      return targetSermon.chunks
        .filter(c => c.emb)
        .map(c => ({ text: c.text, sermon_title: targetSermon.title, date: targetSermon.date, speaker: targetSermon.speaker, audio_url: targetSermon.audioUrl }));
    }
  }

  // Fall back: title-matched chunks first, then semantic fill
  const titleChunks = allChunks
    .filter(c => c.titleMatch)
    .sort((a, b) => b.sim - a.sim)
    .slice(0, ASK_TOP_CHUNKS);

  const seen = new Set(titleChunks.map(c => c.payload.text));
  const semanticChunks = allChunks
    .filter(c => !c.titleMatch && !seen.has(c.payload.text))
    .sort((a, b) => b.sim - a.sim)
    .slice(0, ASK_TOP_CHUNKS - titleChunks.length);

  return [...titleChunks, ...semanticChunks].map(c => c.payload);
}

function newChat() {
  conversationHistory = [];
  document.getElementById('chatMessages').innerHTML = '';
  setHint('');
  document.getElementById('askInput').focus();
}

function appendMessage(role, content, cited, listSermons) {
  const el = document.createElement('div');
  el.className = `msg ${role}`;
  let extraBody = '', count = 0;
  if (listSermons && listSermons.length) {
    count = listSermons.length;
    const rows = listSermons.map(s =>
      `<tr><td>${esc(s.date)}</td><td>${s.audio_url
        ? `<a href="${esc(s.audio_url)}" target="_blank" rel="noopener">${esc(s.title)}</a>`
        : esc(s.title)}</td></tr>`
    ).join('');
    extraBody = `<table class="sermon-table"><thead><tr><th>Date</th><th>Title</th></tr></thead><tbody>${rows}</tbody></table>`;
  } else if (cited && cited.length) {
    count = cited.length;
    extraBody = `<div class="msg-sources">${cited.map(s =>
      `<a class="source-chip" href="${esc(s.audio_url)}" target="_blank" rel="noopener">
        ${audioIcon} ${esc(s.title)} <span style="opacity:0.6">${esc(s.date)}</span>
      </a>`).join('')}</div>`;
  }
  const extra = count > 0
    ? `<button class="extra-toggle" data-count="${count}" onclick="toggleExtra(this)">Show ${count} sermon${count !== 1 ? 's' : ''} <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6,9 12,15 18,9"/></svg></button><div class="extra-body">${extraBody}</div>`
    : '';
  el.innerHTML = `<div class="msg-bubble">${role === 'assistant' ? renderMarkdown(content) : esc(content)}</div>${extra}`;
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
    console.log(`[chunks] sending ${chunks.length}${chunks[0] ? ' from: ' + chunks[0].sermon_title : ''}`);
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
    appendMessage('assistant', data.answer, data.cited_sermons, data.list_sermons);
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

const askInput = document.getElementById('askInput');
function updatePlaceholder() {
  askInput.placeholder = window.innerWidth <= 600
    ? askInput.dataset.placeholderMobile
    : askInput.dataset.placeholderDesktop;
}
updatePlaceholder();
window.addEventListener('resize', updatePlaceholder);
askInput.focus();

// ── Voice input ───────────────────────────────────────────────────────────────
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
  const micBtn = document.getElementById('micBtn');
  micBtn.style.display = 'flex';
  const recognition = new SpeechRecognition();
  recognition.lang = 'en-US';
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  let listening = false;

  micBtn.addEventListener('click', () => {
    if (listening) { recognition.stop(); return; }
    recognition.start();
  });

  recognition.onstart = () => {
    listening = true;
    micBtn.classList.add('listening');
    setHint('Listening…');
  };
  recognition.onresult = (e) => {
    const transcript = e.results[0][0].transcript;
    const input = document.getElementById('askInput');
    input.value = transcript;
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 140) + 'px';
    setHint('');
    submitQuestion();
  };
  recognition.onerror = () => { setHint(''); };
  recognition.onend = () => {
    listening = false;
    micBtn.classList.remove('listening');
  };
}
</script>
</body>
</html>"""

html = html.replace('SERMONS_DATA_PLACEHOLDER', sermons_js)
html = html.replace('SERMON_INDEX_PLACEHOLDER', sermon_index_js)
html = html.replace('APPS_SCRIPT_URL_PLACEHOLDER', apps_script_js)

out = REPO_DIR / "index.html"
out.write_text(html, encoding="utf-8")
print(f"Written → {out}  ({out.stat().st_size // 1024} KB)")
