# lm_studio_client.py
import requests
import logging
from typing import List, Dict, Any, Optional
from .config import LM_STUDIO_BASE_URL, LM_STUDIO_API_KEY, DEFAULT_MODEL, DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS

logger = logging.getLogger("lmstudio")

class LMStudioClient:
    """
    Minimal OpenAI-compatible client for LM Studio (chat + embeddings).
    Uses requests to talk to /v1/chat/completions and /v1/embeddings.
    """

    def __init__(self, base_url: str = LM_STUDIO_BASE_URL, api_key: str = LM_STUDIO_API_KEY, timeout: int = 30, model_name: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.model_name = model_name or DEFAULT_MODEL
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
    def chat(self, messages: List[Dict[str, str]], model: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None, force_system: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a chat request. If `force_system` is provided, it will be inserted as the first
        system message and any other system messages in `messages` will be removed to
        prevent user-supplied system prompts from overriding it.
        Returns the raw LM Studio response (dict).
        """
        # Use defaults if not specified
        model = model or self.model_name
        temperature = temperature if temperature is not None else DEFAULT_TEMPERATURE
        max_tokens = max_tokens or DEFAULT_MAX_TOKENS
        
        # enforce system prompt if requested
        if force_system:
            filtered = [m for m in messages if m.get("role") != "system"]
            messages = [{"role": "system", "content": force_system}] + filtered
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        resp = self._post("/v1/chat/completions", payload)
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

    def generate_response(self, query: str, context: str, model: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        RAG-style response generator that requests a structured JSON output from the LLM.
        Returns a dict with keys: `answer` (str), `evidence` (list), `confidence` (float),
        and optionally `reason` on failure.
        """
        # Use defaults if not specified
        model = model or self.model_name
        temperature = temperature if temperature is not None else DEFAULT_TEMPERATURE
        max_tokens = max_tokens or DEFAULT_MAX_TOKENS
        
        system = (
            "あなたは知識ベースと会話文脈を統合して正確で簡潔な回答を作成するアシスタントです。"
            " 出力は必ずJSON形式で返してください。フォーマット:"
            " {\"answer\":\"...\", \"evidence\":[{\"id\":\"...\",\"text\":\"...\",\"score\":0.0}], \"confidence\":0.0}"
        )

        user = f"Context:\n{context}\n\nQuestion:\n{query}\n\nReturn JSON as specified."
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]

        resp = self.chat(messages, model=model, temperature=temperature, max_tokens=max_tokens, force_system=system)

        try:
            assistant = resp["choices"][0]["message"]["content"]
            import json
            parsed = json.loads(assistant)
            # Ensure keys exist
            return {
                "answer": parsed.get("answer", ""),
                "evidence": parsed.get("evidence", []),
                "confidence": float(parsed.get("confidence", 0.0)),
            }
        except Exception:
            # fallback: return best-effort plain text answer plus metadata
            try:
                fallback_text = resp["choices"][0]["message"]["content"]
            except Exception:
                fallback_text = ""
            return {
                "answer": fallback_text,
                "evidence": [],
                "confidence": 0.0,
                "reason": "parsing_failed"
            }