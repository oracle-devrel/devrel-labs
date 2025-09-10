
"""
Oracle Database Vector Store Component with Local Embeddings Integration
(Configurable retrieval behavior for Langflow)

This component integrates Oracle 23ai Vector Store (OracleVS) with a pluggable
embeddings handle and exposes configurable search parameters such as:
  - number_of_results (k)
  - search_type (similarity, mmr, similarity_score_threshold)
  - score_threshold (for threshold mode)
  - fetch_k (preselect pool size before filtering/MMR)
  - mmr_lambda (diversity vs. similarity)
  - distance_strategy (COSINE, EUCLIDEAN, DOT_PRODUCT)

Author: Paul Parkinson
"""

import oracledb
from typing import List

from langchain_community.vectorstores.oraclevs import OracleVS
from langchain_community.vectorstores.utils import DistanceStrategy

from langflow.base.vectorstores.model import (
    LCVectorStoreComponent,
    check_cached_vector_store,
)
from langflow.helpers.data import docs_to_data
from langflow.io import (
    HandleInput,
    IntInput,
    StrInput,
    SecretStrInput,
    MessageTextInput,
    FloatInput,
    DropdownInput,
)
from langflow.schema import Data


class OracleDatabaseVectorStoreComponent(LCVectorStoreComponent):
    """
    Oracle Database Vector Store optimized for local embeddings with configurable retrieval.
    """

    display_name = "Oracle Database Vector Store"
    description = "Oracle 23ai Vector Store with local embeddings (no cloud dependencies) and configurable retrieval"
    name = "oracledb_vector"

    # ---------------------
    # UI Inputs
    # ---------------------
    inputs = [
        # Connection
        SecretStrInput(
            name="db_user",
            display_name="Database User",
            info="Oracle database username (e.g., ADMIN)",
            required=True,
        ),
        SecretStrInput(
            name="db_password",
            display_name="Database Password",
            info="Oracle database password",
            required=True,
        ),
        SecretStrInput(
            name="dsn",
            display_name="DSN",
            info="Database connection string (e.g., myatp_high)",
            required=True,
        ),
        SecretStrInput(
            name="wallet_dir",
            display_name="Wallet Directory",
            info="Path to Oracle wallet directory",
            required=True,
        ),
        SecretStrInput(
            name="wallet_password",
            display_name="Wallet Password",
            info="Oracle wallet password",
            required=True,
        ),

        # Storage/table
        StrInput(
            name="table_name",
            display_name="Table Name",
            info="Vector table name (e.g., PDFCOLLECTION)",
            value="PDFCOLLECTION",
            required=True,
        ),

        # Query
        MessageTextInput(
            name="search_query",
            display_name="Search Query",
            info="Enter your search query for vector similarity search",
        ),

        # Embedding handle
        *LCVectorStoreComponent.inputs,
        HandleInput(
            name="embedding",
            display_name="Embedding Model",
            input_types=["Embeddings"],
            info="Connect a Local SentenceTransformer or other embedding model",
        ),

        # Retrieval configuration
        IntInput(
            name="number_of_results",
            display_name="Number of Results (k)",
            info="Maximum number of results to return",
            value=5,
            advanced=False,
        ),
        DropdownInput(
            name="search_type",
            display_name="Search Type",
            options=["similarity", "mmr", "similarity_score_threshold"],
            value="similarity",
            advanced=True,
        ),
        FloatInput(
            name="score_threshold",
            display_name="Score Threshold (for threshold mode)",
            value=0.35,
            advanced=True,
        ),
        IntInput(
            name="fetch_k",
            display_name="Fetch K (preselect pool)",
            info="Number of top candidates to fetch before MMR/threshold filtering",
            value=20,
            advanced=True,
        ),
        FloatInput(
            name="mmr_lambda",
            display_name="MMR Lambda (0=diversity, 1=similarity)",
            value=0.5,
            advanced=True,
        ),
        DropdownInput(
            name="distance_strategy_ui",
            display_name="Distance Strategy",
            options=["COSINE", "EUCLIDEAN", "DOT_PRODUCT"],
            value="COSINE",
            advanced=True,
        ),
    ]

    # ---------------------
    # Connection
    # ---------------------
    def get_database_connection(self) -> oracledb.Connection:
        """Create Oracle database connection with wallet authentication."""
        connect_args = {
            "user": self.db_user,
            "password": self.db_password,
            "dsn": self.dsn,
            "config_dir": self.wallet_dir,
            "wallet_location": self.wallet_dir,
            "wallet_password": self.wallet_password,
        }
        try:
            return oracledb.connect(**connect_args)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Oracle Database: {str(e)}")

    # ---------------------
    # Vector Store Builder
    # ---------------------
    @check_cached_vector_store
    def build_vector_store(self) -> OracleVS:
        """Build the Oracle Vector Store with configurable distance strategy."""
        conn = self.get_database_connection()

        try:
            # Validate table exists
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT table_name
                FROM user_tables
                WHERE UPPER(table_name) = UPPER(:table_name)
                """,
                {"table_name": self.table_name},
            )
            row = cursor.fetchone()

            if not row:
                cursor.execute(
                    """
                    SELECT table_name
                    FROM user_tables
                    WHERE UPPER(table_name) LIKE '%COLLECTION%'
                    ORDER BY table_name
                    """
                )
                available = [r[0] for r in cursor.fetchall()]
                cursor.close()
                msg = f"Table '{self.table_name}' does not exist."
                if available:
                    msg += f" Available collection tables: {', '.join(available)}"
                else:
                    msg += " No collection tables found. Create a vector table first."
                self.status = f"❌ {msg}"
                raise RuntimeError(msg)

            actual_table_name = row[0]
            cursor.close()

            # Map UI distance strategy to enum
            ds_map = {
                "COSINE": DistanceStrategy.COSINE,
                "EUCLIDEAN": DistanceStrategy.EUCLIDEAN,
                "DOT_PRODUCT": DistanceStrategy.DOT_PRODUCT,
            }
            distance = ds_map.get(
                getattr(self, "distance_strategy_ui", "COSINE"),
                DistanceStrategy.COSINE,
            )

            vs = OracleVS(
                client=conn,
                table_name=actual_table_name,
                distance_strategy=distance,
                embedding_function=self.embedding,
            )
            self.status = f"✅ Connected to Oracle Vector Store table: {actual_table_name}"
            return vs

        except Exception as e:
            msg = f"Failed to build vector store: {str(e)}"
            self.status = f"❌ {msg}"
            raise RuntimeError(msg)

    # ---------------------
    # Search
    # ---------------------
    def search_documents(self) -> List[Data]:
        """Perform a similarity/MMR/thresholded vector search based on UI settings."""
        if not self.search_query or not self.search_query.strip():
            return []

        vector_store = self.build_vector_store()
        query = self.search_query.strip()

        # read UI values with sane defaults
        try:
            k = max(1, int(getattr(self, "number_of_results", 5) or 5))
        except Exception:
            k = 5

        search_type = getattr(self, "search_type", "similarity") or "similarity"

        # optional knobs
        fetch_k = getattr(self, "fetch_k", None)
        try:
            fetch_k = int(fetch_k) if fetch_k is not None else None
        except Exception:
            fetch_k = None

        try:
            mmr_lambda = float(getattr(self, "mmr_lambda", 0.5))
        except Exception:
            mmr_lambda = 0.5

        try:
            score_threshold = float(getattr(self, "score_threshold", 0.35))
        except Exception:
            score_threshold = 0.35

        try:
            if search_type == "similarity":
                kwargs = {}
                if fetch_k:
                    kwargs["fetch_k"] = fetch_k
                docs = vector_store.similarity_search(query=query, k=k, **kwargs)

            elif search_type == "mmr":
                kwargs = {}
                if fetch_k:
                    kwargs["fetch_k"] = fetch_k
                docs = vector_store.max_marginal_relevance_search(
                    query=query,
                    k=k,
                    lambda_mult=mmr_lambda,
                    **kwargs,
                )

            elif search_type == "similarity_score_threshold":
                retriever = vector_store.as_retriever(
                    search_type="similarity_score_threshold",
                    search_kwargs={
                        "k": k,  # cap
                        "score_threshold": score_threshold,
                        **({"fetch_k": fetch_k} if fetch_k else {}),
                    },
                )
                docs = retriever.get_relevant_documents(query)

            else:
                # fallback to similarity
                docs = vector_store.similarity_search(query=query, k=k)

            data = docs_to_data(docs)
            self.status = data
            return data

        except Exception as e:
            self.status = f"Search failed: {str(e)}"
            return []

    # ---------------------
    # Ingest
    # ---------------------
    def add_documents(self, documents) -> None:
        """Add documents to the vector store."""
        vs = self.build_vector_store()
        try:
            vs.add_documents(documents)
            self.status = f"Successfully added {len(documents)} documents"
        except Exception as e:
            self.status = f"Failed to add documents: {str(e)}"
            raise
