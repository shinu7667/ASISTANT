# Open Assistant 🤖

A personal AI assistant that runs on **your own computer** and opens in your browser (phone too).
It talks (voice in/out), gives ideas, and can control your computer: run commands, open apps/sites, read and write files.

**Bring your own API key.** Nothing is hosted for you and no key is shared. Works with:
- **Google Gemini** – key from https://aistudio.google.com/apikey (has a free tier)
- **Anthropic Claude** – key from https://console.anthropic.com

## Easiest way (no terminal)

1. Extract the zip.
2. **Windows:** double-click `Start Assistant.bat`. **Mac:** right-click `Start Assistant.command` > Open (first time only).
   The first run installs what it needs (1-2 minutes, needs internet; on Windows it also tries to install Python for you).
3. Your browser opens. Click **⚙️ Settings**, paste your API key, press Save. Done!

Tip: right-click the launcher > *Send to > Desktop (create shortcut)* for a desktop icon. Closing the black window stops the assistant.

## Manual start (terminal)

1. Install Python 3.9+ and download this folder.
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and paste your key (only one provider is needed):
   ```
   GEMINI_API_KEY=your-key-here
   ```
4. Run:
   ```
   python server.py
   ```
5. Your browser opens automatically (or open the link printed in the terminal).

(Hindi: `.env` file mein apni key daalo, `python server.py` chalao, browser mein `localhost:5000` kholo.)

## Use it from your phone

- Set `HOST=0.0.0.0` in `.env`, restart, and open `http://<your-computer-IP>:5000` on the same Wi-Fi.
- For use outside home, use a private VPN such as [Tailscale](https://tailscale.com). **Do not port-forward this to the internet.**
- Browsers only allow the microphone on HTTPS or localhost. Over plain Wi-Fi HTTP use your keyboard's mic button, or serve it over HTTPS (e.g. `tailscale serve`).

## Safety (please read)

This app can run commands on your computer. Because of that:
- Every command, file write, and app launch needs your **explicit approval** (✅/❌) in the UI.
- Anyone with your PIN and network access to the server can chat with it. Use a strong `ASSISTANT_PIN`, keep `HOST` at the default unless you need phone access, and never expose it to the public internet.
- The AI can make mistakes. Read the command before approving.
- Never commit your `.env` file (it is in `.gitignore`).

## Customize

- Language/personality: edit `SYSTEM` in `server.py` or set `ASSISTANT_LANG`.
- Voice language: change `hi-IN` in `index.html` (two places: `rec.lang` and `u.lang`), e.g. `en-US`.
- Add tools: add an entry to `TOOLS` and a branch in `execute()` in `server.py`.
- Different model: set `MODEL` in `.env`.

## Contributing

PRs welcome: hands-free wake word, more tools, more providers (OpenAI, Ollama for fully offline), better UI.

## License

MIT. See `LICENSE`.
