from typing import Union
import os
from pathlib import Path

from llama_index.core.llms.function_calling import FunctionCallingLLM
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.anthropic import Anthropic
from llama_index.core import (
    VectorStoreIndex,
    load_index_from_storage,
    StorageContext,
    Settings
)

Settings.llm = Anthropic(model='claude-3-5-sonnet-20240620', max_tokens=2048)
Settings.embed_model = OpenAIEmbedding(model="text-embedding-ada-002")

class PlotGenerator():

    def __init__(
        self,
        vector_store_path: str = None,
    ):
        
        self._vector_store_path = vector_store_path
        self._is_init = False

    def init(self):

        if not os.path.exists(self._vector_store_path):
            # parse repo
            documents = parse_matplotlib_galleries()
            # build vector index
            node_parser = CodeSplitter('python') # NOTE: I EDITED THE SOURCE IN THIS ENV TO PROPERLY LOAD THE PYTHON PARSER
            nodes = node_parser.get_nodes_from_documents(documents)
            vector_index = VectorStoreIndex(nodes)
            vector_index.storage_context.persist(
                persist_dir=persist_dir
            )
        else:
            vector_index = load_index_from_storage(
                StorageContext.from_defaults(persist_dir=persist_dir),
            )

    
    def run(self, prompt_augmentation: str = None):