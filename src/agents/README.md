# A2A Sample Agent

This directory contains an enhanced A2A (Agent-to-Agent) sample agent implementation that demonstrates the agent architecture with additional capabilities.

## Architecture

### Files Structure

- **`basic_agent.py`** - Base class with core A2A functionality
- **`sample_agent.py`** - Enhanced agent that inherits from BasicAgent with additional features
- **`test_sample_agent.py`** - Comprehensive test script for the SampleAgent
- **`usage_examples.py`** - Simple usage examples demonstrating key features

### Class Hierarchy

```
BasicAgent (basic_agent.py)
    ├── Core A2A server functionality
    ├── Registry registration and heartbeat
    └── Basic message handling
    
SampleAgent (sample_agent.py)
    ├── Inherits from BasicAgent
    ├── Poetry generation capability
    ├── Network agent discovery
    ├── Intelligent agent routing
    └── Enhanced message handling
```

## Features

### Core Features (from BasicAgent)
- A2A server implementation
- Registry registration with heartbeat
- Basic message handling
- Error handling and retry logic

### Enhanced Features (SampleAgent)
- **Poetry Generation**: Uses Azure OpenAI to create poetry on various topics
- **Network Discovery**: Can discover other agents in the registry
- **Intelligent Routing**: Uses LLM to route queries to the most appropriate agent
- **Enhanced Messaging**: Processes natural language requests for poetry

## Prerequisites

1. **Environment Variables**: Create a `.env` file with:
   ```env
   AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint
   AZURE_OPENAI_API_KEY=your_azure_openai_api_key
   AZURE_OPENAI_API_VERSION=your_api_version
   REGISTRY_URL=http://localhost:8000
   ```

2. **Dependencies**: Install required packages:
   ```bash
   pip install python-a2a openai python-dotenv requests fastapi pydantic
   ```

## Usage

### 1. Basic Creation and Testing

Run the test script to see all features in action:
```bash
uv run test_sample_agent.py
```

### 2. Simple Usage Examples

Run the usage examples to see step-by-step demonstrations:
```bash
uv run usage_examples.py
```

### 3. Running as a Server

Start the agent as a server that registers with a registry:
```bash
# Basic usage with default settings
uv run agents/sample_agent.py --registry-url "http://localhost:8000"

# Custom configuration
uv run agents/sample_agent.py \
    --name "MyPoetryAgent" \
    --port 8001 \
    --registry-url "http://localhost:8000"
```

### 4. Demo Mode

Run a quick demo without starting the server:
```bash
uv run agents/sample_agent.py --demo
```

### 5. Programmatic Usage

```python
from agents.sample_agent import SampleAgent

# Create agent
agent = SampleAgent(
    name="MyPoetAgent",
    description="A poetry-writing agent",
    url="http://localhost:8001",
    registry_url="http://localhost:8000"
)

# Generate poetry
poem = agent.generate_poetry("artificial intelligence")
print(poem)

# Discover other agents
agents = agent.from_network_get_agents()
print(f"Found {len(agents)} agents")

# Route queries intelligently
best_agent, confidence = agent.from_network_find_best_agent("I need help with math")
print(f"Best agent: {best_agent} (confidence: {confidence})")
```

## Key Capabilities

### Poetry Generation
The agent can generate poetry on any topic using Azure OpenAI:
- Handles requests like "Write a poem about the ocean"
- Extracts topics from natural language
- Fallback to simple poems if LLM is unavailable

### Network Discovery
- Retrieves all registered agents from the registry
- Finds specific agents by name
- Lists agent capabilities and descriptions

### Intelligent Routing
- Uses LLM to analyze user queries
- Matches queries with agent capabilities
- Returns confidence scores for routing decisions

### Enhanced Messaging
- Processes natural language requests
- Detects poetry requests automatically
- Provides helpful responses about capabilities

## Error Handling

The agent includes robust error handling:
- Registry connection failures with retry logic
- LLM service unavailability with fallbacks
- Network timeouts and connection issues
- Graceful degradation when services are unavailable

## Testing

The test suite covers:
- Agent creation and configuration
- Poetry generation functionality
- Message handling and processing
- Network discovery features
- Registry registration process

Run tests with:
```bash
uv run test_sample_agent.py
```

## Extending the Agent

To add new capabilities:

1. **Add new skills** to the AgentCard in `__init__`
2. **Implement new methods** for specific functionality
3. **Enhance `handle_message`** to process new request types
4. **Update capabilities** in the agent card

Example:
```python
def translate_text(self, text: str, target_language: str) -> str:
    """Add translation capability"""
    # Implementation here
    pass

def handle_message(self, message: Message) -> Message:
    user_message = message.content.text.lower()
    
    if "translate" in user_message:
        # Handle translation requests
        return self.handle_translation_request(message)
    elif "poem" in user_message:
        # Handle poetry requests
        return self.handle_poetry_request(message)
    # ... other handlers
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure `python_a2a` package is installed
2. **Registry Connection**: Ensure registry server is running on specified URL
3. **Azure OpenAI**: Verify credentials in `.env` file
4. **Port Conflicts**: Use `--port` argument to specify different ports

### Logs

The agent provides detailed logging:
- Registration attempts and results
- Heartbeat status
- LLM service connections
- Error conditions and retries

Set log level in code:
```python
logging.basicConfig(level=logging.DEBUG)  # For verbose logging
```

## Architecture Benefits

This design provides:
- **Clean Separation**: Base functionality in BasicAgent, extensions in SampleAgent
- **Reusability**: BasicAgent can be extended for different use cases
- **Maintainability**: Clear inheritance hierarchy and modular design
- **Testability**: Comprehensive test coverage and examples
- **Flexibility**: Easy to add new capabilities and modify behavior
