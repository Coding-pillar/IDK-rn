# XIAO ESP32S3 Sense ChatGPT Vision App

## What it does
- Takes a text prompt from serial input.
- Captures a camera image.
- Sends prompt + image to OpenAI Chat Completions.
- Prints the response.

## Setup
1. Copy `config.example.py` to `config.py`.
2. Fill in Wi-Fi credentials and API key.
3. Upload `main.py` and `config.py` to the board.

## mpremote example
```bash
mpremote connect auto fs cp main.py :main.py
mpremote connect auto fs cp config.py :config.py
mpremote connect auto run main.py
```

If camera init fails, your firmware may need different `camera.init(...)` settings.
