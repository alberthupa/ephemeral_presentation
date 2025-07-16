import os
from openai import AzureOpenAI

from dotenv import load_dotenv

load_dotenv(".env", override=True)


class LLMClient:
    """Client for interacting with the Azure OpenAI service."""

    def __init__(self):
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        )

    def get_client(self):
        return self.client
