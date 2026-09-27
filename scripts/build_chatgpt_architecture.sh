#!/usr/bin/env bash
#
# Build ChatGPT System Architecture using GraphNode and export to Mermaid
#
set -euo pipefail

GRAPH_NAME="chatgpt_system"
OUTPUT_DIR="${1:-.}"
MERMAID_FILE="${OUTPUT_DIR}/chatgpt_architecture.mmd"
MARKDOWN_FILE="${OUTPUT_DIR}/chatgpt_architecture.md"

echo "======================================================="
echo "|       BUILDING CHATGPT SYSTEM ARCHITECTURE          |"
echo "======================================================="

# 1. Initialize dedicated named graph & CLI shortcut
graphnode -create "${GRAPH_NAME}"

# 2. Add Ingress & Clients
${GRAPH_NAME} -add web_client mobile_client voice_client api_client -type client
${GRAPH_NAME} -add cloudflare_edge -type gateway -desc "Cloudflare WAF, DDoS protection, and SSL termination"
${GRAPH_NAME} -add api_gateway -type gateway -desc "Kong/Envoy API Gateway with auth routing and rate limits"

# 3. Add Core Application Services
${GRAPH_NAME} -add auth_service -type service -desc "OAuth2, JWT authentication and API key validation"
${GRAPH_NAME} -add billing_service -type service -desc "Token accounting, Stripe billing, and tier quotas"
${GRAPH_NAME} -add chat_orchestrator -type service -desc "Conversation manager, prompt assembly, and SSE streaming"
${GRAPH_NAME} -add moderation_service -type service -desc "Real-time safety guardrails and content classification"

# 4. Add Agent & Tool Execution Subsystem
${GRAPH_NAME} -add agent_runtime -type service -desc "Tool calling engine and execution orchestrator"
${GRAPH_NAME} -add code_interpreter -type worker -desc "Sandboxed Python execution environment (Firecracker/gVisor)"
${GRAPH_NAME} -add web_search_worker -type worker -desc "Live web browsing and document scraping worker"

# 5. Add Inference Engine & GPU Compute
${GRAPH_NAME} -add inference_router -type gateway -desc "Dynamic vLLM/TensorRT-LLM load balancer"
${GRAPH_NAME} -add llm_inference_cluster -type service -desc "NVIDIA H100 GPU cluster running GPT reasoning models"
${GRAPH_NAME} -add kv_cache_cluster -type cache -desc "Distributed PagedAttention KV-cache storage"

# 6. Add Persistence, Vector Search & Data Streaming
${GRAPH_NAME} -add postgres_db -type db -desc "Relational chat logs, users, organizations"
${GRAPH_NAME} -add redis_session_cache -type cache -desc "Active session cache and token bucket rate limits"
${GRAPH_NAME} -add vector_db -type db -desc "Qdrant / Milvus vector search for Custom GPTs and RAG"
${GRAPH_NAME} -add s3_multimodal_store -type storage -desc "User uploads, voice clips, and generated images"
${GRAPH_NAME} -add kafka_events -type queue -desc "Event stream for telemetry, audit logs, and RLHF data"

# 7. Wire Connections & Network Protocols
echo ""
echo "Connecting components..."

# Clients -> Edge CDN
${GRAPH_NAME} -connect web_client cloudflare_edge -label HTTPS
${GRAPH_NAME} -connect mobile_client cloudflare_edge -label HTTPS
${GRAPH_NAME} -connect voice_client cloudflare_edge -label WebRTC
${GRAPH_NAME} -connect api_client cloudflare_edge -label HTTPS

# Edge CDN -> API Gateway
${GRAPH_NAME} -connect cloudflare_edge api_gateway -label "mTLS WireGuard"

# API Gateway -> Core Services
${GRAPH_NAME} -connect api_gateway auth_service -label gRPC
${GRAPH_NAME} -connect api_gateway billing_service -label gRPC
${GRAPH_NAME} -connect api_gateway chat_orchestrator -label "HTTP / WebSocket"

# Auth & Billing -> Data
${GRAPH_NAME} -connect auth_service redis_session_cache -label "Session Cache"
${GRAPH_NAME} -connect auth_service postgres_db -label SQL
${GRAPH_NAME} -connect billing_service redis_session_cache -label "Token Buckets"
${GRAPH_NAME} -connect billing_service postgres_db -label "Quota Checks"

# Chat Orchestrator Dependencies
${GRAPH_NAME} -connect chat_orchestrator moderation_service -label "Pre-check"
${GRAPH_NAME} -connect chat_orchestrator redis_session_cache -label "Active Stream"
${GRAPH_NAME} -connect chat_orchestrator postgres_db -label "Chat History"
${GRAPH_NAME} -connect chat_orchestrator s3_multimodal_store -label "File Attachments"
${GRAPH_NAME} -connect chat_orchestrator agent_runtime -label "Tools & RAG"
${GRAPH_NAME} -connect chat_orchestrator inference_router -label "Token Generation"
${GRAPH_NAME} -connect chat_orchestrator kafka_events -label "Audit & RLHF"

# Agent Runtime -> Tools
${GRAPH_NAME} -connect agent_runtime vector_db -label "Semantic Search"
${GRAPH_NAME} -connect agent_runtime code_interpreter -label "Execute Python"
${GRAPH_NAME} -connect agent_runtime web_search_worker -label "Live Search"

# Inference Cluster & KV Cache
${GRAPH_NAME} -connect inference_router llm_inference_cluster -label "vLLM / TensorRT"
${GRAPH_NAME} -connect llm_inference_cluster kv_cache_cluster -label "PagedAttention"
${GRAPH_NAME} -connect llm_inference_cluster moderation_service -label "Post-filter tokens"

# 8. Export to Mermaid & Markdown
echo ""
echo "Exporting architecture diagrams..."
${GRAPH_NAME} -export mermaid -o "${MERMAID_FILE}"
${GRAPH_NAME} -export markdown -o "${MARKDOWN_FILE}"

echo ""
echo "======================================================="
echo "|                  SYSTEM TREE VIEW                   |"
echo "======================================================="
${GRAPH_NAME} -show tree

echo ""
echo "======================================================="
echo "|             EXPORTED MERMAID DIAGRAM                |"
echo "======================================================="
cat "${MERMAID_FILE}"

echo ""
echo "✨ Saved Mermaid diagram to : ${MERMAID_FILE}"
echo "✨ Saved Markdown report to : ${MARKDOWN_FILE}"
