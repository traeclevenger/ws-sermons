// Westside Sermon Q&A — Google Apps Script backend
// Deploy as: Web app | Execute as: Me | Who has access: Anyone
//
// Before deploying, add your Anthropic API key:
//   Apps Script → Project Settings → Script Properties
//   Add property: ANTHROPIC_API_KEY = sk-ant-...

const CLAUDE_MODEL = "claude-sonnet-4-6";
const MAX_CONTEXT_CHUNKS = 60;
const MAX_HISTORY_MESSAGES = 20; // keep last 10 turns

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    const messages     = (body.messages     || []).slice(-MAX_HISTORY_MESSAGES);
    const chunks       = (body.chunks       || []).slice(0, MAX_CONTEXT_CHUNKS);
    const sermonIndex  = (body.sermonIndex  || []);
    const sessionId    = body.sessionId || "unknown";
    const question     = messages.length ? messages[messages.length - 1].content : "";

    if (!messages.length) return respond({ error: "No messages provided." });

    // Pre-compute counts so the model doesn't have to count manually
    const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const yearMonthCounts = {};
    sermonIndex.forEach(s => {
      const y = s.date.slice(0, 4);
      const m = parseInt(s.date.slice(5, 7)) - 1;
      if (!yearMonthCounts[y]) yearMonthCounts[y] = {};
      yearMonthCounts[y][monthNames[m]] = (yearMonthCounts[y][monthNames[m]] || 0) + 1;
    });
    const statsLines = Object.entries(yearMonthCounts).sort().map(([y, months]) => {
      const total = Object.values(months).reduce((a, b) => a + b, 0);
      const breakdown = Object.entries(months).map(([m, n]) => `${m}:${n}`).join(' ');
      return `${y} (${total} total): ${breakdown}`;
    });
    const statsText = `Total: ${sermonIndex.length} sermons.\n` + statsLines.join('\n');

    // Full sermon catalogue (for listing/browsing questions)
    const catalogueText = sermonIndex.length
      ? sermonIndex.map(s => `• ${s.date} — "${s.title}" (${s.speaker})`).join("\n")
      : "(No sermons in catalogue yet.)";

    // Relevant content chunks (for detailed content questions)
    const contextText = chunks.length
      ? chunks.map((c, i) =>
          `[${i + 1}] ${c.sermon_title} (${c.date} — ${c.speaker})\n${c.text}`
        ).join("\n\n---\n\n")
      : "(No closely matching excerpts found.)";

    const systemPrompt =
      "You are a helpful assistant for Westside church of Christ. " +
      "You help members explore and understand the church's sermon library. " +
      "Be warm but concise — give short, direct answers. Do not volunteer extra background or context unless the user asks for it. " +
      "Maintain context across the conversation. " +
      "Only answer questions related to Westside's sermon library, the sermons themselves, or general church topics. If the user asks about anything unrelated — such as weather, cooking, news, or other off-topic subjects — politely let them know you can only help with questions about Westside's sermons. " +
      "Sermon excerpts are transcripts of spoken sermons — informal speech, not written outlines. " +
      "When asked for an outline, summary, or main points, actively synthesize and structure the content from the excerpts provided. Do not say you lack enough information if excerpts are present — work with what is there. " +
      "You may use bullet lists (lines starting with - ) when listing points or items. " +
      "Do not use any other Markdown formatting — no asterisks for bold, no headers. Plain text otherwise.\n\n" +
      "## Sermon library stats\n" + statsText + "\n\n" +
      "## Available sermons\n" + catalogueText + "\n\n" +
      "## Relevant excerpts for the latest question\n" + contextText + "\n\n" +
      "Use the sermon list to answer browsing questions (what's available, filter by topic/date/speaker). " +
      "Use the excerpts to answer detailed content questions. " +
      "If the excerpts don't support a claim, say so honestly rather than speculating.\n\n" +
      "IMPORTANT: Respond only with a JSON object — no text outside the JSON:\n" +
      "{\"answer\":\"your plain-text response\",\"cited_sermons\":[\"exact sermon title\"],\"list_sermons\":[{\"date\":\"YYYY-MM-DD\",\"title\":\"exact sermon title\"}]}\n" +
      "- cited_sermons: exact titles of sermons you specifically reference or quote in your answer. Empty array if none.\n" +
      "- list_sermons: populated when your answer involves a group, series, or set of sermons — even if the user didn't explicitly ask for a list. For example, if the user asks about a sermon series, include all sermons in that series. Empty array otherwise.\n" +
      "IMPORTANT: You do not have direct access to audio URLs — the app resolves them automatically from the titles you return in cited_sermons and list_sermons. Never tell the user you lack links or URLs. Instead, always return the relevant sermon title(s) in cited_sermons or list_sermons and the app will provide the audio links.";

    const apiKey = PropertiesService.getScriptProperties().getProperty("ANTHROPIC_API_KEY");
    if (!apiKey) throw new Error("ANTHROPIC_API_KEY not set in Script Properties.");

    const fetchPayload = {
      method: "post",
      contentType: "application/json",
      headers: {
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
      },
      payload: JSON.stringify({
        model: CLAUDE_MODEL,
        max_tokens: 2048,
        system: systemPrompt,
        messages: messages,
      }),
      muteHttpExceptions: true,
    };

    let response = UrlFetchApp.fetch("https://api.anthropic.com/v1/messages", fetchPayload);
    let result = JSON.parse(response.getContentText());
    // Retry once on overloaded errors after a short pause
    if (result.error && result.error.type === "overloaded_error") {
      Utilities.sleep(3000);
      response = UrlFetchApp.fetch("https://api.anthropic.com/v1/messages", fetchPayload);
      result = JSON.parse(response.getContentText());
    }
    if (result.error) throw new Error(result.error.message);

    const rawText = result.content[0].text.trim();
    let answerText = rawText, citedTitles = [], listSermonData = [];
    try {
      const jsonMatch = rawText.match(/\{[\s\S]*\}/);
      const parsed = JSON.parse(jsonMatch[0]);
      answerText = parsed.answer || rawText;
      citedTitles = parsed.cited_sermons || [];
      listSermonData = parsed.list_sermons || [];
      // Handle double-encoded JSON (answer field itself is a JSON string)
      if (typeof answerText === 'string' && answerText.trim().startsWith('{')) {
        try {
          const inner = JSON.parse(answerText);
          if (inner.answer) {
            answerText = inner.answer;
            if (inner.cited_sermons) citedTitles = inner.cited_sermons;
            if (inner.list_sermons) listSermonData = inner.list_sermons;
          }
        } catch(e2) {}
      }
    } catch(e) { /* fallback to raw text */ }

    // Log usage
    logUsage(sessionId, question, answerText);

    // Build title → sermon lookup from index
    const titleMap = {};
    sermonIndex.forEach(s => { titleMap[s.title] = s; });

    const citedSermons = citedTitles
      .map(t => titleMap[t])
      .filter(Boolean)
      .map(s => ({ title: s.title, date: s.date, audio_url: s.audioUrl }));

    const listSermons = listSermonData
      .map(s => { const idx = titleMap[s.title]; return idx ? { date: s.date, title: s.title, audio_url: idx.audioUrl } : null; })
      .filter(Boolean);

    return respond({ answer: answerText, cited_sermons: citedSermons, list_sermons: listSermons });

  } catch (err) {
    return respond({ error: err.message });
  }
}

function logUsage(sessionId, question, answer) {
  try {
    const props = PropertiesService.getScriptProperties();
    let sheetId = props.getProperty("ANALYTICS_SHEET_ID");
    const ownerIds = (props.getProperty("OWNER_SESSION_IDS") || "").split(",").map(s => s.trim()).filter(Boolean);
    const isOwner = ownerIds.includes(sessionId);
    let ss;
    if (!sheetId) {
      ss = SpreadsheetApp.create("WS Sermons Usage");
      // Move to My Drive/Westside/Sermon Transcripts
      try {
        const targetFolder = DriveApp.getFoldersByName("Westside").next()
          .getFoldersByName("Sermon Transcripts").next();
        const file = DriveApp.getFileById(ss.getId());
        targetFolder.addFile(file);
        DriveApp.getRootFolder().removeFile(file);
      } catch(folderErr) { /* folder not found — leave in root */ }
      const sheet = ss.getActiveSheet();
      sheet.setName("Usage");
      sheet.appendRow(["Timestamp", "Session ID", "Owner", "Question", "Response"]);
      sheet.setFrozenRows(1);
      props.setProperty("ANALYTICS_SHEET_ID", ss.getId());
    } else {
      ss = SpreadsheetApp.openById(sheetId);
    }
    ss.getSheetByName("Usage").appendRow([
      new Date().toISOString(),
      sessionId,
      isOwner ? "yes" : "",
      question.slice(0, 300),
      (answer || "").slice(0, 1000)
    ]);
  } catch(e) { /* don't let logging failure break the response */ }
}

function respond(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}

function sendDailyDigest() {
  try {
    const props = PropertiesService.getScriptProperties();
    const sheetId = props.getProperty("ANALYTICS_SHEET_ID");
    if (!sheetId) return;

    const ownerIds = (props.getProperty("OWNER_SESSION_IDS") || "").split(",").map(s => s.trim()).filter(Boolean);
    const ownerEmail = props.getProperty("OWNER_EMAIL") || Session.getEffectiveUser().getEmail();

    const ss = SpreadsheetApp.openById(sheetId);
    const sheet = ss.getSheetByName("Usage");
    const data = sheet.getDataRange().getValues();

    // Headers: Timestamp, Session ID, Owner, Question, Response
    const cutoff = new Date(Date.now() - 24 * 60 * 60 * 1000);

    // Filter rows from last 24 hours, non-owners only
    const rows = data.slice(1).filter(row => {
      const ts = new Date(row[0]);
      const isOwner = row[2] === "yes";
      return ts >= cutoff && !isOwner;
    });

    if (!rows.length) return; // No non-owner activity — skip email

    // Group by session ID, preserving chronological order
    const sessions = {};
    const sessionOrder = [];
    rows.forEach(row => {
      const sessionId = row[1];
      if (!sessions[sessionId]) { sessions[sessionId] = []; sessionOrder.push(sessionId); }
      sessions[sessionId].push({
        timestamp: new Date(row[0]),
        question: row[3] || "",
        response: row[4] || ""
      });
    });

    // Build email body
    const dateStr = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    let body = `Westside Sermons — Daily Usage Digest\n`;
    body += `${dateStr}\n`;
    body += `Sessions: ${sessionOrder.length}  |  Questions: ${rows.length}\n`;
    body += `${'='.repeat(60)}\n\n`;

    sessionOrder.forEach((sessionId, i) => {
      const turns = sessions[sessionId];
      const start = turns[0].timestamp.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
      body += `SESSION ${i + 1}  (${turns.length} question${turns.length !== 1 ? 's' : ''}  •  started ${start})\n`;
      body += `${'-'.repeat(60)}\n`;
      turns.forEach((turn, j) => {
        body += `Q${j + 1}: ${turn.question}\n\n`;
        body += `A: ${turn.response}\n\n`;
      });
      body += '\n';
    });

    MailApp.sendEmail({
      to: ownerEmail,
      subject: `WS Sermons Usage — ${dateStr}`,
      body: body.trim()
    });

  } catch(e) { /* silent fail — don't interrupt anything */ }
}

// Run once in the Apps Script editor to create the 7am daily trigger
function setupDailyDigestTrigger() {
  // Remove any existing daily digest triggers to avoid duplicates
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'sendDailyDigest')
    .forEach(t => ScriptApp.deleteTrigger(t));

  ScriptApp.newTrigger('sendDailyDigest')
    .timeBased()
    .atHour(7)
    .everyDays(1)
    .inTimezone(Session.getScriptTimeZone())
    .create();

  Logger.log('Daily digest trigger created — fires at 7am every day.');
}

// Run this in the Apps Script editor to verify logging is working
function testLogging() {
  logUsage("test-session-123", "Test question from testLogging()");
  const sheetId = PropertiesService.getScriptProperties().getProperty("ANALYTICS_SHEET_ID");
  const ss = SpreadsheetApp.openById(sheetId);
  Logger.log("Sheet URL: " + ss.getUrl());
}

// Test in the Apps Script editor to verify your API key works
function testPost() {
  const result = doPost({
    postData: {
      contents: JSON.stringify({
        messages: [{ role: "user", content: "What does the sermon say about faith?" }],
        chunks: [{
          text: "Faith means trusting God even when we cannot see the outcome.",
          sermon_title: "Test Sermon",
          date: "2026-01-01",
          speaker: "Mark Roberts",
          audio_url: "https://example.com/test.mp3"
        }]
      })
    }
  });
  Logger.log(result.getContent());
}
