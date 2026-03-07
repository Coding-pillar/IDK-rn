import gc
import time
import network
import ujson
import ubinascii
import urequests

try:
    import camera
except ImportError:
    raise RuntimeError("camera module not found. Install camera-enabled ESP32-S3 MicroPython firmware.")

from config import WIFI_SSID, WIFI_PASSWORD, OPENAI_API_KEY, MODEL

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
MAX_TOKENS = 250


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
            raise RuntimeError("OpenAI {}: {}".format(resp.status_code, resp.text))
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    finally:
        if resp is not None:
            resp.close()


def loop():
    print("Enter prompt. Type exit to stop.")
    while True:
        prompt = input("Prompt> ").strip()
        if not prompt:
            continue
        if prompt.lower() == "exit":
            return
        try:
            gc.collect()
            image_b64, size = capture_base64_jpeg()
            print("Captured:", size, "bytes")
            reply = ask_openai(prompt, image_b64)
            print("\nAssistant:\n{}\n".format(reply))
        except Exception as e:
            print("Error:", e)


if __name__ == "__main__":
    connect_wifi()
    init_camera()
    loop()
