#!/usr/bin/env python3
"""
Test script for the SampleAgent.
This script demonstrates how to create, configure, and use the SampleAgent.
"""

import os
import sys
import asyncio
import logging

# Add the project root to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.sample_agent import SampleAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_agent_creation():
    """Test creating a SampleAgent instance."""
    print("=" * 50)
    print("Testing Agent Creation")
    print("=" * 50)

    agent = SampleAgent(
        name="TestPoetryAgent",
        description="A test agent for poetry generation",
        url="http://localhost:8002",
        registry_url="http://localhost:8000",
    )

    print(f"Agent Name: {agent.agent_card.name}")
    print(f"Agent Description: {agent.agent_card.description}")
    print(f"Agent URL: {agent.agent_card.url}")
    print(f"Agent Skills: {[skill.name for skill in agent.agent_card.skills]}")
    print(f"Agent Capabilities: {agent.agent_card.capabilities}")

    return agent


def test_poetry_generation(agent):
    """Test the poetry generation functionality."""
    print("\n" + "=" * 50)
    print("Testing Poetry Generation")
    print("=" * 50)

    topics = ["sunset", "technology", "friendship", "dreams"]

    for topic in topics:
        print(f"\nGenerating poem about '{topic}':")
        poem = agent.generate_poetry(topic)
        print(f"Result:\n{poem}")
        print("-" * 30)


def test_message_handling(agent):
    """Test the message handling functionality."""
    print("\n" + "=" * 50)
    print("Testing Message Handling")
    print("=" * 50)

    # This would normally require the python_a2a package to be installed
    # For now, we'll simulate the message structure

    test_messages = [
        "Hello, how are you?",
        "Write a poem about the mountains",
        "Can you create poetry about love?",
        "What can you do?",
    ]

    for i, msg_text in enumerate(test_messages):
        print(f"\nTest Message {i + 1}: '{msg_text}'")

        # Create a mock message object
        class MockTextContent:
            def __init__(self, text):
                self.text = text

        class MockMessage:
            def __init__(self, text, msg_id, conv_id):
                self.content = MockTextContent(text)
                self.message_id = msg_id
                self.conversation_id = conv_id

        mock_message = MockMessage(msg_text, f"test-{i + 1}", "test-conversation")

        try:
            response = agent.handle_message(mock_message)
            print(f"Agent Response: {response.content.text}")
        except Exception as e:
            print(f"Error handling message: {e}")
            # Fallback to direct poetry generation if message handling fails
            if "poem" in msg_text.lower():
                topic = "general"
                if "about" in msg_text:
                    parts = msg_text.split("about")
                    if len(parts) > 1:
                        topic = parts[1].strip()
                poem = agent.generate_poetry(topic)
                print(f"Direct poetry generation result:\n{poem}")

        print("-" * 30)


def test_network_functions(agent):
    """Test network-related functions (these will likely fail without a registry)."""
    print("\n" + "=" * 50)
    print("Testing Network Functions")
    print("=" * 50)

    print("Attempting to get agents from registry...")
    agents = agent.from_network_get_agents()
    print(f"Found {len(agents)} agents in registry")

    if agents:
        print("Available agents:")
        for agent_info in agents:
            print(
                f"  - {agent_info.get('name', 'Unknown')}: {agent_info.get('description', 'No description')}"
            )

    print("\nTesting agent routing...")
    try:
        best_agent, confidence = agent.from_network_find_best_agent(
            "I need help with poetry"
        )
        print(f"Best agent for poetry query: {best_agent} (confidence: {confidence})")
    except Exception as e:
        print(f"Routing failed: {e}")


async def test_agent_setup(agent):
    """Test the agent setup process."""
    print("\n" + "=" * 50)
    print("Testing Agent Setup")
    print("=" * 50)

    try:
        print("Setting up agent (attempting registry registration)...")
        await agent.setup()
        print("Agent setup completed successfully")
    except Exception as e:
        print(f"Agent setup failed (this is expected if no registry is running): {e}")


def run_all_tests():
    """Run all tests."""
    print("Starting SampleAgent Tests")
    print("=" * 60)

    # Test 1: Agent Creation
    agent = test_agent_creation()

    # Test 2: Poetry Generation
    test_poetry_generation(agent)

    # Test 3: Message Handling
    test_message_handling(agent)

    # Test 4: Network Functions
    test_network_functions(agent)

    # Test 5: Agent Setup
    asyncio.run(test_agent_setup(agent))

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
