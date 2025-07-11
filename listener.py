import asyncio, os, time
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

load_dotenv()

speech_config = speechsdk.SpeechConfig(
    subscription=os.environ["AZURE_SPEECH_KEY"],
    region=os.environ["AZURE_SPEECH_REGION"],
)

# block for Polish language
speech_config.speech_recognition_language = "pl-PL"
speech_config.set_property(
    speechsdk.PropertyId.SpeechServiceResponse_PostProcessingOption, "TrueText"
)
# end of block for Polish language


audio_cfg = speechsdk.audio.AudioConfig(use_default_microphone=True)
recogniser = speechsdk.SpeechRecognizer(speech_config, audio_cfg)

results_q: asyncio.Queue[str] = asyncio.Queue()


# ── 1. GRAB a handle to the running loop (we’ll set it in main) ───────────────
loop: asyncio.AbstractEventLoop | None = None


# ── 2. Event handler: use call_soon_threadsafe OR run_coroutine_threadsafe ────
def on_recognized(evt: speechsdk.SpeechRecognitionEventArgs):
    if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech and loop:
        loop.call_soon_threadsafe(
            asyncio.create_task, results_q.put(evt.result.text.strip())
        )


def on_canceled(evt):  # keep your verbose logging here
    cd = evt.cancellation_details
    print("⛔ canceled:", cd.reason, cd.error_details)


recogniser.recognized.connect(on_recognized)
recogniser.canceled.connect(on_canceled)


# ── 3. Main coroutine ────────────────────────────────────────────────────────
async def main():
    global loop
    loop = asyncio.get_running_loop()
    recogniser.start_continuous_recognition()
    print("🎙️  Listening…  Ctrl-C to stop.")

    try:
        while True:
            text = await results_q.get()
            ts = time.strftime("%H:%M:%S")
            print(f"[{ts}]  {text}")
    except KeyboardInterrupt:
        await recogniser.stop_continuous_recognition_async()


if __name__ == "__main__":
    asyncio.run(main())
