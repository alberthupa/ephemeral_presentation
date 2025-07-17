import os
import socket
import logging

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

    def categorize_message(self, message: str) -> dict:
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
        return choice

    def handle_message(self, message: Message) -> Message:
        """Enhanced message handler with poetry generation capability."""
        user_message = message.content.text.lower()
        print(f"Message received: {user_message}")

        # THIS PART IS TO BE UPDATED:
        # HERE MUST BE A CODE TAING INCOMING  user_message TO categorize_message
        # but it must start independent thread / process so that it does not block the main thread

        response_text = "wtf"
        return Message(
            content=TextContent(text=response_text),
            role=MessageRole.AGENT,
            parent_message_id=message.message_id,
            conversation_id=message.conversation_id,
        )


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
