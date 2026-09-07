# RAG and LLM

The default runnable path uses a free local Ollama model (`qwen3:4b`) because it
is easy to demonstrate on a personal workstation.

Vespa remains responsible for:
- document embedding
- BM25
- HNSW
- semantic retrieval
- hybrid retrieval/ranking

FastAPI takes the Top-K evidence and gives only that context to the local LLM.

Vespa itself also supports LocalLLM and RAGSearcher. An optional example is
included in `vespa-app/services.local-llm.example.xml`. It is not enabled by
default because Vespa documents LocalLLM as beta and GGUF models can need
substantial RAM.
