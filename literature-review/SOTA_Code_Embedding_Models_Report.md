# State-of-the-Art Code Embedding Models

**Research Report for RAG-Based Compliance Auditing**
*March 31, 2026*

> **Selection Criteria:** Code retrieval benchmarks • Cross-modal NL ↔ Code • CPU-only inference • Open weights

---

## 1. Introduction and Project Context

This report identifies the most appropriate embedding model for a **code-aware RAG-based compliance auditing** system. The system's core retrieval task is cross-modal: natural language compliance rules (e.g., "Do not train models for commercial products") or HyDE-generated hypothetical violating code snippets are used as queries to retrieve semantically relevant chunks of Python source code from a ChromaDB vector store. All embedding inference runs locally on CPU via the sentence-transformers library, with no external API dependencies.

### 1.1 Current Embedding Usage

The codebase currently uses two different models. The prototype (**phase2_prototype.py**) uses **jinaai/jina-embeddings-v2-base-code**, a code-specialised model that was validated for NL↔code retrieval. However, the production pipeline (**src/audit.py** and **src/rules_parser/rules_vector_db.py**) was downgraded to **BAAI/bge-small-en-v1.5**, a 33M-parameter general-purpose text encoder with no code awareness. This downgrade sacrifices cross-modal retrieval quality—the single most important factor for matching compliance rules to source code—in exchange for a smaller memory footprint (~130 MB vs. ~550 MB).

### 1.2 Deployment Constraints

| Factor | Current Situation | Implication |
|---|---|---|
| **Deployment** | Local CPU-only via HuggingFace | Rules out API models; model must ship with the tool |
| **Speed** | Embeds chunks on-the-fly per audit | Inference speed directly impacts audit latency |
| **Chunk sizes** | ~1500 chars (~375 tokens) | 512+ token context is sufficient today; 8K provides headroom |
| **Query modality** | NL rules → code, or HyDE code → code | Cross-modal NL↔code is the #1 quality factor |
| **Storage** | ChromaDB (local, ephemeral + persistent) | Higher-dim embeddings increase disk/memory usage |

**Evaluation criteria, in priority order:** (1) NL↔code cross-modal retrieval quality, (2) context window length, (3) embedding dimensionality, (4) model size and CPU inference speed, (5) benchmark validation on code-domain tasks.

---

## 2. Candidate Triage

An initial long-list of 12 models was evaluated: four code-specialised open models (Jina v2 Base Code, Jina v3, CodeT5+ 110M, UniXcoder-Base), four general-purpose open models (BGE-small, BGE-large, BGE-M3, MiniLM-L6-v2), and four API-based models (OpenAI text-embedding-3-large/small, Google text-embedding-004, Voyage-Code-3). API models were eliminated by the CPU-only constraint. General-purpose models lacking code training were deprioritised unless they offered a unique advantage (e.g., BGE-M3's hybrid retrieval). Models with 256-token context limits (MiniLM) were excluded outright.

The final five models selected for deep analysis were chosen because each represents a distinct and state-of-the-art approach to code embedding, all satisfy the three filter criteria (code retrieval evaluation, cross-modal NL↔code testing, CPU-feasible open weights), and together they span the relevant parameter-count spectrum from 137M to 7B. Notably, the project's prototype-validated **jina-embeddings-v2-base-code** is included as a mandatory anchor point.

---

## 3. SOTA Model Summaries

### 3.1 Jina Embeddings v2 Base Code (161M)

**Paper:** *Jina Embeddings 2: 8192-Token General-Purpose Text Embeddings for Long Documents* (Günther et al., arXiv 2310.19923, 2023)

A 161M-parameter BERT-variant encoder (JinaBERT) supporting 8192-token context via symmetric bidirectional ALiBi attention. The backbone is pretrained on GitHub code and fine-tuned on over 150 million docstring–code and QA pairs spanning 30+ programming languages. It produces 768-dimensional embeddings and leads on 9 of 15 CodeSearchNet sub-benchmarks. At ~550 MB in FP32 (~1.5 GB loaded), it runs at sub-100 ms per query on a modern multi-core CPU with the sentence-transformers library. **Project relevance:** Already validated in the prototype (phase2_prototype.py). Its 8K context window provides headroom beyond the current 375-token chunk size, and its explicit NL↔code training directly addresses the compliance rule matching task. The model is a drop-in replacement for bge-small via HuggingFaceEmbeddings.

### 3.2 CodeXEmbed / SFR-Embedding-Code (400M–7B)

**Paper:** *CodeXEmbed: A Generalist Embedding Model Family for Multilingual and Multi-task Code Retrieval* (Liu et al., arXiv 2411.12644, 2024)

A family from Salesforce spanning 400M, 2B, and 7B parameters. The training pipeline unifies text-to-code, code-to-text, code-to-code, and hybrid retrieval tasks into a common framework. The 7B variant achieved #1 on the CoIR leaderboard (Feb 2025), surpassing Voyage-Code-002 by over 20%, while also remaining competitive on the general-purpose BeIR text benchmark. For CPU-only deployment, the 400M variant (~1.6 GB RAM) is the practical choice, producing embeddings at interactive speeds. The 2B variant is feasible with INT8 quantisation (~4 GB) but at higher latency; the 7B variant is impractical for real-time CPU use. **Project relevance:** The 400M model uniquely handles both code and documentation retrieval in a single model. Since the auditing pipeline indexes both source code and fetched content files (via rules_vector_db.py), a single model that excels at both modalities avoids maintaining two separate embedders.

### 3.3 Jina Code Embeddings (0.5B / 1.5B)

**Paper:** *Efficient Code Embeddings from Code Generation Models* (Kryvosheieva et al., arXiv 2508.21290, 2025)

Built on Qwen2.5-Coder backbones (494M and 1.54B), these models repurpose autoregressive code-generation decoders as embedding encoders via last-token pooling. Task-specific instruction prefixes (NL2Code, Code2Code, TechQA, etc.) are selected at inference time. Matryoshka Representation Learning allows truncating from 1536 dimensions down to 128 with minimal quality loss. On CPU, the 0.5B model needs ~2 GB RAM and runs at reasonable latency; the 1.5B model needs ~6 GB and benefits from ONNX export or INT8 quantisation. **Project relevance:** The NL2Code instruction prefix directly maps to the compliance use case (NL rule → code retrieval). MRL-based dimension reduction would also reduce ChromaDB storage, which matters for the persistent vector store in rules_vector_db.py.

### 3.4 CoRNStack / CodeRankEmbed (137M)

**Paper:** *CoRNStack: High-Quality Contrastive Data for Better Code Retrieval and Reranking* (Suresh et al., arXiv 2412.01007, ICLR 2025)

A data-centric approach: rather than scaling parameters, CoRNStack curates a high-quality contrastive dataset from The Stack V2 via dual consistency filtering and curriculum-based hard-negative mining. The resulting CodeRankEmbed is a 137M bi-encoder (fine-tuned from Arctic-Embed-M) that outperforms models ten times its size—including CodeSage-Large (1.3B) and Voyage-Code-002—across CodeSearchNet, AdvTest, and CoIR. At only ~600 MB FP32, it delivers sub-50 ms per-query CPU latency. The paper also introduces CodeRankLLM, a 7B listwise code reranker. **Project relevance:** The smallest and fastest model surveyed, making it ideal for the on-the-fly embedding generation in audit.py where latency directly affects audit turnaround. However, it has a 512-token context limit, which is adequate for the current 375-token chunks but leaves no headroom for larger chunks.

### 3.5 Qodo-Embed-1 (1.5B / 7B)

**Reference:** *State-of-the-Art Code Retrieval With Efficient Code Embedding Models* (Qodo, May 2025)

Fine-tuned from Qwen2 backbones, Qodo-Embed-1 uses an LLM-based synthetic data pipeline that generates NL queries for code snippets, producing high-quality training pairs that address the NL–code vocabulary mismatch. On CoIR, the 1.5B variant scores 68.53 (beating larger 7B competitors); the 7B reaches 71.5. For CPU, the 1.5B needs ~6 GB RAM; the 7B (~28 GB) is batch-indexing only. **Project relevance:** The synthetic NL→code training methodology closely mirrors the project's HyDE approach (generating hypothetical violating code, then retrieving). This alignment suggests Qodo-Embed-1 may generalise particularly well for HyDE-augmented queries in the compliance pipeline.

---

## 4. Comparative Summary

| Model | Params | Dim. | Context | NL↔Code | CPU RAM | Latency/q | CoIR | Audit Fit |
|---|---|---|---|---|---|---|---|---|
| **Jina v2 Code** | 161M | 768 | 8,192 | Yes | ~1.5 GB | <100 ms | —\* | ★★★★★ |
| **CodeXEmbed** | 400M | varies | 512–8K | Yes | ~1.6 GB | <150 ms | 71.0 | ★★★★ |
| **Jina Code 0.5B** | 494M | 1536† | 8,192 | Yes | ~2 GB | ~200 ms | SOTA | ★★★★ |
| **CodeRankEmbed** | 137M | 768 | 512 | Yes | ~0.6 GB | <50 ms | Best avg | ★★★ |
| **Qodo-Embed-1** | 1.5B | varies | 8,192 | Yes | ~6 GB | ~400 ms | 68.5 | ★★★ |

\* Jina v2 Base Code predates CoIR; strong CodeSearchNet results. † Supports MRL truncation to 128. Latency estimates assume FP32 on an 8-core CPU. "Audit Fit" reflects alignment with compliance auditing constraints (cross-modal quality, CPU speed, context window, integration effort). Ranges for CodeXEmbed and Qodo show the CPU-recommended variant only.

**Versus the current production model (bge-small-en-v1.5):** bge-small has 33M parameters, 384 dimensions, a 512-token context, and no code-specific training. It loads at ~130 MB and is the fastest option. However, it was designed purely for English text retrieval and has no mechanism for bridging the NL↔code semantic gap. Every model in the table above offers a substantial retrieval quality improvement for the compliance use case, at the cost of a larger footprint.

---

## 5. Key Observations

**Data quality trumps model scale.** CoRNStack's 137M encoder outperforms 1.3B+ models because its training data is aggressively filtered and enriched with hard negatives. Similarly, Qodo-Embed-1 at 1.5B beats many 7B baselines via LLM-generated synthetic NL–code pairs. For the compliance auditing project, this means upgrading from bge-small to a smaller code-specialised model (Jina v2 at 161M or CodeRankEmbed at 137M) will yield a far larger quality jump than upgrading to a bigger general-purpose model (e.g., bge-large at 335M).

**The NL↔code gap is the dominant quality factor.** Every model in this survey addresses the vocabulary mismatch between natural language and code syntax. For compliance auditing, this gap is especially acute: rules are written in policy language ("shall not use third-party APIs without approval") while violations live in import statements and API calls. Models trained on docstring–code pairs (Jina v2, CodeXEmbed) or consistency-filtered NL–code contrastive data (CoRNStack) directly close this gap in ways that general-purpose text encoders cannot.

**CPU inference is viable for the entire sub-500M class.** Jina v2 Base Code (161M), CodeRankEmbed (137M), and CodeXEmbed-400M all run at interactive CPU latency (<150 ms per query) with under 2 GB of RAM. This fits comfortably within the on-the-fly embedding generation model used in audit.py. For the 0.5B–1.5B class, ONNX Runtime export and INT8 quantisation bring latency below 500 ms, which may be acceptable for batch indexing in rules_vector_db.py but is slower than desired for per-rule audit queries.

**HyDE-style queries benefit from NL→code training alignment.** The project generates hypothetical violating code snippets (HyDE) before searching. Qodo-Embed-1's synthetic NL→code training pipeline mirrors this pattern—its training data is literally LLM-generated code keyed to NL descriptions. Jina Code Embeddings' task-specific instruction prefixes (NL2Code vs. Code2Code) allow the pipeline to switch embedding strategies depending on whether the query is a raw NL rule or a HyDE-generated code snippet, a degree of control that other models lack.

---

## 6. Recommendation for This Project

### 6.1 Primary: jina-embeddings-v2-base-code

After weighing the SOTA research against the project's specific constraints, **jinaai/jina-embeddings-v2-base-code** remains the strongest recommendation for both audit.py and rules_vector_db.py. The rationale:

1. **Already validated.** The prototype confirmed its effectiveness for the exact NL↔code retrieval task. Newer models like CodeRankEmbed score higher on CoIR, but CoIR's benchmark tasks (code translation, competitive programming, multi-turn feedback) do not directly test compliance-rule-to-code matching. The prototype's empirical validation on the actual use case carries more weight than benchmark deltas.

2. **8K context provides headroom.** Current chunks are ~375 tokens, but the 8192-token window accommodates future increases in chunk size, multi-function contexts, or longer HyDE-generated snippets—without requiring a model swap. CodeRankEmbed's 512-token limit is adequate today but offers zero margin.

3. **CPU-feasible with acceptable latency.** At 161M parameters and ~550 MB on disk, it runs below 100 ms per query on CPU. This is ~4× slower than bge-small but still sub-second, well within interactive audit latency targets. ONNX Runtime can cut this further.

4. **Zero integration friction.** It is a direct drop-in for bge-small via HuggingFaceEmbeddings. Both audit.py and rules_vector_db.py require only a model name change—no code restructuring, no new dependencies, no dimension changes to ChromaDB collections (both produce 768-dim vectors, vs. bge-small's 384, so collections must be rebuilt once).

### 6.2 Future Upgrade Path

If retrieval quality proves insufficient after switching to Jina v2 Base Code, the following staged upgrades are recommended:

- **Stage 1 — Add a reranker:** Pair Jina v2 Base Code with a lightweight cross-encoder reranker (e.g., cross-encoder/ms-marco-MiniLM-L-6-v2 at 80 MB) applied to the top-k retrieved chunks. This typically yields a larger quality gain than upgrading the bi-encoder itself and adds minimal CPU overhead.

- **Stage 2 — Upgrade to Jina Code Embeddings 0.5B:** The newer decoder-based model from the same team offers task-specific instruction prefixes (NL2Code for raw rules, Code2Code for HyDE queries) and MRL-based dimension reduction. Requires ~2 GB RAM and ONNX export for best CPU performance.

- **Stage 3 — Adopt CodeRankEmbed + CodeRankLLM:** If the project later gains GPU access or moves to a server with 16+ GB RAM, the CoRNStack retriever+reranker pipeline provides the strongest end-to-end code retrieval results, including function-level localisation for GitHub-issue-style queries—closely analogous to localising compliance violations.

---

## 7. Conclusion

The SOTA landscape for code embedding has matured rapidly since the project's prototype was built. The CoIR benchmark (ACL 2025), data-centric training approaches (CoRNStack, ICLR 2025), and decoder-to-encoder transfer techniques (Jina Code Embeddings) have collectively pushed code retrieval quality far beyond CodeSearchNet-era baselines. Crucially, models in the sub-500M parameter class—where jina-embeddings-v2-base-code sits—now deliver production-grade cross-modal NL↔code retrieval on CPU hardware with under 2 GB of RAM and sub-100 ms latency.

The immediate action is straightforward: replace bge-small-en-v1.5 with jina-embeddings-v2-base-code in both audit.py and rules_vector_db.py, rebuild the ChromaDB collections for the new 768-dimension vectors, and empirically validate retrieval quality on a held-out set of compliance rules. This change restores the code-aware retrieval that the prototype demonstrated, at a footprint cost of ~420 MB—a modest price for the quality of the system's most critical component.

---

## References

1. Günther, M. et al. (2023). *Jina Embeddings 2: 8192-Token General-Purpose Text Embeddings for Long Documents.* arXiv:2310.19923.
2. Liu, Y. et al. (2024). *CodeXEmbed: A Generalist Embedding Model Family for Multilingual and Multi-task Code Retrieval.* arXiv:2411.12644.
3. Kryvosheieva, D. et al. (2025). *Efficient Code Embeddings from Code Generation Models.* arXiv:2508.21290.
4. Suresh, T. et al. (2024). *CoRNStack: High-Quality Contrastive Data for Better Code Retrieval and Reranking.* arXiv:2412.01007. ICLR 2025.
5. Qodo (2025). *Qodo-Embed-1: State-of-the-Art Code Retrieval With Efficient Code Embedding Models.* qodo.ai/blog.
6. Li, X. et al. (2025). *CoIR: A Comprehensive Benchmark for Code Information Retrieval Models.* ACL 2025.
7. Husain, H. et al. (2019). *CodeSearchNet Challenge: Evaluating the State of Semantic Code Search.* arXiv:1909.09436.
