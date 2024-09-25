from abc import ABC, abstractmethod
from logging import warn
from multiprocessing import process
import pickle
import re
from typing import Union, List, Any
import os
from pathlib import Path
from time import sleep
import urllib3
import tempfile
from PIL import Image
from io import BytesIO
import requests
from pydantic import BaseModel, Field

from groundx import Groundx
from llmsherpa.readers import LayoutPDFReader
from llmsherpa.readers.layout_reader import Section
from llama_index.postprocessor.cohere_rerank import CohereRerank

from llama_parse import LlamaParse
from llama_index.core.vector_stores.types import MetadataFilters
from llama_index.core.node_parser import MarkdownNodeParser, NodeParser, SentenceSplitter
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
from llama_index.core.multi_modal_llms import MultiModalLLM
from llama_index.multi_modal_llms.openai import OpenAIMultiModal
from llama_index.core.schema import ImageNode, NodeWithScore, MetadataMode
from llama_index.core.prompts import PromptTemplate
from llama_index.core.base.response.schema import Response
from typing import Optional
from llama_index.core.node_parser import SentenceWindowNodeParser
from llama_index.core.postprocessor import MetadataReplacementPostProcessor
from llama_index.core.extractors import PydanticProgramExtractor
from llama_index.core.program import MultiModalLLMCompletionProgram
from llama_index.core.schema import QueryBundle
from llama_index.core.output_parsers.pydantic import PydanticOutputParser

from plotreader.utils.structured_types.paper import PageMetadata
import plotreader
from plotreader import _DEFAULT_EMBEDDING_MODEL, _MM_LLM, _GPT4O_MULTIMODAL
from plotreader.utils.base import BasicAnthropicAgent

_DEFAULT_RETRIEVAL_K = 5


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
    
    @property
    def node_parser(self):
        "Get the node parser for this document handler."
        return None
    
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
    

_DEFAULT_PARSING_PROMPT = """
The provided document is a scientific paper. 
Ignore all headers and footers that are metadata (like citation info).
If possible, create sections for each figure caption - some figure captions may be split across pages.
Be aware that in some PDFs the figurs and captions are embedded in the layout and in others all of the figures are grouped together in a section - often at the end.
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
        
        self._parsing_instructions = parsing_instructions or _DEFAULT_PARSING_PROMPT
        self._dirpath = dirpath

        super().__init__(
            name=name,
            storage_dir=storage_dir,
            desc=desc,
            **kwargs,
        )
        
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

        parser = LlamaParse(
            result_type="markdown",
            parsing_instruction=self._parsing_instructions,
            # use_vendor_multimodal_model=True,
            # vendor_multimodal_model_name='anthropic-sonnet-3.5',
            premium_mode=True,
            split_by_page=True,
            page_separator="\n",
            take_screenshot=True,
        )

        file_extractor =  {".pdf": parser}
        reader = SimpleDirectoryReader(input_dir=self._dirpath, file_extractor=file_extractor)

        return reader.load_data()
    

MM_PROMPT_TMPL = """\
Below we provide information from a paper relevant to the input query.

RETRIEVED INFORMATION:
---------------------
{context_str}
---------------------

Given that information and the provided images, respond to the query below. 
Be sure to check all images for information even if the text seems sufficient.
There may be discrepancies or errors in either one. Use all available information to resolve the discrepancies if possible.

Query: {query_str}
Answer: """

MM_PROMPT = PromptTemplate(MM_PROMPT_TMPL)


class MultimodalQueryEngine(CustomQueryEngine):
    """Custom multimodal Query Engine.

    Takes in a retriever to retrieve a set of document nodes.
    Also takes in a prompt template and multimodal model.

    """
    retriever: BaseRetriever
    qa_prompt: PromptTemplate = Field(default_factory=lambda: MM_PROMPT)
    multi_modal_llm: MultiModalLLM = Field(default_factory=lambda: _MM_LLM)
    node_postprocessors: Optional[list] = Field(default_factory=list)

    # def __init__(self,  
    #              qa_prompt: Optional[PromptTemplate] = None,
    #              node_postprocessors: Optional[List] = None,
    #              **kwargs
    #     ) -> None:
    #     """Initialize."""
    #     self.node_postprocessors = node_postprocessors or []
    #     super().__init__(qa_prompt=qa_prompt or MM_PROMPT, **kwargs)

    def custom_query(self, query_str: str):
        # retrieve text nodes
        nodes = self.retriever.retrieve(query_str)

        # Apply node postprocessors
        for postprocessor in self.node_postprocessors:
            nodes = postprocessor.postprocess_nodes(nodes, query_bundle=QueryBundle(query_str=query_str))
        # create ImageNode items from text nodes
        image_paths = set([
            image["image_path"]
            for n in nodes  
            if n.metadata.get("images")
            for image in n.metadata["images"]
        ])
        converted_image_nodes = [
            ImageNode(image_path=image_path)
            for image_path in image_paths
        ]
        retrieved_image_nodes = [
            node.node
            for node in nodes
            if isinstance(node.node, ImageNode)
        ]
        image_nodes = converted_image_nodes + retrieved_image_nodes

        # postprocessor = MetadataReplacementPostProcessor(target_metadata_key="window")
        # nodes = postprocessor.postprocess_nodes(nodes)
        # create context string from text nodes, dump into the prompt

        

        context_str = "\n\n".join(
            [r.get_content(metadata_mode=MetadataMode.LLM) for r in nodes]
        )
        fmt_prompt = self.qa_prompt.format(context_str=context_str, query_str=query_str)

        

        # synthesize an answer from formatted text and images
        llm_response = self.multi_modal_llm.complete(
            prompt=fmt_prompt,
            image_documents=image_nodes,
        )
        return Response(
            response=str(llm_response),
            source_nodes=nodes,
            metadata={"text_nodes": nodes, "image_nodes": image_nodes},
        )

class MultiModalDocumentHandler(DocumentHandler):

    def _get_retriever(self, top_k: int = _DEFAULT_RETRIEVAL_K, metadata_filters: MetadataFilters = None):
        return self.vector_index().as_retriever(
            similarity_top_k=top_k, 
            filters=metadata_filters
        )

    def query_engine(self, top_k: int = _DEFAULT_RETRIEVAL_K, metadata_filters: MetadataFilters = None, node_postprocessors = None) -> Any:
        "Return a Query Engine for this document."
        
        retriever = self._get_retriever(top_k = top_k, metadata_filters=metadata_filters)
        return MultimodalQueryEngine(
                    retriever=retriever, 
                    multi_modal_llm=_MM_LLM, 
                    node_postprocessors = node_postprocessors,
                )
    
    def query_engine_tool(self, top_k: int = _DEFAULT_RETRIEVAL_K, metadata_filters: MetadataFilters = None, ) -> QueryEngineTool:
        "Return a Tool that can query this document."
        cohere_rerank = CohereRerank(top_n=10)
        return QueryEngineTool(
                query_engine=self.query_engine( 
                    top_k = top_k,
                    metadata_filters=metadata_filters,
                    node_postprocessors=[]#[cohere_rerank]
                ),
                metadata=ToolMetadata(
                    name=f"{self.name}_multimodal_vector_tool",
                    description=f"This tool can query these documents which may include images: {self.desc}.",
                ),
            )
    
class MultimodalDirectoryHandler(DirectoryHandler, MultiModalDocumentHandler):
        
    def load_docs(self) -> List[Document]:
        
        parser = LlamaParse(
            result_type="markdown",
            parsing_instruction=self._parsing_instructions,
            # use_vendor_multimodal_model=True,
            # vendor_multimodal_model_name='anthropic-sonnet-3.5',
            premium_mode=True,
            split_by_page=False,
            page_separator="\n"
        )
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
                

    def load_docs(self) -> List[Document]:

        reader = GithubRepositoryReader(
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

        return reader.load_data(branch=self._branch)
    
    @property
    def node_parser(self):

        if self._language is None:
            return None
        else:
            return CodeSplitter(self._language) # NOTE: I EDITED THE SOURCE IN THIS ENV TO PROPERLY LOAD THE PYTHON PARSER



class ScientificDocNodeMetadata(BaseModel):
    """Node metadata."""

    experimental_variable_entities: list[str] = Field(
        ...,
        description="A list of independent or dependent variables in experiments"
    )
    fig_refs: list[str] = Field(
        ...,
        description="A list of figures that are referenced in this text including figure captions."
    )

class MetadataResponse(BaseModel):
    node_metadata: ScientificDocNodeMetadata
    finished_page_img: bool = Field(
        ...,
        description="Whether or not the next node will require the next page."
    )
    text_not_found: bool = Field(
        ...,
        description="Whether or not the text was not found in the page."
    )

class ScientificDocImageNodeRevision(BaseModel):
    figure_id: str = Field(
        ...,
        description="The name of this figure in the paper (e.g. Figure 1, Figure 2, etc.)."
    )
    revised_text: str = Field(
        ...,
        description="The revised text of the supplied figure description."
    )


from llama_index.core.node_parser import get_leaf_nodes
from llama_index.core.schema import TextNode, IndexNode, NodeRelationship, RelatedNodeInfo

class ScientificPaperHandler(MultiModalDocumentHandler):

    # _LLMSHERPA_LOCAL_URL = "http://localhost:5010/api/parseDocument?renderFormat=all"

    def __init__(
            self,
            filepath: str = None,
            document_id: str = None,
            **kwargs
    ):
        
        if filepath is not None:
            
            file_extension = filepath.split(".")[-1].lower()
            if file_extension != "pdf":
                raise ValueError("Only PDF files are allow.")
        
        self._filepath = filepath
        self._document_id = document_id

        super().__init__(**kwargs)


    # def _get_retriever(self, top_k: int = _DEFAULT_RETRIEVAL_K):
        



    def _llamaindex_parse(self):

        parser = LlamaParse(
            result_type="markdown",
            parsing_instruction=_DEFAULT_PARSING_PROMPT,
            # use_vendor_multimodal_model=True,
            # vendor_multimodal_model_name='anthropic-sonnet-3.5',
            premium_mode=True,
            split_by_page=True,
            page_separator="\n",
            take_screenshot=True,
        )

        json_objs = parser.get_json_result(self._filepath)

        data_images_dir = os.path.join(self.storage_dir, "data_images" + "_page_screenshots")
        if os.path.exists(data_images_dir):
            for filename in os.listdir(data_images_dir):
                file_path = os.path.join(data_images_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")

        image_dicts = parser.get_images(json_objs, download_path=data_images_dir)

        # You've also been provided with an image of the page and the page before and after (if they exist).
        revision_prompt = """Below is a markdown string parsed from a target page of a scientific paper PDF. 
Your job is to revise the levels of each part of the extracted markdown string so it matches the image of the PDF and makes sense with the document so far.
You will be given the image of the target page and the page before (if it exists). The initial parsed markdown string is provided below.
Do your best to infer the image of the page AND the inferred structure of the document so far.
Use common sense about what the main sections of a scientific paper are (e.g. Abstract, Introduction, Methods, Results, Discussion, References, etc.).

DO NOT CHANGE THE CONTENT OF THE PARAGRAPHS, ONLY THE HEADERS AND THEIR LEVELS to best match the PDF image.
You may add headers/levels if a section was only denoted based on visual formating (e.g. an abstract, table of contents, or figure caption).
Assume that each page is a continuation of the section at the end of the previous page unless you are provided with clear evidence to the contrary.
Do not include any content or headers from headings or footers at the top and bottom of each page even if they were originally extracted into the markdown.

Do your best to put figure captions in their own sections. If the target page does not have any other section headers, then the figure caption should be the first section and you should add a header to restart the current section.

To aid you, I've provided the inferred levels and headers of the document so far - separated by page.
IMPORTANT: this is one continuous document, so you don't need to add parent headers if they aren't on the target page.

Target page number: {page_number}

LEVEL/HEADERS OF DOCUMENT SO FAR (SEPARATED BY PAGE):
{previous_page_headers}

PARSED MARKDOWN:
{content1}

Return only the final markdown string without any other text.
        """

        claude_mm = BasicAnthropicAgent(model="claude-3-5-sonnet-20240620")
        image_by_page = []
        full_page_dicts = []
        doc_headers = []
        prev_page_image = None
        for image_dict in image_dicts:
            if image_dict.get("type") == "full_page_screenshot":
                
                full_page_dicts.append(image_dict)
                # get page metadata
                page_num = image_dict.get("page_number")
                page_img = Image.open(image_dict.get("path"))
                image_by_page.append(page_img)
                
        #         # revise page markdown
        #         try:
        #             page_md = json_objs[0]["pages"][page_num-1]["md"]
        #             revision_prompt_with_md = revision_prompt.format(
        #                 page_number=page_num, 
        #                 content1=page_md,
        #                 previous_page_headers=f"\n".join(doc_headers),
        #             )
        #             print(revision_prompt_with_md)
        #             images = [prev_page_image] if prev_page_image is not None else []
        #             images += [page_img]
        #             response = claude_mm.message(revision_prompt_with_md, images=images)
        #             revised_md = response.content[0].text
        #             json_objs[0]["pages"][page_num-1]["md_revised"] = revised_md

                    
        #             doc_headers.append(f"[PAGE {page_num}]")
        #             node = TextNode(text=revised_md)
        #             nodes = MarkdownNodeParser().get_nodes_from_node(node)
        #             for node in nodes:
        #                 node_level = -1
        #                 header = ""
        #                 for key in node.metadata.keys():
        #                     if key.startswith("Header_"):
        #                         level = int(key.split("_")[1])
        #                         if level > node_level:
        #                             node_level = level
        #                             header = "".join(["#"]*level) + " " + node.metadata.get(key)
        #                 doc_headers.append(header)
        #         except Exception as e:
        #             print(e)    
        #             json_objs[0]["pages"][page_num-1]["md_revised"] = page_md

        # full_text = ""
        # for page in json_objs[0]["pages"]:
        #     if page["md_revised"].startswith("#"):
        #         prefix = "\n\n"
        #     else:
        #         prefix = ""
        #     full_text += prefix + page["md_revised"]

        # nodes = MarkdownNodeParser().get_nodes_from_node(TextNode(text=f"{full_text.strip()}"))

        # pickle.dump(nodes, open(os.path.join(self.storage_dir, "llama_text_nodes_cp01.pkl"), "wb"))

#         nodes = pickle.load(open(os.path.join(self.storage_dir, "llama_text_nodes_cp01.pkl"), "rb"))

#         output_parser = PydanticOutputParser(output_cls=ScientificDocNodeMetadata)
#         prompt_page_metadata ="""
# Extract the metadata descrbied in the structure below from the text of the node.

# Node Text:
# {node_text}
# """
           

#         # cur_page = 1
#         # cur_image = image_by_page[0]
#         for node in nodes:
#             clean_txt = node.text.replace("{", "{{").replace("}","}}")
#             prompt = PromptTemplate(
#                 prompt_page_metadata.format(node_text=clean_txt),
#                 output_parser = output_parser
#             ).format(
#                 llm=plotreader._CLAUDE_SONNET35_MULTIMODAL
#             )
#             response = claude_mm.message(prompt)
#             metadata_response = output_parser.parse(response.content[0].text)
#             node.metadata.update(metadata_response.model_dump())
#             # if metadata_response.finished_page_img and cur_page < len(image_by_page):
#             #     cur_image = image_by_page[cur_page]
#             #     cur_page += 1

#         pickle.dump(nodes, open(os.path.join(self.storage_dir, "llama_text_nodes_cp02.pkl"), "wb"))
        nodes = pickle.load(open(os.path.join(self.storage_dir, "llama_text_nodes_cp02.pkl"), "rb"))
        return nodes, full_page_dicts

    # def _llmsherpa_text_parse(self):

    #     reader = LayoutPDFReader(self._LLMSHERPA_LOCAL_URL)
    #     parsed_doc = reader.read_pdf(self._filepath)

    #     return parsed_doc
    
    def _is_groundx_processing(self, groundx, process_id):

        response = groundx.documents.get_processing_status_by_id(
            process_id=process_id
        )

        return response
    
    def _revise_image_nodes(self, image_nodes):

        claude_mm = BasicAnthropicAgent(model="claude-3-5-sonnet-20240620")

        base_prompt = """
You are an expert at detailed descriptions of figures in scientific papers.
You will be given a figure and an attempt to describe that figure with text.
Your job is to revise the text to best describe the figure.
In particular, you should ensure that all details about labels and values are accurate.
Always defer to the image.

ATTEMPTED DESCRIPTION:
{description}

"""

        
        for image_node in image_nodes:
            
            prompt = base_prompt.format(description=image_node.text)

            response = requests.get(image_node.image_url)
            fig_img = Image.open(BytesIO(response.content))

            response = claude_mm.message(prompt, images=[fig_img])
            
            image_node.text = response.content[0].text

            
        return image_nodes
    
    def _get_image_nodes_groundx(self):

        fig_chunks = self._get_figchunks_groundx()
        image_nodes = self._chunks_to_image_nodes(fig_chunks)
        image_nodes = self._revise_image_nodes(image_nodes)

        return image_nodes


    def _get_figchunks_groundx(self):
        
        groundx = Groundx(
            api_key=os.environ['GROUNDX_API_KEY'],
        )

        if self._document_id is not None:

            response = groundx.documents.get(document_id = self._document_id)
            doc = response.body
            url = doc['document']['xrayUrl']

        else:
            filename = os.path.split(self._filepath)[-1].split('.')[0]
            response = groundx.documents.ingest_local(
                body=[
                    {
                        "blob": open(self._filepath, "rb"),
                        "metadata": {
                            "bucketId": 11481,
                            "fileName": filename,
                            "fileType": "pdf",
                            "searchData": {},
                        },
                    },
                ]
            )

            process_id = response.body['ingest']['processId']
            is_processing = True
            while is_processing:
                sleep(10.)
                response = self._is_groundx_processing(groundx, process_id)
                is_processing = response.body['ingest']['status'] != "complete"
                    
            url = response.body['ingest']['progress']['complete']['documents'][0]['xrayUrl']

        doc_json = urllib3.request("GET",url).json()
        fig_chunks = []
        for chunk in doc_json['chunks']:
            if 'figure' in chunk['contentType']:
                fig_chunks.append(chunk)

        return fig_chunks
    
    def _chunks_to_image_nodes(self, fig_chunks):


        image_nodes = []
        for chunk in fig_chunks:
                
            image_nodes.append(
                ImageNode(
                    image_url = chunk['multimodalUrl'],
                    text = "".join(chunk['suggestedText']),
                    metadata = {
                        "page_number": chunk['pageNumbers'][0]
                    }
                )
            )

        return image_nodes
    
    def _extract_page_metadata(self, image_dicts):

        claude_mm = BasicAnthropicAgent(model="claude-3-5-sonnet-20240620")

        output_parser = PydanticOutputParser(output_cls=PageMetadata)
        prompt_page_metadata = PromptTemplate(
            "The image provided is a page from a scientific paper. Is there a figure in this image? If so, what is the figure's name?",
            output_parser=output_parser
        ).format(llm=plotreader._CLAUDE_SONNET35_MULTIMODAL)

        page_metadata_responses = []
        prev_page_contains_fig_caption = False
        for image_dict in image_dicts:
            if image_dict.get("type") == "full_page_screenshot":

                # get page metadata
                page_num = image_dict.get("page_number")
                page_img = Image.open(image_dict.get("path"))
                response = claude_mm.message(prompt_page_metadata, images=[page_img])
                page_metadata_responses.append(output_parser.parse(response.content[0].text))

        return page_metadata_responses
                

    def _build_markdown_nodes(self, page_dicts):

        full_text = ""
        for page in page_dicts:
            if page["md_revised"].startswith("#"):
                prefix = "/n/n"
            else:
                prefix = ""
            full_text += prefix + page["md_revised"]

        return full_text
    
    def load_docs(self):

        # # image_nodes = self._get_image_nodes_groundx()
        # # pickle.dump(image_nodes, open(os.path.join(self.storage_dir, "image_nodes.pkl"), "wb"))
        # image_nodes = pickle.load(open(os.path.join(self.storage_dir, "image_nodes.pkl"), "rb"))

        # # # doc_tree = self._llmsherpa_text_parse()
        # text_nodes, full_page_dicts = self._llamaindex_parse()
        # # pickle.dump(text_nodes, open(os.path.join(self.storage_dir, "text_nodes.pkl"), "wb"))
        # pickle.dump(full_page_dicts, open(os.path.join(self.storage_dir, "full_page_dicts.pkl"), "wb"))
        

        
        # text_nodes = pickle.load(open(os.path.join(self.storage_dir, "text_nodes.pkl"), "rb"))
        # full_page_dicts = pickle.load(open(os.path.join(self.storage_dir, "full_page_dicts.pkl"), "rb"))

        # claude_mm = BasicAnthropicAgent(model="claude-3-5-sonnet-20240620")
        # for node in image_nodes:
        #     page_num = node.metadata.get("page_number")
        #     for page_dict in full_page_dicts:
        #         if page_dict.get("page_number") == page_num:
        #             page_img = Image.open(page_dict.get("path"))

        #     response = requests.get(node.image_url)
        #     fig_image = Image.open(BytesIO(response.content))
        #     class FigureName(BaseModel):
        #         figure_name: str = Field(
        #             ...,
        #             description="The name of the figure in the scientific paper (e.g. Figure 1, Figure 2, etc.)."
        #         )
        #     prompt = "Which figure is shown in the cropped image? Use the full page image as a reference."

        #     output_parser = PydanticOutputParser(output_cls=FigureName)
        #     prompt_figure_name = PromptTemplate(
        #         prompt,
        #         output_parser=output_parser
        #     ).format(llm=plotreader._CLAUDE_SONNET35_MULTIMODAL)

            
        #     response = claude_mm.message(prompt_figure_name, images=[fig_image, page_img])
        #     figure_name = output_parser.parse(response.content[0].text)
        #     node.metadata['fig_refs'] = [figure_name.figure_name]

        # all_nodes = text_nodes + image_nodes

        # pickle.dump(all_nodes, open(os.path.join(self.storage_dir, "all_nodes.pkl"), "wb"))
        all_nodes = pickle.load(open(os.path.join(self.storage_dir, "all_nodes.pkl"), "rb"))

        index_nodes = self._build_hierarchical_structure(all_nodes)

        # all_nodes += index_nodes
                    
        return all_nodes

    def _build_hierarchical_structure(self, nodes: List[TextNode]) -> List[IndexNode]:
        hierarchical_nodes: dict[str, IndexNode] = {}
        root = IndexNode(text="Root", index_id="root")
        hierarchical_nodes[""] = root

        for node in nodes:

            MAX_DEPTH = 10
            metadata = node.metadata
            headers = [metadata.get(f"Header_{i}", "") for i in range(1, MAX_DEPTH) if f"Header_{i}" in metadata]
            
            current_path = ""
            parent_node = root
            
            for i, header in enumerate(headers):
                current_path += header
                if current_path not in hierarchical_nodes:
                    new_index_node = IndexNode(text=header, index_id=f"index_{current_path.replace('/', '_')}")
                    hierarchical_nodes[current_path] = new_index_node
                    # parent_node.add_child(new_index_node)
                    if parent_node.relationships.get(NodeRelationship.CHILD) is None:
                        parent_node.relationships[NodeRelationship.CHILD] = []
                    child_rel = [RelatedNodeInfo(
                        node_id=new_index_node.node_id,
                        # node_type=new_index_node.node_type,
                    )]
                    parent_node.relationships[NodeRelationship.CHILD] += child_rel
                    parent_node = new_index_node
                else:
                    parent_node = hierarchical_nodes[current_path]

            # Add the original TextNode as a child of the deepest IndexNode
            # parent_node.add_child(node)
            if parent_node.relationships.get(NodeRelationship.CHILD) is None:
                parent_node.relationships[NodeRelationship.CHILD] = []
            child_rel = [RelatedNodeInfo(
                node_id=node.node_id,
                # node_type=new_index_node.node_type,
            )]
            parent_node.relationships[NodeRelationship.CHILD] += child_rel

            # Update relationships
            node.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(
                node_id=parent_node.node_id,
                # node_type=parent_node.node_type,
                # metadata={"header": headers[-1] if headers else ""}
            )

        return list(hierarchical_nodes.values())