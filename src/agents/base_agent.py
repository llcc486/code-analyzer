"""智能体基类"""
from abc import ABC, abstractmethod
from typing import Optional
import httpx
from ..config import config

class BaseAgent(ABC):
    """智能体基类 - 封装LLM调用"""
    
    def __init__(self, name: str):
        self.name = name
        self.llm_config = config.llm
        self.history: list[dict] = []
    
    async def call_llm(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """调用LLM"""
        if self.llm_config.provider == "openai":
            return await self._call_openai(prompt, system_prompt)
        elif self.llm_config.provider == "anthropic":
            return await self._call_anthropic(prompt, system_prompt)
        else:
            raise ValueError(f"Unknown LLM provider: {self.llm_config.provider}")
    
    async def _call_openai(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """调用OpenAI兼容API (支持OpenAI/DeepSeek/其他兼容API)"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # 使用配置的base_url，支持DeepSeek等兼容API
        base_url = self.llm_config.openai_base_url.rstrip('/')
        
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.llm_config.openai_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.llm_config.openai_model,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 4096
                    }
                )
                
                if response.status_code == 402:
                    raise Exception("API账户余额不足，请充值后重试")
                elif response.status_code == 401:
                    raise Exception("API密钥无效，请检查配置")
                elif response.status_code == 429:
                    raise Exception("API请求频率过高，请稍后重试")
                
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            raise Exception(f"API调用失败: {e.response.status_code} - {e.response.text[:200]}")
        except httpx.TimeoutException:
            raise Exception("API请求超时，请稍后重试")
        except Exception as e:
            if "余额" in str(e) or "密钥" in str(e) or "频率" in str(e):
                raise
            raise Exception(f"API调用错误: {str(e)}")
    
    async def _call_anthropic(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """调用Anthropic API"""
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.llm_config.anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.llm_config.anthropic_model,
                    "max_tokens": 4096,
                    "system": system_prompt or "You are a helpful coding assistant.",
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]
    
    @abstractmethod
    async def execute(self, *args, **kwargs):
        """执行智能体任务"""
        pass
