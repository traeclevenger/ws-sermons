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

print(f"Building index.html with {len(sermons)} sermons, "
      f"{sum(len(s.get('chunks',[])) for s in sermons)} total chunks")
if not APPS_SCRIPT_URL:
    print("  Note: APPS_SCRIPT_URL is empty — Ask tab will show setup instructions")

# ── HTML template ───────────────────────���──────────────────────────────���───────
html = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>Westside Sermon Search</title>
<link rel="icon" type="image/png" href="WS favicon.png">
<style>
  :root {
    --bg: #0d1210;
    --surface: #141c18;
    --surface2: #1d2820;
    --accent: #96aa9e;
    --accent2: #6a7e72;
    --text: #eaedea;
    --subtext: #7a9082;
    --border: #2a3830;
    --card-shadow: 0 4px 24px rgba(0,0,0,0.5);
    --radius: 14px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; min-height: 100vh; }

  header {
    background: #ffffff;
    border-bottom: 1px solid #d8d8d8;
    padding: 16px 24px 14px;
    position: sticky; top: 0; z-index: 100;
    box-shadow: 0 2px 12px rgba(0,0,0,0.12);
  }
  .site-logo { display: block; height: 64px; width: auto; margin-bottom: 14px; }
  .search-wrap { position: relative; }
  .search-wrap svg { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: #999; pointer-events: none; }
  #searchInput {
    width: 100%; padding: 11px 36px 11px 42px;
    background: #f3f3f3; border: 1px solid #d0d0d0;
    border-radius: 10px; color: #1a1a1a;
    font-size: 0.95rem; outline: none; transition: border-color 0.2s;
    -webkit-appearance: none;
  }
  #searchInput:focus { border-color: #829086; background: #fff; }
  #searchInput::placeholder { color: #999; }
  #searchInput::-webkit-search-cancel-button { -webkit-appearance: none; display: none; }
  #clearBtn {
    display: none; position: absolute; right: 10px; top: 50%; transform: translateY(-50%);
    width: 20px; height: 20px; border-radius: 50%; border: none; cursor: pointer;
    background: #bbb; color: #fff; font-size: 13px; line-height: 1;
    align-items: center; justify-content: center; padding: 0; transition: background 0.15s;
  }
  #clearBtn.visible { display: flex; }
  #clearBtn:hover { background: #999; }

  /* TABS */
  .tabs { display: flex; gap: 4px; padding: 12px 16px 0; background: var(--surface); border-bottom: 1px solid var(--border); }
  .tab { padding: 9px 18px; border-radius: 8px 8px 0 0; font-size: 0.85rem; font-weight: 600; cursor: pointer; border: 1px solid transparent; border-bottom: none; transition: all 0.2s; color: var(--subtext); background: transparent; }
  .tab.active { background: var(--bg); color: var(--accent); border-color: var(--border); border-bottom-color: var(--bg); }
  .tab:hover:not(.active) { color: var(--text); background: var(--surface2); }

  .main { padding: 16px; max-width: 860px; margin: 0 auto; }
  .results-count { font-size: 0.8rem; color: var(--subtext); margin-bottom: 14px; padding-left: 2px; min-height: 1.2em; }

  /* SERMON CARDS */
  .sermon-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 18px 20px; margin-bottom: 12px;
    box-shadow: var(--card-shadow); transition: border-color 0.15s;
  }
  .sermon-card:hover { border-color: var(--accent2); }
  .sermon-meta { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }
  .sermon-title { font-size: 1rem; font-weight: 700; color: var(--text); }
  .sermon-date { font-size: 0.78rem; color: var(--subtext); }
  .sermon-speaker { font-size: 0.78rem; color: var(--accent2); }
  .sermon-excerpt {
    font-size: 0.85rem; color: var(--subtext); line-height: 1.6;
    border-left: 3px solid var(--border); padding-left: 12px; margin: 10px 0;
    display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden;
  }
  .sermon-excerpt.expanded { -webkit-line-clamp: unset; }
  .sermon-actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
  .btn {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 6px 14px; border-radius: 8px; font-size: 0.8rem; font-weight: 600;
    text-decoration: none; border: none; cursor: pointer; transition: all 0.15s;
  }
  .btn-audio { background: rgba(150,170,158,0.15); color: var(--accent); border: 1px solid rgba(150,170,158,0.3); }
  .btn-audio:hover { background: rgba(150,170,158,0.25); }
  .btn-doc { background: rgba(150,170,158,0.08); color: var(--subtext); border: 1px solid var(--border); }
  .btn-doc:hover { color: var(--accent); border-color: var(--accent2); }
  .btn-expand { background: transparent; color: var(--subtext); border: none; padding: 0; font-size: 0.75rem; cursor: pointer; text-decoration: underline; text-decoration-color: var(--border); }
  .btn-expand:hover { color: var(--accent); }

  /* ASK TAB */
  #askView { display: none; }
  .ask-form { display: flex; gap: 10px; margin-bottom: 20px; }
  #askInput {
    flex: 1; padding: 12px 16px; background: var(--surface); border: 1px solid var(--border);
    border-radius: 10px; color: var(--text); font-size: 0.95rem; outline: none;
    transition: border-color 0.2s; resize: none; min-height: 52px; max-height: 160px;
    font-family: inherit;
  }
  #askInput:focus { border-color: var(--accent2); }
  #askInput::placeholder { color: var(--subtext); }
  #askBtn {
    padding: 12px 20px; background: var(--accent2); color: #fff; border: none;
    border-radius: 10px; font-size: 0.9rem; font-weight: 700; cursor: pointer;
    transition: background 0.15s; white-space: nowrap; align-self: flex-end;
  }
  #askBtn:hover:not(:disabled) { background: var(--accent); }
  #askBtn:disabled { opacity: 0.5; cursor: not-allowed; }

  .answer-card {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 20px; margin-bottom: 16px;
    box-shadow: var(--card-shadow);
  }
  .answer-text { font-size: 0.95rem; line-height: 1.7; color: var(--text); white-space: pre-wrap; }
  .answer-sources { margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--border); }
  .answer-sources-label { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: var(--subtext); margin-bottom: 8px; }
  .source-chip {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 5px 10px; margin: 3px 4px 3px 0;
    background: rgba(150,170,158,0.1); border: 1px solid var(--border);
    border-radius: 8px; font-size: 0.78rem; color: var(--accent); text-decoration: none;
    transition: all 0.15s;
  }
  .source-chip:hover { background: rgba(150,170,158,0.2); border-color: var(--accent2); }

  .ask-status { font-size: 0.85rem; color: var(--subtext); padding: 12px 0; min-height: 2em; }
  .ask-setup { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 24px; color: var(--subtext); line-height: 1.7; }
  .ask-setup strong { color: var(--text); }
  .ask-setup code { background: var(--surface2); padding: 2px 6px; border-radius: 4px; color: #f0c070; font-size: 0.82rem; }

  .empty-state { text-align: center; padding: 60px 20px; color: var(--subtext); }
  .empty-state p { margin-top: 8px; font-size: 0.85rem; }
  #searchHint { font-size: 0.75rem; color: var(--subtext); margin-top: 6px; padding-left: 2px; min-height: 1em; }
  .highlight { background: rgba(150,170,158,0.25); border-radius: 3px; padding: 0 2px; color: var(--accent); }

  @media (max-width: 600px) {
    header { padding: 12px 16px 10px; }
    .site-logo { height: 48px; }
    .main { padding: 12px; }
    .sermon-card { padding: 14px 16px; }
    .ask-form { flex-direction: column; }
    #askBtn { align-self: stretch; }
  }
</style>
</head>
<body>

<header>
  <img src="WS logo.png" alt="Westside church of Christ" class="site-logo">
  <div class="search-wrap" id="searchWrap">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
    <input type="search" id="searchInput" placeholder="Search sermons by topic, scripture, keyword…" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false">
    <button id="clearBtn" aria-label="Clear search" onclick="clearSearch()">✕</button>
  </div>
  <div id="searchHint"></div>
</header>

<div class="tabs">
  <button class="tab active" id="tabSearch" onclick="switchTab('search')">🔍 Search</button>
  <button class="tab" id="tabAsk" onclick="switchTab('ask')">💬 Ask</button>
</div>

<div class="main">
  <div id="searchView">
    <div class="results-count" id="resultsCount"></div>
    <div id="sermonList"></div>
  </div>
  <div id="askView">
    <div id="askSetup" style="display:none" class="ask-setup">
      <strong>Ask tab not yet configured.</strong><br>
      To enable Q&amp;A, deploy the Apps Script backend and paste its URL into
      <code>APPS_SCRIPT_URL</code> in <code>build.py</code>, then rebuild.
    </div>
    <div id="askInterface" style="display:none">
      <div class="ask-form">
        <textarea id="askInput" rows="2" placeholder="Ask a question about any sermon… e.g. What did Mark say about perseverance?"></textarea>
        <button id="askBtn" onclick="submitQuestion()">Ask</button>
      </div>
      <div class="ask-status" id="askStatus"></div>
      <div id="answerArea"></div>
    </div>
  </div>
</div>

<script>
SERMONS_DATA_PLACEHOLDER
APPS_SCRIPT_URL_PLACEHOLDER

const TRANSFORMERS_CDN = 'https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.2';
const EMBED_MODEL = 'Xenova/all-MiniLM-L6-v2';
const SEMANTIC_THRESHOLD = 0.30;
const ASK_TOP_CHUNKS = 8;

let semanticReady = false, semanticLoading = false, embedFn = null;
let currentTab = 'search';
let _searchTimer = null;

function cosineSim(a, b) {
  let dot = 0;
  for (let i = 0; i < a.length; i++) dot += a[i] * b[i];
  return dot;
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
    doSearch();
  } catch(e) {
    setHint('Semantic model unavailable — using keyword search');
    semanticLoading = false;
  }
}

function setHint(msg) { document.getElementById('searchHint').textContent = msg; }

function esc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function highlight(text, query) {
  if (!query || !text) return esc(text || '');
  const re = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')})`, 'gi');
  return esc(text).replace(re, '<span class="highlight">$1</span>');
}

// ── Tab switching ─────────────��─────────────────────────────��──────────────────
function switchTab(tab) {
  currentTab = tab;
  document.getElementById('searchView').style.display = tab === 'search' ? 'block' : 'none';
  document.getElementById('askView').style.display    = tab === 'ask'    ? 'block' : 'none';
  document.getElementById('searchWrap').style.display = tab === 'search' ? 'block' : 'none';
  document.getElementById('searchHint').style.display = tab === 'search' ? 'block' : 'none';
  document.getElementById('tabSearch').classList.toggle('active', tab === 'search');
  document.getElementById('tabAsk').classList.toggle('active', tab === 'ask');

  if (tab === 'ask') {
    if (APPS_SCRIPT_URL) {
      document.getElementById('askInterface').style.display = 'block';
      document.getElementById('askSetup').style.display = 'none';
    } else {
      document.getElementById('askInterface').style.display = 'none';
      document.getElementById('askSetup').style.display = 'block';
    }
    if (!semanticReady && !semanticLoading) loadSemanticModel();
  }
}

// ── Search tab ───────────────────────────��─────────────────────────────────���───
document.getElementById('searchInput').addEventListener('input', e => {
  const q = e.target.value.trim();
  document.getElementById('clearBtn').classList.toggle('visible', q.length > 0);
  if (q && !semanticReady && !semanticLoading) loadSemanticModel();
  clearTimeout(_searchTimer);
  _searchTimer = setTimeout(doSearch, 120);
});

function clearSearch() {
  document.getElementById('searchInput').value = '';
  document.getElementById('clearBtn').classList.remove('visible');
  setHint('');
  doSearch();
}

function doSearch() {
  const q = document.getElementById('searchInput').value.trim();
  if (!q) { renderAll(); return; }

  if (semanticReady && embedFn) {
    embedFn(q).then(queryVec => {
      const scored = SERMONS.map(sermon => {
        let bestSim = 0, bestChunk = null;
        for (const chunk of sermon.chunks) {
          if (!chunk.emb) continue;
          const sim = cosineSim(queryVec, chunk.emb);
          if (sim > bestSim) { bestSim = sim; bestChunk = chunk; }
        }
        return { sermon, sim: bestSim, chunk: bestChunk };
      })
      .filter(x => x.sim >= SEMANTIC_THRESHOLD)
      .sort((a, b) => b.sim - a.sim);

      renderResults(scored.length > 0 ? scored : null, q);
      if (!scored.length) renderKeyword(q);
    });
  } else {
    if (semanticLoading) setHint('⏳ Loading semantic model… results will refine shortly.');
    renderKeyword(q);
  }
}

function renderKeyword(q) {
  const ql = q.toLowerCase();
  const scored = SERMONS.map(sermon => {
    const haystack = [sermon.title, sermon.speaker, sermon.date,
      ...sermon.chunks.map(c => c.text)].join(' ').toLowerCase();
    if (!haystack.includes(ql)) return null;
    const chunk = sermon.chunks.find(c => c.text.toLowerCase().includes(ql)) || sermon.chunks[0];
    return { sermon, sim: 1, chunk };
  }).filter(Boolean);
  renderResults(scored, q);
}

function renderAll() {
  updateCount(SERMONS.length, SERMONS.length);
  const sorted = [...SERMONS].sort((a, b) => b.date.localeCompare(a.date));
  document.getElementById('sermonList').innerHTML = SERMONS.length === 0
    ? `<div class="empty-state"><strong>No sermons yet.</strong><p>Transcripts will appear here once processed.</p></div>`
    : sorted.map(s => cardHtml(s, s.chunks[0], '')).join('');
}

function renderResults(scored, q) {
  updateCount(scored ? scored.length : 0, SERMONS.length);
  document.getElementById('sermonList').innerHTML = (!scored || !scored.length)
    ? `<div class="empty-state"><strong>No results found.</strong><p>Try different keywords or a broader phrase.</p></div>`
    : scored.map(({ sermon, chunk }) => cardHtml(sermon, chunk, q)).join('');
}

function updateCount(n, total) {
  document.getElementById('resultsCount').textContent =
    n === total ? `${total} sermon${total !== 1 ? 's' : ''}` : `${n} of ${total} sermons match`;
}

const playIcon = `<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><polygon points="5,3 19,12 5,21"/></svg>`;
const docIcon  = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14,2 14,8 20,8"/></svg>`;
const audioIcon = `<svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor"><polygon points="5,3 19,12 5,21"/></svg>`;
let expandedCards = new Set();

function toggleExpand(id) {
  const el = document.getElementById('excerpt-' + id);
  if (expandedCards.has(id)) {
    expandedCards.delete(id); el.classList.remove('expanded');
    document.getElementById('expand-' + id).textContent = 'Show more';
  } else {
    expandedCards.add(id); el.classList.add('expanded');
    document.getElementById('expand-' + id).textContent = 'Show less';
  }
}

function cardHtml(sermon, chunk, q) {
  const id = esc(sermon.date + sermon.title).replace(/\W/g, '');
  const excerptText = chunk ? chunk.text : '';
  const docBtn = sermon.docUrl
    ? `<a class="btn btn-doc" href="${esc(sermon.docUrl)}" target="_blank" rel="noopener">${docIcon} Full transcript</a>`
    : '';
  return `<div class="sermon-card">
    <div class="sermon-meta">
      <span class="sermon-title">${highlight(sermon.title, q)}</span>
      <span class="sermon-speaker">${highlight(sermon.speaker, q)}</span>
      <span class="sermon-date">${esc(sermon.date)}</span>
    </div>
    ${excerptText ? `<div class="sermon-excerpt" id="excerpt-${id}">${highlight(excerptText, q)}</div>
    <button class="btn-expand" id="expand-${id}" onclick="toggleExpand('${id}')">Show more</button>` : ''}
    <div class="sermon-actions">
      <a class="btn btn-audio" href="${esc(sermon.audioUrl)}" target="_blank" rel="noopener">${playIcon} Listen</a>
      ${docBtn}
    </div>
  </div>`;
}

// ── Ask tab ─────────────────────────────────────────────────────��──────────────
async function getTopChunks(question) {
  if (!embedFn) return [];
  const queryVec = await embedFn(question);
  const allChunks = [];
  for (const sermon of SERMONS) {
    for (const chunk of sermon.chunks) {
      if (!chunk.emb) continue;
      allChunks.push({
        sim: cosineSim(queryVec, chunk.emb),
        payload: {
          text: chunk.text,
          sermon_title: sermon.title,
          date: sermon.date,
          speaker: sermon.speaker,
          audio_url: sermon.audioUrl,
        }
      });
    }
  }
  return allChunks
    .sort((a, b) => b.sim - a.sim)
    .slice(0, ASK_TOP_CHUNKS)
    .map(x => x.payload);
}

async function submitQuestion() {
  const question = document.getElementById('askInput').value.trim();
  if (!question) return;

  const btn = document.getElementById('askBtn');
  const status = document.getElementById('askStatus');
  const answerArea = document.getElementById('answerArea');

  btn.disabled = true;
  answerArea.innerHTML = '';

  try {
    if (!semanticReady) {
      status.textContent = '⏳ Loading semantic model first…';
      await loadSemanticModel();
    }

    status.textContent = '🔍 Finding relevant sermon passages…';
    const chunks = await getTopChunks(question);

    if (chunks.length === 0) {
      status.textContent = '';
      answerArea.innerHTML = `<div class="answer-card"><div class="answer-text">No sermon content found to answer that question.</div></div>`;
      return;
    }

    status.textContent = '💬 Asking Claude…';
    const res = await fetch(APPS_SCRIPT_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain' },
      body: JSON.stringify({ question, chunks }),
    });

    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    status.textContent = '';

    const sourcesHtml = data.sources && data.sources.length
      ? `<div class="answer-sources">
          <div class="answer-sources-label">Sources</div>
          ${data.sources.map(s =>
            `<a class="source-chip" href="${esc(s.audio_url)}" target="_blank" rel="noopener">
              ${audioIcon} ${esc(s.title)} <span style="opacity:0.6">${esc(s.date)}</span>
            </a>`
          ).join('')}
        </div>`
      : '';

    answerArea.innerHTML = `<div class="answer-card">
      <div class="answer-text">${esc(data.answer)}</div>
      ${sourcesHtml}
    </div>`;

  } catch (err) {
    status.textContent = '';
    answerArea.innerHTML = `<div class="answer-card"><div class="answer-text" style="color:var(--subtext)">Error: ${esc(err.message)}</div></div>`;
  } finally {
    btn.disabled = false;
  }
}

document.getElementById('askInput').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitQuestion(); }
});

renderAll();
</script>
</body>
</html>"""

html = html.replace('SERMONS_DATA_PLACEHOLDER', sermons_js)
html = html.replace('APPS_SCRIPT_URL_PLACEHOLDER', apps_script_js)

out = REPO_DIR / "index.html"
out.write_text(html, encoding="utf-8")
print(f"Written → {out}  ({out.stat().st_size // 1024} KB)")
