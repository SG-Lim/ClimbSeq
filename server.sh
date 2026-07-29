#!/bin/bash

# Capture LAN IP and Select Port
HOST_IP=$(ip route get 1 | awk '{print $7;exit}')
PORT=9000
while [ -n "$(ss -tan4H "sport = $PORT")" ]; do
    echo "⚠️ Port $PORT is occupied. Trying $((PORT+1))..."
    PORT=$((PORT+1))
done

# Extract variables from .env
# Make sure your .env file contains TRANSLATOR_MODEL and VLLM_API_KEY
MODEL_PATH=$(grep "^TRANSLATOR_MODEL=" .env | cut -d '=' -f2- | tr -d '"')
API_KEY=$(grep "^VLLM_API_KEY=" .env | cut -d '=' -f2- | tr -d '"')
URL="http://$HOST_IP:$PORT/v1"

# Write to .secret file using tmp file + mv 
echo "Updating .secret file..."
{
    echo "TRANSLATOR_URL=$URL"
    echo "TRANSLATOR_MODEL_NAME=$MODEL_PATH"
    echo "TRANSLATOR_API_KEY=$API_KEY"
} > .secret.tmp && mv .secret.tmp .secret

# Hardware setup: Set which GPU(s) to use. Defaults to 0 if not set in the environment.
export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0}
export VLLM_WORKER_MULTIPROC_METHOD=spawn

# Launch vLLM
nohup uv run python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL_PATH" \
    --gpu-memory-utilization 0.8 \
    --tensor-parallel-size 1 \
    --api-key "$API_KEY" \
    --host 0.0.0.0 \
    --port $PORT >> vllm.log 2>&1 &

echo "✅ vLLM is starting on $HOST_IP:$PORT"
echo "🌐 API is reachable at: $URL"