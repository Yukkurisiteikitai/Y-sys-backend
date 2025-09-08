# main.py
"""
Example workflow:
 1. Load sample texts
 2. Classify each text (hybrid classifier)
 3. Save into vector DB by category with metadata
 4. Run a sample RAG query (search + LLM generation)
"""
from lm_studio_rag.config import LM_STUDIO_BASE_URL, LM_STUDIO_API_KEY
from lm_studio_rag.lm_studio_client import LMStudioClient
from lm_studio_rag.classifier import ContentClassifier
from lm_studio_rag.storage import RAGStorage
from lm_studio_rag.utils import now_iso
import os

# sample data
PERSONALITY_SAMPLES = [
    "私は内向的な性格で、静かな環境を好みます",
    "コーヒーよりも紅茶派です",
    "数学が得意で論理的思考を重視します"
]
EXPERIENCE_SAMPLES = [
    "昨日、新しいレストランに行きました",
    "大学時代にプログラミングを学んだ経験があります",
    "先月の出張で面白い発見をしました"
]

def build_and_run():
    # 1) initialize classifier (no LLM)
    classifier = ContentClassifier(use_llm=False)
    # train small classifier on provided samples for better accuracy
    classifier.train_small_classifier({
        "personality": PERSONALITY_SAMPLES,
        "experience": EXPERIENCE_SAMPLES
    })

    # 2) initialize storage
    storage = RAGStorage()

    # 3) ingest some mixed items
    mixed_items = [
        "私は朝型で、午前中が最も生産的です",
        "先週末に山登りをしてきました",
        "論理的な議論が好きで問題解決が得意です",
        "昨日は同僚と新しいカフェを試した",
    ]
    for t in mixed_items:
        res = classifier.classify(t)
        print("Classify:", t, "->", res)
        metadata = {"classifier": res, "source": "user_upload", "saved_at": now_iso()}
        if res["label"] == "personality":
            storage.save_personality_data(t, metadata)
        else:
            storage.save_experience_data(t, metadata)

    # 4) sample search + RAG generation
    question_query = "朝の生産性を高めるコツは？"
    similar = storage.search_similar(question_query category="personality", top_k=3)
    context_texts = "\n\n".join([f"- {d['text']} (score={d['score']:.3f})" for d in similar])
    # LM Studio LLM
    lm = LMStudioClient()
    rag_answer = lm.generate_response(question_query context_texts if context_texts else "No relevant context found.","gemma-3-1b-it")
    print("RAG answer:\n", rag_answer)

if __name__ == "__main__":
    build_and_run()