"""Anthropic 兼容客户端 — 支持 Claude 原生 和 DeepSeek Anthropic 接口"""

import anthropic
from .base import BaseLLMClient
from utils.logger import logger


class AnthropicCompatClient(BaseLLMClient):
    """统一的 Anthropic Messages API 兼容客户端。
    支持任何兼容 Anthropic Messages API 的服务（Claude、DeepSeek 等）。
    """

    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = anthropic.Anthropic(**kwargs)
        self.model = model

    def chat(self, messages: list[dict], system: str = "", max_tokens: int = 2048) -> str:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )
            # 过滤 ThinkingBlock，只取 TextBlock
            for block in response.content:
                if getattr(block, "type", "") == "text":
                    return block.text
            # fallback：如果全是 ThinkingBlock，返回空
            return ""
        except anthropic.APIError as e:
            logger.error(f"API 错误: {e}")
            return f"API 调用失败: {e}"
        except Exception as e:
            logger.error(f"未知错误: {e}")
            return f"调用失败: {e}"

    def chat_stream(self, messages: list[dict], system: str = "", max_tokens: int = 2048):
        try:
            with self.client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"流式错误: {e}")
            yield f"流式输出失败: {e}"
