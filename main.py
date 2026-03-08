import gc
import time
import network
import ujson
import ubinascii
import urequests
from machine import Pin

try:
    import camera
except ImportError:
    raise RuntimeError("camera module not found. Install camera-enabled ESP32-S3 MicroPython firmware.")

from config import WIFI_SSID, WIFI_PASSWORD, OPENAI_API_KEY, MODEL

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
MAX_TOKENS = 250
MIN_SECONDS_BETWEEN_REQUESTS = 10
BUTTON_PINS = (1, 2)
last_request_ts = None


def connect_wifi(timeout_s=20):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return wlan
    print("Connecting Wi-Fi...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    start = time.time()
    while not wlan.isconnected():
        if time.time() - start > timeout_s:
            raise RuntimeError("Wi-Fi timeout")
        time.sleep(0.4)
    print("Wi-Fi:", wlan.ifconfig()[0])
    return wlan


def init_camera():
    ok = camera.init(
        0,
        format=camera.JPEG,
        framesize=camera.FRAME_QVGA,
        xclk_freq=camera.XCLK_20MHz,
        fb_location=camera.PSRAM,
        quality=12,
    )
    if not ok:
        raise RuntimeError("Camera init failed")
    print("Camera ready")


def capture_base64_jpeg():
    img = camera.capture()
    if not img:
        raise RuntimeError("Camera capture failed")
    b64 = ubinascii.b2a_base64(img).decode("utf-8").strip()
    return b64, len(img)


def ask_openai(prompt, image_b64):
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(OPENAI_API_KEY),
    }
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/jpeg;base64," + image_b64},
                    },
                ],
            }
        ],
        "max_tokens": MAX_TOKENS,
    }

    resp = None
    try:
        resp = urequests.post(OPENAI_URL, headers=headers, data=ujson.dumps(payload))
        if resp.status_code != 200:
            body = resp.text
            if resp.status_code == 429 and "insufficient_quota" in body:
                raise RuntimeError(
                    "OpenAI quota exceeded (insufficient_quota). Add billing/credits, then retry."
                )
            raise RuntimeError("OpenAI {}: {}".format(resp.status_code, body))
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    finally:
        if resp is not None:
            resp.close()


def init_buttons():
    buttons = []
    for pin_num in BUTTON_PINS:
        try:
            buttons.append((pin_num, Pin(pin_num, Pin.IN, Pin.PULL_UP)))
        except Exception as exc:
            print("Warning: GPIO{} unavailable: {}".format(pin_num, exc))
    if not buttons:
        raise RuntimeError("No valid button pins. Check BUTTON_PINS.")
    return buttons


def wait_for_button_press(buttons):
    print("Press button on GPIO1 or GPIO2 to start...")
    while True:
        for pin_num, btn in buttons:
            if btn.value() == 0:
                time.sleep_ms(30)
                if btn.value() == 0:
                    while btn.value() == 0:
                        time.sleep_ms(10)
                    print("Button trigger: GPIO{}".format(pin_num))
                    return pin_num
        time.sleep_ms(20)


def loop():
    global last_request_ts
    buttons = init_buttons()
    print("Button trigger enabled on GPIO1/GPIO2 (active-low, pull-up).")
    print("Min seconds between API calls:", MIN_SECONDS_BETWEEN_REQUESTS)
    while True:
        wait_for_button_press(buttons)
        prompt = input("Prompt> ").strip()
        if not prompt:
            continue
        if prompt.lower() == "exit":
            return
        try:
            gc.collect()
            image_b64, size = capture_base64_jpeg()
            print("Captured:", size, "bytes")
            if last_request_ts is not None:
                elapsed = time.time() - last_request_ts
                if elapsed < MIN_SECONDS_BETWEEN_REQUESTS:
                    wait_s = MIN_SECONDS_BETWEEN_REQUESTS - elapsed
                    print("Rate limit wait:", wait_s, "s")
                    time.sleep(wait_s)
            reply = ask_openai(prompt, image_b64)
            last_request_ts = time.time()
            print("\nAssistant:\n{}\n".format(reply))
        except Exception as e:
            print("Error:", e)


if __name__ == "__main__":
    connect_wifi()
    init_camera()
    loop()
