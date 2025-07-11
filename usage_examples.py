#!/usr/bin/env python3
"""
Simple usage example for the SampleAgent.
This demonstrates the basic ways to create and use the agent.
"""

import os
import sys
import asyncio

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.sample_agent import SampleAgent


def example_1_basic_creation():
    """Example 1: Basic agent creation with default values."""
    print("Example 1: Creating a basic SampleAgent")
    print("-" * 40)

    # Create agent with default values
    agent = SampleAgent()

    print(f"Agent created: {agent.agent_card.name}")
    print(f"Description: {agent.agent_card.description}")
    print(f"URL: {agent.agent_card.url}")
    print(f"Registry URL: {agent.registry_url}")
    print()

    return agent


def example_2_custom_creation():
    """Example 2: Custom agent creation with specific parameters."""
    print("Example 2: Creating a custom SampleAgent")
    print("-" * 40)

    # Create agent with custom values
    agent = SampleAgent(
        name="MyCustomPoetAgent",
        description="A specialized poetry agent for creative writing",
        url="http://localhost:9001",
        registry_url="http://localhost:8000",
    )

    print(f"Agent created: {agent.agent_card.name}")
    print(f"Description: {agent.agent_card.description}")
    print(f"URL: {agent.agent_card.url}")
    print(f"Registry URL: {agent.registry_url}")
    print()

    return agent


def example_3_poetry_generation(agent):
    """Example 3: Using the poetry generation feature."""
    print("Example 3: Generating poetry")
    print("-" * 40)

    topics = ["coding", "artificial intelligence", "teamwork"]

    for topic in topics:
        print(f"Topic: {topic}")
        poem = agent.generate_poetry(topic)
        print(f"Generated poem:\n{poem}")
        print("-" * 20)


def example_4_network_discovery(agent):
    """Example 4: Network discovery features."""
    print("Example 4: Network discovery")
    print("-" * 40)

    # Try to get agents from registry
    print("Attempting to discover other agents...")
    agents = agent.from_network_get_agents()

    if agents:
        print(f"Found {len(agents)} agents:")
        for agent_info in agents:
            print(f"  - {agent_info.get('name', 'Unknown')}")
    else:
        print("No agents found (registry might not be running)")

    # Try agent routing
    print("\nTesting intelligent routing...")
    queries = [
        "I need help with mathematics",
        "Can you write a poem?",
        "Help me with data analysis",
    ]

    for query in queries:
        try:
            best_agent, confidence = agent.from_network_find_best_agent(query)
            print(
                f"Query: '{query}' -> Agent: {best_agent} (confidence: {confidence:.2f})"
            )
        except Exception as e:
            print(f"Query: '{query}' -> Error: {e}")

    print()


async def example_5_agent_registration(agent):
    """Example 5: Agent registration with registry."""
    print("Example 5: Agent registration")
    print("-" * 40)

    try:
        print("Attempting to register agent with registry...")
        await agent.setup()
        print("Agent registration completed successfully!")
    except Exception as e:
        print(f"Registration failed: {e}")
        print("This is normal if no registry server is running.")

    print()


def example_6_simulated_conversation(agent):
    """Example 6: Simulated conversation with the agent."""
    print("Example 6: Simulated conversation")
    print("-" * 40)

    # Mock conversation messages
    conversation_messages = [
        "Hello, what can you do?",
        "Write a poem about software development",
        "Can you create poetry about machine learning?",
        "Tell me about your capabilities",
    ]

    # Simulate message objects (since we might not have the full python_a2a package)
    class MockContent:
        def __init__(self, text):
            self.text = text

    class MockMessage:
        def __init__(self, text, msg_id="sim-msg", conv_id="sim-conv"):
            self.content = MockContent(text)
            self.message_id = msg_id
            self.conversation_id = conv_id

    for i, msg_text in enumerate(conversation_messages):
        print(f"User: {msg_text}")

        try:
            mock_msg = MockMessage(msg_text, f"sim-{i + 1}", "simulation")
            response = agent.handle_message(mock_msg)
            print(f"Agent: {response.content.text}")
        except Exception as e:
            print(f"Agent: Error processing message - {e}")

        print("-" * 30)


def run_all_examples():
    """Run all examples."""
    print("SampleAgent Usage Examples")
    print("=" * 50)

    # Example 1: Basic creation
    basic_agent = example_1_basic_creation()

    # Example 2: Custom creation
    custom_agent = example_2_custom_creation()

    # Example 3: Poetry generation
    example_3_poetry_generation(custom_agent)

    # Example 4: Network discovery
    example_4_network_discovery(custom_agent)

    # Example 5: Agent registration
    asyncio.run(example_5_agent_registration(custom_agent))

    # Example 6: Simulated conversation
    example_6_simulated_conversation(custom_agent)

    print("=" * 50)
    print("All examples completed!")
    print("\nTo run the agent as a server:")
    print("uv run agents/sample_agent.py --name 'MyAgent' --port 8001")
    print("\nTo run in demo mode:")
    print("uv run agents/sample_agent.py --demo")


if __name__ == "__main__":
    run_all_examples()
