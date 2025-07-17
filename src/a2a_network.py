import json
import requests
from typing import Tuple

from llm_client import LLMClient


class A2ANetwork:
    def __init__(self, registry_url: str):
        self.registry_url = registry_url
        self.llm_client = None  # Initialize LLM client as None

    def get_agents(self):
        """
        Retrieves all registered agents from the registry.
        """
        try:
            response = requests.get(f"{self.registry_url}/registry/agents")
            response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
            agents_data = response.json()
            return [dict(data) for data in agents_data]

        except requests.exceptions.RequestException as e:
            print(f"Error connecting to the agent registry: {e}")
            return []
        except json.JSONDecodeError:
            print("Error: Failed to decode JSON from registry response.")
            return []

    def find_best_agent(self, query) -> Tuple[str, float]:
        """
        Routes a given query to the most appropriate agent.

        Args:
            query: The user's query string.

        Returns:
            A tuple containing the name of the best agent and a confidence score.
        """
        agents = self.get_agents()
        if not agents:
            raise RuntimeError("No agents are available in the network.")

        agent_descriptions = []
        for agent in agents:
            description = (
                f"Agent Name: {agent['name']}\\n"
                f"Description: {agent['description']}\\n"
                f"Capabilities: {json.dumps(agent['capabilities'])}"
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
            if self.llm_client is None:
                self.llm_client = LLMClient().get_client()

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
            llm_assessment = json.loads(choice)
            best_agent_url = next(
                (a["url"] for a in agents if a["name"] == llm_assessment["agent_name"]),
                None,
            )
            return best_agent_url
        except Exception as e:
            raise RuntimeError(
                f"Failed to get a routing decision from the LLM: {e}"
            ) from e


if __name__ == "__main__":
    registry_url = "http://localhost:8000"  # Replace with your actual registry URL
    network = A2ANetwork(registry_url)
