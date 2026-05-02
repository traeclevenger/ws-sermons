// Westside Sermon Q&A — Google Apps Script backend
// Deploy as: Web app | Execute as: Me | Who has access: Anyone
//
// Before deploying, add your Anthropic API key:
//   Apps Script → Project Settings → Script Properties
//   Add property: ANTHROPIC_API_KEY = sk-ant-...

const CLAUDE_MODEL = "claude-haiku-4-5-20251001";
const MAX_CONTEXT_CHUNKS = 8;
const MAX_HISTORY_MESSAGES = 20; // keep last 10 turns

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    const messages = (body.messages || []).slice(-MAX_HISTORY_MESSAGES);
    const chunks   = (body.chunks   || []).slice(0, MAX_CONTEXT_CHUNKS);

    if (!messages.length) return respond({ error: "No messages provided." });

    // Build sermon context for the system prompt
    const contextText = chunks.length
      ? chunks.map((c, i) =>
          `[${i + 1}] ${c.sermon_title} (${c.date} — ${c.speaker})\n${c.text}`
        ).join("\n\n---\n\n")
      : "(No matching sermon excerpts found for this question.)";

    const systemPrompt =
      "You are a helpful assistant for Westside church of Christ. " +
      "Answer questions based on the sermon excerpts below. " +
      "Be conversational, warm, and concise. Maintain context across the conversation. " +
      "If the answer isn't clearly supported by the excerpts, say so honestly rather than speculating. " +
      "When citing a specific sermon, mention its title naturally.\n\n" +
      "Relevant sermon excerpts for the latest question:\n\n" + contextText;

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
        max_tokens: 1024,
        system: systemPrompt,
        messages: messages,
      }),
      muteHttpExceptions: true,
    });

    const result = JSON.parse(response.getContentText());
    if (result.error) throw new Error(result.error.message);

    const answer = result.content[0].text;

    // Deduplicated source list
    const seen = new Set();
    const sources = chunks
      .filter(c => { const k = c.audio_url; if (seen.has(k)) return false; seen.add(k); return true; })
      .map(c => ({ title: c.sermon_title, date: c.date, speaker: c.speaker, audio_url: c.audio_url }));

    return respond({ answer, sources });

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
