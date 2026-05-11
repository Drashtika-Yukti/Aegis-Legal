import os
import tempfile
import asyncio
import uuid
import numpy as np
from typing import List, Dict
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_cohere import CohereEmbeddings
import cohere
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as rest
import pickle
from core.logger import get_logger
from core.config import settings

logger = get_logger("LocalVault")
VAULT_PATH = "./data/vault.pkl"

class LocalVault:
    """Standalone local vector vault with Async Qdrant integration and local fallback."""
    def __init__(self):
        self.embeddings = None
        self.co_client = None
        self.qdrant = None
        
        if settings.COHERE_API_KEY:
            self.embeddings = CohereEmbeddings(model="embed-english-v3.0", cohere_api_key=settings.COHERE_API_KEY)
            self.co_client = cohere.ClientV2(api_key=settings.COHERE_API_KEY)
        
        if settings.QDRANT_URL:
            try:
                self.qdrant = AsyncQdrantClient(
                    url=settings.QDRANT_URL, 
                    api_key=settings.QDRANT_API_KEY
                )
                # Note: Collections ensured in background or first call
                logger.info("Vault initialized with Async Qdrant Cloud.")
            except Exception as e:
                logger.error(f"Qdrant Connection Failed: {e}")

        self.ingest_semaphore = asyncio.Semaphore(5)
        self.vectors = [] 
        self.documents = []
        self.parent_documents = {}
        self._load_vault()

    async def _ensure_collections(self):
        """Idempotent collection creation."""
        try:
            collections = await self.qdrant.get_collections()
            existing = [c.name for c in collections.collections]
            
            if "aegis_legal_docs" not in existing:
                logger.info("Creating Qdrant collection: aegis_legal_docs")
                await self.qdrant.create_collection(
                    collection_name="aegis_legal_docs",
                    vectors_config=rest.VectorParams(size=1024, distance=rest.Distance.COSINE),
                )
            
            if "aegis_facts" not in existing:
                logger.info("Creating Qdrant collection: aegis_facts")
                await self.qdrant.create_collection(
                    collection_name="aegis_facts",
                    vectors_config=rest.VectorParams(size=1024, distance=rest.Distance.COSINE),
                )
        except Exception as e:
            # If it already exists or other error, log it but don't crash
            logger.warning(f"Vault | Collection Ensure Note: {e}")

    def _load_vault(self):
        if os.path.exists(VAULT_PATH):
            try:
                with open(VAULT_PATH, "rb") as f:
                    data = pickle.load(f)
                    self.vectors = data.get("vectors", [])
                    self.documents = data.get("documents", [])
                    self.parent_documents = data.get("parent_documents", {})
                logger.info(f"Loaded {len(self.documents)} local chunks.")
            except Exception as e:
                logger.error(f"Failed to load vault: {e}")

    def _save_vault(self):
        try:
            os.makedirs(os.path.dirname(VAULT_PATH), exist_ok=True)
            with open(VAULT_PATH, "wb") as f:
                pickle.dump({
                    "vectors": self.vectors, 
                    "documents": self.documents,
                    "parent_documents": self.parent_documents
                }, f)
        except Exception as e:
            logger.error(f"Failed to save vault: {e}")

    async def store_fact(self, user_id: str, fact: str):
        """Stores a long-term atomic fact in Qdrant."""
        if not self.qdrant or not self.embeddings:
            return
        try:
            await self._ensure_collections()
            vector = await self.embeddings.aembed_query(fact)
            await self.qdrant.upsert(
                collection_name="aegis_facts",
                points=[rest.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={"fact": fact, "user_id": user_id, "type": "atomic_fact"}
                )]
            )
            logger.info(f"Fact stored in Qdrant for {user_id}")
        except Exception as e:
            logger.error(f"Fact Storage Error: {e}")

    async def ingest(self, filename: str, content: bytes, user_id: str):
        async with self.ingest_semaphore:
            logger.info(f"Ingestion Started: {filename}")
            start_time = asyncio.get_event_loop().time()
            temp_dir = tempfile.gettempdir()
            tmp_path = os.path.join(temp_dir, f"ingest_{uuid.uuid4().hex}_{filename}")
            
            try:
                with open(tmp_path, "wb") as f:
                    f.write(content)
                
                if filename.endswith(".pdf"):
                    loader = PyPDFLoader(tmp_path)
                    docs = await asyncio.to_thread(loader.load)
                else:
                    with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                        text_content = f.read()
                    from langchain_core.documents import Document
                    docs = [Document(page_content=text_content, metadata={"source": filename})]
                
                # Semantic Legal Chunking: Respects document structure and clauses
                text_splitter = RecursiveCharacterTextSplitter(
                    separators=[
                        "\n\nArticle", "\n\nSection", "\n\nClause", 
                        "\n\n", "\n", ". ", " ", ""
                    ],
                    chunk_size=1200,
                    chunk_overlap=250,
                    keep_separator=True
                )
                chunks = text_splitter.split_documents(docs)
                if not chunks: return {"status": "error", "message": "Empty doc."}

                texts = [chunk.page_content for chunk in chunks]
                batch_size = 90
                vectors = []
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    batch_vectors = await asyncio.to_thread(self.embeddings.embed_documents, batch)
                    vectors.extend(batch_vectors)
                    await asyncio.sleep(0.5) 
                
                parent_id = str(uuid.uuid4())
                self.parent_documents[parent_id] = {"filename": filename, "user_id": user_id}

                # Push to Qdrant if available
                if self.qdrant:
                    await self._ensure_collections()
                    points = []
                    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                        points.append(rest.PointStruct(
                            id=str(uuid.uuid4()),
                            vector=vector,
                            payload={
                                "content": chunk.page_content,
                                "parent_id": parent_id,
                                "source": filename,
                                "user_id": user_id,
                                **chunk.metadata
                            }
                        ))
                    await self.qdrant.upsert(collection_name="aegis_legal_docs", points=points)

                # Local Fallback
                for chunk, vector in zip(chunks, vectors):
                    self.vectors.append(vector)
                    self.documents.append({
                        "content": chunk.page_content,
                        "source": filename,
                        "user_id": user_id,
                        "parent_id": parent_id
                    })
                
                self._save_vault()
                elapsed = asyncio.get_event_loop().time() - start_time
                return {"status": "success", "chunks": len(chunks)}
            except Exception as e:
                logger.error(f"Ingestion Failure: {e}")
                return {"status": "error", "message": str(e)}
            finally:
                if os.path.exists(tmp_path): os.remove(tmp_path)

    async def retrieve(self, query: str, limit: int = 5) -> List[Dict]:
        if self.qdrant and self.embeddings:
            try:
                await self._ensure_collections()
                query_vec = await self.embeddings.aembed_query(query)
                # Use modern query_points API
                results = await self.qdrant.query_points(
                    collection_name="aegis_legal_docs",
                    query=query_vec,
                    limit=limit
                )
                return [{
                    "content": r.payload["content"],
                    "source": r.payload["source"],
                    "score": r.score,
                    "parent_id": r.payload.get("parent_id")
                } for r in results.points]
            except Exception as e:
                logger.error(f"Qdrant Search Error: {e}")

        # Local Fallback
        if not self.vectors: return []
        query_vec = await self.embeddings.aembed_query(query)
        def cosine_sim(a, b): return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        scores = [cosine_sim(query_vec, v) for v in self.vectors]
        top_indices = np.argsort(scores)[-limit:][::-1]
        return [self.documents[i] for i in top_indices]

    async def rerank(self, query: str, documents: List[Dict], top_n: int = 3) -> List[Dict]:
        if not self.co_client or not documents: return documents[:top_n]
        try:
            doc_contents = [doc["content"] for doc in documents]
            response = await asyncio.to_thread(self.co_client.rerank, model="rerank-english-v3.0", query=query, documents=doc_contents, top_n=top_n)
            return [{**documents[r.index], "rerank_score": r.relevance_score} for r in response.results]
        except Exception: return documents[:top_n]

vault = LocalVault()
