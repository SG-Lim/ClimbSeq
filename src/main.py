import os
import time
import json
import asyncio
import logging
import argparse
from typing import Dict, Any, List

from config import config
from utils import TranslatorClient 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def load_secrets(filepath: str = ".secret") -> Dict[str, str]:
    secrets = {}
    if not os.path.exists(filepath):
        logger.warning(f"{filepath} not found. Falling back to default or OS env variables.")
        return secrets
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                secrets[key.strip()] = value.strip()
    return secrets


class AppConfig:
    """Encapsulates all application settings, CLI arguments, and secrets."""
    def __init__(
        self, 
        input_path: str, 
        output_dir: str, 
        target_languages: List[str], 
        secrets_path: str = ".secret"
    ):
        self.target_languages = target_languages
        self.args = self._parse_args(input_path, output_dir)
        self.secrets = load_secrets(secrets_path)

    def _parse_args(self, default_input: str, default_output: str) -> argparse.Namespace:
        parser = argparse.ArgumentParser(description="Multi-language Batch Translation for Text Lines.")
        parser.add_argument(
            "--input_path", type=str, 
            default=default_input,
            help="Path to the input text file"
        )
        parser.add_argument(
            "--output_dir", type=str, 
            default=default_output,
            help="Directory to save the translated output files"
        )
        config.add_cli_arguments(parser)
        args = parser.parse_args()
        config.update_from_args(args)
        return args

    @property
    def client_settings(self) -> Dict[str, Any]:
        """Returns the dictionary required to initialize the TranslatorClient."""
        return {
            "api_url": self.secrets.get("TRANSLATOR_URL"),
            "api_key": self.secrets.get("TRANSLATOR_API_KEY"),
            "model_name": self.secrets.get("TRANSLATOR_MODEL_NAME")
        }


async def run_pipeline(app_config: AppConfig):
    """Executes the core translation I/O pipeline using the provided configuration."""
    pipeline_start_time = time.perf_counter()  # Start pipeline timer
    texts_to_translate = []
    
    # Read the extracted plain strings, unescaping them for accurate translation
    with open(app_config.args.input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                # Wrap the line back in quotes to use json.loads and properly unescape \n, \", etc.
                original_text = json.loads(f'"{line}"')
                texts_to_translate.append(original_text)
            except json.JSONDecodeError:
                logger.warning("Could not unescape line, appending raw text instead.")
                texts_to_translate.append(line)
                
    logger.info(f"Loaded {len(texts_to_translate)} records from: {app_config.args.input_path}")
    client_settings = app_config.client_settings
    logger.info(f"Initializing TranslatorClient with model '{client_settings['model_name']}' at {client_settings['api_url']}")
    client = TranslatorClient(settings=client_settings)

    try:
        os.makedirs(app_config.args.output_dir, exist_ok=True)
        
        for lang_name in app_config.target_languages:
            lang_start_time = time.perf_counter()  # Start per-language timer
            logger.info(f"Starting translation pass for: {lang_name.upper()}")
            
            lang_payload = [lang_name] * len(texts_to_translate)
            results = await client.batch_translate(
                source_texts=texts_to_translate,
                target_languages=lang_payload
            )

            translated_texts = [res.get("summary", "").strip() for res in results]
            failed_count = sum(1 for text in translated_texts if not text)
            if failed_count > 0:
                logger.warning(f"{failed_count} items resulted in empty translations for {lang_name}.")

            # Save to separate file (e.g., chinese_output.jsonl)
            output_filename = f"{lang_name.lower()}_output.jsonl"
            output_filepath = os.path.join(app_config.args.output_dir, output_filename)
            
            logger.info(f"Saving {len(translated_texts)} processed records to: {output_filepath}")
            with open(output_filepath, "w", encoding="utf-8") as f:
                for trans_text in translated_texts:
                    # Escape internal newlines/quotes and strip outer quotes [1:-1]
                    escaped_trans_text = json.dumps(trans_text, ensure_ascii=False)[1:-1]
                    f.write(escaped_trans_text + "\n")
            
            # Calculate and log per-language duration
            lang_elapsed = time.perf_counter() - lang_start_time
            logger.info(f"Completed {lang_name.upper()} translation pass in {lang_elapsed:.2f} seconds.")

        # Calculate and log total pipeline duration
        total_elapsed = time.perf_counter() - pipeline_start_time
        logger.info(f"Batch translation pipeline complete in {total_elapsed:.2f} seconds.")

    finally:
        await client.close()


async def main(input_path: str, output_dir: str, target_languages: List[str]):
    app_config = AppConfig(
        input_path=input_path,
        output_dir=output_dir,
        target_languages=target_languages
    )
    await run_pipeline(app_config)


if __name__ == "__main__":
    # ==========================================
    # Pipeline Configuration
    # ==========================================
    INPUT_PATH = "data/input.jsonl"
    OUTPUT_DIR = "data/"
    
    TARGET_LANGUAGES = [
        "Chinese",
        "Thai",
        "Tamil",
    ]
    
    asyncio.run(main(
        input_path=INPUT_PATH,
        output_dir=OUTPUT_DIR,
        target_languages=TARGET_LANGUAGES
    ))