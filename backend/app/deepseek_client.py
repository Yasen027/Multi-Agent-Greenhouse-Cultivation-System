"""轻量级 OpenAI 兼容 DeepSeek 客户端，支持 JSON 解析和重试。

客户端使用标准库 urllib，避免后端额外引入 HTTP 依赖；
未配置密钥时，调用方可以使用本地回退逻辑。
"""

import asyncio
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class DeepSeekError(RuntimeError):
    """DeepSeek 无法返回可用响应时抛出的异常。"""


# 从模型输出中提取 JSON 对象：先剥离代码块围栏，再直接解析；失败时用正则截取首个 {...} 片段。
def _json_from_text(value: str) -> Dict[str, Any]:
    text = (value or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise DeepSeekError("DeepSeek returned non-JSON content")
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise DeepSeekError("DeepSeek returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise DeepSeekError("DeepSeek JSON response must be an object")
    return parsed


# OpenAI 兼容的 DeepSeek HTTP 客户端：配置参数优先取显式值，否则回退到 DEEPSEEK_* 环境变量。
class DeepSeekClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        vision_model: Optional[str] = None,
        timeout: Optional[float] = None,
        retries: Optional[int] = None,
    ):
        # API Key：未显式传入时读 DEEPSEEK_API_KEY；为空则调用方应走本地回退。
        self.api_key = (
            api_key if api_key is not None else os.getenv("DEEPSEEK_API_KEY", "")
        )
        # Base URL 去掉末尾斜杠，避免与 /chat/completions 拼接出双斜杠。
        self.base_url = (
            base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        ).rstrip("/")
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        # 视觉模型默认复用文本模型，仅在请求携带图片时被选用。
        self.vision_model = vision_model or os.getenv(
            "DEEPSEEK_VISION_MODEL", self.model
        )
        self.timeout = float(
            timeout if timeout is not None else os.getenv("DEEPSEEK_TIMEOUT", "30")
        )
        # 重试次数下限为 0，防止负值导致循环范围异常。
        self.retries = max(
            0,
            int(retries if retries is not None else os.getenv("DEEPSEEK_RETRIES", "2")),
        )
        # 记录最近一次请求错误，供上层日志/状态展示使用。
        self.last_error: Optional[str] = None

    @property
    def available(self) -> bool:
        # 配置了 API Key 才视为可用；不可用时由调用方切换到本地回退。
        return bool(self.api_key or os.getenv("DEEPSEEK_API_KEY", ""))

    # 发起一次对话补全并强制 JSON 输出；网络/解析错误按指数退避重试，耗尽后抛错供上层回退。
    def complete_json(
        self,
        prompt: str,
        image_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        # 未配置密钥直接报错，让上层据此走本地回退。
        if not self.available:
            raise DeepSeekError("DEEPSEEK_API_KEY is not configured")
        content: Any = prompt
        # 有图片时组装多模态消息（文本 + 图片 URL），并改用视觉模型。
        if image_url:
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url}},
            ]
        # temperature 固定 0.1 并强制 JSON 输出，保证低随机性且结果可解析。
        payload = {
            "model": model or (self.vision_model if image_url else self.model),
            "messages": [{"role": "user", "content": content}],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        api_key = self.api_key or os.getenv("DEEPSEEK_API_KEY", "")
        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        # 重试循环：每次失败按 0.25 * 2^n 秒指数退避，最多重试 retries 次。
        for attempt in range(self.retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    body = json.loads(response.read().decode("utf-8"))
                # OpenAI 兼容响应结构：choices[0].message.content，可能是字符串或分段列表。
                message = body.get("choices", [{}])[0].get("message", {})
                content_value = (
                    message.get("content", "") if isinstance(message, dict) else ""
                )
                if isinstance(content_value, list):
                    content_value = "".join(
                        str(part.get("text", ""))
                        for part in content_value
                        if isinstance(part, dict)
                    )
                # 将模型输出解析为 JSON 对象；解析失败同样进入重试。
                result = _json_from_text(str(content_value))
                self.last_error = None
                return result
            # 统一捕获网络、超时与解析类异常，最终转为 DeepSeekError 抛出。
            except (
                urllib.error.URLError,
                urllib.error.HTTPError,
                TimeoutError,
                OSError,
                ValueError,
                DeepSeekError,
            ) as exc:
                self.last_error = str(exc)
                # 还有重试机会时退避等待后继续；否则记录日志并抛出，提示上层使用本地回退。
                if attempt < self.retries:
                    time.sleep(0.25 * (2**attempt))
                    continue
                logger.warning(
                    "DeepSeek request failed; local fallback will be used: %s", exc
                )
                raise DeepSeekError(str(exc)) from exc
        raise DeepSeekError("DeepSeek request failed")

    async def complete_json_async(
        self,
        prompt: str,
        image_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        # 在线程池中执行同步阻塞请求，避免阻塞事件循环。
        return await asyncio.to_thread(self.complete_json, prompt, image_url, model)


# 进程级单例：各 Agent 与决策服务复用同一客户端配置。
deepseek_client = DeepSeekClient()
