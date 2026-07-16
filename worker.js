/**
 * Cloudflare Worker: serves /api/health and /api/chat for the JobLink dashboard.
 * The static page (index.html) is served by Workers Static Assets — see wrangler.toml.
 * The Groq key lives in a Worker secret (wrangler secret put GROQ_API_KEY),
 * so it never reaches the browser.
 */

const MODEL = "meta-llama/llama-4-scout-17b-16e-instruct";
const GROQ_URL = "https://api.groq.com/openai/v1/chat/completions";
const MAX_BODY = 24 * 1024 * 1024;

const json = (code, obj) =>
  new Response(JSON.stringify(obj), {
    status: code,
    headers: { "Content-Type": "application/json" },
  });

export default {
  async fetch(request, env) {
    const path = new URL(request.url).pathname;

    if (path === "/api/health") {
      return json(200, { ok: Boolean(env.GROQ_API_KEY), model: MODEL });
    }

    if (path === "/api/chat") {
      if (request.method !== "POST") return json(405, { error: "POST only" });
      if (!env.GROQ_API_KEY) {
        return json(500, { error: "GROQ_API_KEY secret is not set on this Worker." });
      }
      const length = Number(request.headers.get("Content-Length") || 0);
      if (length > MAX_BODY) {
        return json(413, { error: "request too large — try a smaller screenshot" });
      }

      let messages;
      try {
        messages = (await request.json()).messages;
        if (!Array.isArray(messages)) throw new Error();
      } catch {
        return json(400, { error: "malformed request" });
      }

      try {
        const r = await fetch(GROQ_URL, {
          method: "POST",
          headers: {
            Authorization: "Bearer " + env.GROQ_API_KEY,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            model: MODEL,
            messages,
            max_tokens: 1024,
            temperature: 0.2,
          }),
        });
        const data = await r.json();
        if (!r.ok) {
          const detail = data?.error?.message || JSON.stringify(data).slice(0, 500);
          return json(r.status, { error: `Groq returned ${r.status}: ${detail}` });
        }
        return json(200, {
          reply: data.choices[0].message.content,
          usage: data.usage || {},
        });
      } catch (e) {
        return json(502, { error: `Could not reach Groq: ${e.message}` });
      }
    }

    return json(404, { error: "not found" });
  },
};
