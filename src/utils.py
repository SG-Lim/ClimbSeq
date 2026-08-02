import re
import yaml
import logging
import asyncio
import aiohttp
from typing import Dict, Any, List, Tuple

from config import config

logger = logging.getLogger(__name__)

# =============================================================================
# Global Configuration Variables 
# =============================================================================

# Network & HTTP Configuration
TCP_CONNECTOR_LIMIT = config.TCP_CONNECTOR_LIMIT
CLIENT_TIMEOUT_SECONDS = config.CLIENT_TIMEOUT_SECONDS
BATCH_RETRY_BACKOFF_SECONDS = config.BATCH_RETRY_BACKOFF_SECONDS

# LLM Generation Parameters
LLM_MAX_TOKENS = config.LLM_MAX_TOKENS
LLM_TOP_P = config.LLM_TOP_P
LLM_TOP_K = config.LLM_TOP_K
LLM_PRESENCE_PENALTY = config.LLM_PRESENCE_PENALTY
LLM_REPETITION_PENALTY = config.LLM_REPETITION_PENALTY
LLM_MIN_P = config.LLM_MIN_P

# Concurrency & Worker Limits
MAX_BATCH_WORKERS = config.MAX_BATCH_WORKERS
CHUNK_SEMAPHORE_LIMIT = config.CHUNK_SEMAPHORE_LIMIT
MAX_RETRY_WORKERS = config.MAX_RETRY_WORKERS

# Translation Defaults & Tuning
DEFAULT_DELIMITER = config.DEFAULT_DELIMITER
DEFAULT_LINES_PER_CHUNK = config.DEFAULT_LINES_PER_CHUNK
DEFAULT_MAX_ATTEMPTS = config.DEFAULT_MAX_ATTEMPTS
DEFAULT_PASS_SCORE = config.DEFAULT_PASS_SCORE
DEFAULT_INIT_TEMP = config.DEFAULT_INIT_TEMP
DEFAULT_INCREMENT_TEMP = config.DEFAULT_INCREMENT_TEMP
DEFAULT_MAX_TEMP = config.DEFAULT_MAX_TEMP

# File Paths
DEFAULT_SCAFFOLDS_PATH = config.DEFAULT_SCAFFOLDS_PATH

# =============================================================================
# Translator Client
# =============================================================================

class TranslatorClient:
    def __init__(self, settings: Dict[str, Any], scaffolds_path: str = None):
        self.api_url = settings.get("api_url")
        self.api_key = settings.get("api_key")
        self.model_name = settings.get("model_name")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self._session = None 
        path_to_use = scaffolds_path or DEFAULT_SCAFFOLDS_PATH
        try:
            with open(path_to_use, 'r', encoding='utf-8') as file:
                self.scaffolds = yaml.safe_load(file)
        except Exception as e:
            logger.error(f"Failed to load scaffolds from {path_to_use}: {e}")
            raise

    def chunk_text(self, text: str, lines_per_chunk: int = None) -> List[str]:
        """
        Divides text into chunks based on the configured delimiter.
        """
        if lines_per_chunk is None:
            lines_per_chunk = DEFAULT_LINES_PER_CHUNK
        lines = text.split(DEFAULT_DELIMITER)
        chunks = []
        for i in range(0, len(lines), lines_per_chunk):
            chunk = DEFAULT_DELIMITER.join(lines[i:i + lines_per_chunk])
            chunks.append(chunk)
        return chunks        

    async def get_session(self) -> aiohttp.ClientSession:
        """Lazily initialize the aiohttp session for connection pooling."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=CLIENT_TIMEOUT_SECONDS)
            connector = aiohttp.TCPConnector(limit=TCP_CONNECTOR_LIMIT) 
            self._session = aiohttp.ClientSession(
                headers=self.headers, 
                timeout=timeout, 
                connector=connector
            )
        return self._session

    async def close(self):
        """Helper to cleanly close the HTTP session when completely done."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def call_llm(
        self, 
        system_prompt: str = None, 
        user_prompt: str = None, 
        messages: List[Dict[str, str]] = None, 
        temperature: float = 0.0
    ) -> str:
        """
        Helper function to handle async LLM API requests. Supports raw messages for multi-turn.
        """
        session = await self.get_session()
        if messages is None:
            messages = [
                {"role": "system", "content": system_prompt or ""},
                {"role": "user", "content": user_prompt or ""}
            ]
            
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "top_p": LLM_TOP_P,
            "presence_penalty": LLM_PRESENCE_PENALTY,
            "max_tokens": LLM_MAX_TOKENS,
            "top_k": LLM_TOP_K,
            "min_p": LLM_MIN_P,
            "repetition_penalty": LLM_REPETITION_PENALTY,
        }
        
        async with session.post(f"{self.api_url}/chat/completions", json=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"API Error {response.status}: {error_text}")
            response.raise_for_status()
            data = await response.json()
            return data['choices'][0]['message']['content'].strip()

    async def evaluate(self, original: str, translation: str, target_language: str) -> Tuple[int, str]:
        """
        Evaluates translation quality, pulling a score from the LAST LaTeX \boxed{Score} macro.
        Returns the parsed integer score (1-10) or 0 if invalid/out-of-bounds, and raw response.
        """
        system_prompt = self.scaffolds['evaluation']['system']
        user_prompt = self.scaffolds['evaluation']['user'].format(
            target_language=target_language,
            original_text=original,
            translated_text=translation
        )
        try:
            response = await self.call_llm(system_prompt, user_prompt, temperature=0.0)
            matches = re.findall(r'\\boxed\{\s*([0-9.]+)\s*\}', response)
            if matches:
                raw_score = matches[-1].strip() # Take the last match in the list
                try:
                    score = int(float(raw_score))
                    if 1 <= score <= 10:
                        return score, response
                    logger.warning(f"Parsed score {score} outside valid range (1-10). Defaulting to 0.")
                except ValueError:
                    pass
            logger.warning(f"Could not parse evaluation score macro. Response: {response}")
            return 0, response
            
        except Exception as e:
            logger.warning(f"Evaluation check failed: {e}. Defaulting score to 0.")
            return 0, ""

    async def climb_sequence(
        self, 
        source_text: str, 
        target_language: str,
        lines_per_chunk: int = None,
        max_attempts: int = None,
        pass_score: int = None,
        init_temp: float = None,
        increment_temp: float = None,
        max_temp: float = None
    ) -> Dict[str, str]:
        """
        Retry logic: Translates all chunks. If the whole text fails evaluation,
        it increments the temperature and re-translates the entire sequence.
        """
        lines_per_chunk = lines_per_chunk or DEFAULT_LINES_PER_CHUNK
        max_attempts = max_attempts or DEFAULT_MAX_ATTEMPTS
        pass_score = pass_score or DEFAULT_PASS_SCORE
        init_temp = init_temp if init_temp is not None else DEFAULT_INIT_TEMP
        increment_temp = increment_temp if increment_temp is not None else DEFAULT_INCREMENT_TEMP
        max_temp = max_temp or DEFAULT_MAX_TEMP
        
        if not source_text or not source_text.strip():
            return {"new_snippet": source_text}

        lang_title = target_language.title()
        chunks = self.chunk_text(source_text, lines_per_chunk=lines_per_chunk)
        chunk_semaphore = asyncio.Semaphore(CHUNK_SEMAPHORE_LIMIT)

        attempt = 0
        highest_score = -1
        best_translation = ""

        while attempt < max_attempts:
            current_temp = min(init_temp + (attempt * increment_temp), max_temp)
            translations = [""] * len(chunks)

            async def _translate_chunk(idx: int, chunk: str):
                if not chunk.strip():
                    translations[idx] = chunk
                    return
                trans_system = self.scaffolds['translation']['system'].format(target_language=lang_title)
                trans_user = self.scaffolds['translation']['user'].format(
                    source_text=chunk, target_language=lang_title
                )
                async with chunk_semaphore:
                    translations[idx] = await self.call_llm(trans_system, trans_user, temperature=current_temp)

            # Re-translate all chunks concurrently for this attempt
            await asyncio.gather(*[_translate_chunk(i, c) for i, c in enumerate(chunks)], return_exceptions=True)

            full_translation = DEFAULT_DELIMITER.join(translations)
            
            # Evaluate the entire block
            score, _ = await self.evaluate(source_text, full_translation, lang_title)
            logger.info(f"Attempt {attempt+1}/{max_attempts}: Scored {score}/10 at temp {current_temp}")

            # Track the best score
            if score > highest_score:
                highest_score = score
                best_translation = full_translation

            # Exit early if we passed
            if highest_score >= pass_score:
                return {"new_snippet": best_translation}
            attempt += 1

        logger.warning(f"Exhausted {max_attempts} attempts. Best score: {highest_score}/10.")
        return {"new_snippet": best_translation}

    async def batch_translate(
        self, 
        source_texts: List[str], 
        target_languages: List[str],
        max_workers: int = None,
        lines_per_chunk: int = None,
        max_attempts: int = None,
        pass_score: int = None,
        init_temp: float = None,
        increment_temp: float = None,
        max_temp: float = None
    ) -> List[Dict[str, str]]:
        """
        Executes parallel verification with retries on outer API failures.
        Routes to climb_sequence or climb_chunk based on config.
        """
        max_workers = max_workers or MAX_BATCH_WORKERS
        lines_per_chunk = lines_per_chunk or DEFAULT_LINES_PER_CHUNK
        max_attempts = max_attempts or DEFAULT_MAX_ATTEMPTS
        pass_score = pass_score or DEFAULT_PASS_SCORE
        init_temp = init_temp if init_temp is not None else DEFAULT_INIT_TEMP
        increment_temp = increment_temp if increment_temp is not None else DEFAULT_INCREMENT_TEMP
        max_temp = max_temp or DEFAULT_MAX_TEMP
        batch_semaphore = asyncio.Semaphore(max_workers)

        async def _task_wrapper(s_text: str, lang: str):
            retry_count = 0
            while True:
                try:
                    async with batch_semaphore:
                        kwargs = {
                            "source_text": s_text,
                            "target_language": lang,
                            "lines_per_chunk": lines_per_chunk,
                            "max_attempts": max_attempts,
                            "pass_score": pass_score,
                            "init_temp": init_temp,
                            "increment_temp": increment_temp,
                            "max_temp": max_temp
                        }
                        return await self.climb_sequence(**kwargs)
                            
                except Exception as e:
                    retry_count += 1
                    logger.warning(f"Batch task failed: {e}. Retrying... (Attempt {retry_count})")
                    await asyncio.sleep(BATCH_RETRY_BACKOFF_SECONDS)

        payloads = list(zip(source_texts, target_languages))
        tasks = [_task_wrapper(s, l) for s, l in payloads]
        results = await asyncio.gather(*tasks)
        return list(results)