import os
import json
import time
import logging
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

   