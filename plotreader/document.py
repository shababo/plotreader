from abc import ABC, abstractmethod
from typing import Union, List, Any
import os
from pathlib import Path

from llama_cloud import NodeParser
from llama_index.core import (
    VectorStoreIndex,
    load_index_from_storage,
    StorageContext,
    Document
)
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.readers.github import GithubRepositoryReader, GithubClient
from llama_index.core.node_parser import CodeSplitter

from plotreader import _DEFAULT_EMBEDDING_MODEL

_DEFAULT_RETRIEVAL_K = 5

class DocumentHandler(ABC):
    name: str
    desc: str
    storage_dir: str
    embedding_model: str = _DEFAULT_EMBEDDING_MODEL

    @abstractmethod
    def load_docs(self) -> List[Document]:
        "Load the raw documents into a set of Document instances."

    def vector_index(
            self, 
            node_parser: NodeParser = None, 
            save: bool = True, 
            use_cache: bool = True
        ) -> VectorStoreIndex:
        "Return a Vector Index for this document."
        
        save_dir = os.path.join(self.storage_dir, self.name)
        cache_exists = self._index_files_in_dir(save_dir)

        if cache_exists and use_cache:
            vec_index = load_index_from_storage(
                StorageContext.from_defaults(persist_dir=save_dir),
            )

        else:
            docs = self.load_docs()
            vec_index = self._build_vec_index(docs, node_parser)
            if save:
                vec_index.storage_context.persist(
                    persist_dir=save_dir
                )

        return vec_index

    @abstractmethod
    @property
    def node_parser(self):
        pass

    def _build_vec_index(self, docs: List[Document], node_parser: NodeParser = None):
        
        node_parser = node_parser or self.node_parser

        if node_parser is not None:
            nodes = node_parser.get_nodes_from_documents(docs)
            return VectorStoreIndex(nodes)
        else:
            return VectorStoreIndex(docs)
        

    def query_engine(self, top_k: int = _DEFAULT_RETRIEVAL_K) -> Any:
        "Return a Query Engine for this document."
        
        return self.vector_index.as_query_engine(similarity_top_k=top_k)
    
    
    def query_engine_tool(self, top_k: int = _DEFAULT_RETRIEVAL_K) -> QueryEngineTool:
        "Return a Tool that can query this document."
        return QueryEngineTool(
                query_engine=self.vector_index.as_query_engine(similarity_top_k=top_k),
                metadata=ToolMetadata(
                    name=f"{self.name}_vector_tool",
                    description=f"This tool can query these documents: {self.desc}.",
                ),
            )

    def _index_files_in_dir(self, dirpath: str):

        _DIR_FILES = [
            'default__vector_store.json',
            'docstore.json',
            'graph_store.json',
            'image__vector_store.json',
            'index_store.json',
        ]

        return all([os.path.exists(os.path.join(dirpath, self.name))])
    


class DirectoryHandler(DocumentHandler):
    pass



class GitHubRepoHandler(DocumentHandler):

    def __init__(
            self,
            name: str,
            repo: str,
            owner: str,
            desc: str,
            storage_dir: str,
            branch: str = None,
            github_token: str = None,
            include_dirs: List[str] = None,
            include_exts: List[str] = None,
            language: str = None,
    ):
        
        self._repo = repo
        self._owner = owner
        self._branch = branch or "main"
        super().__init__(
            name = name, 
            desc = desc, 
            storage_dir = storage_dir
        )
        
        self._github_token = github_token or os.environ.get("GITHUB_TOKEN")
        self._include_dirs = include_dirs or []
        self._include_exts = include_exts or [".py"]
        self._language = language
        
        self._github_client = GithubClient(github_token=self._github_token, verbose=True)
        self._repo_reader = GithubRepositoryReader(
            github_client=self._github_client,
            owner=owner,
            repo=repo,
            use_parser=False,
            verbose=False,
            filter_directories=(
                include_dirs,
                GithubRepositoryReader.FilterType.INCLUDE,
            ),
            filter_file_extensions=(
                include_exts,
                GithubRepositoryReader.FilterType.INCLUDE,
            ),
        )

    def load_docs(self) -> List[Document]:

        return self._repo_reader.load_data(branch=self._branch)
    
    @property
    def node_parser(self):

        if self._language is None:
            return None
        else:
            return CodeSplitter(self._language) # NOTE: I EDITED THE SOURCE IN THIS ENV TO PROPERLY LOAD THE PYTHON PARSER


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
