"""
Enhanced Memory System with Vector Embeddings
Replaces keyword matching with proper semantic search using ChromaDB
"""

import json
import hashlib
import numpy as np
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import asyncio

# Try to import ChromaDB, fallback to simple storage if not available
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    print("Warning: ChromaDB not available, using fallback storage")

# Try to import sentence-transformers for local embeddings
try:
    from sentence_transformers import SentenceTransformer
    LOCAL_EMBEDDINGS = True
except ImportError:
    LOCAL_EMBEDDINGS = False


@dataclass
class MemoryEntry:
    """Base memory entry with embedding support"""
    content: str
    timestamp: str
    source: str
    importance: float
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


class EmbeddingProvider:
    """Abstract embedding provider - supports local and API-based"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._local_model = None
        
        if LOCAL_EMBEDDINGS:
            try:
                self._local_model = SentenceTransformer(model_name)
                print(f"✓ Loaded local embedding model: {model_name}")
            except Exception as e:
                print(f"⚠ Failed to load local model: {e}")
    
    async def embed(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if self._local_model:
            # Use local model
            embedding = self._local_model.encode(text, convert_to_list=True)
            return embedding
        else:
            # Fallback: simple hash-based (not semantic, but consistent)
            # In production, you'd call OpenAI/Anthropic API here
            return self._fallback_embed(text)
    
    def _fallback_embed(self, text: str) -> List[float]:
        """Simple fallback - not semantic but consistent"""
        # Create a simple vector based on word hashes
        words = text.lower().split()
        vector = [0.0] * 128
        for i, word in enumerate(words[:50]):
            word_hash = hash(word) % 128
            vector[word_hash] += 1.0
        # Normalize
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = [v / norm for v in vector]
        return vector


class WorkingMemory:
    """Short-term scratchpad for current task"""
    
    def __init__(self, max_entries: int = 50):
        self.scratchpad: List[MemoryEntry] = []
        self.current_task: Optional[str] = None
        self.task_context: Dict[str, Any] = {}
        self.max_entries = max_entries
    
    def set_task(self, task: str, context: Optional[Dict] = None):
        self.current_task = task
        self.task_context = context or {}
        self.scratchpad = []
    
    def add(self, content: str, source: str = "tool_result", importance: float = 0.5):
        entry = MemoryEntry(
            content=content,
            timestamp=datetime.now().isoformat(),
            source=source,
            importance=importance
        )
        self.scratchpad.append(entry)
        
        if len(self.scratchpad) > self.max_entries:
            self.scratchpad = sorted(
                self.scratchpad, 
                key=lambda x: x.importance, 
                reverse=True
            )[:self.max_entries]
    
    def get_context(self) -> str:
        if not self.scratchpad:
            return ""
        
        lines = ["### Current Task Context"]
        if self.current_task:
            lines.append(f"Task: {self.current_task}")
        
        lines.append("\n### Working Memory:")
        for entry in self.scratchpad[-10:]:
            lines.append(f"- [{entry.source}] {entry.content[:200]}...")
        
        return "\n".join(lines)
    
    def clear(self):
        self.scratchpad = []
        self.current_task = None
        self.task_context = {}


class VectorMemory:
    """
    Long-term semantic memory with vector embeddings.
    Uses ChromaDB for vector storage and similarity search.
    """
    
    def __init__(self, 
                 workspace_path: str = "/root/.openclaw/workspace",
                 collection_name: str = "agent_memory"):
        self.workspace = Path(workspace_path)
        self.memory_dir = self.workspace / "memory" / "vector_db"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.embedding_provider = EmbeddingProvider()
        self.collection_name = collection_name
        
        # Initialize ChromaDB or fallback
        self.chroma_client = None
        self.collection = None
        self._init_vector_db()
    
    def _init_vector_db(self):
        """Initialize ChromaDB client"""
        if CHROMA_AVAILABLE:
            try:
                self.chroma_client = chromadb.PersistentClient(
                    path=str(self.memory_dir),
                    settings=Settings(anonymized_telemetry=False)
                )
                self.collection = self.chroma_client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                print(f"✓ Vector DB initialized at {self.memory_dir}")
            except Exception as e:
                print(f"⚠ ChromaDB init failed: {e}, using fallback")
                self.chroma_client = None
    
    async def store(self, 
                   content: str, 
                   category: str = "general",
                   tags: Optional[List[str]] = None,
                   importance: float = 0.7,
                   metadata: Optional[Dict] = None) -> str:
        """
        Store memory with vector embedding.
        Returns memory ID.
        """
        memory_id = f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(content) % 10000}"
        
        # Generate embedding
        embedding = await self.embedding_provider.embed(content)
        
        # Prepare metadata
        doc_metadata = {
            "category": category,
            "importance": importance,
            "tags": tags or [],
            "timestamp": datetime.now().isoformat(),
            **(metadata or {})
        }
        
        if self.collection:
            # Store in ChromaDB
            self.collection.add(
                ids=[memory_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[doc_metadata]
            )
        else:
            # Fallback: JSON file storage
            await self._fallback_store(memory_id, content, embedding, doc_metadata)
        
        return memory_id
    
    async def _fallback_store(self, memory_id: str, content: str, 
                            embedding: List[float], metadata: Dict):
        """Fallback storage using JSON files"""
        fallback_file = self.memory_dir / "fallback_memories.jsonl"
        entry = {
            "id": memory_id,
            "content": content,
            "embedding": embedding,
            "metadata": metadata
        }
        with open(fallback_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    async def retrieve(self, 
                      query: str, 
                      limit: int = 5,
                      category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories using vector similarity.
        """
        # Generate query embedding
        query_embedding = await self.embedding_provider.embed(query)
        
        if self.collection:
            # Query ChromaDB
            where_filter = {"category": category} if category else None
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_filter
            )
            
            memories = []
            for i, doc_id in enumerate(results['ids'][0]):
                memories.append({
                    "id": doc_id,
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i]
                })
            return memories
        else:
            # Fallback: brute force search
            return await self._fallback_retrieve(query_embedding, limit)
    
    async def _fallback_retrieve(self, query_embedding: List[float], 
                               limit: int) -> List[Dict[str, Any]]:
        """Fallback retrieval using cosine similarity"""
        fallback_file = self.memory_dir / "fallback_memories.jsonl"
        if not fallback_file.exists():
            return []
        
        entries = []
        with open(fallback_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    # Calculate cosine similarity
                    entry_vec = np.array(entry['embedding'])
                    query_vec = np.array(query_embedding)
                    similarity = np.dot(entry_vec, query_vec) / (
                        np.linalg.norm(entry_vec) * np.linalg.norm(query_vec)
                    )
                    entry['similarity'] = float(similarity)
                    entries.append(entry)
                except:
                    continue
        
        # Sort by similarity and return top
        entries.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        return entries[:limit]
    
    async def hybrid_search(self, 
                           query: str,
                           keywords: Optional[List[str]] = None,
                           limit: int = 5) -> List[Dict[str, Any]]:
        """
        Hybrid search: vector similarity + keyword filtering.
        Best of both worlds.
        """
        # Get vector results
        results = await self.retrieve(query, limit=limit * 2)
        
        if keywords:
            # Boost results containing keywords
            for result in results:
                content = result['content'].lower()
                keyword_matches = sum(1 for kw in keywords if kw.lower() in content)
                # Adjust score (assuming distance, lower is better)
                if 'distance' in result:
                    result['distance'] *= (1 - 0.1 * keyword_matches)
                elif 'similarity' in result:
                    result['similarity'] *= (1 + 0.1 * keyword_matches)
            
            # Re-sort
            if results and 'distance' in results[0]:
                results.sort(key=lambda x: x.get('distance', float('inf')))
            else:
                results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        
        return results[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        if self.collection:
            count = self.collection.count()
        else:
            fallback_file = self.memory_dir / "fallback_memories.jsonl"
            count = sum(1 for _ in open(fallback_file)) if fallback_file.exists() else 0
        
        return {
            "total_memories": count,
            "using_chroma": self.collection is not None,
            "embedding_model": self.embedding_provider.model_name,
            "storage_path": str(self.memory_dir)
        }


class SessionMemory:
    """Per-session memory with persistence"""
    
    def __init__(self, session_id: str, 
                 workspace_path: str = "/root/.openclaw/workspace"):
        self.session_id = session_id
        self.workspace = Path(workspace_path)
        self.session_file = self.workspace / "memory" / "sessions" / f"{session_id}.json"
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.notes: List[MemoryEntry] = []
        self.user_preferences: Dict[str, Any] = {}
        self.load()
    
    def load(self):
        """Load session from disk"""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    data = json.load(f)
                    self.notes = [MemoryEntry(**e) for e in data.get('notes', [])]
                    self.user_preferences = data.get('preferences', {})
            except Exception as e:
                print(f"Error loading session: {e}")
    
    def save(self):
        """Save session to disk"""
        try:
            with open(self.session_file, 'w') as f:
                json.dump({
                    'session_id': self.session_id,
                    'notes': [n.to_dict() for n in self.notes],
                    'preferences': self.user_preferences,
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"Error saving session: {e}")
    
    def add_note(self, content: str, source: str = "session", 
                importance: float = 0.6):
        entry = MemoryEntry(
            content=content,
            timestamp=datetime.now().isoformat(),
            source=source,
            importance=importance
        )
        self.notes.append(entry)
        self.save()
    
    def set_preference(self, key: str, value: Any):
        self.user_preferences[key] = {
            'value': value,
            'timestamp': datetime.now().isoformat()
        }
        self.save()
    
    def get_preferences_context(self) -> str:
        if not self.user_preferences:
            return ""
        
        lines = ["\n### User Preferences:"]
        for key, data in self.user_preferences.items():
            lines.append(f"- {key}: {data['value']}")
        return "\n".join(lines)


class MemoryManager:
    """
    Central memory manager coordinating all memory tiers.
    NEW: Vector-based semantic memory replaces keyword matching.
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or self._generate_session_id()
        self.working = WorkingMemory()
        self.session = SessionMemory(self.session_id)
        self.vector = VectorMemory()  # NEW: Vector-based long-term memory
    
    def _generate_session_id(self) -> str:
        return f"sess_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(datetime.now()) % 10000}"
    
    async def store_long_term(self, content: str, category: str = "general",
                            tags: Optional[List[str]] = None,
                            importance: float = 0.7) -> str:
        """Store to vector memory"""
        return await self.vector.store(content, category, tags, importance)
    
    async def recall(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Recall from vector memory"""
        return await self.vector.retrieve(query, limit)
    
    async def get_full_context(self, query: str = "") -> str:
        """Assemble full context from all memory tiers"""
        parts = []
        
        # Working memory
        working_ctx = self.working.get_context()
        if working_ctx:
            parts.append(working_ctx)
        
        # Session preferences
        prefs_ctx = self.session.get_preferences_context()
        if prefs_ctx:
            parts.append(prefs_ctx)
        
        # Vector memory (async)
        if query:
            memories = await self.recall(query, limit=3)
            if memories:
                ctx = "\n### Relevant Past Experiences:\n"
                for mem in memories:
                    content = mem.get('content', '')
                    dist = mem.get('distance', 0)
                    ctx += f"- {content[:300]}... (relevance: {1-dist:.2f})\n"
                parts.append(ctx)
        
        return "\n\n".join(parts) if parts else ""
    
    def capture_interaction(self, user_input: str, assistant_output: str,
                          tool_calls: Optional[List[Dict]] = None):
        """Capture interaction to session memory"""
        summary = f"User: {user_input[:200]}\nAssistant: {assistant_output[:200]}"
        if tool_calls:
            summary += f"\nTools: {', '.join(t.get('name', 'unknown') for t in tool_calls)}"
        
        self.session.add_note(summary, source="interaction", importance=0.5)


# Global instance
_global_memory: Optional[MemoryManager] = None

def get_memory(session_id: Optional[str] = None) -> MemoryManager:
    """Get or create global memory manager"""
    global _global_memory
    if _global_memory is None or (session_id and _global_memory.session_id != session_id):
        _global_memory = MemoryManager(session_id)
    return _global_memory
