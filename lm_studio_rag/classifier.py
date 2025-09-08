# classifier.py
from typing import Tuple, Dict
import re
import logging
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from .config import EMBEDDING_MODEL_NAME
from .lm_studio_client import LMStudioClient
from .utils import now_iso

logger = logging.getLogger("classifier")

class ContentClassifier:
    """
    Hybrid classifier:
     - Simple rule-based heuristics for fast classification
     - Optional embedding + small logistic regression classifier (weak supervised) for better accuracy
     - Optional LLM-based classification via LMStudioClient.classify_content_via_llm (fallback or ensemble)
    """

    def __init__(self, use_llm: bool = False):
        self.emb_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        self.scaler = StandardScaler()
        self.clf = LogisticRegression()
        self._is_trained = False
        self.use_llm = use_llm
        if use_llm:
            self.llm = LMStudioClient()

    # --- Rule-based heuristics ---
    def _heuristic(self, text: str) -> Tuple[str, float, str]:
        """
        Quick heuristics:
         - If text contains time words, past tense, specific events -> experience
         - If text contains personality adjectives, preferences (I prefer, I like), stable traits -> personality
        Returns: (label, score, reason)
        """
        t = text.lower()
        # simple markers for experience
        experience_markers = [
            r"\b(yesterday|last month|last week|today|this morning|on .+ day)\b",
            r"\b(visited|went to|traveled|attended|met|saw|arrived|left|interview|presentation)\b",
            r"\b(in \d{4}|\d{4}年)\b",
            r"\b(my (trip|travel|visit|experience|internship|job|work|project))\b"
        ]
        personality_markers = [
            r"\b(i am|i'm|i tend to|i prefer|i like|i dislike|introvert|extrovert|shy|outgoing|personality|trait)\b",
            r"\b(prefer|rather than|more than|less than|enjoy|hate|love)\b",
            r"\b(skill|good at|bad at|talent|strength|weakness)\b"
        ]
        for pat in experience_markers:
            if re.search(pat, t):
                return "experience", 0.85, f"matched_experience:{pat}"
        for pat in personality_markers:
            if re.search(pat, t):
                return "personality", 0.85, f"matched_personality:{pat}"
        # fallback: neutral
        return "personality", 0.5, "no_strong_marker"

    # --- small embedding-based classifier training ---
    def train_small_classifier(self, samples: Dict[str, list]):
        """
        samples: {"personality": [...], "experience":[...]}
        Train a small logistic regression on embeddings of provided samples.
        """
        texts = []
        labels = []
        for label, l in samples.items():
            texts.extend(l)
            labels.extend([label]*len(l))
        embs = self.emb_model.encode(texts, show_progress_bar=False)
        X = np.array(embs)
        # numeric mapping
        y = np.array([1 if lab == "personality" else 0 for lab in labels])
        self.scaler.fit(X)
        Xs = self.scaler.transform(X)
        self.clf.fit(Xs, y)
        self._is_trained = True
        logger.info("Trained small classifier on %d samples", len(texts))

    def classify(self, text: str) -> Dict:
        """
        Return: {
            'label': 'personality'|'experience',
            'score': float (0..1),
            'method': 'heuristic'|'embedding'|'llm'|'ensemble',
            'reason': str,
            'timestamp': iso
        }
        """
        # 1) quick heuristic
        label_h, score_h, reason_h = self._heuristic(text)
        # 2) if trained, use embedding classifier
        if self._is_trained:
            emb = self.emb_model.encode([text], show_progress_bar=False)
            Xs = self.scaler.transform(emb)
            prob = self.clf.predict_proba(Xs)[0]  # [prob_class0, prob_class1]
            # mapping: class1 == personality
            prob_personality = float(prob[1])
            label_e = "personality" if prob_personality >= 0.5 else "experience"
            score_e = prob_personality if label_e == "personality" else (1.0 - prob_personality)
            # ensemble: if both agree, boost confidence
            if label_e == label_h:
                label = label_e
                score = min(0.95, 0.6 + score_e * 0.4 + score_h * 0.4)
                method = "ensemble"
                reason = f"heuristic:{reason_h} + embedding_prob:{prob_personality:.3f}"
            else:
                # disagree -> pick embedding result but show both
                label = label_e
                score = max(score_e, score_h * 0.6)
                method = "embedding"
                reason = f"heuristic:{reason_h} vs embedding_prob:{prob_personality:.3f}"
        else:
            label = label_h
            score = score_h
            method = "heuristic"
            reason = reason_h

        # 3) optional LLM fallback/confirmation
        if self.use_llm and score < 0.7:
            try:
                llm_resp = self.llm.classify_content_via_llm(text)
                llm_label = llm_resp.get("label")
                llm_score = float(llm_resp.get("score", 0.5))
                # choose majority or higher-confidence
                if llm_score > score + 0.15:
                    label = llm_label
                    score = llm_score
                    method = "llm"
                    reason = f"llm_reason:{llm_resp.get('reason','')}"
            except Exception as e:
                logger.warning("LLM classification failed: %s", e)

        return {
            "label": label,
            "score": float(score),
            "method": method,
            "reason": reason,
            "timestamp": now_iso()
        }
