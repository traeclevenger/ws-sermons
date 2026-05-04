// Westside Sermon Q&A — Google Apps Script backend
// Deploy as: Web app | Execute as: Me | Who has access: Anyone
//
// Before deploying, add your Anthropic API key:
//   Apps Script → Project Settings → Script Properties
//   Add property: ANTHROPIC_API_KEY = sk-ant-...

const CLAUDE_MODEL = "claude-haiku-4-5-20251001";
const MAX_CONTEXT_CHUNKS = 60;
const MAX_HISTORY_MESSAGES = 20; // keep last 10 turns

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    const messages     = (body.messages     || []).slice(-MAX_HISTORY_MESSAGES);
    const chunks       = (body.chunks       || []).slice(0, MAX_CONTEXT_CHUNKS);
    const sermonIndex  = (body.sermonIndex  || []);

    if (!messages.length) return respond({ error: "No messages provided." });

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
      "Sermon excerpts are transcripts of spoken sermons — informal speech, not written outlines. " +
      "When asked for an outline, summary, or main points, actively synthesize and structure the content from the excerpts provided. Do not say you lack enough information if excerpts are present — work with what is there. " +
      "You may use bullet lists (lines starting with - ) when listing points or items. " +
      "Do not use any other Markdown formatting — no asterisks for bold, no headers. Plain text otherwise.\n\n" +
      "## Available sermons\n" + catalogueText + "\n\n" +
      "## Relevant excerpts for the latest question\n" + contextText + "\n\n" +
      "Use the sermon list to answer browsing questions (what's available, filter by topic/date/speaker). " +
      "Use the excerpts to answer detailed content questions. " +
      "If the excerpts don't support a claim, say so honestly rather than speculating.\n\n" +
      "IMPORTANT: Respond only with a JSON object — no text outside the JSON:\n" +
      "{\"answer\":\"your plain-text response\",\"cited_sermons\":[\"exact sermon title\"],\"list_sermons\":[{\"date\":\"YYYY-MM-DD\",\"title\":\"exact sermon title\"}]}\n" +
      "- cited_sermons: exact titles of sermons you specifically reference or quote in your answer. Empty array if none.\n" +
      "- list_sermons: populated when your answer involves a group, series, or set of sermons — even if the user didn't explicitly ask for a list. For example, if the user asks about a sermon series, include all sermons in that series. Empty array otherwise.";

    const apiKey = PropertiesService.getScriptProperties().getProperty("ANTHROPIC_API_KEY");
    if (!apiKey) throw new Error("ANTHROPIC_API_KEY not set in Script Properties.");

    const response = UrlFetchApp.fetch("https://api.anthropic.com/v1/messages", {
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
    });

    const result = JSON.parse(response.getContentText());
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

    // Build title → sermon lookup from index
    const titleMap = {};
    sermonIndex.forEach(s => { titleMap[s.title] = s; });

    const citedSermons = citedTitles
      .map(t => titleMap[t])
      .filter(Boolean)
      .map(s => ({ title: s.title, date: s.date, audio_url: s.audioUrl }));

    const listSermons = listSermonData.map(s => {
      const idx = titleMap[s.title];
      return { date: s.date, title: s.title, audio_url: idx ? idx.audioUrl : null };
    });

    return respond({ answer: answerText, cited_sermons: citedSermons, list_sermons: listSermons });

  } catch (err) {
    return respond({ error: err.message });
  }
}

function respond(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
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
