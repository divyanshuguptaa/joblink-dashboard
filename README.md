# JobLink Placement Dashboard

A filterable dashboard of the 104-person JobLink cohort and their 49 job placements,
with a screenshot-reading chart assistant powered by Groq.

## Files

- `dashboard.html` — the dashboard (all data embedded; no build step)
- `index.html` — the same page wrapped as a standalone document, for static hosts
  like GitHub Pages
- `serve.py` — a tiny server that hosts the page **and** holds your Groq API
  key so the browser never sees it
- `render.yaml` — one-click deploy blueprint for Render (dashboard + assistant
  in the cloud)

## Hosted versions

- **GitHub Pages** (always on, no assistant): the repo's Pages URL serves
  `index.html` — every chart and filter works; the chat assistant stays hidden
  because there is no server holding a key.
- **Render** (always on, WITH assistant): click "New +" → "Blueprint" at
  https://dashboard.render.com, point it at this repo, and set `GROQ_API_KEY`
  when prompted. Free tier works (the service sleeps when idle and wakes on
  visit).

## Running it with the assistant

The assistant needs `serve.py` running, because a browser page cannot call the Groq
API directly (and embedding a key in a shared page would leak it). The key lives in
your shell environment only:

```bash
export GROQ_API_KEY=gsk_your_new_key_here
python3 serve.py
```

Then open **http://localhost:8765**. A chat button appears in the bottom-right.

- **Attach a chart:** click the paperclip, paste (`⌘V`) a screenshot, or drag one in.
  On a Mac, `⌘⇧4` grabs a screen region to the clipboard.
- Ask a question and send. The assistant reads the image and also knows the live
  filter state, so it can tell you when a screenshot is of a different selection.

Model: `meta-llama/llama-4-scout-17b-16e-instruct` (Groq's vision model).

## Opening the page WITHOUT the server

Opening `dashboard.html` straight from disk (or publishing it) works fine — every
chart and filter runs client-side. The assistant simply doesn't appear, because it
checks for the local server first. Nothing breaks.

## Security notes

- **Rotate the key that was shared in chat** at https://console.groq.com — a key
  that has been pasted into a message should be treated as compromised.
- The key is read from `GROQ_API_KEY` at runtime. It is **not** stored in any file
  in this folder. Keep it that way — never commit a key.
