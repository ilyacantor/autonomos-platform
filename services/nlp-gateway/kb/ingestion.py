import os
import uuid
import hashlib
from typing import List, Dict, Optional
from datetime import datetime
import random

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    tiktoken = None

from ..schemas.kb import IngestItem, IngestPolicy, IngestedDocument
from ..utils.logger import get_logger
from ..utils.pii_redaction import redact_pii

logger = get_logger(__name__)

if not SENTENCE_TRANSFORMERS_AVAILABLE:
    logger.warning(
        "⚠️ sentence-transformers not installed. "
        "Embeddings will use random vectors (demo mode only). "
        "Install with: pip install sentence-transformers"
    )

if not TIKTOKEN_AVAILABLE:
    logger.warning(
        "⚠️ tiktoken not installed. "
        "Using simple text splitting for chunking. "
        "Install with: pip install tiktoken"
    )


class ChunkingStrategy:
    """
    Document chunking strategies.
    
    Supports:
    - auto: Adaptive chunking based on document structure
    - fixed: Fixed-size chunks with overlap
    
    Optional Dependencies:
    - tiktoken: Required for accurate token-based chunking
      Without it, simple character-based splitting is used
    """
    
    @staticmethod
    def chunk_text(
        text: str,
        strategy: str = "auto",
        max_tokens: int = 1200,
        overlap_tokens: int = 200
    ) -> List[Dict[str, any]]:
        """
        Chunk text into semantic sections.
        
        Args:
            text: Text to chunk
            strategy: Chunking strategy ("auto" or "fixed")
            max_tokens: Maximum tokens per chunk (requires tiktoken package)
            overlap_tokens: Overlap between chunks (for "fixed" strategy)
            
        Returns:
            List of chunks with metadata
        """
        if strategy == "auto":
            return ChunkingStrategy._auto_chunk(text, max_tokens)
        else:
            return ChunkingStrategy._fixed_chunk(text, max_tokens, overlap_tokens)
    
    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Estimate token count when tiktoken is not available."""
        return len(text) // 4
    
    @staticmethod
    def _auto_chunk(text: str, max_tokens: int) -> List[Dict[str, any]]:
        """
        Adaptive chunking based on paragraph boundaries.
        """
        if TIKTOKEN_AVAILABLE:
            encoding = tiktoken.get_encoding("cl100k_base")
        else:
            encoding = None
        paragraphs = text.split("\n\n")
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_index = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if encoding:
                para_tokens = len(encoding.encode(para))
            else:
                para_tokens = ChunkingStrategy._estimate_tokens(para)
            
            if current_tokens + para_tokens > max_tokens and current_chunk:
                chunk_text = "\n\n".join(current_chunk)
                chunks.append({
                    "index": chunk_index,
                    "text": chunk_text,
                    "tokens": current_tokens,
                    "section": f"Chunk {chunk_index + 1}"
                })
                current_chunk = []
                current_tokens = 0
                chunk_index += 1
            
            current_chunk.append(para)
            current_tokens += para_tokens
        
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append({
                "index": chunk_index,
                "text": chunk_text,
                "tokens": current_tokens,
                "section": f"Chunk {chunk_index + 1}"
            })
        
        return chunks
    
    @staticmethod
    def _fixed_chunk(
        text: str,
        max_tokens: int,
        overlap_tokens: int
    ) -> List[Dict[str, any]]:
        """
        Fixed-size chunking with overlap.
        """
        if TIKTOKEN_AVAILABLE:
            encoding = tiktoken.get_encoding("cl100k_base")
            tokens = encoding.encode(text)
            
            chunks = []
            chunk_index = 0
            start = 0
            
            while start < len(tokens):
                end = min(start + max_tokens, len(tokens))
                chunk_tokens = tokens[start:end]
                chunk_text = encoding.decode(chunk_tokens)
                
                chunks.append({
                    "index": chunk_index,
                    "text": chunk_text,
                    "tokens": len(chunk_tokens),
                    "section": f"Chunk {chunk_index + 1}"
                })
                
                start += max_tokens - overlap_tokens
                chunk_index += 1
        else:
            chars_per_token = 4
            max_chars = max_tokens * chars_per_token
            overlap_chars = overlap_tokens * chars_per_token
            
            chunks = []
            chunk_index = 0
            start = 0
            
            while start < len(text):
                end = min(start + max_chars, len(text))
                chunk_text = text[start:end]
                
                chunks.append({
                    "index": chunk_index,
                    "text": chunk_text,
                    "tokens": ChunkingStrategy._estimate_tokens(chunk_text),
                    "section": f"Chunk {chunk_index + 1}"
                })
                
                start += max_chars - overlap_chars
                chunk_index += 1
        
        return chunks


class IngestionPipeline:
    """
    Document ingestion pipeline.
    
    Process:
    1. Load document from source (file, URL, text)
    2. Chunk document (requires tiktoken for accurate token counting)
    3. Generate embeddings (requires sentence-transformers)
    4. Redact PII (requires presidio, if enabled)
    5. Store in database
    
    Optional Dependencies:
    - sentence-transformers: For semantic embeddings (fallback: random vectors)
    - tiktoken: For accurate token-based chunking (fallback: character-based splitting)
    - presidio: For PII redaction (fallback: no redaction)
    """
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    ):
        """
        Initialize ingestion pipeline.
        
        Args:
            model_name: SentenceTransformer model name (requires sentence-transformers package)
        """
        self.model_name = model_name
        self._model = None
        logger.info(f"IngestionPipeline initialized with model: {model_name}")
    
    @property
    def model(self):
        """Lazy load the sentence transformer model or use fallback."""
        if self._model is None:
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                logger.warning("Using random embedding fallback (sentence-transformers not available)")
                return None
            try:
                self._model = SentenceTransformer(self.model_name)
                logger.info(f"Loaded sentence transformer model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to load model {self.model_name}: {e}")
                return None
        return self._model
    
    def _generate_random_embedding(self, dimension: int = 384) -> List[float]:
        """Generate random embedding for demo/fallback mode."""
        return [random.random() for _ in range(dimension)]
    
    def process_item(
        self,
        item: IngestItem,
        policy: IngestPolicy
    ) -> Dict[str, any]:
        """
        Process a single ingest item.
        
        Args:
            item: Item to ingest
            policy: Ingestion policy
            
        Returns:
            Processed item with chunks and embeddings
        """
        text = self._load_text(item)
        
        if not text:
            return {
                "error": f"Failed to load text from {item.type}: {item.location}",
                "chunks": []
            }
        
        chunks = ChunkingStrategy.chunk_text(
            text,
            strategy=policy.chunk,
            max_tokens=policy.max_chunk_tokens
        )
        
        processed_chunks = []
        for chunk in chunks:
            chunk_text = chunk["text"]
            chunk_text_redacted = chunk_text
            
            if policy.redact_pii:
                redaction_result = redact_pii(chunk_text)
                if redaction_result.get("redacted"):
                    chunk_text_redacted = redaction_result["redacted_text"]
                    logger.info(f"Redacted {len(redaction_result.get('entities_found', []))} PII entities")
            
            if self.model is not None:
                embedding = self.model.encode(chunk_text).tolist()
            else:
                embedding = self._generate_random_embedding()
            
            processed_chunks.append({
                "index": chunk["index"],
                "section": chunk["section"],
                "text": chunk_text,
                "text_redacted": chunk_text_redacted if chunk_text_redacted != chunk_text else None,
                "embedding": embedding,
                "tokens": chunk["tokens"],
                "metadata": {
                    "source_type": item.type.value,
                    "source_location": item.location
                }
            })
        
        doc_id = self._generate_doc_id(item)
        title = self._extract_title(item, text)
        
        return {
            "doc_id": doc_id,
            "title": title,
            "source_type": item.type.value,
            "source_location": item.location,
            "tags": item.tags,
            "chunks": processed_chunks,
            "metadata": {
                "chunks_count": len(processed_chunks),
                "total_tokens": sum(c["tokens"] for c in processed_chunks)
            }
        }
    
    def _load_text(self, item: IngestItem) -> Optional[str]:
        """
        Load text from item source.
        
        Supports:
        - file: Read from file path
        - url: Fetch from URL (TODO: implement)
        - text: Use directly
        """
        if item.type.value == "text":
            return item.location
        
        elif item.type.value == "file":
            try:
                with open(item.location, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Failed to read file {item.location}: {e}")
                return None
        
        elif item.type.value == "url":
            logger.warning("URL ingestion not yet implemented")
            return None
        
        return None
    
    def _generate_doc_id(self, item: IngestItem) -> str:
        """Generate unique document ID."""
        content = f"{item.type.value}:{item.location}"
        hash_digest = hashlib.md5(content.encode()).hexdigest()[:12]
        return f"doc_{hash_digest}"
    
    def _extract_title(self, item: IngestItem, text: str) -> str:
        """Extract title from document or generate one."""
        if item.type.value == "file":
            return os.path.basename(item.location)
        
        first_line = text.split("\n")[0][:100]
        if first_line:
            return first_line
        
        return f"Document from {item.type.value}"


_pipeline_instance: Optional[IngestionPipeline] = None


def get_ingestion_pipeline() -> IngestionPipeline:
    """Get singleton ingestion pipeline instance."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = IngestionPipeline()
    return _pipeline_instance
