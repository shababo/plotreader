from abc import ABC, abstractmethod
import re
from typing import Union, List, Any
import os
from pathlib import Path

from llama_parse import LlamaParse
from llama_cloud import NodeParser
from llama_index.core import (
    VectorStoreIndex,
    load_index_from_storage,
    StorageContext,
    Document,
    SimpleDirectoryReader
)
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.readers.github import GithubRepositoryReader, GithubClient
from llama_index.core.node_parser import CodeSplitter
from llama_index.core.schema import TextNode

from plotreader import _DEFAULT_EMBEDDING_MODEL

_DEFAULT_RETRIEVAL_K = 5

class DocumentHandler(ABC):
    

    def __init__(
        self,
        name: str,
        desc: str,
        storage_dir: str,
        # embedding_model: str = _DEFAULT_EMBEDDING_MODEL
    ):
        self.name = name
        self.desc = desc
        self.storage_dir = storage_dir

        self._reader = self.get_reader()

    def get_parser(self):
        return None
    
    @abstractmethod
    def get_reader(self):
        raise NotImplementedError(
            f"{self.__class__.__name__} does not provide necerssary get_reader method."
        )

    @abstractmethod
    def load_docs(self) -> List[Document]:
        "Load the raw documents into a set of Document instances."
        raise NotImplementedError(
            f"{self.__class__.__name__} does not provide necerssary load_docs method."
        )


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

    @property
    def node_parser(self):
        return None

    def _build_vec_index(self, docs: List[Document], node_parser: NodeParser = None):
        
        node_parser = node_parser or self.node_parser

        if node_parser is not None:
            nodes = node_parser.get_nodes_from_documents(docs)
            return VectorStoreIndex(nodes)
        else:
            return VectorStoreIndex(docs)
        

    def query_engine(self, top_k: int = _DEFAULT_RETRIEVAL_K) -> Any:
        "Return a Query Engine for this document."
        
        return self.vector_index().as_query_engine(similarity_top_k=top_k)
    
    
    def query_engine_tool(self, top_k: int = _DEFAULT_RETRIEVAL_K) -> QueryEngineTool:
        "Return a Tool that can query this document."
        
        return QueryEngineTool(
                query_engine=self.vector_index().as_query_engine(similarity_top_k=top_k),
                metadata=ToolMetadata(
                    name=f"{self.name}_vector_tool",
                    description=f"This tool can query these documents: {self.desc}.",
                ),
            )

    def _index_files_in_dir(self, dirpath: str):

        _INDEX_FILES = [
            'default__vector_store.json',
            'docstore.json',
            'graph_store.json',
            'image__vector_store.json',
            'index_store.json',
        ]

        return all([os.path.exists(os.path.join(dirpath, filename)) for filename in _INDEX_FILES])
    


class DirectoryHandler(DocumentHandler):

    # _DEFAULT_PARSING_INSTRUCTION = "Please extract all infor"    
    def __init__(
            self,
            name: str,
            dirpath: str,
            storage_dir: str,
            desc: str,
            parsing_instructions: str = None
    ):
        
        self._parsing_instructions = parsing_instructions
        self._dirpath = dirpath

        super().__init__(
            name=name,
            storage_dir=storage_dir,
            desc=desc,
        )

    def get_parser(self):

        return LlamaParse(
            result_type="markdown",
            parsing_instruction=self._parsing_instructions,
            use_vendor_multimodal_model=True,
            vendor_multimodal_model_name='anthropic-sonnet-3.5',
        )
        
    def get_reader(self):
        
        file_extractor =  {".pdf": self.get_parser()}
        return SimpleDirectoryReader(input_dir=self._dirpath, file_extractor=file_extractor)
        
    def load_docs(self) -> List[Document]:

        return self._reader.load_data()
    



    
class MultimodalDirectoryHandler(DirectoryHandler):

    def get_parser(self):

        return LlamaParse(
            result_type="markdown",
            parsing_instruction=self._parsing_instructions,
            use_vendor_multimodal_model=True,
            vendor_multimodal_model_name='anthropic-sonnet-3.5',
        )
        
    def get_reader(self):
        "Multimodal parsing and retrieval does not use a built in reader."
        return None
        
    def load_docs(self) -> List[Document]:
        
        parser = self.get_parser()
        # text_parser = LlamaParse(result_type="text")
        # Get all files in self._dirpath, non-recursively, excluding directories
        files = [os.path.join(self._dirpath, f) for f in os.listdir(self._dirpath) if os.path.isfile(os.path.join(self._dirpath, f))]
        
        docs = []
        for file in files:

            json_objs = parser.get_json_result(file)

            image_dicts = parser.get_images(json_objs, download_path="data_images")
            json_dicts = json_objs[0]["pages"]

            # docs_text = text_parser.load_data(file)

            docs += self._get_nodes(json_dicts, image_dir="data_images")

        return docs
    
    # def _get_text_nodes(self, json_list: List[dict]):
    #     text_nodes = []
    #     for idx, page in enumerate(json_list):
    #         text_node = TextNode(text=page["md"], metadata={"page": page["page"]})
    #         text_nodes.append(text_node)
    #     return text_nodes
    
    def _get_page_number(self, file_name):
        match = re.search(r"-page-(\d+)\.jpg$", str(file_name))
        if match:
            return int(match.group(1))
        return 0
    
    def _get_sorted_image_files(self, image_dir):
        """Get image files sorted by page."""
        raw_files = [f for f in list(Path(image_dir).iterdir()) if f.is_file()]
        sorted_files = sorted(raw_files, key=self._get_page_number)
        return sorted_files
    
    def _get_nodes(self, json_dicts, image_dir):
        """Creates nodes from json + images"""

        nodes = []

        docs = [doc["md"] for doc in json_dicts]  # extract text
        image_files = self._get_sorted_image_files(image_dir)  # extract images

        for idx, doc in enumerate(docs):
            # adds both a text node and the corresponding image node (jpg of the page) for each page
            node = TextNode(
                text=doc,
                metadata={"image_path": str(image_files[idx]), "page_num": idx + 1},
            )
            nodes.append(node)

        return nodes


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

        self._github_token = github_token or os.environ.get("GITHUB_TOKEN")
        self._include_dirs = include_dirs or []
        self._include_exts = include_exts or [".py"]
        self._language = language
        
        self._github_client = GithubClient(github_token=self._github_token, verbose=True)

        super().__init__(
            name = name, 
            desc = desc, 
            storage_dir = storage_dir
        )
        
        
        
    def get_reader(self):
        return GithubRepositoryReader(
            github_client=self._github_client,
            owner=self._owner,
            repo=self._repo,
            use_parser=False,
            verbose=False,
            filter_directories=(
                self._include_dirs,
                GithubRepositoryReader.FilterType.INCLUDE,
            ),
            filter_file_extensions=(
                self._include_exts,
                GithubRepositoryReader.FilterType.INCLUDE,
            ),
        )

    def load_docs(self) -> List[Document]:

        return self._reader.load_data(branch=self._branch)
    
    @property
    def node_parser(self):

        if self._language is None:
            return None
        else:
            return CodeSplitter(self._language) # NOTE: I EDITED THE SOURCE IN THIS ENV TO PROPERLY LOAD THE PYTHON PARSER


