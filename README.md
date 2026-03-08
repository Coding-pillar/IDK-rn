# XIAO ESP32S3 Sense ChatGPT Vision App

## What it does
- XIAO mode (`main.py`): waits for a button trigger on GPIO1 or GPIO2, then takes a serial prompt.
- Captures a camera image.
- Sends prompt + image to OpenAI Chat Completions.
- Prints the response.
- Applies client-side API rate limiting.

## Setup
1. Copy `config.example.py` to `config.py`.
2. Fill in Wi-Fi credentials and API key.
3. Upload `main.py` and `config.py` to the board.
4. Open serial monitor:
   - press button connected to GPIO1 or GPIO2
   - then enter your prompt

## Button wiring (XIAO)
- Connect one side of a momentary button to `GPIO1` or `GPIO2`.
- Connect the other side to `GND`.
- Internal pull-up is enabled in software (active-low press).

## mpremote example
```bash
mpremote connect auto fs cp main.py :main.py
mpremote connect auto fs cp config.py :config.py
mpremote connect auto run main.py
```

## PC voice wake word (`pc_test.py`)
- Install deps:
```bash
pip install -r requirements-pc.txt
```
- Run with wake word mode:
```bash
set OPENAI_API_KEY=your_key
set VOICE_MODE=1
set WAKE_WORD_MODE=1
set WAKE_WORD=hey chat gpt
python pc_test.py
```

When you say the wake word, the app listens for your prompt, captures webcam image, and sends it.

If camera init fails, your firmware may need different `camera.init(...)` settings.
