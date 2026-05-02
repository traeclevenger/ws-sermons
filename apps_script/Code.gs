// Westside Sermon Q&A — Google Apps Script backend
// Deploy as: Web app | Execute as: Me | Who has access: Anyone
//
// Before deploying, add your Anthropic API key:
//   Apps Script → Project Settings → Script Properties
//   Add property: ANTHROPIC_API_KEY = sk-ant-...

const CLAUDE_MODEL = "claude-haiku-4-5-20251001";
const MAX_CONTEXT_CHUNKS = 8;

function doPost(e) {
  const cors = ContentService.createTextOutput();

  try {
    const body = JSON.parse(e.postData.contents);
    const question = (body.question || "").trim();
    const chunks   = (body.chunks  || []).slice(0, MAX_CONTEXT_CHUNKS);

    if (!question) {
      return respond({ error: "No question provided." });
    }

    // Build context block from sermon chunks
    const contextText = chunks.map((c, i) =>
      `[${i + 1}] ${c.sermon_title} (${c.date} — ${c.speaker})\n${c.text}`
    ).join("\n\n---\n\n");

    const systemPrompt =
      "You are a helpful assistant for Westside church of Christ. " +
      "Answer questions based on the sermon excerpts provided. " +
      "Be conversational and concise. " +
      "If the answer isn't in the provided excerpts, say so honestly. " +
      "When referencing a specific sermon, mention its title naturally in your response.";

    const userMessage =
      `Here are relevant sermon excerpts:\n\n${contextText}\n\n---\n\nQuestion: ${question}`;

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
        messages: [{ role: "user", content: userMessage }],
      }),
      muteHttpExceptions: true,
    });

    const result = JSON.parse(response.getContentText());
    if (result.error) throw new Error(result.error.message);

    const answer = result.content[0].text;

    // Deduplicated source list from the chunks
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

// Test this function in the Apps Script editor to verify your API key works
function testPost() {
  const result = doPost({
    postData: {
      contents: JSON.stringify({
        question: "What does the sermon say about faith?",
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
