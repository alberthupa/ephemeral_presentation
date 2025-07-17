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

    def get_categorization_result(self, message_id: str) -> dict:
        # Get the result of a categorization task
        """
        The `get_categorization_result()` method is used to retrieve the results of background message categorization after the initial response has been sent. Here's how it works:

        ## Usage Pattern:

        1. **First**: `handle_message()` returns immediately with a message ID
        2. **Later**: Use `get_categorization_result(message_id)` to check the actual categorization result

        ## Example Usage:

        ```python
        # 1. Agent receives a message
        message = Message(content=TextContent(text="I want to learn about data science presentations"))
        response = agent.handle_message(message)
        # response.content.text = "Message received and queued for categorization (ID: abc-123-def)"

        # 2. After some time (seconds to minutes), check the result
        result = agent.get_categorization_result("abc-123-def")
        # Returns one of:
        # {"assessment": "yes"} - message relates to presentations
        # {"assessment": "no"} - message doesn't relate to presentations
        # {"assessment": "processing"} - still being processed
        # {"assessment": "error", "error": "..."} - processing failed
        # {"assessment": "not_found"} - message ID doesn't exist
        ```

        ## Integration Options:

        The method can be used in several ways:

        1. **Polling**: Periodically check results
        2. **Callback system**: Another agent could query results
        3. **Storage**: Store results in a database for later retrieval
        4. **Webhook**: Notify when processing completes

        ## Typical Flow:

        ```
        Incoming Message → handle_message() → Immediate Response + Message ID
                                                            ↓
                                                    Background Processing
                                                            ↓
                                                get_categorization_result(ID) → Final Result
        ```

        This allows your agent to handle high message volumes without blocking, while still providing access to the actual categorization results when needed.

        """
        with self.processing_lock:
            if message_id in self.processing_results:
                result = self.processing_results[message_id]
                if result.get("processed"):
                    return result["result"]
                else:
                    return {"assessment": "processing", "message_id": message_id}
            else:
                return {"assessment": "not_found", "message_id": message_id}

    def cleanup_old_results(self, max_age_hours=24):
        """Clean up old processing results to prevent memory leaks"""
        """
            The `cleanup_old_results()` method is used to prevent memory leaks by removing old processing results from memory. Here's when and how to use it:

            ## When to Use:

            1. **Scheduled Cleanup**: Run periodically (e.g., every hour or daily)
            2. **Memory Threshold**: When memory usage gets high
            3. **Startup/Shutdown**: Clean during agent startup or graceful shutdown
            4. **Batch Processing**: After processing large batches of messages

            ## Usage Examples:

            ```python
            # 1. Scheduled cleanup (run every 6 hours)
            import threading
            import time

            def scheduled_cleanup(agent):
                while True:
                    time.sleep(6 * 3600)  # 6 hours
                    agent.cleanup_old_results(max_age_hours=24)

            # Start background cleanup thread
            cleanup_thread = threading.Thread(
                target=scheduled_cleanup, 
                args=(agent,), 
                daemon=True
            )
            cleanup_thread.start()

            # 2. Manual cleanup with custom age
            agent.cleanup_old_results(max_age_hours=1)  # Remove results older than 1 hour

            # 3. Cleanup on shutdown
            def graceful_shutdown(agent):
                agent.cleanup_old_results(max_age_hours=0)  # Clean all
                agent.executor.shutdown(wait=True)
            ```

            ## Default Behavior:
            - **Default**: Removes results older than 24 hours
            - **Configurable**: Pass `max_age_hours` parameter to adjust
            - **Thread-safe**: Uses locks to prevent race conditions

            ## Typical Integration:

            ```python
            # Add to agent initialization
            def __init__(...):
                super().__init__(...)
                # Start cleanup scheduler
                self._start_cleanup_scheduler()

            def _start_cleanup_scheduler(self):
                def cleanup_worker():
                    while True:
                        time.sleep(3600)  # Run every hour
                        self.cleanup_old_results(max_age_hours=6)
                
                cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
                cleanup_thread.start()
            ```

This prevents the `processing_results` dictionary from growing indefinitely as messages are processed over time.        
        """
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
