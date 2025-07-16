import asyncio, os, time
import azure.cognitiveservices.speech as speechsdk
from python_a2a import A2AClient, Message, TextContent, MessageRole

from src.a2a_network import A2ANetwork

from dotenv import load_dotenv

load_dotenv()

speech_config = speechsdk.SpeechConfig(
    subscription=os.environ["AZURE_SPEECH_KEY"],
    region=os.environ["AZURE_SPEECH_REGION"],
)

# block for Polish language
# speech_config.speech_recognition_language = "pl-PL"
# speech_config.set_property(
#    speechsdk.PropertyId.SpeechServiceResponse_PostProcessingOption, "TrueText"
# )
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


def prep_a2a_message(text: str) -> Message:
    """Prepare a message for A2A communication."""
    return Message(
        content=TextContent(text=text),
        role=MessageRole.USER,  # Changed from AGENT to USER for proper flow
        parent_message_id=None,  # Use None instead of "none"
        conversation_id="default-conversation",  # Better conversation ID
    )


recogniser.recognized.connect(on_recognized)
recogniser.canceled.connect(on_canceled)

network_registry_url = "http://localhost:8000"  # Replace with your actual registry URL
network = A2ANetwork(network_registry_url)
query = "assess if a sentence relates to the content of a presentation"
best_agent_url = network.find_best_agent(query)
asessors_client = A2AClient(best_agent_url)


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

            message_to_assesor = prep_a2a_message(text)
            try:
                # Use async/await properly instead of run_in_executor
                response = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: asessors_client.send_message(message_to_assesor)
                )
                print(f"Response from assessor: {response}")
            except Exception as e:
                print(f"Error sending message to assessor: {e}")

    except KeyboardInterrupt:
        await recogniser.stop_continuous_recognition_async()


if __name__ == "__main__":
    asyncio.run(main())
