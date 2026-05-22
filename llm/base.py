"""LLM 客户端抽象基类"""

from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    @abstractmethod
    def chat(self, messages: list[dict], system: str = "", max_tokens: int = 2048) -> str:
        """发送聊天请求，返回文本回复"""
        ...

    @abstractmethod
    def chat_stream(self, messages: list[dict], system: str = "", max_tokens: int = 2048):
        """流式聊天，返回 generator"""
        ...
