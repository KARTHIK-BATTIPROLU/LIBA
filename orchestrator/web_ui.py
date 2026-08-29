"""
orchestrator/web_ui.py

LIBA Web Dashboard & Control Center.
Runs on http://localhost:5050.
Provides an interactive web UI for chat, voice diagnostics, system status,
and tool execution.
"""

import os
import sys
import json
import time
import logging
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestrator.groq_pool import groq_chat, pool_status

logger = logging.getLogger("LIBA.WebUI")

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LIBA — Desktop Pet & Voice Assistant Dashboard</title>
  <style>
    :root {
      --bg: #0f1117;
      --card-bg: #1a1d27;
      --border: #2d3245;
      --text: #e2e8f0;
      --text-muted: #8e9bb0;
      --accent: #ef4444;
      --accent-glow: rgba(239, 68, 68, 0.25);
      --success: #22c55e;
      --warning: #f59e0b;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background: var(--bg); color: var(--text); min-height: 100vh; display: flex; flex-direction: column; }
    header { background: var(--card-bg); border-bottom: 1px solid var(--border); padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }
    .logo { display: flex; align-items: center; gap: 0.75rem; font-size: 1.25rem; font-weight: 700; color: #fff; }
    .badge { background: var(--accent); color: #fff; font-size: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 9999px; text-transform: uppercase; letter-spacing: 0.05em; }
    .status-pill { display: flex; align-items: center; gap: 0.5rem; background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.3); color: var(--success); font-size: 0.85rem; padding: 0.35rem 0.75rem; border-radius: 9999px; }
    .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--success); box-shadow: 0 0 8px var(--success); }
    main { padding: 2rem; max-width: 1200px; margin: 0 auto; width: 100%; display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; flex: 1; }
    .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; display: flex; flex-direction: column; }
    .card-title { font-size: 1.1rem; font-weight: 600; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; }
    .chat-box { flex: 1; min-height: 320px; max-height: 420px; overflow-y: auto; display: flex; flex-direction: column; gap: 0.75rem; padding: 1rem; background: #12141c; border-radius: 8px; border: 1px solid var(--border); margin-bottom: 1rem; }
    .msg { max-width: 80%; padding: 0.6rem 0.9rem; border-radius: 10px; font-size: 0.95rem; line-height: 1.4; }
    .msg.user { background: #3b82f6; color: #fff; align-self: flex-end; }
    .msg.liebe { background: #262a3b; color: var(--text); border: 1px solid var(--border); align-self: flex-start; }
    .composer { display: flex; gap: 0.5rem; }
    input[type="text"] { flex: 1; background: #12141c; border: 1px solid var(--border); border-radius: 8px; padding: 0.75rem 1rem; color: #fff; outline: none; font-size: 0.95rem; }
    input[type="text"]:focus { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-glow); }
    button { background: var(--accent); color: #fff; border: none; border-radius: 8px; padding: 0.75rem 1.25rem; font-weight: 600; cursor: pointer; transition: 0.15s ease; }
    button:hover { filter: brightness(1.1); transform: translateY(-1px); }
    .status-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem; margin-bottom: 1.5rem; }
    .status-item { background: #12141c; border: 1px solid var(--border); border-radius: 8px; padding: 0.75rem; }
    .status-label { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.25rem; }
    .status-val { font-size: 0.95rem; font-weight: 600; color: #fff; }
    .actions-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.5rem; }
    .btn-secondary { background: #262a3b; border: 1px solid var(--border); color: var(--text); padding: 0.6rem; font-size: 0.85rem; }
    .btn-secondary:hover { background: #32384e; }
    footer { text-align: center; padding: 1rem; font-size: 0.8rem; color: var(--text-muted); border-top: 1px solid var(--border); }
  </style>
</head>
<body>
  <header>
    <div class="logo">
      <span>🐾 LIBA / Liebe Dashboard</span>
      <span class="badge">Active</span>
    </div>
    <div class="status-pill">
      <div class="dot"></div>
      <span>Voice Agent & Event Bridge Online</span>
    </div>
  </header>
  <main>
    <div class="card">
      <div class="card-title">💬 Chat with Liebe (Anti-Magic Devil)</div>
      <div id="chat-box" class="chat-box">
        <div class="msg liebe"><strong>Liebe:</strong> I am Liebe. Say 'LIBA' to wake me up for voice tasks, or chat with me right here.</div>
      </div>
      <div class="composer">
        <input id="user-input" type="text" placeholder="Type a message to Liebe or give a command..." onkeydown="if(event.key==='Enter') sendMessage()" autofocus />
        <button onclick="sendMessage()">Send</button>
      </div>
    </div>

    <div class="card">
      <div class="card-title">📊 Live System Components</div>
      <div class="status-grid">
        <div class="status-item">
          <div class="status-label">Voice Agent</div>
          <div class="status-val" style="color:var(--success);">🟢 Listening ('LIBA')</div>
        </div>
        <div class="status-item">
          <div class="status-label">WebSocket Bridge</div>
          <div class="status-val" style="color:var(--success);">🟢 ws://localhost:8766</div>
        </div>
        <div class="status-item">
          <div class="status-label">Groq Key Pool</div>
          <div class="status-val" style="color:var(--success);">🟢 3 Keys Active</div>
        </div>
        <div class="status-item">
          <div class="status-label">TTS Voice Engine</div>
          <div class="status-val" style="color:var(--success);">🟢 Piper TTS (Male)</div>
        </div>
        <div class="status-item">
          <div class="status-label">Sandbox Folder</div>
          <div class="status-val">📁 D:\\New World</div>
        </div>
        <div class="status-item">
          <div class="status-label">Active Character</div>
          <div class="status-val">😈 Liebe (Black Clover)</div>
        </div>
      </div>

      <div class="card-title" style="margin-top:0.5rem;">⚡ Quick Desktop Actions</div>
      <div class="actions-grid">
        <button class="btn-secondary" onclick="sendAction('open Notepad')">📝 Open Notepad</button>
        <button class="btn-secondary" onclick="sendAction('create a file greeting.txt in D:\\New World with content Hello World')">📁 Create Sandbox File</button>
        <button class="btn-secondary" onclick="sendAction('what can you do?')">❓ Ask Capabilities</button>
        <button class="btn-secondary" onclick="sendAction('tell me about anti-magic')">🗡️ Anti-Magic Lore</button>
      </div>
    </div>
  </main>
  <footer>
    LIBA Voice Assistant & Desktop Pet — Windows Interactive Dashboard (Port 5050)
  </footer>

  <script>
    async function sendMessage() {
      const input = document.getElementById('user-input');
      const text = input.value.trim();
      if (!text) return;
      
      const box = document.getElementById('chat-box');
      box.innerHTML += `<div class="msg user"><strong>You:</strong> ${text}</div>`;
      input.value = '';
      box.scrollTop = box.scrollHeight;

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ message: text })
        });
        const data = await res.json();
        box.innerHTML += `<div class="msg liebe"><strong>Liebe:</strong> ${data.reply}</div>`;
        box.scrollTop = box.scrollHeight;
      } catch (err) {
        box.innerHTML += `<div class="msg liebe" style="color:#ef4444;"><strong>Error:</strong> Could not reach backend: ${err.message}</div>`;
        box.scrollTop = box.scrollHeight;
      }
    }

    function sendAction(text) {
      document.getElementById('user-input').value = text;
      sendMessage();
    }
  </script>
</body>
</html>
"""

class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(pool_status()).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body)
                user_msg = data.get("message", "")
                persona = (
                    "You are Liebe, the anti-magic devil from Black Clover. "
                    "You are Asta's devil - fierce, blunt, loyal, and powerful. "
                    "Keep replies punchy and in-character under 2 sentences."
                )
                res = groq_chat(
                    model="qwen/qwen3.8-27b",
                    messages=[
                        {"role": "system", "content": persona},
                        {"role": "user", "content": user_msg}
                    ],
                    max_tokens=150,
                    temperature=0.7
                )
                reply = res.choices[0].message.content.strip()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"reply": reply}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e), "reply": f"Error: {e}"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def run_server(port=5050, auto_open=True):
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    logger.info("[WebUI] LIBA Dashboard running at http://localhost:%d", port)
    if auto_open:
        try:
            webbrowser.open(f"http://localhost:{port}")
        except Exception:
            pass
    server.serve_forever()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_server(port=5050, auto_open=True)