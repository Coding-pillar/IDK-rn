import os
import base64
import time
import cv2
from openai import OpenAI

try:
    import speech_recognition as sr
except ImportError:
    sr = None


def capture_frame_base64(camera_index=0, jpeg_quality=85):
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam")

    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError("Could not capture frame")

    encode_ok, buf = cv2.imencode(
        ".jpg",
        frame,
        [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)],
    )
    if not encode_ok:
        raise RuntimeError("Could not encode JPEG")

    return base64.b64encode(buf.tobytes()).decode("utf-8")


def ask_vision(prompt, image_b64, model="gpt-4.1-mini"):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY in your environment")

    client = OpenAI(api_key=api_key)

    resp = client.chat.completions.create(
        model=model,
        messages=[
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
        max_tokens=300,
    )

    return resp.choices[0].message.content


def wait_for_rate_limit(last_request_time, min_interval_seconds):
    if last_request_time is None:
        return
    elapsed = time.time() - last_request_time
    remaining = min_interval_seconds - elapsed
    if remaining > 0:
        print("Rate limit: waiting {:.1f}s before next API call...".format(remaining))
        time.sleep(remaining)


def get_typed_prompt():
    return input("Prompt> ").strip()


def get_voice_prompt(recognizer, microphone, timeout_s=6, phrase_time_limit_s=12):
    print("Listening... (say 'exit' to quit)")
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.4)
        audio = recognizer.listen(
            source,
            timeout=timeout_s,
            phrase_time_limit=phrase_time_limit_s,
        )
    text = recognizer.recognize_google(audio)
    print("Heard:", text)
    return text.strip()


def wait_for_wake_word(recognizer, microphone, wake_word, timeout_s=4, phrase_time_limit_s=4):
    print("Waiting for wake word: '{}'".format(wake_word))
    while True:
        try:
            with microphone as source:
                audio = recognizer.listen(
                    source,
                    timeout=timeout_s,
                    phrase_time_limit=phrase_time_limit_s,
                )
            heard = recognizer.recognize_google(audio).strip().lower()
            if heard:
                print("Heard:", heard)
            if "exit" in heard:
                return "exit"
            if wake_word in heard:
                print("Wake word detected. Listening for prompt...")
                return "wake"
        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            continue
        except Exception as exc:
            print("Wake-word input error:", exc)
            continue


def main():
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    min_interval = float(os.getenv("OPENAI_MIN_SECONDS_BETWEEN_REQUESTS", "10"))
    voice_mode = os.getenv("VOICE_MODE", "0").strip().lower() in ("1", "true", "yes")
    wake_word_mode = os.getenv("WAKE_WORD_MODE", "1").strip().lower() in ("1", "true", "yes")
    wake_word = os.getenv("WAKE_WORD", "hey chat gpt").strip().lower()
    last_request_time = None
    recognizer = None
    microphone = None

    if voice_mode:
        if sr is None:
            raise RuntimeError(
                "VOICE_MODE is enabled but SpeechRecognition is not installed. "
                "Run: pip install SpeechRecognition pyaudio"
            )
        recognizer = sr.Recognizer()
        try:
            microphone = sr.Microphone()
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.8)
        except Exception as exc:
            raise RuntimeError("Could not access microphone: {}".format(exc))

    print("PC webcam vision tester")
    if voice_mode:
        print("Voice mode enabled.")
        if wake_word_mode:
            print("Wake-word mode enabled. Say '{}' to start prompt capture.".format(wake_word))
            print("Say 'exit' to quit.")
        else:
            print("Speak your prompt directly. Say 'exit' to quit.")
    else:
        print("Type a prompt and press Enter. Type 'exit' to quit.")
    print("Minimum seconds between API calls:", min_interval)

    while True:
        try:
            if voice_mode:
                if wake_word_mode:
                    wake_state = wait_for_wake_word(recognizer, microphone, wake_word)
                    if wake_state == "exit":
                        break
                    prompt = get_voice_prompt(recognizer, microphone)
                else:
                    prompt = get_voice_prompt(recognizer, microphone)
            else:
                prompt = get_typed_prompt()
        except Exception as exc:
            print("Input error:", exc)
            continue

        if not prompt:
            continue
        if prompt.lower() == "exit":
            break

        try:
            image_b64 = capture_frame_base64()
            wait_for_rate_limit(last_request_time, min_interval)
            answer = ask_vision(prompt, image_b64, model=model)
            last_request_time = time.time()
            print("\nAssistant:\n{}\n".format(answer))
        except Exception as exc:
            print("Error:", exc)


if __name__ == "__main__":
    main()
