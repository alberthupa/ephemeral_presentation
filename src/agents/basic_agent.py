import os
import json
import time
import logging
from openai import AzureOpenAI
from typing import Tuple

import requests

from python_a2a import (
    A2AServer,
    Message,
    TextContent,
    MessageRole,
)
from python_a2a.discovery import enable_discovery

from dotenv import load_dotenv

load_dotenv(".env", override=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BasicAgent(A2AServer):
    def __init__(
        self,
        logger: logging.Logger = None,
        name: str = None,
        description: str = None,
        url: str = None,
        registry_url: str = None,
    ):
        # Initialize the parent A2AServer class properly
        super().__init__()

        self.name = name
        self.description = description
        self.url = url
        self.registry_url = registry_url
        self._registration_retries = 3
        self._heartbeat_interval = 30  # seconds
        self._discovery_client = None
        self.llm_client = None

        # Set required attributes for A2AServer compatibility
        self._use_google_a2a = True  # This fixes the AttributeError

    async def setup(self):
        """Registers the agent with the registry."""
        if self.registry_url:
            for attempt in range(self._registration_retries):
                try:
                    # Register with discovery
                    self._discovery_client = enable_discovery(
                        self,
                        registry_url=self.registry_url,
                        heartbeat_interval=self._heartbeat_interval,
                    )

                    # Add heartbeat logging
                    def heartbeat_callback(results):
                        for result in results:
                            if result.get("success"):
                                logger.info(
                                    f"Heartbeat successful with registry {result['registry']}"
                                )
                            else:
                                logger.warning(
                                    f"Heartbeat failed with registry {result['registry']}: {result.get('message', 'Unknown error')}"
                                )

                    # Set the callback
                    self._discovery_client.heartbeat_callback = heartbeat_callback

                    # Verify registration
                    response = requests.get(f"{self.registry_url}/registry/agents")
                    if response.status_code == 200:
                        agents = response.json()
                        # if any(agent["url"] == self.url for agent in agents):
                        if any(agent["url"] == self.agent_card.url for agent in agents):
                            logger.info(
                                f"Agent '{self.agent_card.name}' registered successfully with registry: {self.registry_url}"
                            )
                            return  # Success, exit the retry loop
                        else:
                            logger.warning(
                                f"Registration verification failed (attempt {attempt + 1}/{self._registration_retries})"
                            )
                    else:
                        logger.warning(
                            f"Failed to verify registration: {response.status_code} (attempt {attempt + 1}/{self._registration_retries})"
                        )

                    # Wait before retrying
                    time.sleep(2)
                except Exception as e:
                    logger.error(
                        f"Error during registration attempt {attempt + 1}: {e}"
                    )
                    if attempt < self._registration_retries - 1:
                        time.sleep(2)

            logger.error(
                f"Failed to register agent after {self._registration_retries} attempts"
            )

        # Initialize LLM client for enhanced functionality
        self._init_llm_client()

    def _init_llm_client(self):
        """Initialize the Azure OpenAI client."""
        try:
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
            azure_version = os.getenv("AZURE_OPENAI_API_VERSION")

            if azure_endpoint and azure_api_key and azure_version:
                self.llm_client = AzureOpenAI(
                    api_key=azure_api_key,
                    api_version=azure_version,
                    azure_endpoint=azure_endpoint,
                )
                logger.info("Azure OpenAI client initialized successfully")
            else:
                logger.warning(
                    "Azure OpenAI credentials not found in environment variables"
                )
        except Exception as e:
            logger.error(f"Failed to initialize Azure OpenAI client: {e}")

    def handle_message(self, message: Message) -> Message:
        """
        if method handle_task exists, it will be called instead of handle_message
        """
        return Message(
            content=TextContent(
                text=f"Hello from {self.agent_card.name}! I received: {message.content.text}"
            ),
            role=MessageRole.AGENT,
            parent_message_id=message.message_id,
            conversation_id=message.conversation_id,
        )

    def from_network_get_agents(self):
        """Retrieves all registered agents from the registry."""
        try:
            response = requests.get(f"{self.registry_url}/registry/agents")
            response.raise_for_status()
            agents_data = response.json()
            return [dict(data) for data in agents_data]
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to the agent registry: {e}")
            return []
        except json.JSONDecodeError:
            logger.error("Error: Failed to decode JSON from registry response.")
            return []

    def from_network_get_agent_url(self, agent_name: str) -> str:
        """Retrieves a specific agent URL from the registry by name."""
        agents = self.from_network_get_agents()
        agent = next((a for a in agents if a.get("name") == agent_name), None)
        if not agent:
            logger.warning(f"Agent {agent_name} not found.")
            return None
        return agent.get("url")

    def from_network_find_best_agent(self, query: str) -> Tuple[str, float]:
        """Routes a given query to the most appropriate agent using LLM."""
        agents = self.from_network_get_agents()
        if not agents:
            raise RuntimeError("No agents are available in the network.")

        if not self.llm_client:
            logger.warning("LLM client not available for routing")
            return agents[0].get("name", "Unknown"), 0.5

        agent_descriptions = []
        for agent in agents:
            description = (
                f"Agent Name: {agent.get('name', 'Unknown')}\\n"
                f"Description: {agent.get('description', 'No description')}\\n"
                f"Capabilities: {json.dumps(agent.get('capabilities', {}))}"
            )
            agent_descriptions.append(description)

        prompt = f"""
        You are an intelligent router responsible for routing user queries to the correct agent.
        Based on the user's query and the available agents' capabilities, determine the best agent to handle the query.

        User Query: "{query}"

        Available Agents:
        ---
        {" --- ".join(agent_descriptions)}
        ---

        Please respond with a JSON object containing the 'agent_name' of the most suitable agent and a 'confidence' score (from 0.0 to 1.0).
        """

        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that responds in JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
            choice = response.choices[0].message.content
            data = json.loads(choice)
            return data["agent_name"], float(data["confidence"])
        except Exception as e:
            logger.error(f"Failed to get a routing decision from the LLM: {e}")
            # Fallback to first agent
            return agents[0].get("name", "Unknown"), 0.5
