"""Open Assistant: a personal AI assistant that runs on YOUR computer.
Bring your own API key (Gemini or Claude). See README.md."""
import os, hmac, platform, secrets, socket, subprocess, threading, webbrowser
from flask import Flask, request, jsonify, send_from_directory

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

OS = platform.system()
HERE = os.path.dirname(os.path.abspath(__file__))
LANG = os.environ.get("ASSISTANT_LANG", "Hinglish")
HOST = os.environ.get("HOST", "127.0.0.1")  # 0.0.0.0 = phone/LAN se bhi chale
PORT = int(os.environ.get("PORT", "5000"))


def load_token():
    """Secret token: browser ko link ke saath milta hai, dusri websites ise nahi jaan sakti."""
    if os.environ.get("ASSISTANT_PIN"):
        return os.environ["ASSISTANT_PIN"]
    f = os.path.join(HERE, ".token")
    if os.path.exists(f):
        t = open(f).read().strip()
        if t:
            return t
    t = secrets.token_urlsafe(12)
    open(f, "w").write(t)
    return t


PIN = load_token()

SYSTEM = f"""You are a personal AI assistant running on the user's {OS} computer.
Reply in {LANG}, short and friendly (replies may be read aloud, so avoid long text and markdown).
Give ideas, ask questions, and use your tools to do tasks on the computer when needed.
Before doing anything risky (deleting, formatting, system changes), say clearly what you will do."""

# (name, description, [string params - all required])
TOOLS = [
    ("run_command", "Run a shell command on the computer and return its output.", ["command"]),
    ("open_target", "Open a website URL, an app by name, or a file/folder.", ["target"]),
    ("read_file", "Read a text file.", ["path"]),
    ("write_file", "Write text to a file (overwrites).", ["path", "content"]),
]


class Claude:
    def __init__(self):
        import anthropic
        self.c = anthropic.Anthropic()
        self.model = os.environ.get("MODEL", "claude-sonnet-5-5")
        self.tools = [{"name": n, "description": d,
                       "input_schema": {"type": "object", "properties": {p: {"type": "string"} for p in ps},
                                        "required": ps}} for n, d, ps in TOOLS]
        self.h = []

    def user(self, t):
        self.h.append({"role": "user", "content": t})

    def gen(self):
        r = self.c.messages.create(model=self.model, max_tokens=1500, system=SYSTEM,
                                   tools=self.tools, messages=self.h)
        self.h.append({"role": "assistant", "content": r.content})
        text = "".join(b.text for b in r.content if b.type == "text")
        return text, [(b.id, b.name, dict(b.input)) for b in r.content if b.type == "tool_use"]

    def results(self, rs):
        self.h.append({"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": i, "content": t} for i, n, t in rs]})


class Gemini:
    def __init__(self):
        from google import genai
        from google.genai import types
        self.t, self.c = types, genai.Client()
        self.model = os.environ.get("MODEL", "gemini-2.5-flash")
        decls = [types.FunctionDeclaration(
            name=n, description=d,
            parameters={"type": "OBJECT", "properties": {p: {"type": "STRING"} for p in ps}, "required": ps})
            for n, d, ps in TOOLS]
        self.cfg = types.GenerateContentConfig(
            system_instruction=SYSTEM, tools=[types.Tool(function_declarations=decls)],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
        self.h = []

    def user(self, t):
        self.h.append(self.t.Content(role="user", parts=[self.t.Part(text=t)]))

    def gen(self):
        r = self.c.models.generate_content(model=self.model, contents=self.h, config=self.cfg)
        if not r.candidates or not r.candidates[0].content:
            return "(Model ne jawab nahi diya, dobara try karo.)", []
        c = r.candidates[0].content
        self.h.append(c)
        ps = c.parts or []
        return ("".join(p.text for p in ps if p.text),
                [(p.function_call.name, p.function_call.name, dict(p.function_call.args or {}))
                 for p in ps if p.function_call])

    def results(self, rs):
        self.h.append(self.t.Content(role="user", parts=[
            self.t.Part.from_function_response(name=n, response={"result": t}) for i, n, t in rs]))


def pick():
    p = os.environ.get("PROVIDER", "").lower()
    if not p:
        if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
            p = "gemini"
        elif os.environ.get("ANTHROPIC_API_KEY"):
            p = "claude"
        else:
            return None  # key baad mein Settings (⚙️) se daali jayegi
    try:
        return Gemini() if p == "gemini" else Claude()
    except Exception:
        return None


P = pick()
app = Flask(__name__)
pending = None


def needs_ok(name, args):
    if name == "read_file":
        return False
    if name == "open_target" and args.get("target", "").startswith("http"):
        return False
    return True  # commands, file writes, apps: ask the user first


def execute(name, a):
    try:
        if name == "run_command":
            r = subprocess.run(a["command"], shell=True, capture_output=True, text=True, timeout=60)
            return ((r.stdout or "") + (r.stderr or ""))[-4000:] or "Done (no output)."
        if name == "open_target":
            t = a["target"]
            if t.startswith("http"):
                webbrowser.open(t)
            elif OS == "Windows":
                os.startfile(t)
            elif OS == "Darwin":
                subprocess.Popen(["open", t] if os.path.exists(t) else ["open", "-a", t])
            else:
                subprocess.Popen(["xdg-open", t] if os.path.exists(t) else [t])
            return "Opened."
        if name == "read_file":
            with open(os.path.expanduser(a["path"]), encoding="utf-8", errors="replace") as f:
                return f.read(20000)
        if name == "write_file":
            with open(os.path.expanduser(a["path"]), "w", encoding="utf-8") as f:
                f.write(a["content"])
            return "File saved."
    except Exception as e:
        return f"Error: {e}"
    return "Unknown tool"


def run_tools(calls, results):
    global pending
    while calls:
        i, name, args = calls[0]
        if needs_ok(name, args):
            pending = {"calls": calls, "results": results}
            return {"approve": {"tool": name, "input": args}}
        results.append((i, name, execute(name, args)))
        calls.pop(0)
    P.results(results)
    return None


def loop():
    for _ in range(10):
        text, calls = P.gen()
        if not calls:
            return {"reply": text}
        out = run_tools(calls, [])
        if out:
            return out
    return {"reply": "Kaam bahut lamba ho gaya, yahin rok raha hoon."}


@app.before_request
def auth():
    if request.path.startswith("/api/") and not hmac.compare_digest(request.headers.get("X-PIN", ""), PIN):
        return jsonify(error="Galat PIN"), 401


@app.post("/api/chat")
def chat():
    global pending
    pending = None
    if P is None:
        return jsonify(reply="Pehle ⚙️ Settings mein API key daalo.")
    n = len(P.h)
    P.user(request.json["text"])
    try:
        return jsonify(loop())
    except Exception as e:
        del P.h[n:]
        return jsonify(reply=f"Error: {e}")


@app.post("/api/approve")
def approve():
    global pending
    if not pending:
        return jsonify(reply="Kuch pending nahi hai.")
    p, pending = pending, None
    i, name, args = p["calls"].pop(0)
    p["results"].append((i, name, execute(name, args) if request.json["ok"] else "User ne mana kar diya."))
    try:
        return jsonify(run_tools(p["calls"], p["results"]) or loop())
    except Exception as e:
        return jsonify(reply=f"Error: {e}")


@app.post("/api/reset")
def reset():
    global pending
    if P:
        P.h.clear()
    pending = None
    return jsonify(ok=True)


def set_env(k, v):
    path = os.path.join(HERE, ".env")
    lines = open(path, encoding="utf-8").read().splitlines() if os.path.exists(path) else []
    lines = [l for l in lines if not l.startswith(k + "=")] + [f"{k}={v}"]
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    os.environ[k] = v


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except Exception:
        return "computer-ka-IP"
    finally:
        s.close()


@app.get("/api/status")
def status():
    open_ = HOST != "127.0.0.1"
    return jsonify(ready=P is not None, provider=type(P).__name__ if P else None,
                   model=P.model if P else None, host_open=open_,
                   phone=f"http://{lan_ip()}:{PORT}/?t={PIN}" if open_ else None)


@app.post("/api/settings")
def settings():
    global P, pending
    d = request.json or {}
    key = (d.get("key") or "").strip().strip("\"'")
    if key:
        if d.get("provider") not in ("gemini", "claude") or "\n" in key or "\r" in key:
            return jsonify(ok=False, error="Key ya provider galat hai")
        set_env("GEMINI_API_KEY" if d["provider"] == "gemini" else "ANTHROPIC_API_KEY", key)
        set_env("PROVIDER", d["provider"])
        P, pending = pick(), None
    if "phone" in d:
        set_env("HOST", "0.0.0.0" if d["phone"] else "127.0.0.1")
    return jsonify(ok=P is not None, error=None if P else "Key daalo aur Save dabao")


@app.get("/")
def index():
    return send_from_directory(HERE, "index.html")


if __name__ == "__main__":
    url = f"http://localhost:{PORT}/?t={PIN}"
    print("\n=== Open Assistant chal raha hai ===")
    print("Browser apne aap khulega. Na khule to ye link kholo:\n" + url)
    print("\nIs window ko band mat karna (band karoge to assistant band ho jayega).")
    if HOST != "127.0.0.1":
        print("WARNING: Server network par khula hai. Sirf apne Wi-Fi/VPN par use karo, internet par kabhi nahi.")
    if os.environ.get("NO_BROWSER") != "1":
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(host=HOST, port=PORT)
