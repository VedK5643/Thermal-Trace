"""
LLM Provider Abstraction & Gemini Provider Implementation.
Implements multi-turn tool-calling loop using Gemini REST API / httpx.
"""
import json
import logging
import httpx
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.llm.prompts import SYSTEM_PROMPT
from app.services.llm.tools import TOOL_DECLARATIONS, ToolExecutor

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        executor: ToolExecutor,
        max_tool_iterations: int = 5
    ) -> Dict[str, Any]:
        """Runs multi-turn chat generation with dynamic tool calling."""
        pass


class GeminiProvider(LLMProvider):
    """Gemini Flash LLM Provider implementation using REST API."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.llm_model or "gemini-1.5-flash"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        executor: ToolExecutor,
        max_tool_iterations: int = 5
    ) -> Dict[str, Any]:
        if not self.api_key:
            logger.warning("Gemini API key not configured. Returning unconfigured fallback response.")
            return {
                "message": "Gemini API key is not configured in backend environment (.env). Please set GEMINI_API_KEY.",
                "tool_calls": [],
                "metadata": {"provider": "gemini", "model": self.model, "status": "unconfigured"}
            }

        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"

        # 1. Build initial request payload
        contents = []
        for msg in messages:
            role = "user" if msg.get("role") in ("user", "human") else "model"
            contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})

        payload: Dict[str, Any] = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": contents,
            "tools": [{"function_declarations": TOOL_DECLARATIONS}]
        }

        executed_tool_calls = []
        iterations = 0

        async with httpx.AsyncClient(timeout=30.0) as client:
            while iterations < max_tool_iterations:
                iterations += 1
                try:
                    resp = await client.post(url, json=payload)
                    resp_json = resp.json()

                    if resp.status_code != 200:
                        logger.error(f"Gemini API HTTP Error {resp.status_code}: {resp_json}")
                        return {
                            "message": f"Gemini API returned error: {resp_json.get('error', {}).get('message', 'API Error')}",
                            "tool_calls": executed_tool_calls,
                            "metadata": {"provider": "gemini", "model": self.model, "status": "error"}
                        }

                    candidates = resp_json.get("candidates", [])
                    if not candidates:
                        return {
                            "message": "No response returned from Gemini API.",
                            "tool_calls": executed_tool_calls,
                            "metadata": {"provider": "gemini", "model": self.model, "status": "empty"}
                        }

                    first_candidate = candidates[0]
                    content_block = first_candidate.get("content", {})
                    parts = content_block.get("parts", [])

                    # Check for tool call vs text response
                    function_call_part = None
                    text_parts = []

                    for part in parts:
                        if "functionCall" in part:
                            function_call_part = part["functionCall"]
                        elif "text" in part:
                            text_parts.append(part["text"])

                    if function_call_part:
                        tool_name = function_call_part.get("name")
                        tool_args = function_call_part.get("args", {})
                        logger.info(f"LLM requested tool call '{tool_name}' with args {tool_args}")

                        # Execute tool
                        tool_result = await executor.execute_tool(tool_name, tool_args)
                        executed_tool_calls.append({"name": tool_name, "args": tool_args, "result": tool_result})

                        # Update conversation history with model's content block (preserving thought_signature if present)
                        payload["contents"].append(content_block)
                        payload["contents"].append({
                            "role": "user",
                            "parts": [{
                                "functionResponse": {
                                    "name": tool_name,
                                    "response": {"name": tool_name, "content": tool_result}
                                }
                            }]
                        })
                    else:
                        # Final text response from model
                        final_text = "\n".join(text_parts) if text_parts else "No response text generated."
                        return {
                            "message": final_text,
                            "tool_calls": executed_tool_calls,
                            "metadata": {
                                "provider": "gemini",
                                "model": self.model,
                                "iterations": iterations,
                                "status": "success"
                            }
                        }

                except Exception as e:
                    logger.error(f"LLM Provider Exception: {e}", exc_info=True)
                    return {
                        "message": f"Error communicating with LLM Provider: {str(e)}",
                        "tool_calls": executed_tool_calls,
                        "metadata": {"provider": "gemini", "model": self.model, "status": "exception"}
                    }

        return {
            "message": "Maximum tool call iterations reached.",
            "tool_calls": executed_tool_calls,
            "metadata": {"provider": "gemini", "model": self.model, "status": "max_iterations"}
        }


class OpenRouterProvider(LLMProvider):
    """OpenRouter LLM Provider implementation using OpenAI-compatible REST API."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.openrouter_api_key
        self.model = model or settings.llm_model or "google/gemini-2.5-flash"
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        executor: ToolExecutor,
        max_tool_iterations: int = 5
    ) -> Dict[str, Any]:
        if not self.api_key:
            logger.warning("OpenRouter API key not configured. Returning unconfigured fallback response.")
            return {
                "message": "OpenRouter API key is not configured in backend environment (.env). Please set OPENROUTER_API_KEY.",
                "tool_calls": [],
                "metadata": {"provider": "openrouter", "model": self.model, "status": "unconfigured"}
            }

        # Transform messages for OpenAI format
        formatted_messages = []
        formatted_messages.append({"role": "system", "content": SYSTEM_PROMPT})
        
        for msg in messages:
            role = msg.get("role", "user")
            # Ensure roles are 'user' or 'assistant'
            if role == "human": role = "user"
            elif role == "model": role = "assistant"
            formatted_messages.append({"role": role, "content": msg.get("content", "")})

        # Transform tools
        openai_tools = [{"type": "function", "function": tool} for tool in TOOL_DECLARATIONS]

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": formatted_messages,
            "tools": openai_tools,
            "tool_choice": "auto",
            "max_tokens": 8192
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": settings.frontend_origin,
            "X-Title": "ThermalTrace AI"
        }

        executed_tool_calls = []
        iterations = 0

        async with httpx.AsyncClient(timeout=45.0) as client:
            while iterations < max_tool_iterations:
                iterations += 1
                try:
                    resp = await client.post(self.base_url, headers=headers, json=payload)
                    
                    if resp.status_code != 200:
                        try:
                            resp_json = resp.json()
                            error_msg = resp_json.get('error', {}).get('message', 'API Error')
                        except Exception:
                            error_msg = resp.text
                        logger.error(f"OpenRouter API HTTP Error {resp.status_code}: {error_msg}")
                        return {
                            "message": f"OpenRouter API returned error: {error_msg}",
                            "tool_calls": executed_tool_calls,
                            "metadata": {"provider": "openrouter", "model": self.model, "status": "error"}
                        }

                    resp_json = resp.json()
                    choices = resp_json.get("choices", [])
                    if not choices:
                        return {
                            "message": "No response returned from OpenRouter API.",
                            "tool_calls": executed_tool_calls,
                            "metadata": {"provider": "openrouter", "model": self.model, "status": "empty"}
                        }

                    message_obj = choices[0].get("message", {})
                    tool_calls = message_obj.get("tool_calls", [])
                    content = message_obj.get("content", "")

                    if tool_calls:
                        # We have tool calls
                        # Append the assistant's message with the tool_calls to the conversation
                        payload["messages"].append(message_obj)
                        
                        for tc in tool_calls:
                            if tc.get("type") != "function":
                                continue
                            
                            func_obj = tc.get("function", {})
                            tool_name = func_obj.get("name")
                            args_str = func_obj.get("arguments", "{}")
                            try:
                                tool_args = json.loads(args_str)
                            except json.JSONDecodeError:
                                tool_args = {}
                                
                            logger.info(f"LLM requested tool call '{tool_name}' with args {tool_args}")

                            # Execute tool
                            tool_result = await executor.execute_tool(tool_name, tool_args)
                            executed_tool_calls.append({"name": tool_name, "args": tool_args, "result": tool_result})
                            
                            # Append tool response
                            payload["messages"].append({
                                "role": "tool",
                                "tool_call_id": tc.get("id"),
                                "content": json.dumps(tool_result)
                            })
                    else:
                        # Final text response
                        return {
                            "message": content or "No response text generated.",
                            "tool_calls": executed_tool_calls,
                            "metadata": {
                                "provider": "openrouter",
                                "model": self.model,
                                "iterations": iterations,
                                "status": "success"
                            }
                        }

                except httpx.TimeoutException as e:
                    logger.error(f"OpenRouter API Timeout: {e}", exc_info=True)
                    return {
                        "message": "The AI provider timed out. Please try again.",
                        "tool_calls": executed_tool_calls,
                        "metadata": {"provider": "openrouter", "model": self.model, "status": "timeout"}
                    }
                except Exception as e:
                    logger.error(f"LLM Provider Exception: {e}", exc_info=True)
                    return {
                        "message": f"Error communicating with LLM Provider: {str(e)}",
                        "tool_calls": executed_tool_calls,
                        "metadata": {"provider": "openrouter", "model": self.model, "status": "exception"}
                    }

        return {
            "message": "Maximum tool call iterations reached.",
            "tool_calls": executed_tool_calls,
            "metadata": {"provider": "openrouter", "model": self.model, "status": "max_iterations"}
        }


def get_llm_provider() -> LLMProvider:
    """Factory function returning configured LLMProvider instance."""
    provider_type = settings.llm_provider.lower()
    if provider_type == "openrouter":
        return OpenRouterProvider()
    elif provider_type == "gemini":
        return GeminiProvider()
    else:
        # Fallback default
        return OpenRouterProvider()

