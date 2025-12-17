"""配置管理模块"""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

class LLMConfig(BaseModel):
    provider: str = os.getenv("LLM_PROVIDER", "openai")
    openai_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    anthropic_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")

class FuzzerConfig(BaseModel):
    timeout: int = int(os.getenv("FUZZER_TIMEOUT", "60"))
    max_iterations: int = int(os.getenv("MAX_ITERATIONS", "1000"))
    coverage_threshold: float = float(os.getenv("COVERAGE_THRESHOLD", "80"))

class AppConfig(BaseModel):
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # 路径配置
    base_dir: Path = Path(__file__).parent.parent
    output_dir: Path = base_dir / "output"
    harness_dir: Path = output_dir / "harness"
    exception_dir: Path = output_dir / "exception"
    corpus_dir: Path = output_dir / "corpus"

    llm: LLMConfig = LLMConfig()
    fuzzer: FuzzerConfig = FuzzerConfig()

config = AppConfig()

# 确保输出目录存在
for d in [config.output_dir, config.harness_dir, config.exception_dir, config.corpus_dir]:
    d.mkdir(parents=True, exist_ok=True)
