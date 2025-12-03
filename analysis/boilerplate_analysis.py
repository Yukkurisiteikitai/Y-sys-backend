"""
定型文分析スクリプト
100サンプルの現在の出力を収集・分析し、多様性を阻む要因を特定します。

Usage:
    python analysis/boilerplate_analysis.py --samples 100 --output analysis/results.json
"""

import json
import re
from typing import List, Dict, Any
from collections import Counter
import statistics

class BoilerplateAnalyzer:
    """定型文の多様性・パターンを定量的に分析"""

    def __init__(self):
        self.responses: List[str] = []
        self.metrics: Dict[str, Any] = {}

    def add_response(self, response: str):
        """応答を追加"""
        self.responses.append(response)

    def distinct_n(self, n: int = 1) -> float:
        """
        Distinct-n: 全応答内のユニークなn-gram数 / 全n-gram数
        0.0 (完全に同じ) ~ 1.0 (完全に異なる)
        """
        all_ngrams = []
        for response in self.responses:
            words = response.split()
            ngrams = [" ".join(words[i:i+n]) for i in range(len(words) - n + 1)]
            all_ngrams.extend(ngrams)
        if not all_ngrams:
            return 0.0
        unique_count = len(set(all_ngrams))
        return unique_count / len(all_ngrams)

    def self_bleu(self, n: int = 1) -> float:
        """
        Self-BLEU: 各応答と他の応答の平均BLEU値（低いほど多様）
        応答間の類似度を測定。1.0に近い＝定型的、0.0に近い＝多様
        簡略版: 単語レベルのジャッカード係数を平均
        """
        if len(self.responses) < 2:
            return 0.0
        similarities = []
        for i, resp1 in enumerate(self.responses):
            words1 = set(resp1.split())
            for resp2 in self.responses[i+1:]:
                words2 = set(resp2.split())
                if words1 and words2:
                    jaccard = len(words1 & words2) / len(words1 | words2)
                    similarities.append(jaccard)
        return statistics.mean(similarities) if similarities else 0.0

    def common_patterns(self, top_k: int = 10) -> List[tuple]:
        """
        最頻出フレーズを抽出（定型文の証拠）
        3-gramと5-gramで共通パターンをキャッチ
        """
        all_phrases = []
        for response in self.responses:
            words = response.split()
            # 3-gram と 5-gram
            for n in [3, 5]:
                phrases = [" ".join(words[i:i+n]) for i in range(len(words) - n + 1)]
                all_phrases.extend(phrases)
        counter = Counter(all_phrases)
        return counter.most_common(top_k)

    def response_length_variance(self) -> Dict[str, float]:
        """応答長のバリエーション"""
        lengths = [len(r.split()) for r in self.responses]
        return {
            "mean_words": statistics.mean(lengths) if lengths else 0,
            "stdev_words": statistics.stdev(lengths) if len(lengths) > 1 else 0,
            "min_words": min(lengths) if lengths else 0,
            "max_words": max(lengths) if lengths else 0,
        }

    def json_parse_success_rate(self) -> float:
        """JSON出力のパース成功率"""
        success = 0
        for response in self.responses:
            try:
                # JSON のような構造を検出
                if "{" in response and "}" in response:
                    json_str = response[response.find("{"):response.rfind("}")+1]
                    json.loads(json_str)
                    success += 1
            except:
                pass
        return success / len(self.responses) if self.responses else 0

    def vocabulary_richness(self) -> Dict[str, Any]:
        """語彙の豊かさ"""
        all_words = []
        for response in self.responses:
            words = response.lower().split()
            all_words.extend(words)
        unique_words = len(set(all_words))
        total_words = len(all_words)
        return {
            "unique_words": unique_words,
            "total_words": total_words,
            "type_token_ratio": unique_words / total_words if total_words > 0 else 0,  # 語彙の多様性
        }

    def analyze_all(self) -> Dict[str, Any]:
        """全指標を計算"""
        return {
            "sample_count": len(self.responses),
            "distinct_1": self.distinct_n(n=1),
            "distinct_2": self.distinct_n(n=2),
            "distinct_3": self.distinct_n(n=3),
            "self_bleu": self.self_bleu(),
            "common_patterns": dict(self.common_patterns(top_k=15)),
            "response_length": self.response_length_variance(),
            "json_parse_success": self.json_parse_success_rate(),
            "vocabulary": self.vocabulary_richness(),
        }


def generate_100_samples():
    """
    ここで100サンプルを実際に生成
    （現在のAPIエンドポイントを呼び出すか、テストデータを読み込む）
    """
    # プレースホルダー: 実装時は API を呼ぶか、保存されたサンプルを読む
    sample_responses = [
        "【感情的トリガー】不安と期待が混在している。【情報的インプット】過去の成功例と現在の状況が似ている。【思考の変遷】迷いながらも前に進もうと決めた。【DECISION】挑戦する。【ACTION】準備を始める。【NUANCE】少し不安な表情。【DIALOGUE】「やってみます」。【BEHAVIOR】深く息を吸った。",
        "【感情的トリガー】焦燥感。【情報的インプット】時間が限られている。【思考の変遷】急いで決断した。【DECISION】急ぐ。【ACTION】すぐに実行する。【NUANCE】急いでいる様子。【DIALOGUE】「急ぎます」。【BEHAVIOR】立ち上がった。"
    ]
    return sample_responses


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="定型文分析")
    parser.add_argument("--samples", type=int, default=100, help="サンプル数")
    parser.add_argument("--output", type=str, default="analysis/results.json", help="出力ファイル")
    args = parser.parse_args()
    
    analyzer = BoilerplateAnalyzer()
    
    # サンプルを生成（本来はここで API 呼び出し）
    samples = generate_100_samples()
    for sample in samples:
        analyzer.add_response(sample)
    
    # 分析を実行
    results = analyzer.analyze_all()
    
    # 結果を出力
    print(json.dumps(results, indent=2, ensure_ascii=False))
    
    # ファイルに保存
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n分析結果を {args.output} に保存しました。")
    
    # インサイト
    print("\n--- 分析インサイト ---")
    print(f"Distinct-1: {results['distinct_1']:.3f} (高いほど多様)")
    print(f"Self-BLEU: {results['self_bleu']:.3f} (低いほど多様)")
    print(f"Type-Token Ratio: {results['vocabulary']['type_token_ratio']:.3f} (語彙の豊かさ)")
    print(f"最頻出フレーズ: {list(results['common_patterns'].keys())[:5]}")
