<div align="center">

[![Hugging Face Models](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Models-yellow)](https://huggingface.co/sglim/models)
[![Hugging Face Datasets](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Datasets-yellow)](https://huggingface.co/sglim/datasets)
[![ArXiv Publication](https://img.shields.io/badge/ArXiv-Publication-B31B1B?logo=arxiv)](https://arxiv.org/abs/2608.00533)
[![GitHub OSCD](https://img.shields.io/badge/GitHub-OSCD-blue?logo=github)](https://github.com/SG-Lim/OSCD)
[![GitHub ClimbSeq](https://img.shields.io/badge/GitHub-ClimbSeq-blue?logo=github)](https://github.com/SG-Lim/ClimbSeq)

</div>

# ClimbSeq Translator Framework

A chunk-based asynchronous agentic translator framework with sequence-level hill climbing. It translates long texts in parallel chunks, scores the combined translation using an LLM evaluator, and automatically retries the entire sequence with incrementing temperatures if the output quality falls below a specified threshold.

## Motivation

Standard full-context translation suffers from quadratic autoregressive complexity $\mathcal{O}(N^2)$ due to causal attention and accumulating generation steps; meaning generation slows down exponentially the longer the target output grows. 

ClimbSeq addresses this bottleneck by decomposing long documents into $k$ smaller, bounded chunks processed asynchronously in parallel. This bounds each sub-task to a short generation window ($n \ll N$) and shifts total wall-clock latency from single-pass quadratic generation down to:

$$\mathcal{O}\left(\max_{1 \le i \le k}(t_i) + t_{\text{eval}}\right)$$

By keeping context lengths short per request and executing them concurrently, ClimbSeq eliminates long-document generation drag while maintaining global output quality through hill-climbing evaluation. Simple yet effective 👍!

## Features

* **Chunk-Based Processing:** Automatically splits source text into manageable chunks and translates them concurrently using `aiohttp` connection pooling.
* **Global LLM Evaluation:** Evaluates the complete, stitched translation quality on a scale of 1-10 using a custom prompt scaffold.
* **Sequence Hill Climbing:** If the global translation fails the pass score, the system automatically increments the temperature and re-translates *all* chunks concurrently up to a maximum number of attempts.
* **Batch Processing:** Robust batch translation with built-in retries and constant backoff time for API failures.

## Benchmark Summary

Across Chinese, Thai, and Tamil test cases, **ClimbSeq** consistently outperforms standard single-pass vanilla translation in both throughput and output consistency using [aisingapore/Gemma-SEA-LION-v4-27B-IT](https://huggingface.co/aisingapore/Gemma-SEA-LION-v4-27B-IT).

| Method | Parameters | Avg. Score | Wall-Clock Time |
| --- | --- | --- | --- |
| **Vanilla Translation** | Single attempt ($T = 0.0$) | $8.7 \pm 3.1$ | $2,098.84\text{ s}$ |
| **ClimbSeq Translation** | Step-up retries (max $10$ attempts) | **$9.9 \pm 0.3$** | **$398.00\text{ s}$** |

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

## Credits

If you use this repository or build upon our work, please consider citing our preprint:

```bibtex
@misc{lim2026nativemultilingualchainofthoughtreasoning,
      title={Native Multilingual Chain-of-Thought Reasoning in Low-Resource Southeast Asian Languages}, 
      author={Sean Gip Lim and William Chandra Tjhi and Hai Leong Chieu},
      year={2026},
      eprint={2608.00533},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2608.00533}, 
}

```