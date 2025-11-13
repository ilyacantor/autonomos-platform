"""
RAG Engine for DCL Schema Mapping
Uses Pinecone Inference API for cloud-based embeddings
"""

import os
import json
import time
import logging
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import hashlib

# Configure logger
logger = logging.getLogger(__name__)

class RAGEngine:
    """
    Retrieval-Augmented Generation engine for schema mapping.
    Stores historical mappings in Pinecone and retrieves similar examples to guide LLM.
    Uses Pinecone Inference API for embeddings (no local ML models).
    """
    
    def __init__(self, pinecone_api_key: Optional[str] = None):
        """Initialize RAG engine with Pinecone cloud embeddings."""
        # Get Pinecone API key from environment if not provided
        self.pinecone_api_key = pinecone_api_key or os.environ.get("PINECONE_API_KEY")
        
        if not self.pinecone_api_key:
            raise ValueError(
                "Pinecone API key not found. Please set PINECONE_API_KEY environment variable."
            )
        
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=self.pinecone_api_key)
        
        # Index name and embedding model  
        self.index_name = "schema-mappings-e5"  # New index for cloud embeddings
        self.embedding_model = "multilingual-e5-large"  # Pinecone hosted model
        self.embedding_dim = 1024  # multilingual-e5-large dimension
        
        # Initialize inference client for embeddings (Pinecone SDK 3.x)
        self.pc_inference = self.pc
        
        # sentence-transformers removed (2GB dependency) - rely on Pinecone Inference API
        self.sentence_encoder = None

        # LRU cache with TTL for retrieve_similar_mappings
        # Key: (field_name, field_type, source_system, top_k, min_confidence)
        # Value: (result, timestamp)
        self._cache: Dict[Tuple, Tuple[List[Dict[str, Any]], float]] = {}
        self._cache_ttl = 300  # 5 minutes TTL
        self._cache_max_size = 1000  # Max 1000 entries

        logger.info(f"✅ RAG Engine ready for embeddings ({self.embedding_model})")
        
        # Create or connect to index
        self._ensure_index()
    
    def _ensure_index(self):
        """Create index if it doesn't exist and wait for it to be ready."""
        import time
        
        try:
            # Check if index exists
            if self.index_name not in self.pc.list_indexes().names():
                # Create index with serverless spec (free tier)
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.embedding_dim,
                    metric='cosine',
                    spec=ServerlessSpec(
                        cloud='aws',
                        region='us-east-1'
                    )
                )
                logger.info(f"🔄 Created new index: {self.index_name}, waiting for readiness...")

                # Wait for index to be ready
                max_wait = 60
                wait_time = 0
                while wait_time < max_wait:
                    desc = self.pc.describe_index(self.index_name)
                    if desc.status.get('ready', False):
                        logger.info(f"✅ Index {self.index_name} is ready")
                        break
                    time.sleep(2)
                    wait_time += 2
                    if wait_time % 10 == 0:
                        logger.debug(f"   Still waiting... ({wait_time}s)")

                if wait_time >= max_wait:
                    error_msg = f"Pinecone index '{self.index_name}' did not become ready within {max_wait}s. Cannot proceed with unready index."
                    logger.error(f"❌ {error_msg}")
                    raise RuntimeError(error_msg)
            else:
                logger.info(f"✅ Connected to existing index: {self.index_name}")
            
            # Get index
            self.index = self.pc.Index(self.index_name)
        except RuntimeError:
            # Re-raise readiness timeout errors - do not proceed with unready index
            raise
        except Exception as e:
            logger.warning(f"⚠️  Error with index: {e}")
            # For other errors, try to connect anyway (index might exist but had temporary issue)
            self.index = self.pc.Index(self.index_name)
    
    def _create_field_signature(self, field_name: str, field_type: str, 
                                 source_system: str = "") -> str:
        """
        Create a text signature for a field that captures its semantic meaning.
        This will be embedded and used for similarity search.
        """
        signature = f"{field_name} ({field_type})"
        if source_system:
            signature = f"{source_system}: {signature}"
        return signature
    
    def _create_mapping_document(self, mapping: Dict[str, Any]) -> str:
        """
        Create a rich text document from a mapping for better retrieval.
        """
        doc = f"""
Source: {mapping.get('source_system', 'Unknown')}
Field: {mapping['source_field']}
Type: {mapping.get('source_type', 'string')}
Mapped To: {mapping['ontology_entity']}
Transformation: {mapping.get('transformation', 'direct')}
Confidence: {mapping.get('confidence', 0.0)}
        """.strip()
        return doc
    
    def _create_vector_id(self, source_system: str, source_field: str) -> str:
        """Create a unique vector ID from source system and field."""
        text = f"{source_system}_{source_field}_{int(datetime.now().timestamp())}"
        # Create hash for unique ID
        return hashlib.md5(text.encode()).hexdigest()[:16]
    
    def _generate_embedding(self, text: str, input_type: str = "passage") -> List[float]:
        """
        Generate embedding using Pinecone Inference API or fallback to sentence-transformers.
        
        Args:
            text: Text to embed
            input_type: "passage" for documents, "query" for search queries
            
        Returns:
            Embedding vector as list of floats
        """
        # Try sentence-transformers first (most reliable with Pinecone 3.x)
        if self.sentence_encoder is not None:
            try:
                # For multilingual-e5, prefix text based on type
                if input_type == "query":
                    prefixed_text = f"query: {text}"
                else:
                    prefixed_text = f"passage: {text}"
                
                embedding = self.sentence_encoder.encode(prefixed_text, convert_to_numpy=True)
                return embedding.tolist()
            except Exception as e:
                logger.warning(f"⚠️ Sentence transformer encoding failed: {e}")
        
        # Try Pinecone Inference API as fallback
        try:
            response = self.pc_inference.inference.embed(
                model=self.embedding_model,
                inputs=[text],
                parameters={"input_type": input_type, "truncate": "END"}
            )
            return response.data[0].values
        except (AttributeError, Exception) as e:
            logger.warning(f"⚠️ Pinecone Inference API not available: {e}")
            # Last resort: deterministic hash-based embeddings
            import hashlib
            import random
            hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
            random.seed(hash_val)
            return [random.gauss(0, 0.1) for _ in range(self.embedding_dim)]
    
    def store_mapping(self, 
                     source_field: str,
                     source_type: str,
                     ontology_entity: str,
                     source_system: str = "Unknown",
                     transformation: str = "direct",
                     confidence: float = 1.0,
                     validated: bool = False,
                     dev_mode_enabled: bool = True) -> Optional[str]:
        """
        Store a successful mapping in the vector database.
        
        Args:
            dev_mode_enabled: If False, blocks all writes (read-only/heuristic mode)
        
        Returns:
            Vector ID of stored mapping, or None if write blocked
        """
        # GUARD: Block writes in heuristic/production mode (dev_mode=false)
        if not dev_mode_enabled:
            logger.info(f"🔒 RAG path: retrieve-only (read-only) - Write blocked for {source_field} → {ontology_entity}")
            return None

        logger.info(f"✅ RAG path: retrieve+learn (write enabled) - Storing mapping")
        
        # Create unique ID
        vector_id = self._create_vector_id(source_system, source_field)
        
        # Create mapping data
        mapping = {
            "source_field": source_field,
            "source_type": source_type,
            "source_system": source_system,
            "ontology_entity": ontology_entity,
            "transformation": transformation,
            "confidence": confidence,
            "validated": validated,
            "timestamp": datetime.now().isoformat()
        }
        
        # Create document for embedding
        document = self._create_mapping_document(mapping)
        
        # Generate embedding using Pinecone Inference API
        embedding = self._generate_embedding(document, input_type="passage")
        
        # Upsert to Pinecone
        self.index.upsert(
            vectors=[{
                "id": vector_id,
                "values": embedding,
                "metadata": mapping
            }]
        )

        logger.info(f"📝 Stored mapping: {source_field} → {ontology_entity}")
        return vector_id
    
    def clear_cache(self):
        """Clear the retrieval cache. Called when dev_mode toggles or schema changes."""
        self._cache.clear()
        logger.info("🗑️ RAG cache cleared")
    
    def _get_from_cache(self, cache_key: Tuple) -> Optional[List[Dict[str, Any]]]:
        """Get result from cache if valid (within TTL)."""
        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                logger.debug(f"💾 Cache HIT for {cache_key[0]} ({time.time() - timestamp:.1f}s old)")
                return result
            else:
                # Expired, remove from cache
                del self._cache[cache_key]
                logger.debug(f"⏰ Cache EXPIRED for {cache_key[0]}")
        return None
    
    def _put_in_cache(self, cache_key: Tuple, result: List[Dict[str, Any]]):
        """Put result in cache with current timestamp."""
        # Evict oldest entries if cache is full (simple LRU)
        if len(self._cache) >= self._cache_max_size:
            # Remove 10% oldest entries
            sorted_keys = sorted(self._cache.items(), key=lambda x: x[1][1])
            for key, _ in sorted_keys[:self._cache_max_size // 10]:
                del self._cache[key]

        self._cache[cache_key] = (result, time.time())
        logger.debug(f"💾 Cached result for {cache_key[0]} ({len(result)} mappings)")
    
    def retrieve_similar_mappings(self,
                                   field_name: str,
                                   field_type: str,
                                   source_system: str = "",
                                   top_k: int = 5,
                                   min_confidence: float = 0.7) -> List[Dict[str, Any]]:
        """
        Retrieve similar historical mappings from vector store with LRU cache + TTL.
        
        Args:
            field_name: Name of field to map
            field_type: Data type of field
            source_system: Optional source system name
            top_k: Number of similar examples to retrieve
            min_confidence: Minimum confidence threshold
        
        Returns:
            List of similar mapping examples with metadata
        """
        # Create cache key
        cache_key = (field_name, field_type, source_system, top_k, min_confidence)
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Cache miss - proceed with Pinecone query
        # Create query
        query = self._create_field_signature(field_name, field_type, source_system)
        
        # Check if index has any vectors
        stats = self.index.describe_index_stats()
        if stats.total_vector_count == 0:
            logger.info("ℹ️  No historical mappings in vector store yet")
            return []
        
        # Generate query embedding using Pinecone Inference API
        query_embedding = self._generate_embedding(query, input_type="query")
        
        # Build filter for minimum confidence
        query_filter = None
        if min_confidence > 0:
            query_filter = {"confidence": {"$gte": min_confidence}}
        
        # Query Pinecone
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter=query_filter
        )
        
        # Format results
        similar_mappings = []
        for match in results.matches:
            similar_mappings.append({
                **match.metadata,
                "similarity": round(match.score, 3)
            })

        logger.info(f"🔍 Found {len(similar_mappings)} similar mappings for '{field_name}'")
        
        # Store in cache
        self._put_in_cache(cache_key, similar_mappings)
        
        return similar_mappings
    
    def build_context_for_llm(self, similar_mappings: List[Dict[str, Any]]) -> str:
        """
        Build context string from similar mappings to include in LLM prompt.
        
        Args:
            similar_mappings: List of similar mapping dictionaries
        
        Returns:
            Formatted context string for LLM prompt
        """
        if not similar_mappings:
            return ""
        
        context = "SIMILAR SUCCESSFUL MAPPINGS FROM HISTORY:\n\n"
        
        for i, mapping in enumerate(similar_mappings, 1):
            context += f"{i}. Source: {mapping.get('source_system', 'Unknown')}\n"
            context += f"   Field: {mapping['source_field']} ({mapping.get('source_type', 'unknown')})\n"
            context += f"   Mapped To: {mapping['ontology_entity']}\n"
            context += f"   Transformation: {mapping.get('transformation', 'direct')}\n"
            context += f"   Similarity: {mapping.get('similarity', 0.0):.1%}\n"
            context += f"   Confidence: {mapping.get('confidence', 0.0):.1%}\n"
            context += "\n"
        
        context += "Use these examples to guide your mapping decisions for similar fields.\n"
        context += "Maintain consistency with historical mappings when appropriate.\n"
        
        return context
    
    def seed_from_schema(self, source_system: str, tables: Dict[str, Any], 
                        ontology_mappings: Dict[str, Any]):
        """
        Seed the vector store with mappings from an existing schema.
        Useful for bootstrapping the RAG engine with known-good mappings.
        
        Args:
            source_system: Name of source system (e.g., "Salesforce")
            tables: Table schemas with field information
            ontology_mappings: Known mappings to ontology entities
        """
        count = 0
        for table_name, table_info in tables.items():
            schema = table_info.get('schema', {})
            
            for field_name, field_type in schema.items():
                # Check if we have a mapping for this field
                mapping_key = f"{table_name}.{field_name}"
                if mapping_key in ontology_mappings:
                    mapping = ontology_mappings[mapping_key]
                    
                    self.store_mapping(
                        source_field=field_name,
                        source_type=field_type,
                        ontology_entity=mapping['entity'],
                        source_system=source_system,
                        transformation=mapping.get('transform', 'direct'),
                        confidence=mapping.get('confidence', 0.9),
                        validated=True
                    )
                    count += 1

        logger.info(f"🌱 Seeded {count} mappings from {source_system}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        stats = self.index.describe_index_stats()
        return {
            "total_mappings": stats.total_vector_count,
            "index_name": self.index_name,
            "embedding_model": self.embedding_model,
            "embedding_dimension": self.embedding_dim,
            "vector_db": "Pinecone Inference"
        }
