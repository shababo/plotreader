from typing import Union
import os
from pathlib import Path

from llama_index.core import (
    VectorStoreIndex,
    load_index_from_storage,
    StorageContext,
)
from llama_index.readers.github import GithubRepositoryReader, GithubClient
from llama_index.core.node_parser import CodeSplitter

def parse_matplotlib_galleries(persist_dir: str):
    
    if not os.path.exists(persist_dir):
        github_token = os.environ.get("GITHUB_TOKEN")
        owner = "matplotlib"
        repo = "matplotlib"
        branch = "main"

        github_client = GithubClient(github_token=github_token, verbose=True)

        documents = GithubRepositoryReader(
            github_client=github_client,
            owner=owner,
            repo=repo,
            use_parser=False,
            verbose=False,
            filter_directories=(
                ["galleries"],
                GithubRepositoryReader.FilterType.INCLUDE,
            ),
            filter_file_extensions=(
                [
                    ".py",
                ],
                GithubRepositoryReader.FilterType.INCLUDE,
            ),
        ).load_data(branch=branch)

        
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

    return vector_index
