# https://medium.com/@akanshak/the-critical-role-of-rerankers-in-rag-98309f52abe5
import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate

load_dotenv()
from cti_app.llm_constants import PROVIDER, LLM_MODEL, TEMPERATURE, OLLAMA_URL, llm
from pathlib import Path

from flashrank import Ranker
from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest
from langchain_chroma import Chroma
from langchain_classic.retrievers.contextual_compression import ContextualCompressionRetriever
from langchain_community.chains.graph_qa.cypher import GraphCypherQAChain
from langchain_community.document_compressors import FlashrankRerank
from langchain_community.graphs import Neo4jGraph
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents.base import Document
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_mistralai import ChatMistralAI
from pydantic import SecretStr
from langgraph.checkpoint.memory import InMemorySaver

from cti_app.embedding_constants import VECTOR_STORE_DIR, COLLECTION_NAME, EMBEDDING_MODEL
from cti_app.services.extract_query_intent import build_filter_from_intent
from cti_app.services.prompt_templates import SYSTEM_PROMPT, CYPHER_PROMPT
from datetime import datetime
import json

# Configuration Parameters
BASE_DIR = Path(__file__).resolve().parents[2]


def get_llm(
    provider: str = PROVIDER,
    model_name: str = LLM_MODEL,
    temperature: float = TEMPERATURE,
    is_cypher_llm: bool = False,
):
    provider = provider.lower()

    if is_cypher_llm and provider == "ollama":
        # model_name = "deepseek-coder:6.7b"
        model_name = "qwen2.5-coder:7b-instruct"

    if provider == "ollama":
        return ChatOllama(
            model=model_name,
            temperature=temperature,
            base_url=OLLAMA_URL
        )
    elif provider == "openai":
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
        )
    elif provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        return ChatAnthropic(
            model_name=model_name,
            temperature=temperature,
            api_key=SecretStr(api_key),
            stop=None,
            timeout=None,
        )
    elif provider == "mistral":
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY not set")

        return ChatMistralAI(
            model_name=model_name,
            temperature=temperature,
            api_key=SecretStr(api_key)
        )
    raise ValueError(f"Unsupported provider: {provider}")


class NomicEmbeddingWrapper(OllamaEmbeddings):
    def __init__(self, model):
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        super().__init__(
            model=model,
            base_url=base_url
        )

    def embed_query(self, text):
        if EMBEDDING_MODEL == "nomic-embed-text":
            return super().embed_query(f"search_query: {text}")
        else:
            return super().embed_query(text)

def load_vectorstore() -> Chroma:
    # needs ollama serve to run
    # If switching to an embedding model that doesn't require a prefix, don't use the wrapper anymore. Also, remove the prefix from the documents then.
    embeddings = NomicEmbeddingWrapper(model=EMBEDDING_MODEL)
    return Chroma(
        persist_directory=VECTOR_STORE_DIR,
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
    )

def build_graph_retriever():
    # access it with a user that has read-only permission (CREATE USER read_only_user SET PASSWORD 'securepassword'; GRANT ROLE reader TO read_only_user; via Neo4j shell or Neo4j Browser)
    graph = Neo4jGraph(
        url= os.getenv("NEO4J_URL", "bolt://localhost:7687"),
        username="neo4j",
        password="password",
        database="neo4j",
    )
    print(graph.schema) # useful for debugging / inspection

    chat_llm = get_llm(temperature=0.0)
    cypher_llm = get_llm(is_cypher_llm=True)

    cypher_chain = GraphCypherQAChain.from_llm(
        llm=chat_llm,
        cypher_llm=cypher_llm,
        cypher_prompt=CYPHER_PROMPT,
        graph=graph,
        return_direct=True,
        validate_cypher=True,
        verbose=True,
        allow_dangerous_requests=True,
    )

    return cypher_chain

def build_compression_retriever(vectorstore: Chroma, k: int = 20, top_n_rerank_docs: int = 10):
    # from https://docs.langchain.com/oss/python/integrations/retrievers/flashrank-reranker
    # make sure that top-n is less than k to actually reduce the results to the best ones

    cache_dir = os.path.join(BASE_DIR, "models", "flashrank")
    os.makedirs(cache_dir, exist_ok=True)

    # Manually initialize the Flashrank Ranker client (else ONNX loading/downloading error)
    flashrank_client = Ranker(
        model_name="ms-marco-MiniLM-L-12-v2",
        cache_dir=cache_dir
    )

    # Pass the pre-initialized client to the LangChain wrapper
    compressor = FlashrankRerank(
        client=flashrank_client,
        top_n=top_n_rerank_docs
    )

    # retriever won't be used, only the compressor
    base_retriever = vectorstore.as_retriever(
        search_kwargs={"k": k}
    )

    return ContextualCompressionRetriever(
        base_retriever=base_retriever,
        base_compressor=compressor,
    )

def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)

def graph_results_to_documents(
    graph_results,
    source: str = "knowledge_graph",
) -> list[Document]:
    """
    Normalize GraphCypherQAChain results into LangChain Documents.
    Handles dicts, lists of dicts, and strings.
    """
    docs = []

    if not graph_results:
        return docs

    # Case 1: list of records (most common)
    if isinstance(graph_results, list):
        for record in graph_results:
            if isinstance(record, dict):
                content = "\n".join(
                    f"{k}: {v}" for k, v in record.items() if v is not None
                )
            else:
                content = str(record)

            docs.append(
                Document(
                    page_content=content,
                    metadata={
                        "source": source,
                        "confidence": "high",
                        "type": "graph",
                    },
                )
            )

    # Case 2: single dict
    elif isinstance(graph_results, dict):
        content = "\n".join(f"{k}: {v}" for k, v in graph_results.items())
        docs.append(
            Document(
                page_content=content,
                metadata={
                    "source": source,
                    "confidence": "high",
                    "type": "graph",
                },
            )
        )

    # Case 3: string fallback
    else:
        docs.append(
            Document(
                page_content=str(graph_results),
                metadata={
                    "source": source,
                    "confidence": "high",
                    "type": "graph",
                },
            )
        )

    return docs

def build_prompt_middleware(vectorstore: Chroma, cypher_chain, evaluation_mode = False):
    """
    Campaign-aware dynamic prompt RAG.
    Uses a two-step chain that always performs retrieval and injects the results as context into a single LLM query.
    https://docs.langchain.com/oss/python/langchain/rag
    """
    compression_retriever = build_compression_retriever(vectorstore)
    # Build BM25 retriever from all documents in the vectorstore
    data = vectorstore.get(include=["documents", "metadatas"])
    if not data["documents"]:
        print("No documents found.")
    all_docs = [
        Document(
            page_content=doc,
            metadata=meta or {}
        )
        for doc, meta in zip(data["documents"], data["metadatas"])
        if (meta or {}).get("type") != "mitre_attack_background"
    ]
    bm25_retriever = BM25Retriever.from_documents(all_docs)
    bm25_retriever.k = 10 # use same default k as dense retrieval

    @dynamic_prompt
    def prompt_with_context(request: ModelRequest) -> str:
        """
        Inject retrieved MITRE context for RAG
        """
        # campaign_id is REQUIRED to perform hybrid search
        last_message_obj = request.messages[-1]
        additional_kwargs = last_message_obj.additional_kwargs or {}
        campaign_id = additional_kwargs.get("campaign_id")
        reference = additional_kwargs.get("reference")
        filter_pdf = additional_kwargs.get("filter_pdf")
        use_filter = filter_pdf == "true"
        non_background_filter = {
            "type": {"$ne": "mitre_attack_background"}
        }

        k = 10

        if not campaign_id:
            raise ValueError("campaign_id (thread_id) is required for RAG")

        last_message = request.state["messages"][-1].text
        print("User Prompt: ", last_message)

        # GRAPH RETRIEVAL: generate Cypher, then execute to give LLM both query and results
        generated_cypher = cypher_chain.cypher_generation_chain.predict(
            question=last_message,
            schema=cypher_chain.graph_schema
        )
        try:
            graph_results = cypher_chain.run({"query": generated_cypher})
        except Exception as e:
            graph_results = None
            print(f"Neo4j query failed: {e}")
        print("Documents from Graph: \n")
        print(graph_results)

        # Adjust the number of vector-store documents that will be retrieved based on whether reference or graph results are
        # already contributing documents, to avoid exceeding the context window
        if graph_results and reference:
            k = 2
        elif graph_results:
            # adapt k as more graph documents are present (graph results take priority)
            # k ranges from 2 to 10 based on how many graph documents are already retrieved
            result_size = len(graph_results)
            k = max(2, int(10 * (1-(result_size / 10))))
        elif reference:
            # reference will add at least 1-7 very relevant documents
            k = 3

        # VECTOR STORE RETRIEVAL: Recall (large k)
        # Uses an LLM to infer the intended subject from the query (especially helpful when the graph returns no results)
        semantic_filter = build_filter_from_intent(
            query=last_message,
            campaign_id=campaign_id
        )
        print(semantic_filter)

        # Filtered search leveraging metadata and known entities/relationships.
        keyword_docs = vectorstore.similarity_search(
            last_message,
            k=k,
            filter=semantic_filter,
        )
        print("Documents from Intent Filter: \n")
        pretty_print_docs(keyword_docs)

        # Dense semantic search to retrieve documents based on meaning, including both campaign-related and general context (e.g., group descriptions)
        semantic_docs = vectorstore.similarity_search(
            last_message,
            k=k,
            filter=non_background_filter if use_filter else None,
        )
        print("\nDocuments from Dense Semantic Search: \n")
        pretty_print_docs(semantic_docs)

        # Sparse BM25 search: retrieves the top-k documents using keyword matching rather than embeddings
        bm25_retriever.k = k
        bm25_docs = bm25_retriever.invoke(last_message)
        print("\nDocuments from Sparse Keyword Search: \n")
        pretty_print_docs(bm25_docs)

        # VECTOR STORE RETRIEVAL: Rerank + Compress
        docs = semantic_docs + keyword_docs + bm25_docs
        # Deduplicate before sending to compressor
        unique_docs_dict = {}
        for doc in docs:
            key = doc.page_content
            if key not in unique_docs_dict:
                unique_docs_dict[key] = doc
        unique_docs = list(unique_docs_dict.values())
        print("Unique Documents: \n")
        pretty_print_docs(unique_docs)

        # Keep only the 10 most relevant documents for the LLM; does not summarize or truncate.
        reranked = compression_retriever.base_compressor.compress_documents(
            documents=unique_docs,
            query=last_message,
        )
        print("Reranked Documents: \n")
        pretty_print_docs(reranked)

        if reference:
            reference_filter = {
                "name": reference["label"]
            }
            searched_entity_doc = vectorstore.similarity_search(
                last_message,
                k=1,
                filter=reference_filter,
            )
            reranked = searched_entity_doc + list(reranked)

            for doc in searched_entity_doc:
                # Extract the STIX ID from the metadata of the retrieved document which was fetched by filtering on the entity name.
                # (maybe refactor later to pass the STIX ID instead of deriving it from the retrieved document metadata)
                ref_stix_id = doc.metadata.get("stix_id")
                print(ref_stix_id)
                if ref_stix_id:
                    searched_entity_rel_docs = vectorstore.similarity_search(
                        last_message,
                        k=5,
                        filter={ # type: ignore[arg-type]
                            "$or": [
                                {"source_ref": ref_stix_id},
                                {"target_ref": ref_stix_id},
                            ]
                        }
                    )
                    # the following search will return a relationship document of the selected campaign to the referenced entity
                    searched_entity_rel_campaign_doc = vectorstore.similarity_search(
                        last_message,
                        k=1,
                        filter={ # type: ignore[arg-type]
                            "$and": [
                                {"source_ref": campaign_id},
                                {"target_ref": ref_stix_id},
                            ]
                        }
                    )
                    reranked = searched_entity_rel_docs + searched_entity_rel_campaign_doc + reranked
            print("Reranked Entities with reference docs: \n")
            pretty_print_docs(reranked)

        docs = {doc.page_content: doc for doc in reranked}
        retrieved_docs = list(docs.values())

        context = "\n\n".join(doc.page_content for doc in retrieved_docs)
        if evaluation_mode:
            # save docs in json file to evaluate them
            trace = init_trace(last_message, campaign_id)
            if not graph_results:
                trace["graph"] = {"cypher": generated_cypher, "documents": []}
            else:
                graph_docs = graph_results_to_documents(graph_results)
                trace["graph"] = {"cypher": generated_cypher, "documents": serialize_docs(graph_docs, include_metadata=False)} # graph results don't include any of the original documents metadata, will be checked manual
            trace["retrievers"]["dense"] = serialize_docs(semantic_docs)
            trace["retrievers"]["intent_filter"] = serialize_docs(keyword_docs)
            trace["retrievers"]["sparse"] = serialize_docs(bm25_docs)
            trace["reranker"]["input"] = serialize_docs(unique_docs)
            trace["reranker"]["output"] = serialize_docs(reranked)
            logs_dir = BASE_DIR / "cti_app" / "evaluation" / "rag_documents_from_queries"
            logs_dir.mkdir(parents=True, exist_ok=True)
            file_identification = last_message.replace(" ", "_")
            filename = logs_dir / f"{file_identification}.json"
            with open(filename, "w") as f:
                json.dump(trace, f, indent=2)

        if graph_results:
            graph_docs = graph_results_to_documents(graph_results)
            graph_context = "\n\n".join(doc.page_content for doc in graph_docs)
            system_message = (
                SYSTEM_PROMPT.format() + "\n\n"
                "Answer the user's question using the retrieved MITRE ATT&CK context below. "
                "The context has already been filtered, scoped, and validated to directly answer the user’s question and is relevant for the campaign.\n"
                "The authoritative context directly represents the answer to the user’s question."
                "All listed entities, techniques, and relationships are already attributed to the subject of the question.\n"
                "Knowledge graph results are authoritative. "
                "If knowledge graph and vector store information differ, ALWAYS follow the knowledge graph.\n\n"
                "### AUTHORITATIVE MITRE ATT&CK CONTEXT WHICH SHOULD BE USED TO ANSWER (KNOWLEDGE GRAPH)\n"
                "The used Cypher query to answer the question was:\n"
                f"{generated_cypher}\n"
                "Results:\n"
                f"{graph_context}\n\n"

                "### SUPPORTING MITRE ATT&CK CONTEXT (VECTOR STORE) — only use this if the knowledge graph results are insufficient\n"
                f"{context}"
            )
            tokens = estimate_tokens(system_message) # context length of 128K
            print("TOKENS: ", tokens)
            print(system_message)
            return system_message
        else:
            system_message = (
                SYSTEM_PROMPT.format() + "\n\n"
                "Answer the user's question using the retrieved MITRE ATT&CK context below whenever possible. "
                "If the information needed to answer the question is NOT present in the retrieved context, "
                "clearly state that the answer is NOT found in the MITRE ATT&CK data and that the response is AI-generated and may contain inaccuracies.\n\n"
                "Retrieved MITRE ATT&CK context:\n"
                f"{context}"
            )
            print(system_message)
            return system_message

    return prompt_with_context


def build_rag_agent(
        provider: str = PROVIDER,
        model_name: str = LLM_MODEL,
        temperature: float = TEMPERATURE,
):
    """
    Builds a RAG agent with short-term memory and automatic vectorstore retrieval, using a system prompt tailored for C-level communication.
    """
    chat_llm = get_llm(
        provider=provider,
        model_name=model_name,
        temperature=temperature,
    )

    vectorstore = load_vectorstore()
    graph_retriever = build_graph_retriever()
    prompt_middleware = build_prompt_middleware(vectorstore, graph_retriever)

    agent = create_agent(
        model=chat_llm,
        tools=[],
        system_prompt=SYSTEM_PROMPT.format(),
        middleware=[prompt_middleware],
        checkpointer=InMemorySaver(),
    )

    return agent

def build_simple_agent_with_memory(
        provider: str = PROVIDER,
        model_name: str = LLM_MODEL,
        temperature: float = TEMPERATURE,
):
    """
    Create a non-RAG LangChain agent that uses only the provided context,
    without automatic data retrieval from the vectorstore.
    Suitable for fixed-scope tasks (e.g., FAQ generation) where all data
    is already prepared and given to the agent.
    """
    chat_llm = get_llm(
        provider=provider,
        model_name=model_name,
        temperature=temperature,
    )

    agent = create_agent(
        model=chat_llm,
        tools=[],
        system_prompt=SYSTEM_PROMPT.format(),
        checkpointer=InMemorySaver(),
    )
    return agent

def build_simple_agent():
    """
    Create an agent with a system prompt focused on communication to C-level suite
    Uses the default settings (else use get_llm to specify temperature etc.)
    """
    agent = create_agent(
        model=llm,
        tools=[],
        system_prompt=SYSTEM_PROMPT.format(),
    )

    return agent

def build_simple_agent_no_system_prompt():
    """
    Create an agent with a system prompt focused on communication to C-level suite
    Uses the default ollama settings (else use get_llm to specify temperature etc.)
    """
    agent = create_agent(
        model=llm,
    )

    return agent

def pretty_print_docs(docs):
    """
    Helper function for printing docs
    """
    print(
        f"\n{'-' * 100}\n".join(
            [
                f"Document {i + 1}:\n\n{d.page_content}\nMetadata: {d.metadata}"
                for i, d in enumerate(docs)
            ]
        )
    )

def init_trace(query: str, campaign_id: str):
    return {
        "query": query,
        "campaign_id": campaign_id,
        "retrievers": {},
        "reranker": {},
    }

def serialize_docs(docs, include_metadata=True):
    return [
        {
            "content": doc.page_content,
            **({"metadata": str(doc.metadata)} if include_metadata else {})
        }
        for doc in docs
    ]
