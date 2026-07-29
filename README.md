# climbseq

A chunk-based asynchronous agentic translator with sequence-level hill climbing. It translates long texts in parallel chunks, scores the combined translation using an LLM evaluator, and automatically retries the entire sequence with incrementing temperatures if the output quality falls below a specified threshold.

By processing $k$ chunks in parallel, total wall-clock latency drops from sequential $\mathcal{O}(\sum_{i=1}^{k} t_i)$ to $\mathcal{O}(\max(t_i) + t_{eval})$, drastically accelerating the auto-regressive translation process of long documents. Simple yet effective 👍!

## Features

* **Chunk-Based Processing:** Automatically splits source text into manageable chunks and translates them concurrently using `aiohttp` connection pooling.
* **Global LLM Evaluation:** Evaluates the complete, stitched translation quality on a scale of 1-10 using a custom prompt scaffold.
* **Sequence Hill Climbing:** If the global translation fails the pass score, the system automatically increments the temperature and re-translates *all* chunks concurrently up to a maximum number of attempts.
* **Batch Processing:** Robust batch translation with built-in retries and constant backoff time for API failures.

## Prerequisites

* Python >= 3.12
* [uv](https://github.com/astral-sh/uv) package manager
* An OpenAI-compatible API endpoint or a local GPU for vLLM.

## Installation

Initialize the environment and sync dependencies using `uv`:

```bash
uv venv
uv sync

```

## Server Setup (vLLM)

If you are running the LLM locally using vLLM, you can use the provided startup script (`server.sh`). This script automatically finds an open port, configures the environment, and generates a `.secret` file that `climbseq` can use for configuration.

**1. Create a `.env` file:**
In the root directory, create a `.env` file with your model path and a custom API key:

```env
TRANSLATOR_MODEL="your-model-name-or-local-path"
VLLM_API_KEY="your-custom-api-key"

```

**2. Start the vLLM server:**
Make the script executable and run it:

```bash
chmod +x server.sh
./server.sh

```

This will launch the vLLM server in the background (logging to `vllm.log`) and generate a `.secret` file containing the `TRANSLATOR_URL`, `TRANSLATOR_MODEL_NAME`, and `TRANSLATOR_API_KEY` for your client settings.

## Usage

Once your server is running and your `.secret` or `settings` dictionary is configured, run the main application script:

```bash
uv run src/main.py

```