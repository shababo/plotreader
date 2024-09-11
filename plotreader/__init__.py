from dotenv import load_dotenv
load_dotenv()

from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.anthropic import Anthropic
from llama_index.core import Settings

Settings.llm = Anthropic(model='claude-3-5-sonnet-20240620', max_tokens=2048)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-ada-002")
