"""LLM 工厂 — 根据配置自动选择合适的客户端"""

import os
# 确保 config 先加载，触发 dotenv
import config as _  # noqa: F401

from .base import BaseLLMClient
from .anthropic_client import AnthropicCompatClient
from utils.logger import logger

_llm: BaseLLMClient | None = None


def get_llm(force_provider: str | None = None) -> BaseLLMClient:
    """获取 LLM 客户端单例。
    优先级：force_provider > LLM_PROVIDER 环境变量 > 自动检测（有哪个 key 用哪个）
    """
    global _llm
    if _llm is not None:
        return _llm

    provider = force_provider or os.getenv("LLM_PROVIDER", "")

    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
    claude_key = os.getenv("ANTHROPIC_API_KEY", "")

    if provider == "deepseek" and deepseek_key:
        _llm = _make_deepseek()
    elif provider == "claude" and claude_key:
        _llm = _make_claude()
    elif deepseek_key:
        logger.info("自动选择 DeepSeek 作为 LLM 提供商")
        _llm = _make_deepseek()
    elif claude_key:
        logger.info("自动选择 Claude 作为 LLM 提供商")
        _llm = _make_claude()
    else:
        raise RuntimeError(
            "未配置任何 LLM API Key！请在 .env 文件中设置 DEEPSEEK_API_KEY 或 ANTHROPIC_API_KEY"
        )

    logger.info(f"LLM 客户端: {_llm.__class__.__name__} (model={_llm.model})")
    return _llm


def _make_deepseek():
    """创建 DeepSeek 客户端（走 Anthropic 兼容接口）"""
    return AnthropicCompatClient(
        api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        model=os.getenv("DEEPSEEK_MODEL", "DeepSeek-V4-pro[1m]"),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/anthropic"),
    )


def _make_claude():
    """创建 Claude 客户端"""
    return AnthropicCompatClient(
        api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        base_url=None,  # 使用 Anthropic 默认地址
    )


def switch_provider(provider: str):
    """切换 LLM 提供商（重新创建客户端）"""
    global _llm
    _llm = None
    return get_llm(force_provider=provider)
