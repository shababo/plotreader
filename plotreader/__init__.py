from dotenv import load_dotenv
load_dotenv(override=True)

import logging
import sys
from datetime import datetime

from llama_index.llms.openai import OpenAI
from llama_index.multi_modal_llms.openai import OpenAIMultiModal
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.anthropic import Anthropic
from llama_index.multi_modal_llms.anthropic import AnthropicMultiModal
from llama_index.core import Settings

_DEFAULT_EMBEDDING_MODEL = "text-embedding-3-large"

_CLAUDE_SONNET35_TEXT = Anthropic(model='claude-3-5-sonnet-20240620', max_tokens=2048)

_CLAUDE_SONNET35_MULTIMODAL = AnthropicMultiModal(model='claude-3-5-sonnet-20240620', max_tokens=2048)
# Settings.llm = Anthropic(model='claude-3-opus-20240229', max_tokens=4096)
# Settings.llm = Anthropic(model='claude-3-sonnet-20240229', max_tokens=2048)
_GPT4O_TEXT = OpenAI(model="gpt-4o")
_GPT4O_MULTIMODAL = OpenAIMultiModal(model="gpt-4o")

Settings.llm = _CLAUDE_SONNET35_TEXT
_MM_LLM = _CLAUDE_SONNET35_MULTIMODAL


# Settings.llm = OpenAI(model="gpt-4o", max_tokens = 2048)
Settings.embed_model = OpenAIEmbedding(model=_DEFAULT_EMBEDDING_MODEL)



# generate unique logfile name
# logging.basicConfig(level=logging.DEBUG, filename=f"./logs/logfile_{datetime.now()}", filemode="a+",
#                         format="%(asctime)-15s %(levelname)-8s %(message)s")

# root = logging.getLogger()
# root.setLevel(logging.DEBUG)

# handler = logging.StreamHandler(sys.stdout)
# handler.setLevel(logging.DEBUG)
# formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# handler.setFormatter(formatter)
# root.addHandler(handler)

