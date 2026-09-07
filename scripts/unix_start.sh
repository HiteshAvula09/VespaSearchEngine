#!/usr/bin/env bash
set -euo pipefail
docker compose up -d vespa ollama
sleep 10
python3 scripts/deploy_vespa.py
docker compose exec ollama ollama pull qwen3:4b
