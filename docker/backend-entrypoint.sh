#!/bin/bash
# =============================================================================
# Backend Server Entrypoint
# =============================================================================
# This script manages the Reverie backend simulation server.
# It can run in interactive mode or automated mode.
# =============================================================================

set -e

# Change to backend server directory
cd /app/reverie/backend_server

# Ensure storage directories exist
mkdir -p ../../environment/frontend_server/storage
mkdir -p ../../environment/frontend_server/temp_storage
mkdir -p ../../environment/frontend_server/compressed_storage

# Check if OpenAI API key is set
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "<Your OpenAI API>" ]; then
    echo "WARNING: OPENAI_API_KEY is not set or is using default value."
    echo "Please set the OPENAI_API_KEY environment variable."
    if [ "$ENABLE_TEXTGEN_FALLBACK" != "true" ] && [ "$ENABLE_TEXTGEN_FALLBACK" != "True" ]; then
        echo "ERROR: No LLM backend available. Set OPENAI_API_KEY or enable TEXTGEN_FALLBACK."
        exit 1
    fi
fi

# Display configuration
echo "==================================================="
echo "Reverie Backend Server"
echo "==================================================="
echo "OpenAI Model: ${OPENAI_CHAT_MODEL:-gpt-3.5-turbo}"
echo "Embedding Model: ${OPENAI_EMBEDDING_MODEL:-text-embedding-ada-002}"
echo "TextGen Fallback: ${ENABLE_TEXTGEN_FALLBACK:-False}"
echo "Debug Mode: ${REVERIE_DEBUG:-False}"
echo "==================================================="

# Run the reverie server
if [ -z "$AUTO_SIMULATION" ]; then
    # Interactive mode - requires TTY
    exec python reverie.py
else
    # Automated mode - for scripted simulations
    echo "Running automated simulation: $AUTO_SIMULATION"
    echo -e "$AUTO_FORK_SIM\n$AUTO_NEW_SIM\nrun $AUTO_STEPS\nfin" | python reverie.py
fi
