import os
import socket
import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
import json
import time

from python_a2a import (
    AgentCard,
    AgentSkill,
    Message,
    TextContent,
    MessageRole,
    run_server,
)


from basic_agent import BasicAgent
from llm_client import LLMClient


from dotenv import load_dotenv

load_dotenv(".env", override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_free_port() -> int:
    """Find an available port to use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", 0))
        return s.getsockname()[1]


class AssesorAgent(BasicAgent):
    def __init__(
        self,
        name: str = None,
        description: str = None,
        url: str = None,
        registry_url: str = None,
    ):
        # Set default values if not provided
        name = name or "AssessorAgent"
        description = (
            description
            or "An agent that assesses if text relates to presentation content"
        )
        url = url or f"http://localhost:{find_free_port()}"
        registry_url = registry_url or os.getenv(
            "REGISTRY_URL", "http://localhost:8000"
        )

        # Initialize the basic agent first
        super().__init__(
            name=name,
            description=description,
            url=url,
            registry_url=registry_url,
        )

        # Create a sample skill for the agent
        skill = AgentSkill(
            id="text_assessment",
            name="assessing text relevance to presentation",
            description="Returns a binary decision if a sentence relates to a presentation.",
            tags=["assessment", "presentation"],
            examples=[
                {
                    "input": {"sentence": "i want to learn about math"},
                    "output": {"assessment": "yes"},
                },
                {
                    "input": {"sentence": "hi"},
                    "output": {"assessment": "no"},
                },
            ],
        )

        # Create agent card with skills and capabilities
        self.agent_card = AgentCard(
            name=name,
            description=description,
            url=url,
            version="1.0.0",
            skills=[skill],
            capabilities={
                "streaming": True,
                "pushNotifications": False,
                "stateTransitionHistory": False,
                "google_a2a_compatible": True,
                "parts_array_format": True,
            },
        )

        self.llm_client = None  # Initialize LLM client to None

        # Background processing setup
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.processing_results = {}  # Store results for correlation
        self.processing_lock = threading.Lock()

    def categorize_message(self, message: str) -> dict:
        """Categorize a message using LLM - runs in background thread"""
        try:
            if self.llm_client is None:
                self.llm_client = LLMClient().get_client()

            response = self.llm_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """Your role is to tell if a sentence relates to the content of a presentation. 
                        Respond with a JSON object containing 'assessment' with values 'yes' or 'no'.""",
                    },
                    {"role": "user", "content": message},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
            choice = response.choices[0].message.content
            return json.loads(choice)
        except Exception as e:
            logger.error(f"Error categorizing message: {e}")
            return {"assessment": "error", "error": str(e)}

    def _process_message_async(self, message_id: str, user_message: str):
        """Process message categorization in background thread"""
        try:
            logger.info(f"Starting background categorization for message: {message_id}")
            result = self.categorize_message(user_message)

            with self.processing_lock:
                self.processing_results[message_id] = {
                    "result": result,
                    "timestamp": time.time(),
                    "processed": True,
                }

            logger.info(
                f"Completed categorization for message: {message_id}, result: {result}"
            )
        except Exception as e:
            logger.error(
                f"Error in background processing for message {message_id}: {e}"
            )
            with self.processing_lock:
                self.processing_results[message_id] = {
                    "result": {"assessment": "error", "error": str(e)},
                    "timestamp": time.time(),
                    "processed": True,
                }

    def get_categorization_result(self, message_id: str) -> dict:
        """Get the result of a categorization task"""
        with self.processing_lock:
            if message_id in self.processing_results:
                result = self.processing_results[message_id]
                if result.get("processed"):
                    return result["result"]
                else:
                    return {"assessment": "processing", "message_id": message_id}
            else:
                return {"assessment": "not_found", "message_id": message_id}

    def handle_message(self, message: Message) -> Message:
        """Enhanced message handler with non-blocking categorization"""
        user_message = message.content.text
        print(f"Message received: {user_message}")

        # Generate unique ID for tracking this message
        message_id = str(uuid.uuid4())

        # Submit categorization task to background thread
        future = self.executor.submit(
            self._process_message_async, message_id, user_message
        )

        # Store initial tracking info
        with self.processing_lock:
            self.processing_results[message_id] = {
                "future": future,
                "original_message": user_message,
                "timestamp": time.time(),
                "processed": False,
            }

        # Return immediate response - categorization happens in background
        response_text = (
            f"Message received and queued for categorization (ID: {message_id})"
        )
        return Message(
            content=TextContent(text=response_text),
            role=MessageRole.AGENT,
            parent_message_id=message.message_id,
            conversation_id=message.conversation_id,
        )

    def cleanup_old_results(self, max_age_hours=24):
        """Clean up old processing results to prevent memory leaks"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600

        with self.processing_lock:
            to_remove = []
            for message_id, data in self.processing_results.items():
                if current_time - data["timestamp"] > max_age_seconds:
                    to_remove.append(message_id)

            for message_id in to_remove:
                del self.processing_results[message_id]

            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old processing results")


def run_agent(name: str = None, port: int = None, registry_url: str = None):
    """Runs a sample agent that registers with the specified registry."""

    # Use provided port or find a free one
    if port is None:
        port = find_free_port()

    # Create and setup the agent
    agent = AssesorAgent(
        name=name or "SamplePoetryAgent",
        description=f"Sample agent '{name or 'SamplePoetryAgent'}' that can write poetry and route messages.",
        url=f"http://localhost:{port}",
        registry_url=registry_url or os.getenv("REGISTRY_URL", "http://localhost:8000"),
    )

    # Setup the agent (register with registry)
    import asyncio

    asyncio.run(agent.setup())

    # Start the server
    logger.info(f"Starting agent '{agent.agent_card.name}' on http://localhost:{port}")
    run_server(agent, host="0.0.0.0", port=port)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sample A2A Agent")
    parser.add_argument(
        "--name",
        type=str,
        default="SamplePoetryAgent",
        help="Name of the agent",
    )
    parser.add_argument(
        "--port", type=int, default=None, help="Port for the agent to run on"
    )
    parser.add_argument(
        "--registry-url",
        type=str,
        default=None,
        help="URL of the agent registry server",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run a simple demo without starting the server",
    )

    args = parser.parse_args()
    run_agent(args.name, args.port, args.registry_url)

# Example usage:
# uv run src/assessor_agent.py --name "AssessorAgent" --port 8001 --registry-url "http://localhost:8000"
