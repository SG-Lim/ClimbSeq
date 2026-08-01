import argparse

class AppConfig:
    """Central configuration for the translation client."""

    # Network & HTTP Configuration
    TCP_CONNECTOR_LIMIT: int = 5120
    CLIENT_TIMEOUT_SECONDS: int = 1800
    BATCH_RETRY_BACKOFF_SECONDS: int = 1

    # LLM Generation Parameters
    LLM_MAX_TOKENS: int = 8192
    LLM_TOP_P: float = 0.95
    LLM_TOP_K: int = 20
    LLM_PRESENCE_PENALTY: float = 1.5
    LLM_REPETITION_PENALTY: float = 1.0
    LLM_MIN_P: float = 0.0

    # Concurrency & Worker Limits
    MAX_BATCH_WORKERS: int = 512
    CHUNK_SEMAPHORE_LIMIT: int = 5
    MAX_RETRY_WORKERS: int = 5

    # Translation Defaults & Tuning
    DEFAULT_DELIMITER: str = "\n\n"
    DEFAULT_LINES_PER_CHUNK: int = 10
    DEFAULT_MAX_ATTEMPTS: int = 10
    DEFAULT_PASS_SCORE: int = 8
    DEFAULT_INIT_TEMP: float = 0.0
    DEFAULT_INCREMENT_TEMP: float = 0.1
    DEFAULT_MAX_TEMP: float = 0.4

    # File Paths
    DEFAULT_SCAFFOLDS_PATH: str = "src/scaffolds.yaml"

    @classmethod
    def add_cli_arguments(cls, parser: argparse.ArgumentParser):
        """Attaches configuration variables to an argparse parser."""
        group = parser.add_argument_group("Translation Client Configuration")
        
        # Network & HTTP Configuration
        group.add_argument("--tcp-connector-limit", type=int, default=cls.TCP_CONNECTOR_LIMIT, 
                           help="Maximum number of simultaneous TCP connections in the aiohttp connection pool.")
        group.add_argument("--client-timeout-seconds", type=int, default=cls.CLIENT_TIMEOUT_SECONDS, 
                           help="Total timeout in seconds for HTTP requests before giving up.")
        group.add_argument("--batch-retry-backoff", type=int, default=cls.BATCH_RETRY_BACKOFF_SECONDS, 
                           help="How long to wait (in seconds) before retrying a failed batch request due to an outer API error.")

        # LLM Generation Parameters
        group.add_argument("--llm-max-tokens", type=int, default=cls.LLM_MAX_TOKENS, 
                           help="The maximum number of tokens the model is allowed to generate in a single response.")
        group.add_argument("--llm-top-p", type=float, default=cls.LLM_TOP_P, 
                           help="Nucleus sampling threshold. Lowers the probability of choosing less likely tokens.")
        group.add_argument("--llm-top-k", type=int, default=cls.LLM_TOP_K, 
                           help="Limits the generated tokens to the top K most likely options.")
        group.add_argument("--llm-presence-penalty", type=float, default=cls.LLM_PRESENCE_PENALTY, 
                           help="Penalizes new tokens based on whether they appear in the text so far (encourages new topics).")
        group.add_argument("--llm-repetition-penalty", type=float, default=cls.LLM_REPETITION_PENALTY, 
                           help="Penalizes new tokens based on their existing frequency in the text (discourages repetition).")
        group.add_argument("--llm-min-p", type=float, default=cls.LLM_MIN_P, 
                           help="Minimum probability threshold relative to the most likely token (alternative to Top-P).")

        # Concurrency & Worker Limits
        group.add_argument("--batch-workers", type=int, default=cls.MAX_BATCH_WORKERS, 
                           help="Maximum number of concurrent documents to process in batch_translate.")
        group.add_argument("--chunk-concurrency", type=int, default=cls.CHUNK_SEMAPHORE_LIMIT, 
                           help="Concurrency limit for processing chunks within a single document translation to prevent API surges.")
        group.add_argument("--max-retry-workers", type=int, default=cls.MAX_RETRY_WORKERS, 
                           help="Maximum number of async workers spawned to handle chunks that failed the diagnostic check.")

        # Translation Defaults & Tuning
        group.add_argument("--delimiter", type=str, default=cls.DEFAULT_DELIMITER, 
                           help="String delimiter used to separate chunks/lines in document processing.")        
        group.add_argument("--lines-per-chunk", type=int, default=cls.DEFAULT_LINES_PER_CHUNK, 
                           help="Default number of lines to process in a single chunk.")
        group.add_argument("--max-attempts", type=int, default=cls.DEFAULT_MAX_ATTEMPTS, 
                           help="Maximum number of evaluation/retry cycles before accepting the best available translation.")
        group.add_argument("--pass-score", type=int, default=cls.DEFAULT_PASS_SCORE, 
                           help="The threshold score (out of 10) required to exit the retry loop early.")
        group.add_argument("--init-temp", type=float, default=cls.DEFAULT_INIT_TEMP,
                           help="Starting temperature for generation attempts.")
        group.add_argument("--increment-temp", type=float, default=cls.DEFAULT_INCREMENT_TEMP,
                           help="Temperature increment per retry attempt.")
        group.add_argument("--max-temp", type=float, default=cls.DEFAULT_MAX_TEMP, 
                           help="The maximum temperature reached during escalating retries.")

        # File Paths
        group.add_argument("--scaffolds-path", type=str, default=cls.DEFAULT_SCAFFOLDS_PATH, 
                           help="Path to the YAML file containing system and user prompt templates.")

    @classmethod
    def update_from_args(cls, args: argparse.Namespace):
        """Updates the configuration state based on parsed command line arguments."""
        # Network & HTTP
        if hasattr(args, 'tcp_connector_limit'): cls.TCP_CONNECTOR_LIMIT = args.tcp_connector_limit
        if hasattr(args, 'client_timeout_seconds'): cls.CLIENT_TIMEOUT_SECONDS = args.client_timeout_seconds
        if hasattr(args, 'batch_retry_backoff'): cls.BATCH_RETRY_BACKOFF_SECONDS = args.batch_retry_backoff
        
        # LLM Generation
        if hasattr(args, 'llm_max_tokens'): cls.LLM_MAX_TOKENS = args.llm_max_tokens
        if hasattr(args, 'llm_top_p'): cls.LLM_TOP_P = args.llm_top_p
        if hasattr(args, 'llm_top_k'): cls.LLM_TOP_K = args.llm_top_k
        if hasattr(args, 'llm_presence_penalty'): cls.LLM_PRESENCE_PENALTY = args.llm_presence_penalty
        if hasattr(args, 'llm_repetition_penalty'): cls.LLM_REPETITION_PENALTY = args.llm_repetition_penalty
        if hasattr(args, 'llm_min_p'): cls.LLM_MIN_P = args.llm_min_p
        
        # Concurrency
        if hasattr(args, 'batch_workers'): cls.MAX_BATCH_WORKERS = args.batch_workers
        if hasattr(args, 'chunk_concurrency'): cls.CHUNK_SEMAPHORE_LIMIT = args.chunk_concurrency
        if hasattr(args, 'max_retry_workers'): cls.MAX_RETRY_WORKERS = args.max_retry_workers
        
        # Defaults & Tuning
        if hasattr(args, 'delimiter'): cls.DEFAULT_DELIMITER = args.delimiter.encode('utf-8').decode('unicode_escape')
        if hasattr(args, 'lines_per_chunk'): cls.DEFAULT_LINES_PER_CHUNK = args.lines_per_chunk
        if hasattr(args, 'max_attempts'): cls.DEFAULT_MAX_ATTEMPTS = args.max_attempts
        if hasattr(args, 'pass_score'): cls.DEFAULT_PASS_SCORE = args.pass_score
        if hasattr(args, 'init_temp'): cls.DEFAULT_INIT_TEMP = args.init_temp
        if hasattr(args, 'increment_temp'): cls.DEFAULT_INCREMENT_TEMP = args.increment_temp
        if hasattr(args, 'max_temp'): cls.DEFAULT_MAX_TEMP = args.max_temp
        
        # Paths
        if hasattr(args, 'scaffolds_path'): cls.DEFAULT_SCAFFOLDS_PATH = args.scaffolds_path

# Global configuration instance
config = AppConfig()