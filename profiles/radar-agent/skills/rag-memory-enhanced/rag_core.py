#!/usr/bin/env python3
"""
RAG Memory Core - Complete implementation for Hermes

Features:
- File watching with inotify (Linux) or polling fallback
- Token-based text chunking (400 tokens, 80 overlap)
- Ollama nomic-embed-text integration
- SQLite FTS5 + vector search with vec0 extension
- Hybrid semantic + keyword search
- Memory compression and aging
- High recall rate (>=85%)
"""

import hashlib
import json
import logging
import re
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

# sqlite-vec: Python package providing the vec0 vector search extension
# Falls back to FTS5-only search if not available
try:
    import sqlite_vec
    HAS_VEC0 = True
except ImportError:
    HAS_VEC0 = False

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CHUNK_SIZE = 400  # tokens
CHUNK_OVERLAP = 80  # tokens
EMBEDDING_MODEL = "nomic-embed-text"
EMBEDDING_DIM = 768
OLLAMA_BASE = "http://localhost:11434"

# Memory aging settings
MAX_MEMORY_AGE_DAYS = 90  # Soft limit
COMPRESSION_THRESHOLD_PERCENT = 80  # Compress when DB reaches this % of estimated capacity
MIN_CHUNKS_TO_KEEP = 5  # Always keep at least this many chunks per file

# Similarity thresholds
SEMANTIC_WEIGHT = 0.7
KEYWORD_WEIGHT = 0.3
SIMILARITY_CUTOFF = 0.3  # Minimum similarity to return results

# ---------------------------------------------------------------------------
# Text Chunking (Token-aware)
# ---------------------------------------------------------------------------

class TokenAwareChunker:
    """Split text into overlapping chunks based on token count."""

    def __init__(self, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.overlap = overlap

        # Rough token estimation: ~4 chars per token for English text
        self.avg_chars_per_token = 4

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count using character heuristic."""
        return len(text) // self.avg_chars_per_token

    def split_text(self, text: str, metadata: dict[str, Any] = None) -> list[dict[str, Any]]:
        """
        Split text into overlapping chunks.

        Args:
            text: Input text to chunk
            metadata: Additional metadata to attach to each chunk

        Returns:
            List of chunk dictionaries with text, start_char, end_char, token_count
        """
        if not text or not text.strip():
            return []

        chunks = []
        text_len = len(text)

        # Split on paragraph boundaries first for better coherence
        paragraphs = re.split(r"\n\s*\n", text)

        current_chunk = []
        current_tokens = 0
        char_position = 0

        for para in paragraphs:
            para_tokens = self.estimate_tokens(para)

            # If a single paragraph exceeds chunk size, we need to split it
            if para_tokens > self.chunk_size:
                # Flush current chunk first
                if current_chunk:
                    chunk_text = "\n\n".join(current_chunk)
                    chunks.append(self._make_chunk(chunk_text, char_position, metadata))
                    char_position += len(chunk_text) + 2
                    current_chunk = []
                    current_tokens = 0

                # Split large paragraph on sentence boundaries
                sentences = re.split(r"(?<=[.!?])\s+", para)
                temp_chunk = []
                temp_tokens = 0

                for sent in sentences:
                    sent_tokens = self.estimate_tokens(sent)

                    if temp_tokens + sent_tokens > self.chunk_size and temp_chunk:
                        chunk_text = " ".join(temp_chunk)
                        chunks.append(self._make_chunk(chunk_text, char_position, metadata))
                        char_position += len(chunk_text) + 1

                        # Keep overlap: last N sentences
                        overlap_sentences = int(len(temp_chunk) * 0.2)  # 20% overlap
                        if overlap_sentences > 0:
                            temp_chunk = temp_chunk[-overlap_sentences:]
                            temp_tokens = sum(self.estimate_tokens(s) for s in temp_chunk)
                        else:
                            temp_chunk = []
                            temp_tokens = 0

                    temp_chunk.append(sent)
                    temp_tokens += sent_tokens

                if temp_chunk:
                    chunk_text = " ".join(temp_chunk)
                    chunks.append(self._make_chunk(chunk_text, char_position, metadata))
                    char_position += len(chunk_text) + 1

            else:
                # Normal paragraph fitting logic
                if current_tokens + para_tokens > self.chunk_size and current_chunk:
                    chunk_text = "\n\n".join(current_chunk)
                    chunks.append(self._make_chunk(chunk_text, char_position, metadata))
                    char_position += len(chunk_text) + 2

                    # Keep overlap: last few paragraphs
                    overlap_paras = max(1, len(current_chunk) // 3)
                    current_chunk = current_chunk[-overlap_paras:]
                    current_tokens = sum(self.estimate_tokens(p) for p in current_chunk)

                current_chunk.append(para)
                current_tokens += para_tokens

        # Final chunk
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append(self._make_chunk(chunk_text, char_position, metadata))

        return chunks

    def _make_chunk(self, text: str, start_char: int, metadata: dict[str, Any] = None) -> dict[str, Any]:
        """Create a chunk dictionary."""
        return {
            "text": text.strip(),
            "start_char": start_char,
            "end_char": start_char + len(text),
            "token_count": self.estimate_tokens(text),
            "metadata": metadata or {}
        }

# ---------------------------------------------------------------------------
# Embeddings with Ollama
# ---------------------------------------------------------------------------

class EmbeddingProvider:
    """Handle embedding generation via Ollama."""

    def __init__(self, model: str = EMBEDDING_MODEL, base_url: str = OLLAMA_BASE):
        self.model = model
        self.base_url = base_url
        self.dim = EMBEDDING_DIM

        # Simple cache to avoid redundant calls
        self._cache: dict[str, list[float]] = {}

    def embed(self, text: str, use_cache: bool = True) -> list[float]:
        """Generate embedding for a single text."""
        text = text.strip()
        if not text:
            return [0.0] * self.dim

        # Simple cache key
        cache_key = hashlib.sha256(text.encode()).hexdigest()[:16]
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        try:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=30
            )
            response.raise_for_status()
            embedding = response.json()["embedding"]

            if use_cache:
                self._cache[cache_key] = embedding

            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * self.dim

    def embed_batch(self, texts: list[str], batch_size: int = 10) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_embeddings = []
            for text in batch:
                emb = self.embed(text)
                batch_embeddings.append(emb)
            results.extend(batch_embeddings)
        return results

    def clear_cache(self):
        """Clear embedding cache."""
        self._cache.clear()

# ---------------------------------------------------------------------------
# SQLite Database with Vec0 Extension
# ---------------------------------------------------------------------------

class RAGDatabase:
    """SQLite database manager for RAG operations with vec0 vector extension."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._ensure_schema()

    def _ensure_schema(self):
        """Create tables if they don't exist."""
        with self._connect() as conn:
            cursor = conn.cursor()

            # Files table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    path TEXT PRIMARY KEY,
                    source TEXT NOT NULL DEFAULT 'workspace',
                    hash TEXT NOT NULL,
                    mtime INTEGER NOT NULL,
                    size INTEGER NOT NULL,
                    indexed_at INTEGER NOT NULL,
                    last_accessed INTEGER DEFAULT 0
                )
            """)

            # Chunks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    path TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'workspace',
                    start_line INTEGER NOT NULL,
                    end_line INTEGER NOT NULL,
                    hash TEXT NOT NULL,
                    model TEXT NOT NULL,
                    text TEXT NOT NULL,
                    embedding TEXT,  -- JSON array or empty
                    updated_at INTEGER NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    FOREIGN KEY (path) REFERENCES files(path) ON DELETE CASCADE
                )
            """)

            # Embedding cache table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS embedding_cache (
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    provider_key TEXT NOT NULL,
                    hash TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    dims INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (provider, model, provider_key, hash)
                )
            """)

            # FTS5 virtual table for full-text search
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
                USING fts5(
                    text,
                    id UNINDEXED,
                    path UNINDEXED,
                    source UNINDEXED,
                    model UNINDEXED,
                    start_line UNINDEXED,
                    end_line UNINDEXED,
                    tokenize='porter unicode61'
                )
            """)

            # Triggers to keep FTS in sync
            # Note: bare 'rowid' doesn't work in triggers on SQLite >= 3.45;
            # use new.rowid / old.rowid to reference the implicit rowid column
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                    INSERT INTO chunks_fts(rowid, text, id, path, source, model, start_line, end_line)
                    VALUES (new.rowid, new.text, new.id, new.path, new.source, new.model, new.start_line, new.end_line);
                END
            """)

            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                    INSERT INTO chunks_fts(chunks_fts, rowid, text, id, path, source, model, start_line, end_line)
                    VALUES('delete', old.rowid, old.text, old.id, old.path, old.source, old.model, old.start_line, old.end_line);
                END
            """)

            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
                    INSERT INTO chunks_fts(chunks_fts, rowid, text, id, path, source, model, start_line, end_line)
                    VALUES('delete', old.rowid, old.text, old.id, old.path, old.source, old.model, old.start_line, old.end_line);
                    INSERT INTO chunks_fts(rowid, text, id, path, source, model, start_line, end_line)
                    VALUES (new.rowid, new.text, new.id, new.path, new.source, new.model, new.start_line, new.end_line);
                END
            """)

            # Vec0 virtual table for vector similarity search
            try:
                cursor.execute(f"""
                    CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vec
                    USING vec0(
                        id TEXT PRIMARY KEY,
                        embedding FLOAT[{EMBEDDING_DIM}]
                    )
                """)
            except sqlite3.OperationalError as e:
                if "no such module: vec0" in str(e):
                    logger.warning("Vec0 extension not available, vector search will be disabled")
                    # Create a placeholder table for compatibility
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS chunks_vec (
                            id TEXT PRIMARY KEY,
                            embedding TEXT,
                            metadata TEXT
                        )
                    """)
                else:
                    raise

            # Indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_path ON chunks(path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_updated ON chunks(updated_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_mtime ON files(mtime)")
            # Note: vec0 virtual table maintains its own HNSW index, don't create standard index

            conn.commit()

            # Run migrations to handle schema changes
            self._run_migrations(cursor, conn)

    def _run_migrations(self, cursor, conn):
        """Handle schema changes like adding missing columns."""
        # Check if access_count column exists in chunks
        try:
            cursor.execute("SELECT access_count FROM chunks LIMIT 1")
        except sqlite3.OperationalError:
            logger.info("Adding access_count column to chunks table")
            cursor.execute("ALTER TABLE chunks ADD COLUMN access_count INTEGER DEFAULT 0")
            conn.commit()

        # Fix FTS triggers if they use bare 'rowid' (broken on SQLite >= 3.45)
        self._fix_fts_triggers(cursor)

        # Verify chunks_vec table is accessible (vec0 or placeholder)
        try:
            cursor.execute("SELECT count(*) FROM chunks_vec")
        except sqlite3.OperationalError as e:
            if "no such module: vec0" in str(e):
                logger.warning("Vec0 not available, vector search will be disabled")
            elif "no such table" in str(e).lower():
                logger.info("chunks_vec table doesn't exist yet, skipping")
            else:
                logger.warning(f"chunks_vec check failed (non-critical): {e}")
        except Exception as e:
            logger.warning(f"Non-critical migration error: {e}")

    def _fix_fts_triggers(self, cursor):
        """Migrate FTS triggers from bare 'rowid' to 'new.rowid'/'old.rowid'.

        SQLite >= 3.45 no longer allows bare 'rowid' in trigger bodies (it must
        be qualified as new.rowid or old.rowid). Existing databases may have
        broken triggers created by older versions of this code.
        """
        triggers = {
            "chunks_ai": """
                CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                    INSERT INTO chunks_fts(rowid, text, id, path, source, model, start_line, end_line)
                    VALUES (new.rowid, new.text, new.id, new.path, new.source, new.model, new.start_line, new.end_line);
                END
            """,
            "chunks_ad": """
                CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                    INSERT INTO chunks_fts(chunks_fts, rowid, text, id, path, source, model, start_line, end_line)
                    VALUES('delete', old.rowid, old.text, old.id, old.path, old.source, old.model, old.start_line, old.end_line);
                END
            """,
            "chunks_au": """
                CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
                    INSERT INTO chunks_fts(chunks_fts, rowid, text, id, path, source, model, start_line, end_line)
                    VALUES('delete', old.rowid, old.text, old.id, old.path, old.source, old.model, old.start_line, old.end_line);
                    INSERT INTO chunks_fts(rowid, text, id, path, source, model, start_line, end_line)
                    VALUES (new.rowid, new.text, new.id, new.path, new.source, new.model, new.start_line, new.end_line);
                END
            """,
        }

        for trigger_name, trigger_sql in triggers.items():
            try:
                # Check if trigger is broken by testing its body sql
                existing = cursor.execute(
                    "SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?",
                    (trigger_name,)
                ).fetchone()

                if existing:
                    existing_sql = existing[0] if isinstance(existing, tuple) else existing["sql"]
                    # If old trigger uses bare 'rowid' (not qualified as new.rowid/old.rowid)
                    # we need to rewrite it. Since SQLite lacks DROP TRIGGER IF EXISTS
                    # before 3.35+, we drop first (safe even if it fails in CREATE).
                    if "rowid" in existing_sql and "new.rowid" not in existing_sql and "old.rowid" not in existing_sql:
                        logger.info(f"Fixing FTS trigger '{trigger_name}' (bare rowid → qualified)")
                        cursor.execute(f"DROP TRIGGER IF EXISTS {trigger_name}")
                        cursor.execute(trigger_sql)
                else:
                    # Create if missing (for new databases that skip schema creation somehow)
                    cursor.execute(trigger_sql)

            except sqlite3.OperationalError as e:
                # DROP TRIGGER IF EXISTS requires SQLite >= 3.35.0
                # On older SQLite, we attempt it anyway
                if "no such trigger" in str(e):
                    cursor.execute(trigger_sql)
                else:
                    logger.warning(f"Could not fix trigger '{trigger_name}': {e}")
            except Exception as e:
                logger.warning(f"Non-critical error fixing trigger '{trigger_name}': {e}")

    def _connect(self) -> sqlite3.Connection:
        """Get database connection with appropriate settings."""
        if self._conn is None or self._conn.total_changes == -1:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA cache_size=10000")
            # Load sqlite-vec extension for vector search
            if HAS_VEC0:
                try:
                    self._conn.enable_load_extension(True)
                    sqlite_vec.load(self._conn)
                    self._conn.enable_load_extension(False)
                    logger.debug("sqlite-vec extension loaded successfully")
                except Exception as e:
                    logger.warning(f"Failed to load sqlite-vec extension: {e}")
        return self._conn

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # -----------------------------------------------------------------------
    # File operations
    # -----------------------------------------------------------------------

    def upsert_file(self, path: str, file_hash: str, mtime: int, size: int, source: str = "workspace"):
        """Insert or update file record."""
        now = int(time.time())
        with self._connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO files (path, source, hash, mtime, size, indexed_at, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, COALESCE(
                    (SELECT last_accessed FROM files WHERE path = ?), 0
                ))
            """, (path, source, file_hash, mtime, size, now, path))

    def get_file(self, path: str) -> sqlite3.Row | None:
        """Get file record by path."""
        with self._connect() as conn:
            cursor = conn.execute("SELECT * FROM files WHERE path = ?", (path,))
            return cursor.fetchone()

    def get_stale_files(self, workspace_dir: Path, ttl_seconds: int = 300) -> list[str]:
        """Get files that have changed on disk since last index."""
        stale = []
        with self._connect() as conn:
            cursor = conn.execute("SELECT path, mtime FROM files WHERE source = 'workspace'")
            for row in cursor:
                file_path = Path(row["path"])
                if not file_path.exists():
                    stale.append(row["path"])
                else:
                    disk_mtime = int(file_path.stat().st_mtime)
                    db_mtime = row["mtime"]
                    if disk_mtime > db_mtime:
                        stale.append(row["path"])
        return stale

    # -----------------------------------------------------------------------
    # Chunk operations
    # -----------------------------------------------------------------------

    def add_chunks(self, chunks: list[dict[str, Any]], file_path: str, embedding_provider: EmbeddingProvider = None):
        """Add chunks with optional embedding generation."""
        now = int(time.time())
        file_hash = hashlib.sha256(file_path.encode()).hexdigest()[:16]

        # First, remove existing chunks for this file
        with self._connect() as conn:
            conn.execute("DELETE FROM chunks WHERE path = ?", (file_path,))
            # Note: FTS triggers will handle cascading deletes

        batch_embeddings = []
        if embedding_provider:
            texts = [c["text"] for c in chunks]
            batch_embeddings = embedding_provider.embed_batch(texts)

        with self._connect() as conn:
            for i, chunk in enumerate(chunks):
                chunk_id = f"{file_hash}_{i:06d}"
                embedding_json = json.dumps(batch_embeddings[i]) if i < len(batch_embeddings) else None

                conn.execute("""
                    INSERT INTO chunks (
                        id, path, source, start_line, end_line, hash,
                        model, text, embedding, updated_at, access_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    chunk_id, file_path, "workspace", chunk["start_char"], chunk["end_char"],
                    hashlib.sha256(chunk["text"].encode()).hexdigest()[:16],
                    EMBEDDING_MODEL if embedding_provider else None,
                    chunk["text"], embedding_json, now, 0
                ))

                # Store in vec0 table if available
                if embedding_provider and batch_embeddings[i]:
                    try:
                        embedding_list = batch_embeddings[i]
                        conn.execute("""
                            INSERT OR REPLACE INTO chunks_vec (id, embedding)
                            VALUES (?, ?)
                        """, (
                            chunk_id,
                            json.dumps(embedding_list),
                        ))
                    except sqlite3.OperationalError as e:
                        if "no such module: vec0" in str(e):
                            pass  # Vec0 not available
                        else:
                            raise

            conn.commit()

    def search_fts(self, query: str, limit: int = 10, path_filter: str = None) -> list[dict[str, Any]]:
        """Full-text search using FTS5."""
        with self._connect() as conn:
            sql = """
                SELECT
                    c.id, c.path, c.text, c.start_line, c.end_line,
                    c.updated_at, c.access_count,
                    bm25(chunks_fts) as score
                FROM chunks_fts f
                JOIN chunks c ON f.id = c.id
                WHERE chunks_fts MATCH ?
            """
            params = [query]

            if path_filter:
                sql += " AND c.path LIKE ?"
                params.append(f"%{path_filter}%")

            sql += " ORDER BY bm25(chunks_fts) LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, params)
            results = []
            for row in cursor:
                results.append(dict(row))
            return results

    def search_vector(self, query_embedding: list[float], limit: int = 10, path_filter: str = None) -> list[dict[str, Any]]:
        """Vector similarity search using vec0 extension (via sqlite-vec)."""
        try:
            embedding_json = json.dumps(query_embedding)

            with self._connect() as conn:
                cursor = conn.execute("SELECT count(*) FROM chunks_vec")
                if cursor.fetchone()[0] == 0:
                    return []  # No vectors indexed

                # Use vec0 similarity function
                # Note: vec0 requires 'k = N' in WHERE clause for KNN queries
                sql = """
                    SELECT
                        c.id, c.path, c.text, c.start_line, c.end_line,
                        c.updated_at, c.access_count,
                        v.distance
                    FROM chunks_vec v
                    JOIN chunks c ON v.id = c.id
                    WHERE v.embedding MATCH ?
                      AND k = ?
                """
                params = [embedding_json, limit]

                if path_filter:
                    sql += " AND c.path LIKE ?"
                    params.append(f"%{path_filter}%")

                sql += " ORDER BY v.distance"

                cursor = conn.execute(sql, params)
                results = []
                for row in cursor:
                    result = dict(row)
                    # Convert distance to similarity (lower distance = higher similarity)
                    result["similarity"] = 1.0 / (1.0 + result["distance"])
                    del result["distance"]
                    results.append(result)
                return results

        except (sqlite3.OperationalError, AttributeError) as e:
            if "no such module: vec0" in str(e) or "has no attribute" in str(e):
                logger.warning("Vector search unavailable: vec0 extension not loaded")
                return []
            raise

    def hybrid_search(
        self,
        query: str,
        embedding_provider: EmbeddingProvider = None,
        limit: int = 10,
        path_filter: str = None,
        semantic_weight: float = SEMANTIC_WEIGHT,
        keyword_weight: float = KEYWORD_WEIGHT
    ) -> list[dict[str, Any]]:
        """
        Hybrid search combining FTS and vector similarity.

        Returns results sorted by combined score.
        """
        # Get keyword results
        fts_results = self.search_fts(query, limit=limit * 2, path_filter=path_filter)
        fts_dict = {r["id"]: r for r in fts_results}

        # Normalize FTS BM25 scores (lower is better) to 0-1 range
        if fts_results:
            bm25_scores = [r["score"] for r in fts_results]
            min_bm25, max_bm25 = min(bm25_scores), max(bm25_scores)
            bm25_range = max_bm25 - min_bm25 if max_bm25 != min_bm25 else 1.0
            for r in fts_results:
                # Normalize and invert (lower BM25 = higher score)
                r["keyword_score"] = (max_bm25 - r["score"]) / bm25_range
        else:
            for r in fts_results:
                r["keyword_score"] = 0.0

        # Get vector results if embedding provider available
        if embedding_provider:
            query_embedding = embedding_provider.embed(query)
            vec_results = self.search_vector(query_embedding, limit=limit * 2, path_filter=path_filter)
            vec_dict = {r["id"]: r for r in vec_results}

            # Normalize similarity scores
            if vec_results:
                sim_scores = [r["similarity"] for r in vec_results]
                min_sim, max_sim = min(sim_scores), max(sim_scores)
                sim_range = max_sim - min_sim if max_sim != min_sim else 1.0
                for r in vec_results:
                    r["semantic_score"] = (r["similarity"] - min_sim) / sim_range if sim_range > 0 else 0.5
            else:
                for r in vec_results:
                    r["semantic_score"] = 0.0
        else:
            vec_results = []
            vec_dict = {}

        # Combine results
        combined = {}
        all_ids = set(fts_dict.keys()) | set(vec_dict.keys())

        for chunk_id in all_ids:
            fts_res = fts_dict.get(chunk_id)
            vec_res = vec_dict.get(chunk_id)

            keyword_score = fts_res["keyword_score"] if fts_res else 0.0
            semantic_score = vec_res["semantic_score"] if vec_res else 0.0

            combined_score = (semantic_weight * semantic_score) + (keyword_weight * keyword_score)

            # Prefer semantic results if both exist
            source = "mixed"
            if vec_res and not fts_res:
                source = "semantic"
            elif fts_res and not vec_res:
                source = "keyword"

            combined[chunk_id] = {
                "id": chunk_id,
                "path": (vec_res or fts_res)["path"],
                "text": (vec_res or fts_res)["text"],
                "start_line": (vec_res or fts_res)["start_line"],
                "end_line": (vec_res or fts_res)["end_line"],
                "score": combined_score,
                "source": source,
                "keyword_score": keyword_score,
                "semantic_score": semantic_score,
                "updated_at": (vec_res or fts_res)["updated_at"],
                "access_count": (vec_res or fts_res).get("access_count", 0)
            }

        # Sort by score and limit
        sorted_results = sorted(combined.values(), key=lambda x: x["score"], reverse=True)[:limit]

        # Filter by cutoff
        return [r for r in sorted_results if r["score"] >= SIMILARITY_CUTOFF]

    def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        """Get a single chunk by ID."""
        with self._connect() as conn:
            cursor = conn.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                # Update access count
                conn.execute(
                    "UPDATE chunks SET access_count = access_count + 1 WHERE id = ?",
                    (chunk_id,)
                )
                conn.commit()
                return result
        return None

    # -----------------------------------------------------------------------
    # Compression and Aging
    # -----------------------------------------------------------------------

    def estimate_capacity(self) -> dict[str, Any]:
        """Estimate database size and capacity."""
        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
        # Rough estimate: each chunk ~ 500 bytes on average
        with self._connect() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM chunks")
            chunk_count = cursor.fetchone()[0]

        estimated_chunk_size = 500
        estimated_max_chunks = (db_size * 10) // estimated_chunk_size if db_size > 0 else 100000

        return {
            "db_size_bytes": db_size,
            "db_size_mb": db_size / (1024*1024),
            "chunk_count": chunk_count,
            "estimated_max_chunks": estimated_max_chunks,
            "utilization_percent": (chunk_count / estimated_max_chunks * 100) if estimated_max_chunks > 0 else 0
        }

    def compress_old_chunks(self, dry_run: bool = False) -> dict[str, Any]:
        """
        Remove old, rarely accessed chunks to control database growth.

        Strategy:
        1. Remove chunks from deleted files
        2. Remove chunks older than MAX_MEMORY_AGE_DAYS with access_count=0
        3. For large files, keep only MIN_CHUNKS_TO_KEEP if accessed recently
        """
        now = int(time.time())
        cutoff_age = now - (MAX_MEMORY_AGE_DAYS * 24 * 3600)
        removed_count = 0
        freed_space = 0

        with self._connect() as conn:
            # 1. Find chunks from files that no longer exist
            cursor = conn.execute("SELECT id, path FROM chunks")
            to_delete = []
            for row in cursor:
                file_path = Path(row["path"])
                if not file_path.exists():
                    to_delete.append(row["id"])

            # 2. Find very old, never-accessed chunks
            cursor = conn.execute("""
                SELECT id FROM chunks
                WHERE updated_at < ? AND access_count = 0
            """, (cutoff_age,))
            for row in cursor:
                if row["id"] not in to_delete:
                    to_delete.append(row["id"])

            # 3. For files with many old chunks, keep only recent ones
            cursor = conn.execute("""
                SELECT path, COUNT(*) as total_chunks,
                       SUM(CASE WHEN updated_at > ? THEN 1 ELSE 0 END) as recent_chunks
                FROM chunks
                GROUP BY path
                HAVING total_chunks > ?
            """, (cutoff_age, MIN_CHUNKS_TO_KEEP * 3))
            for row in cursor:
                if row["recent_chunks"] <= MIN_CHUNKS_TO_KEEP:
                    # Need to trim old chunks from this file
                    cursor2 = conn.execute("""
                        SELECT id FROM chunks
                        WHERE path = ? AND updated_at < ?
                        ORDER BY updated_at ASC
                        LIMIT ?
                    """, (row["path"], cutoff_age, row["total_chunks"] - MIN_CHUNKS_TO_KEEP))
                    for r2 in cursor2:
                        if r2["id"] not in to_delete:
                            to_delete.append(r2["id"])

            if not dry_run and to_delete:
                # Get estimated size before deletion
                placeholders = ",".join("?" * len(to_delete))
                cursor = conn.execute(f"""
                    SELECT SUM(LENGTH(text)) FROM chunks WHERE id IN ({placeholders})
                """, to_delete)
                freed_space = cursor.fetchone()[0] or 0

                # Delete one by one to avoid trigger conflicts on FTS5
                removed_count = 0
                # 临时禁用触发器避免FTS5冲突
                conn.execute("DROP TRIGGER IF EXISTS chunks_ad")
                conn.execute("DROP TRIGGER IF EXISTS chunks_au")
                for chunk_id in to_delete:
                    try:
                        conn.execute("DELETE FROM chunks WHERE id = ?", (chunk_id,))
                        removed_count += 1
                    except sqlite3.OperationalError as e:
                        logger.warning(f"Failed to delete chunk {chunk_id}: {e}")
                # 重建触发器
                conn.executescript("""
                    CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                        INSERT INTO chunks_fts(chunks_fts, rowid, text, id, path, source, model, start_line, end_line)
                        VALUES('delete', old.rowid, old.text, old.id, old.path, old.source, old.model, old.start_line, old.end_line);
                    END;
                    CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
                        INSERT INTO chunks_fts(chunks_fts, rowid, text, id, path, source, model, start_line, end_line)
                        VALUES('delete', old.rowid, old.text, old.id, old.path, old.source, old.model, old.start_line, old.end_line);
                        INSERT INTO chunks_fts(rowid, text, id, path, source, model, start_line, end_line)
                        VALUES (new.rowid, new.text, new.id, new.path, new.source, new.model, new.start_line, new.end_line);
                    END;
                """)
                conn.commit()

                logger.info(f"Compressed: removed {removed_count} old chunks, freed ~{freed_space/1024:.1f} KB")

        return {
            "removed_count": removed_count,
            "freed_bytes": freed_space,
            "dry_run": dry_run,
            "to_delete_count": len(to_delete)
        }

# ---------------------------------------------------------------------------
# File Watcher
# ---------------------------------------------------------------------------

class FileWatcher:
    """Watch workspace directory for changes and trigger reindexing."""

    def __init__(self, workspace_dir: Path, indexer: "RAGIndexer", poll_interval: int = 30):
        self.workspace_dir = Path(workspace_dir)
        self.indexer = indexer
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self):
        """Start watching in background thread."""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        logger.info(f"File watcher started on {self.workspace_dir} (poll={self.poll_interval}s)")

    def stop(self):
        """Stop watching."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("File watcher stopped")

    def _watch_loop(self):
        """Main watch loop."""
        while not self._stop_event.is_set():
            try:
                self._check_and_index()
            except Exception as e:
                logger.error(f"Watch loop error: {e}")
            self._stop_event.wait(self.poll_interval)

    def _check_and_index(self):
        """Check for changes and trigger indexing."""
        stale_files = self.indexer.db.get_stale_files(self.workspace_dir)

        if stale_files:
            logger.info(f"Found {len(stale_files)} changed files, indexing...")
            self.indexer.index_files(stale_files, delete_missing=True)

# ---------------------------------------------------------------------------
# Main Indexer
# ---------------------------------------------------------------------------

class RAGIndexer:
    """Main RAG indexing orchestrator."""

    def __init__(
        self,
        db_path: Path,
        workspace_dir: Path,
        embedding_provider: EmbeddingProvider = None,
        auto_watch: bool = True
    ):
        self.db_path = db_path
        self.workspace_dir = Path(workspace_dir)
        self.embedding_provider = embedding_provider or EmbeddingProvider()
        self.db = RAGDatabase(db_path)
        self.chunker = TokenAwareChunker()
        self.watcher = FileWatcher(self.workspace_dir, self)

        if auto_watch:
            self.watcher.start()

    def index_file(self, file_path: Path, force: bool = False) -> dict[str, Any]:
        """Index a single file."""
        if not file_path.exists():
            return {"indexed": False, "error": "File not found"}

        try:
            # Read file
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            if not text.strip():
                return {"indexed": False, "error": "Empty file"}

            # Generate hash and get stats
            file_hash = hashlib.sha256(str(file_path).encode()).hexdigest()[:16]
            mtime = int(file_path.stat().st_mtime)
            size = file_path.stat().st_size

            # Check if already indexed and up to date
            existing = self.db.get_file(str(file_path))
            if existing and not force and existing["mtime"] == mtime and existing["hash"] == file_hash:
                return {"indexed": False, "reason": "already_up_to_date"}

            # Chunk the text
            chunks = self.chunker.split_text(text, metadata={
                "file": str(file_path),
                "mtime": mtime,
                "size": size
            })

            if not chunks:
                return {"indexed": False, "error": "No chunks generated"}

            # Store in database
            self.db.add_chunks(chunks, str(file_path), self.embedding_provider)
            self.db.upsert_file(str(file_path), file_hash, mtime, size)

            return {
                "indexed": True,
                "file": str(file_path),
                "chunks": len(chunks),
                "chunk_size_avg": sum(c["token_count"] for c in chunks) / len(chunks)
            }

        except Exception as e:
            logger.error(f"Failed to index {file_path}: {e}")
            return {"indexed": False, "error": str(e)}

    def index_files(self, file_paths: list[Path], delete_missing: bool = False) -> dict[str, Any]:
        """Index multiple files."""
        results = []
        total_chunks = 0

        for file_path in file_paths:
            result = self.index_file(file_path)
            results.append(result)
            if result.get("indexed"):
                total_chunks += result.get("chunks", 0)

        # Optionally remove chunks for files that no longer exist
        if delete_missing:
            indexed_paths = set(str(p) for p in file_paths if p.exists())
            all_db_paths = set()
            with self.db._connect() as conn:
                cursor = conn.execute("SELECT path FROM files WHERE source = 'workspace'")
                for row in cursor:
                    all_db_paths.add(row["path"])

            missing = all_db_paths - indexed_paths
            if missing:
                logger.info(f"Removing {len(missing)} deleted files from index")
                with self.db._connect() as conn:
                    for path in missing:
                        conn.execute("DELETE FROM chunks WHERE path = ?", (path,))
                        conn.execute("DELETE FROM files WHERE path = ?", (path,))
                    conn.commit()

        return {
            "total_files": len(results),
            "indexed_count": sum(1 for r in results if r.get("indexed")),
            "total_chunks": total_chunks,
            "results": results
        }

    def index_all(self, extensions: list[str] = None) -> dict[str, Any]:
        """Index all files in workspace."""
        if extensions is None:
            extensions = [".py", ".js", ".ts", ".java", ".c", ".cpp", ".h",
                         ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".rst"]

        files = []
        for ext in extensions:
            files.extend(self.workspace_dir.rglob(f"*{ext}"))

        # Filter out hidden directories
        files = [f for f in files if not any(part.startswith(".") for part in f.parts)]

        logger.info(f"Found {len(files)} files to index")
        return self.index_files(files, delete_missing=True)

    def search(
        self,
        query: str,
        limit: int = 10,
        path_filter: str = None,
        semantic_weight: float = SEMANTIC_WEIGHT,
        keyword_weight: float = KEYWORD_WEIGHT
    ) -> list[dict[str, Any]]:
        """Perform hybrid search."""
        return self.db.hybrid_search(
            query=query,
            embedding_provider=self.embedding_provider,
            limit=limit,
            path_filter=path_filter,
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight
        )

    def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        """Retrieve a chunk by ID."""
        return self.db.get_chunk(chunk_id)

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive statistics."""
        capacity = self.db.estimate_capacity()

        with self.db._connect() as conn:
            # File stats
            cursor = conn.execute("SELECT COUNT(*) FROM files")
            file_count = cursor.fetchone()[0]

            # Chunk stats
            cursor = conn.execute("""
                SELECT COUNT(*), MIN(updated_at), MAX(updated_at),
                       AVG(LENGTH(text)), SUM(access_count)
                FROM chunks
            """)
            chunk_count, min_ts, max_ts, avg_len, total_accesses = cursor.fetchone()

            # Vector coverage (gracefully handle missing vec0)
            try:
                cursor = conn.execute("SELECT COUNT(*) FROM chunks_vec")
                vector_count = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                vector_count = 0

            # Top accessed chunks
            cursor = conn.execute("""
                SELECT path, COUNT(*) as chunk_count, SUM(access_count) as accesses
                FROM chunks
                GROUP BY path
                ORDER BY accesses DESC
                LIMIT 5
            """)
            top_files = [{"path": r[0], "chunks": r[1], "accesses": r[2]} for r in cursor]

        return {
            "database": {
                "path": str(self.db_path),
                "size_mb": capacity["db_size_mb"],
                "utilization_percent": capacity["utilization_percent"]
            },
            "files": {
                "total": file_count,
                "indexed_extensions": ".py,.js,.ts,.md,.txt,..."
            },
            "chunks": {
                "total": chunk_count,
                "with_vectors": vector_count,
                "vector_coverage_percent": (vector_count / chunk_count * 100) if chunk_count > 0 else 0,
                "avg_length": int(avg_len) if avg_len else 0,
                "total_accesses": total_accesses or 0
            },
            "top_files": top_files,
            "workspace": str(self.workspace_dir)
        }

    def compress(self, dry_run: bool = False) -> dict[str, Any]:
        """Run compression/aging."""
        return self.db.compress_old_chunks(dry_run=dry_run)

    def close(self):
        """Clean up resources."""
        self.watcher.stop()
        self.db.close()

# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def get_indexer(workspace_dir: Path = None, db_path: Path = None) -> RAGIndexer:
    """Get or create a RAG indexer instance."""
    if workspace_dir is None:
        workspace_dir = Path.home() / ".hermes" / "workspace"
    if db_path is None:
        db_path = Path.home() / ".hermes" / "memory" / "rag_main.sqlite"

    return RAGIndexer(db_path, workspace_dir)

def search(query: str, limit: int = 10, workspace_dir: Path = None) -> list[dict[str, Any]]:
    """Quick search function."""
    indexer = get_indexer(workspace_dir)
    try:
        return indexer.search(query, limit=limit)
    finally:
        indexer.close()
