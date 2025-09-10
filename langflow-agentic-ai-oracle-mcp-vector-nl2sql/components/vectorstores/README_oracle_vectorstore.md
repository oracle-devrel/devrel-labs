
# Oracle Database Vector Store (Langflow Custom Component)

This custom component wraps `OracleVS` (Oracle 23ai Vector Store) and exposes *configurable retrieval* knobs inside Langflow.

## Features
- Local embeddings handle (connect any Embeddings node)
- Choose distance: COSINE / EUCLIDEAN / DOT_PRODUCT
- Search types:
  - `similarity` (top-k)
  - `mmr` (diversity via MMR)
  - `similarity_score_threshold` (filter by min score; `k` becomes a cap)
- Tunables: `number_of_results (k)`, `fetch_k`, `mmr_lambda`, `score_threshold`

## Installation
1. Save `oracledb_vectorstore.py` into your Langflow custom components folder, e.g.:
   - macOS/Linux: `~/.langflow/components/`
   - Windows: `%USERPROFILE%\\.langflow\\components\\`
2. Restart Langflow. The component appears as **Oracle Database Vector Store**.

## Inputs
- **Database User / Password / DSN / Wallet Dir / Wallet Password**
- **Table Name**: e.g., `PDFCOLLECTION`
- **Embedding Model**: connect a local `Embeddings` node
- **Search Query**
- **Number of Results (k)**
- **Search Type**
- **Score Threshold** (only used for threshold mode)
- **Fetch K**
- **MMR Lambda**
- **Distance Strategy**

## Notes
- Ensure your vector column dimensions match the embedding model dimension.
- If using threshold mode, set a reasonable `score_threshold` (e.g., 0.3–0.4).
- Set `fetch_k > k` for better MMR/threshold results.
