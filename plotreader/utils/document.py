from abc import ABC, abstractmethod
from logging import warn
import re
from typing import Union, List, Any
import os
from pathlib import Path
import io
import base64

from llama_parse import LlamaParse
from llama_cloud import NodeParser, SentenceSplitter
from llama_index.core import (
    VectorStoreIndex,
    load_index_from_storage,
    StorageContext,
    Document,
    SimpleDirectoryReader,
    Settings,
    
)
from llama_index.core.indices.multi_modal import MultiModalVectorStoreIndex
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.readers.github import GithubRepositoryReader, GithubClient
from llama_index.core.node_parser import CodeSplitter
from llama_index.core.schema import TextNode
from llama_index.core.query_engine import CustomQueryEngine, SimpleMultiModalQueryEngine
from llama_index.core.retrievers import BaseRetriever
from llama_index.multi_modal_llms.openai import OpenAIMultiModal
from llama_index.core.schema import ImageNode, NodeWithScore, MetadataMode
from llama_index.core.prompts import PromptTemplate
from llama_index.core.base.response.schema import Response
from typing import Optional
from llama_index.core.node_parser import SentenceWindowNodeParser
from llama_index.core.postprocessor import MetadataReplacementPostProcessor


from plotreader import _DEFAULT_EMBEDDING_MODEL, _MM_LLM

_DEFAULT_RETRIEVAL_K = 5

def image_to_base64(image: Union[str, Any]):

    if isinstance(image, str):
        with open(image, "rb") as image_file:
            binary_data = image_file.read()
        
    else:
        # image = image.convert('RGB')
        image_data = io.BytesIO()
        image.save(image_data, format=image.format.lower(), optimize=True, quality=100)
        image_data.seek(0)
        binary_data = image_data.getvalue()
    
    
    base_64_encoded_data = base64.b64encode(binary_data)
    return base_64_encoded_data.decode('utf-8')

class DocumentHandler(ABC):
    

    def __init__(
        self,
        name: str,
        desc: str,
        storage_dir: str,
        # embedding_model: str = _DEFAULT_EMBEDDING_MODEL,
        use_cache: bool = True,
    ):
        self.name = name
        self.desc = desc
        self.storage_dir = storage_dir
        self._use_cache = use_cache

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
            use_cache: bool = None,
        ) -> VectorStoreIndex:
        "Return a Vector Index for this document."
        
        use_cache = use_cache or self._use_cache

        save_dir = os.path.join(self.storage_dir, self.name)
        cache_exists = self._index_files_in_dir(save_dir)

        if cache_exists and use_cache:
            vec_index = load_index_from_storage(
                StorageContext.from_defaults(persist_dir=save_dir),
            )

        else:
            docs = self.load_docs()
            vec_index = self._build_vec_index(docs, node_parser=node_parser)
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
    

_DEFAULT_PARSING_PROMPTS = """
The provided document is a scientific paper. 
Extract the all of the text but DO NOT generate textual or tabular descriptions of the image. 
Ignore all headers and footers that are metadata (like citation info).
Ignore page boundaries!!
Denote the beginning of figure captions with a new line followed by `[START FIGURE {fig_num} CAPTION]`.
Denote the end of figure captions with a new line followed by `[END FIGURE {fig_num} CAPTION]`.
BE AWARE THAT FIGURE CAPTIONS MAY EXTEND ON TO NEIGHBORING PAGES. 
"""

class DirectoryHandler(DocumentHandler):

    # _DEFAULT_PARSING_INSTRUCTION = "Please extract all infor"    
    def __init__(
            self,
            name: str,
            dirpath: str,
            storage_dir: str,
            desc: str,
            parsing_instructions: str = None,
            **kwargs,
    ):
        
        self._parsing_instructions = parsing_instructions or _DEFAULT_PARSING_PROMPTS
        self._dirpath = dirpath

        super().__init__(
            name=name,
            storage_dir=storage_dir,
            desc=desc,
            **kwargs,
        )

    def get_parser(self):

        return LlamaParse(
            result_type="markdown",
            parsing_instruction=self._parsing_instructions,
            # use_vendor_multimodal_model=True,
            # vendor_multimodal_model_name='anthropic-sonnet-3.5',
            premium_mode=True,
            split_by_page=False,
            page_separator="\n"
        )
        
    def get_reader(self):
        
        file_extractor =  {".pdf": self.get_parser()}
        return SimpleDirectoryReader(input_dir=self._dirpath, file_extractor=file_extractor)
        
    @property
    def node_parser(self):
        return SentenceWindowNodeParser.from_defaults(
            # sentence_splitter = SentenceSplitter(
            #     chunk_size=256,
            #     chunk_overlap=32,
            #     include_prev_next_rel = True,
            #     paragraph_separator='[paragraph break]'
            # ),
            window_size=50,
            window_metadata_key="window",
            original_text_metadata_key="original_text",
        )
    
    def load_docs(self) -> List[Document]:

        return self._reader.load_data()
    

MM_PROMPT_TMPL = """\
Below we have information extracted from a paper relevant to the input query.
Use all of the information available - both markdown and images.

---------------------
{context_str}
---------------------
Given the context information and images and not prior knowledge, respond the query. Explain whether you got the response 
from the markdown text or images, and if there's discrepancies, and your reasoning for the final answer.

Query: {query_str}
Answer: """

MM_PROMPT = PromptTemplate(MM_PROMPT_TMPL)


class MultimodalQueryEngine(CustomQueryEngine):
    """Custom multimodal Query Engine.

    Takes in a retriever to retrieve a set of document nodes.
    Also takes in a prompt template and multimodal model.

    """
    qa_prompt: PromptTemplate
    retriever: BaseRetriever
    multi_modal_llm: Any

    def __init__(self,  
                 qa_prompt: Optional[PromptTemplate] = None,
                 **kwargs
        ) -> None:
        """Initialize."""

        super().__init__(qa_prompt=qa_prompt or MM_PROMPT,  **kwargs)

    def custom_query(self, query_str: str):
        # retrieve text nodes
        nodes = self.retriever.retrieve(query_str)
        # create ImageNode items from text nodes
        image_paths = set([
            image["image_path"]
            for n in nodes  
            for image in n.metadata["images"]
        ])
        image_nodes = [
            NodeWithScore(node=ImageNode(image_path=image_path))
            for image_path in image_paths
        ]

        postprocessor = MetadataReplacementPostProcessor(target_metadata_key="window")
        nodes = postprocessor.postprocess_nodes(nodes)
        # create context string from text nodes, dump into the prompt
        context_str = "\n\n".join(
            [r.get_content(metadata_mode=MetadataMode.LLM) for r in nodes]
        )
        fmt_prompt = self.qa_prompt.format(context_str=context_str, query_str=query_str)

        # synthesize an answer from formatted text and images
        llm_response = self.multi_modal_llm.complete(
            prompt=fmt_prompt,
            image_documents=[image_node.node for image_node in image_nodes],
        )
        return Response(
            response=str(llm_response),
            source_nodes=nodes,
            metadata={"text_nodes": nodes, "image_nodes": image_nodes},
        )


    
class MultimodalDirectoryHandler(DirectoryHandler):

    # def get_parser(self):

    #     return LlamaParse(
    #         result_type="markdown",
    #         parsing_instruction=self._parsing_instructions,
    #         # use_vendor_multimodal_model=True,
    #         # vendor_multimodal_model_name='anthropic-sonnet-3.5',
    #         premium_mode=True,
    #     )
        
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

            try:
                json_objs = parser.get_json_result(file)
            except Exception as e:
                warn(f"Error processing file {file}: {e}")
                continue

            if len(json_objs) == 0:
                continue
            
            # Remove all files in data_images dir
            data_images_dir = os.path.join(self.storage_dir, "data_images")
            if os.path.exists(data_images_dir):
                for filename in os.listdir(data_images_dir):
                    file_path = os.path.join(data_images_dir, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except Exception as e:
                        print(f"Error deleting file {file_path}: {e}")

            image_dicts = parser.get_images(json_objs, download_path=data_images_dir)
            json_dicts = json_objs[0]["pages"]

            # docs_text = text_parser.load_data(file)

            docs += self._get_nodes(json_dicts, image_dicts)

        return docs

    # def _build_vec_index(self, docs: List[Document], node_parser: NodeParser = None):
        
    #     node_parser = node_parser or self.node_parser

    #     if node_parser is not None:
    #         nodes = node_parser.get_nodes_from_documents(docs)
    #         return MultiModalVectorStoreIndex(nodes)
    #     else:
    #         return MultiModalVectorStoreIndex(docs)
    
    def query_engine(self, top_k: int = _DEFAULT_RETRIEVAL_K) -> Any:
        "Return a Query Engine for this document."
        
        return MultimodalQueryEngine(
                    retriever=self.vector_index().as_retriever(
                        similarity_top_k=top_k,
                        node_postprocessors=[
                            MetadataReplacementPostProcessor(target_metadata_key="window")
                        ],
                    ), 
                    multi_modal_llm=_MM_LLM, 
                    similarity_top_k=top_k
                )
    
    def query_engine_tool(self, top_k: int = _DEFAULT_RETRIEVAL_K) -> QueryEngineTool:
        "Return a Tool that can query this document."
        
        return QueryEngineTool(
                query_engine=self.query_engine(top_k = top_k),
                metadata=ToolMetadata(
                    name=f"{self.name}_multimodal_vector_tool",
                    description=f"This tool can query these documents which may include images: {self.desc}.",
                ),
            )
    
    def _get_page_number(self, file_name):
        match = re.search(r"-page[-_](\d+)\.jpg$", str(file_name))
        if match:
            return int(match.group(1))
        return 0
    
    def _get_sorted_image_files(self, image_dir):
        """Get image files sorted by page."""
        raw_files = [f for f in list(Path(image_dir).iterdir()) if f.is_file()]
        sorted_files = sorted(raw_files, key=self._get_page_number)
        return sorted_files
    
    def _get_images_by_page(self, image_dicts):

        image_dicts_by_page = {}
        for image_dict in image_dicts:
            page_num = image_dict['page_number']
            image_path = image_dict['path']
            image_metadata = {"image_path": image_path, "page_num": page_num}
            if image_dicts_by_page.get(page_num):
                image_dicts_by_page[image_dict['page_number']].append(
                    image_metadata
                )
            else:
                image_dicts_by_page[image_dict['page_number']] = [
                    image_metadata
                ]

        return image_dicts_by_page
    
    def _get_nodes(self, json_dicts, image_dicts):
        """Creates nodes from json + images"""

        nodes = []

        # docs = [doc["md"] for doc in json_dicts]  # extract text
        image_dicts_by_page = self._get_images_by_page(image_dicts)  # extract images

        for idx, doc in enumerate(json_dicts):
            # adds both a text node and the corresponding image node (jpg of the page) for each page
            node = TextNode(
                text=doc["md"],
                metadata={"images": image_dicts_by_page[idx + 1]},
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


