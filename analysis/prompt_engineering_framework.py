"""
Prompt Engineering Framework: 多様性を生む指示設計

このファイルは、定量分析から判明した問題を解決するための
複数の prompt 設計パターンを提供します。

段階的に試し、定量指標で検証します。
"""

from enum import Enum
from typing import List, Dict, Any

class PromptVariant(Enum):
    """Prompt設計の段階的改善パターン"""
    
    BASELINE = "baseline"  # 現在の状態（比較用）
    FEW_SHOT = "few_shot"  # 良い多様性の例を示す
    STRUCTURED_VARIATION = "structured_variation"  # 複数スタイルから選択
    TONE_DIVERSITY = "tone_diversity"  # 語調の多様性を明示的に指導
    COMBINED = "combined"  # 複数テクニックを組み合わせ


def generate_prompt(variant: PromptVariant, abstract_info: Dict[str, Any], field_info: str) -> str:
    """指定されたバリアントに従ってpromptを生成"""
    
    base_context = f"""
    # あなたの状態
    - 感情: {abstract_info['emotion_estimation']}
    - 思考: {abstract_info['think_estimation']}
    - 状況: {field_info}
    """

    if variant == PromptVariant.BASELINE:
        return base_context + """
        # 指示
        上記に基づいて、一人称で思考と応答を生成してください。
        
        出力フォーマット:
        - DECISION: 
        - ACTION:
        - DIALOGUE:
        """

    elif variant == PromptVariant.FEW_SHOT:
        return base_context + """
        # 指示
        上記に基づいて、一人称で思考と応答を生成してください。
        
        # 良い回答の例（多様性がある）
        
        例1: フォーマル・論理的
        DECISION: 状況を冷静に分析し、長期的メリットを考慮して挑戦することに決めた。
        ACTION: まず小規模な実験から始め、学習を積む。
        DIALOGUE: 「少し時間をもらって、準備してから挑戦します」
        
        例2: カジュアル・感情的
        DECISION: 怖いけど、ここでやらないと後悔すると思った。
        ACTION: 思い切ってやってみることにした。
        DIALOGUE: 「やってみようかな。怖いけど」
        
        例3: 詩的・省察的
        DECISION: 不安と期待が重なった瞬間、進む道が見えた。
        ACTION: 迷いながらも、一歩を踏み出す。
        DIALOGUE: 「未知へ」
        
        # あなたの応答
        上記のバリエーションを参考に、あなた自身の声で応答してください。
        """

    elif variant == PromptVariant.STRUCTURED_VARIATION:
        return base_context + """
        # 指示
        以下から1つを選んで、その語調・スタイルで応答してください。
        
        語調選択肢:
        1. フォーマル・論理的 (ビジネスライク、分析的)
        2. カジュアル・親密 (友人に話すような、ざっくばらん)
        3. 詩的・省察的 (内省的、比喩的表現を含む)
        4. ユーモラス・軽妙 (ジョークやウィットを含む)
        
        選んだ語調で、以下を答えてください:
        - DECISION: (決断)
        - ACTION: (行動)
        - DIALOGUE: (会話)
        
        ※ あなたの性格や状態に最適な語調を自由に選んでください。
        """

    elif variant == PromptVariant.TONE_DIVERSITY:
        return base_context + """
        # 指示
        あなたはこの状況で複数の応答方法を考えられます。
        
        思考の多層性を示すために、以下を3つの異なる視点から作成してください:
        
        1. 理性的な自分: (論理と分析に基づく応答)
        2. 感情的な自分: (直感と感情に基づく応答)
        3. 慎重な自分: (リスク回避と思慮に基づく応答)
        
        各視点から:
        - DECISION
        - ACTION
        - DIALOGUE
        
        最終的には、この3つの視点を統合した「本当のあなた」の応答を示してください。
        """

    elif variant == PromptVariant.COMBINED:
        return base_context + """
        # 指示
        
        ## Step 1: 複数視点の思考
        以下の3つの視点から状況を分析してください:
        1. 理性的視点: どう判断するか
        2. 感情的視点: どう感じるか
        3. 他者視点: 友人ならどう勧めるか
        
        ## Step 2: 語調を選択
        この3つの視点を踏まえて、以下から最適な語調を選んでください:
        - フォーマル (論理的、ビジネスライク)
        - カジュアル (親密、ざっくばらん)
        - 詩的 (内省的、比喩的)
        
        ## Step 3: 統合応答を生成
        選んだ語調で、分析を踏まえた最終応答を作成してください:
        
        - 思考プロセス: (上記3視点の葛藤を簡潔に)
        - DECISION: (最終判断)
        - ACTION: (取る行動)
        - NUANCE: (非言語的な態度)
        - DIALOGUE: (発話)
        """

    return ""


# テンプレート: 段階的テスト計画
TEST_PLAN = """
### 段階的な prompt 改善テスト計画

#### Phase 1: ベースライン測定 (Variant.BASELINE)
- 現在の出力を分析し、定型文パターンを特定
- Distinct-1/2/3, Self-BLEU, Type-Token Ratio を記録

#### Phase 2: Few-shot 導入 (Variant.FEW_SHOT)
- 良い多様性の例を示す
- 100サンプル再収集
- 指標と比較 → 改善度 %

#### Phase 3: 構造化変動 (Variant.STRUCTURED_VARIATION)
- スタイル選択肢を明示
- 100サンプル再収集
- Phase 1, 2 と比較

#### Phase 4: 複合手法 (Variant.COMBINED)
- 複数テクニックを組み合わせ
- 100サンプル再収集
- 最良パターンを選定

#### Phase 5: 最終チューニング
- temperature: 0.2 → 0.3 (最小限の調整のみ)
- Human Evaluation: ユーザー満足度 A/B テスト

### 成功基準
- Distinct-1: > 0.7 (ユニークな語彙の割合)
- Self-BLEU: < 0.3 (低い類似度 = 多様性)
- Type-Token Ratio: > 0.5 (語彙の豊かさ)
- JSON Parse Success: > 0.95 (形式の安定性)
- ユーザー満足度: A/B テストで有意差あり
"""

if __name__ == "__main__":
    # 使用例
    sample_abstract_info = {
        "emotion_estimation": "期待と不安が混在",
        "think_estimation": "新しいことへの挑戦を考えている"
    }
    
    sample_field_info = "新しいプロジェクトを提案されている状況"
    
    for variant in PromptVariant:
        print(f"\n{'='*60}")
        print(f"Variant: {variant.value}")
        print(f"{'='*60}")
        prompt = generate_prompt(variant, sample_abstract_info, sample_field_info)
        print(prompt)
    
    print("\n" + TEST_PLAN)
