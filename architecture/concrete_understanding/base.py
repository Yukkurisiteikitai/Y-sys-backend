# archtecture_base
from lm_studio_rag.storage import RAGStorage
from lm_studio_rag.lm_studio_client import LMStudioClient
from . import schama_architecture as schama
from typing import List, Optional, Dict, Any

def artechture_base(storage: RAGStorage, field_info_input: str) -> Optional[schama.abstract_recognition_response]:
    # この体験とフィールド情報を組み合わせて推論を行います。
    experience_old = storage.search_similar(field_info_input, category="experience", top_k=3)
    field_info = field_info_input
    
    context_texts = f"""
    Context:
      context_experience:{experience_old}
      context_field_info:{field_info}
    """
    
    lm = LMStudioClient()
    # result_schama = schama.abstract_recognition_response()
    
    question_query:str = "「context_field_info」に書かれている状況において「context_experience」のような体験をしてきた人はどのような感情の動きをするのかを予測してください。"
    emostion_result:str = lm.generate_response(question_query, context_texts if context_texts else "No relevant context found.","gemma-3-1b-it")
    question_query:str = "「context_field_info」に書かれている状況において「context_experience」のような体験をしてきた人はどのような思考をするのかを予測してくだい。"
    think_result:str = lm.generate_response(question_query, context_texts if context_texts else "No relevant context found.","gemma-3-1b-it")
    print("RAG answer:\n", emostion_result)
    print("RAG answer:\n", think_result)

    
    try:
        result_schama = schama.abstract_recognition_response(
            emotion_estimation=emostion_result,
            think_estimation=think_result
        )
        return result_schama
    except ValidationError as e:
        print(f"スキーマの検証に失敗しました: {e}")
        # エラーが発生した場合の処理をここに書く (例: Noneを返す)
        return None
    # result_schama.emotion_estimation = emostion_result
    # result_schama.think_estimation = think_result
    
    return result_schama


# def generate_response(self:LMStudioClient, query: str, context: str, model: str = "gpt-4o-mini", temperature: float = 0.2, max_tokens: int = 512) -> str:
#         """
#         Simple RAG-style prompt: system prompt sets behavior, context is appended.
#         """
#         system = "あなたは知識ベースと会話文脈を統合して正確で簡潔な回答を作成するアシスタントです。"
#         user = f"Context:\n{context}\n\nQuestion:\n{query}\n\nAnswer concisely and cite context snippets if helpful."
#         messages = [
#             {"role": "system", "content": system},
#             {"role": "user", "content": user}
#         ]
#         resp = self.chat(messages, model=model, temperature=temperature, max_tokens=max_tokens)
#         return resp["choices"][0]["message"]["content"]

"""
つまりどんなことができたらいいのかって言うと

入力に単純に近いベクトルしてる体験を読み取ります。
この体験とフィールド情報を組み合わせて推論を行います。

その方向に向かう方向の軸として
 - 感情
 - 体験からユーザーが想像する曖昧な予測(思考)
があるのでこの２つを推論します。

推論の中断の待機
    userの入力ができます
    空入力の場合推論を再開する

    userの入力を(質問内容が何に対して言っているのか,アーキテクチャとして正しいのか)で評価します
        もし今のセクションでなかった場合
            質問の再入力
            空入力の場合推論を再開する

        フィードバックの評価
            feedback_db、episode_dbの中からフィードバックの中で同じようなシチュエーションでどんな反応をしたのかを評価
                乖離
                    今回はどっちにするとかの場合は基本的にユーザーの中で評価をする
                同等
                    選択しきれない悩む、葛藤状態として処理をする person_dbの困難への立ち向かい方
"""


