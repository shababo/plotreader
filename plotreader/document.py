from abc import ABC, abstractmethod
from typing import Union, List
import os
from pathlib import Path

from llama_index.core import (
    VectorStoreIndex,
    load_index_from_storage,
    StorageContext,
)
from llama_index.readers.github import GithubRepositoryReader, GithubClient
from llama_index.core.node_parser import CodeSplitter


class Document(ABC):
    name: str
    desc: str
    top_k: int = 5

    @abstractmethod
    @property
    def vector_index(self) -> VectorStoreIndex:
        "Return a Vector Index for this document."

        pass

    @abstractmethod
    @property
    def query_engine(self) -> BaseQueryEngine:
        "Return a Query Engine for this document."

        pass
    
    def query_engine_tool(self) -> QueryEngineTool:
        "Return a Tool that can query this document."

        pass


class GitHubRepo(Document):

    def __init__(
            self,
            repo: str,
            owner: str,
            output_dir: str,
            branch: str = None,
            github_token: str = None,
            include_dirs: List[str] = None,
            include_exts: List[str] = None,
    ):
        
        self._repo = repo
        self._owner = owner
        self._output_dir = os.path.join(output_dir, f"{owner}_{repo}_{branch}")
        self._branch = branch
        self._github_token = github_token or os.environ.get("GITHUB_TOKEN")
        self._include_dirs = include_dirs or []
        self._include_exts = include_exts or [".py"]
        
        self._github_client = GithubClient(github_token=self._github_token, verbose=True)


    @property
    def vector_index(self):



def parse_matplotlib_galleries(persist_dir: str):

    print(persist_dir)
    
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


def parse_seaborn_examples(persist_dir: str):
    
    if not os.path.exists(persist_dir):
        github_token = os.environ.get("GITHUB_TOKEN")
        owner = "mwaskom"
        repo = "seaborn"
        branch = "master"

        github_client = GithubClient(github_token=github_token, verbose=True)

        documents = GithubRepositoryReader(
            github_client=github_client,
            owner=owner,
            repo=repo,
            use_parser=False,
            verbose=False,
            filter_directories=(
                ["examples"],
                GithubRepositoryReader.FilterType.INCLUDE,
            ),
            filter_file_extensions=(
                [
                    ".py",
                ],
                GithubRepositoryReader.FilterType.INCLUDE,
            ),
        ).load_data(branch=branch)

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
