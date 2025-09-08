# lm_studio_client.py
import requests
import logging
from typing import List, Dict, Any, Optional
from .config import LM_STUDIO_BASE_URL, LM_STUDIO_API_KEY

logger = logging.getLogger("lmstudio")

class LMStudioClient:
    """
    Minimal OpenAI-compatible client for LM Studio (chat + embeddings).
    Uses requests to talk to /v1/chat/completions and /v1/embeddings.
    """

    def __init__(self, base_url: str = LM_STUDIO_BASE_URL, api_key: str = LM_STUDIO_API_KEY, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _post(self, path: str, payload: dict) -> dict:
        url = f"{self.base_url}{path}"
        try:
            r = requests.post(url, json=payload, headers=self.headers, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            logger.exception("Request to LM Studio failed: %s", e)
            raise

    # --- embeddings ---
    def embed_texts(self, texts: List[str], model: str = "text-embedding-3-small") -> List[List[float]]:
        """
        Call embeddings endpoint. model name may vary by LMStudio install; adjust accordingly.
        Returns: list of embeddings (list of floats).
        """
        payload = {
            "model": model,
            "input": texts
        }
        resp = self._post("/v1/embeddings", payload)
        # Response format assumed: {'data': [{'embedding': [...], 'index': 0}, ...], ...}
        embeddings = [d["embedding"] for d in resp.get("data", [])]
        return embeddings

    # --- chat completions (for generating RAG responses or classification via prompt) ---
    def chat(self, messages: List[Dict[str, str]], model: str = "gpt-4o-mini", temperature: float = 0.2, max_tokens: int = 512) -> Dict[str, Any]:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        resp = self._post("/v1/chat/completions", payload)
        # assumed response: {'choices': [{'message': {'role':'assistant','content':'...'}}], ...}
        return resp

    def classify_content_via_llm(self, text: str, labels: List[str] = ["personality", "experience"]) -> Dict[str, Any]:
        """
        Use an LLM prompt to classify text into 'personality' or 'experience', returning label and confidence-like score.
        Note: LLM-based confidence is heuristic (we extract numeric if provided).
        """
        system = (
            "あなたは短いテキストを「人格情報(personality)」か「体験情報(experience)」に分類するアシスタントです。"
            " 出力は必ずJSONのみで返してください： {\"label\":\"personality|experience\", \"score\":0.0, \"reason\":\"...\"}"
            " scoreは0.0〜1.0の推定信頼度で簡潔に答えてください。"
        )
        user_msg = f"テキストを分類してください:\n\n\"\"\"\n{text}\n\"\"\"\n\n"
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg}
        ]
        resp = self.chat(messages, temperature=0.0, max_tokens=200)
        # extract assistant content
        try:
            assistant = resp["choices"][0]["message"]["content"]
            import json
            parsed = json.loads(assistant)
            return parsed
        except Exception:
            # fallback: return naive default if parsing fails
            return {"label": "personality", "score": 0.5, "reason": "parsing_failed; returned fallback"}

    def generate_response(self, query: str, context: str, model: str = "gpt-4o-mini", temperature: float = 0.2, max_tokens: int = 512) -> str:
        """
        Simple RAG-style prompt: system prompt sets behavior, context is appended.
        """
        system = "あなたは知識ベースと会話文脈を統合して正確で簡潔な回答を作成するアシスタントです。"
        user = f"Context:\n{context}\n\nQuestion:\n{query}\n\nAnswer concisely and cite context snippets if helpful."
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
        resp = self.chat(messages, model=model, temperature=temperature, max_tokens=max_tokens)
        return resp["choices"][0]["message"]["content"]
