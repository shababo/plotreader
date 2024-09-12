from dotenv import load_dotenv
load_dotenv(override=True)

from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.anthropic import Anthropic
from llama_index.core import Settings

_DEFAULT_EMBEDDING_MODEL = "text-embedding-ada-002"
# Settings.llm = Anthropic(model='claude-3-5-sonnet-20240620', max_tokens=2048)
# Settings.llm = Anthropic(model='claude-3-opus-20240229', max_tokens=2048)
Settings.llm = OpenAI(model="gpt-4o")

# Settings.llm = OpenAI(model="gpt-4o", max_tokens = 2048)
Settings.embed_model = OpenAIEmbedding(model=_DEFAULT_EMBEDDING_MODEL)

import logging
import sys

# generate unique logfile name
logging.basicConfig(level=logging.DEBUG, filename="logfile", filemode="a+",
                        format="%(asctime)-15s %(levelname)-8s %(message)s")

root = logging.getLogger()
root.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)

