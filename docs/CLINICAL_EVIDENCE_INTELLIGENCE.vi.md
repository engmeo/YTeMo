# Clinical Evidence Intelligence – implementation notes

## What this increment adds
- pgvector storage for 768-dimensional embeddings, HNSW cosine index and a SQL similarity function.
- Hybrid API that first obtains the existing governance-filtered lexical candidate set, then reranks only those candidates with vector similarity and reciprocal-rank fusion (RRF).
- Explicit embedding-provider configuration through `CLINICAL_EMBEDDING_API_URL`, `CLINICAL_EMBEDDING_API_KEY`, and `CLINICAL_EMBEDDING_MODEL`. The endpoint must implement the OpenAI-compatible embeddings request/response shape and return exactly 768 dimensions.
- Provenance-bearing Knowledge Graph entity/edge tables; edges default to CANDIDATE and must not be treated as approved clinical facts.
- Source synchronization run ledger and a benchmark-case registry with separate PUBLIC_SOURCE_CURATED and EXPERT_ADJUDICATED states.
- Structured evidence-map draft endpoint. It does not perform meta-analysis or clinical recommendation.

## Migration
Apply `202611240009_clinical_evidence_intelligence.sql` only after migrations 001–008. Validate in a separate Supabase staging project first. This migration has not been applied by this code change.

## API
- `POST /clinical-intelligence/search`: governance-filtered hybrid search; if embeddings are not configured or vector RPC fails, explicitly reports lexical fallback.
- `GET /clinical-intelligence/graph/entities`
- `GET /clinical-intelligence/graph/edges?entity_id=...`
- `POST /clinical-intelligence/synthesis/draft`: body is an array of accepted claim IDs.

## Safety and evidence limitations
- Vector similarity is relevance ranking, not evidence quality or truth.
- Hybrid search cannot introduce a claim excluded by current document, jurisdiction, population, scope, credential, or conflict filters.
- Graph assertions remain candidates until reviewed; terminology licenses must be cleared before importing licensed vocabularies.
- A public-source-curated benchmark is not an expert-adjudicated clinical gold set. Online clinician opinions may be captured as attributed secondary sources but do not become gold labels by popularity or consensus.
- This increment does not create real prospective clinical validation, certify diagnoses, or establish patient-facing clinical decision support.
