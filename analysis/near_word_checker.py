import json
import re
import statistics
from collections import Counter
from typing import List, Dict, Any, Optional, Tuple
import warnings


class BoilerplateAnalyzer:
    """
    定型文の多様性・パターンを定量的に分析
    
    主要指標:
    - Distinct-n: 語彙の多様性 (高いほど多様)
    - Self-BLEU: 応答間の類似度 (低いほど多様)
    - TTR: Type-Token Ratio (語彙の豊かさ)
    - JSON成功率: 構造化出力の安定性
    """

    def __init__(self, language: str = "ja"):
        """
        Args:
            language: "ja" (日本語) or "en" (英語)
        """
        self.responses: List[str] = []
        self.language = language
        self._tokenizer = None
        
        if language == "ja":
            try:
                import MeCab
                self._tokenizer = MeCab.Tagger("-Owakati")
            except ImportError:
                warnings.warn(
                    "MeCab not installed. Falling back to character-based tokenization for Japanese."
                )

    def add_response(self, response: str):
        """応答を追加"""
        if not response or not response.strip():
            warnings.warn("Empty response added")
        self.responses.append(response)

    def add_responses(self, responses: List[str]):
        """複数応答を一括追加"""
        self.responses.extend(responses)

    def clear(self):
        """応答をクリア"""
        self.responses = []

    def tokenize(self, text: str) -> List[str]:
        """言語に応じた適切なトークン化"""
        if not text:
            return []
        
        if self.language == "ja":
            if self._tokenizer:
                try:
                    return self._tokenizer.parse(text).strip().split()
                except:
                    # MeCabが失敗したら文字単位にフォールバック
                    return list(text.replace(" ", ""))
            else:
                # MeCabなしの場合は文字単位
                return list(text.replace(" ", ""))
        else:
            # 英語: 単純な空白分割 + 句読点処理
            text = re.sub(r'([.,!?;:])', r' \1 ', text)
            return text.lower().split()

    def distinct_n(self, n: int = 1) -> Dict[str, Any]:
        """
        Distinct-n: 全応答内のユニークなn-gram数 / 全n-gram数
        
        Returns:
            {
                "score": float (0.0~1.0, 高いほど多様),
                "unique_count": int,
                "total_count": int,
                "skipped_responses": int
            }
        """
        unique_ngrams = set()
        total_ngrams = 0
        skipped = 0
        
        for response in self.responses:
            tokens = self.tokenize(response)
            if len(tokens) < n:
                skipped += 1
                continue
            
            for i in range(len(tokens) - n + 1):
                ngram = tuple(tokens[i:i+n])
                unique_ngrams.add(ngram)
                total_ngrams += 1
        
        score = len(unique_ngrams) / total_ngrams if total_ngrams > 0 else 0.0
        
        return {
            "score": score,
            "unique_count": len(unique_ngrams),
            "total_count": total_ngrams,
            "skipped_responses": skipped
        }

    def self_bleu(self, max_n: int = 4, smoothing: bool = True) -> Dict[str, Any]:
        """
        Self-BLEU: 各応答と他の応答との平均BLEU値
        
        低いほど多様（応答が互いに似ていない）
        高いほど定型的（応答が互いに似ている）
        
        Args:
            max_n: n-gramの最大値 (通常4)
            smoothing: ゼロ除算を避けるスムージング
        
        Returns:
            {
                "score": float (0.0~1.0, 低いほど多様),
                "individual_scores": List[float],
                "std_dev": float
            }
        """
        if len(self.responses) < 2:
            return {
                "score": 0.0,
                "individual_scores": [],
                "std_dev": 0.0,
                "error": "Need at least 2 responses"
            }
        
        bleu_scores = []
        
        for i, response in enumerate(self.responses):
            hypothesis = self.tokenize(response)
            if not hypothesis:
                continue
            
            # 他の全応答を参照として使用
            references = [
                self.tokenize(r) 
                for j, r in enumerate(self.responses) 
                if i != j
            ]
            references = [ref for ref in references if ref]  # 空を除外
            
            if not references:
                continue
            
            # BLEU計算
            score = self._compute_bleu(hypothesis, references, max_n, smoothing)
            bleu_scores.append(score)
        
        if not bleu_scores:
            return {
                "score": 0.0,
                "individual_scores": [],
                "std_dev": 0.0,
                "error": "Could not compute BLEU"
            }
        
        return {
            "score": statistics.mean(bleu_scores),
            "individual_scores": bleu_scores,
            "std_dev": statistics.stdev(bleu_scores) if len(bleu_scores) > 1 else 0.0
        }

    def _compute_bleu(
        self, 
        hypothesis: List[str], 
        references: List[List[str]], 
        max_n: int,
        smoothing: bool
    ) -> float:
        """
        Modified BLEU計算 (sentence-level)
        
        BLEU = BP * exp(sum(w_n * log(p_n)))
        """
        # Brevity Penalty
        hyp_len = len(hypothesis)
        ref_lens = [len(ref) for ref in references]
        closest_ref_len = min(ref_lens, key=lambda x: abs(x - hyp_len))
        
        if hyp_len > closest_ref_len:
            bp = 1.0
        elif hyp_len == 0:
            return 0.0
        else:
            bp = statistics.exp(1 - closest_ref_len / hyp_len)
        
        # n-gram precisions
        log_precisions = []
        for n in range(1, max_n + 1):
            hyp_ngrams = self._get_ngrams(hypothesis, n)
            if not hyp_ngrams:
                if smoothing:
                    log_precisions.append(-10)  # 小さな値
                continue
            
            max_counts = Counter()
            for reference in references:
                ref_ngrams = self._get_ngrams(reference, n)
                for ngram in hyp_ngrams:
                    max_counts[ngram] = max(max_counts[ngram], ref_ngrams[ngram])
            
            clipped_counts = {
                ngram: min(count, max_counts[ngram])
                for ngram, count in hyp_ngrams.items()
            }
            
            numerator = sum(clipped_counts.values())
            denominator = sum(hyp_ngrams.values())
            
            if denominator == 0:
                precision = 0.0
            else:
                precision = numerator / denominator
            
            # スムージング (add-1)
            if precision == 0.0 and smoothing:
                precision = 1 / (2 * denominator)
            
            if precision > 0:
                log_precisions.append(statistics.log(precision))
        
        if not log_precisions:
            return 0.0
        
        # 幾何平均
        avg_log_precision = sum(log_precisions) / len(log_precisions)
        bleu = bp * statistics.exp(avg_log_precision)
        
        return bleu

    def _get_ngrams(self, tokens: List[str], n: int) -> Counter:
        """n-gramのカウンタを取得"""
        ngrams = [tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]
        return Counter(ngrams)

    def common_patterns(self, top_k: int = 10, ngram_sizes: List[int] = [3, 5]) -> Dict[str, Any]:
        """
        最頻出フレーズを抽出（定型文の証拠）
        
        Args:
            top_k: 上位何件を返すか
            ngram_sizes: チェックするn-gramサイズ
        
        Returns:
            {
                "3gram": [(phrase, count), ...],
                "5gram": [(phrase, count), ...],
                "total_analyzed": int
            }
        """
        results = {}
        
        for n in ngram_sizes:
            all_ngrams = []
            for response in self.responses:
                tokens = self.tokenize(response)
                if len(tokens) < n:
                    continue
                ngrams = [tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]
                all_ngrams.extend(ngrams)
            
            counter = Counter(all_ngrams)
            # 出現回数2回以上のみ（1回は定型文じゃない）
            patterns = [(self._join_tokens(ngram), count) 
                       for ngram, count in counter.most_common(top_k * 2)
                       if count > 1][:top_k]
            
            results[f"{n}gram"] = patterns
        
        results["total_analyzed"] = len(self.responses)
        return results

    def _join_tokens(self, tokens: Tuple[str, ...]) -> str:
        """トークンを結合（言語に応じて）"""
        if self.language == "ja":
            return "".join(tokens)
        return " ".join(tokens)

    def response_length_stats(self) -> Dict[str, float]:
        """応答長の統計（トークン単位）"""
        lengths = [len(self.tokenize(r)) for r in self.responses]
        
        if not lengths:
            return {
                "mean": 0, "median": 0, "stdev": 0,
                "min": 0, "max": 0, "variance": 0
            }
        
        return {
            "mean": statistics.mean(lengths),
            "median": statistics.median(lengths),
            "stdev": statistics.stdev(lengths) if len(lengths) > 1 else 0,
            "min": min(lengths),
            "max": max(lengths),
            "variance": statistics.variance(lengths) if len(lengths) > 1 else 0,
            "total_responses": len(lengths)
        }

    def json_parse_analysis(self) -> Dict[str, Any]:
        """JSON出力のパース成功率（詳細版）"""
        results = {
            "total": len(self.responses),
            "success": 0,
            "malformed": 0,
            "parse_errors": [],
            "success_rate": 0.0
        }
        
        for i, response in enumerate(self.responses):
            try:
                # より堅牢なJSON抽出（ネスト対応）
                json_match = self._extract_json(response)
                
                if not json_match:
                    results["malformed"] += 1
                    continue
                
                parsed = json.loads(json_match)
                results["success"] += 1
                
            except json.JSONDecodeError as e:
                results["parse_errors"].append({
                    "index": i,
                    "error": str(e),
                    "excerpt": response[:100] + "..." if len(response) > 100 else response
                })
        
        results["success_rate"] = results["success"] / results["total"] if results["total"] > 0 else 0.0
        return results

    def _extract_json(self, text: str) -> Optional[str]:
        """テキストからJSON文字列を抽出（ネスト対応）"""
        # 最初の { を見つける
        start = text.find('{')
        if start == -1:
            return None
        
        # ブレースのバランスを取りながら終了位置を探す
        depth = 0
        in_string = False
        escape = False
        
        for i in range(start, len(text)):
            char = text[i]
            
            if escape:
                escape = False
                continue
            
            if char == '\\':
                escape = True
                continue
            
            if char == '"':
                in_string = not in_string
                continue
            
            if in_string:
                continue
            
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i+1]
        
        return None

    def vocabulary_richness(self) -> Dict[str, Any]:
        """語彙の豊かさ（TTR, Yule's K など）"""
        all_tokens = []
        for response in self.responses:
            tokens = self.tokenize(response)
            all_tokens.extend(tokens)
        
        if not all_tokens:
            return {
                "unique_tokens": 0,
                "total_tokens": 0,
                "ttr": 0.0,
                "log_ttr": 0.0,
                "yules_k": 0.0
            }
        
        unique_tokens = len(set(all_tokens))
        total_tokens = len(all_tokens)
        ttr = unique_tokens / total_tokens
        
        # Log TTR (長いテキストでも安定)
        log_ttr = unique_tokens / statistics.log(total_tokens) if total_tokens > 1 else 0.0
        
        # Yule's K (語彙の偏り: 低いほど均等)
        token_freq = Counter(all_tokens)
        freq_freq = Counter(token_freq.values())
        
        M1 = sum(freq_freq.values())
        M2 = sum(freq * (count ** 2) for freq, count in freq_freq.items())
        
        yules_k = 10000 * (M2 - M1) / (M1 ** 2) if M1 > 0 else 0.0
        
        return {
            "unique_tokens": unique_tokens,
            "total_tokens": total_tokens,
            "ttr": ttr,  # 0.0~1.0, 高いほど多様
            "log_ttr": log_ttr,
            "yules_k": yules_k,  # 低いほど語彙が均等に分布
            "top_10_tokens": token_freq.most_common(10)
        }

    def confidence_interval(
        self, 
        metric_name: str,
        confidence: float = 0.95,
        n_bootstrap: int = 1000
    ) -> Dict[str, Any]:
        """
        ブートストラップ法で信頼区間を計算
        
        Args:
            metric_name: "distinct_1", "distinct_2", "self_bleu" など
            confidence: 信頼水準 (0.95 = 95%)
            n_bootstrap: ブートストラップ回数
        """
        if len(self.responses) < 10:
            return {
                "error": "Need at least 10 responses for reliable confidence intervals"
            }
        
        import random
        
        metric_map = {
            "distinct_1": lambda: self.distinct_n(1)["score"],
            "distinct_2": lambda: self.distinct_n(2)["score"],
            "distinct_3": lambda: self.distinct_n(3)["score"],
            "self_bleu": lambda: self.self_bleu()["score"],
            "ttr": lambda: self.vocabulary_richness()["ttr"],
        }
        
        if metric_name not in metric_map:
            return {"error": f"Unknown metric: {metric_name}"}
        
        bootstrap_scores = []
        original_responses = self.responses.copy()
        
        for _ in range(n_bootstrap):
            # リサンプリング
            sample = random.choices(original_responses, k=len(original_responses))
            self.responses = sample
            
            try:
                score = metric_map[metric_name]()
                bootstrap_scores.append(score)
            except:
                continue
        
        self.responses = original_responses
        
        if not bootstrap_scores:
            return {"error": "Bootstrap failed"}
        
        bootstrap_scores.sort()
        alpha = 1 - confidence
        lower_idx = int(len(bootstrap_scores) * alpha / 2)
        upper_idx = int(len(bootstrap_scores) * (1 - alpha / 2))
        
        return {
            "metric": metric_name,
            "mean": statistics.mean(bootstrap_scores),
            "median": statistics.median(bootstrap_scores),
            "lower_bound": bootstrap_scores[lower_idx],
            "upper_bound": bootstrap_scores[upper_idx],
            "confidence": confidence,
            "n_bootstrap": len(bootstrap_scores)
        }

    def grade_diversity(self) -> Dict[str, str]:
        """
        多様性の総合評価（ベンチマーク比較）
        
        Returns:
            各指標の評価 ("excellent", "good", "fair", "poor")
        """
        BENCHMARKS = {
            "distinct_1": {"excellent": 0.85, "good": 0.70, "fair": 0.50},
            "distinct_2": {"excellent": 0.75, "good": 0.60, "fair": 0.40},
            "self_bleu": {"excellent": 0.30, "good": 0.50, "fair": 0.70},  # 低い方が良い
            "ttr": {"excellent": 0.60, "good": 0.45, "fair": 0.30},
            "json_success": {"excellent": 0.95, "good": 0.85, "fair": 0.70}
        }
        
        def grade(value: float, thresholds: Dict[str, float], inverse: bool = False) -> str:
            if inverse:
                if value <= thresholds["excellent"]:
                    return "excellent"
                elif value <= thresholds["good"]:
                    return "good"
                elif value <= thresholds["fair"]:
                    return "fair"
                else:
                    return "poor"
            else:
                if value >= thresholds["excellent"]:
                    return "excellent"
                elif value >= thresholds["good"]:
                    return "good"
                elif value >= thresholds["fair"]:
                    return "fair"
                else:
                    return "poor"
        
        results = {}
        
        distinct_1 = self.distinct_n(1)["score"]
        results["distinct_1"] = grade(distinct_1, BENCHMARKS["distinct_1"])
        
        distinct_2 = self.distinct_n(2)["score"]
        results["distinct_2"] = grade(distinct_2, BENCHMARKS["distinct_2"])
        
        self_bleu = self.self_bleu()["score"]
        results["self_bleu"] = grade(self_bleu, BENCHMARKS["self_bleu"], inverse=True)
        
        ttr = self.vocabulary_richness()["ttr"]
        results["ttr"] = grade(ttr, BENCHMARKS["ttr"])
        
        json_rate = self.json_parse_analysis()["success_rate"]
        results["json_success"] = grade(json_rate, BENCHMARKS["json_success"])
        
        return results

    def analyze_all(self) -> Dict[str, Any]:
        """全指標を一括計算"""
        if not self.responses:
            return {"error": "No responses to analyze"}
        
        return {
            "meta": {
                "sample_count": len(self.responses),
                "language": self.language,
                "tokenizer": "MeCab" if self._tokenizer else "fallback"
            },
            "diversity": {
                "distinct_1": self.distinct_n(n=1),
                "distinct_2": self.distinct_n(n=2),
                "distinct_3": self.distinct_n(n=3),
                "self_bleu": self.self_bleu(),
                "vocabulary": self.vocabulary_richness(),
            },
            "patterns": self.common_patterns(top_k=10),
            "structure": {
                "response_length": self.response_length_stats(),
                "json_parse": self.json_parse_analysis(),
            },
            "grading": self.grade_diversity()
        }

    def compare_with(self, other: 'BoilerplateAnalyzer', label_self: str = "Current", label_other: str = "Baseline") -> Dict[str, Any]:
        """
        別のアナライザーと比較（A/Bテスト用）
        
        Args:
            other: 比較対象のアナライザー
            label_self: 自分のラベル
            label_other: 相手のラベル
        """
        def compare_metric(name: str, val_self: float, val_other: float, higher_is_better: bool = True) -> Dict:
            diff = val_self - val_other
            pct_change = (diff / val_other * 100) if val_other != 0 else 0
            
            if higher_is_better:
                better = label_self if diff > 0 else label_other
            else:
                better = label_self if diff < 0 else label_other
            
            return {
                label_self: val_self,
                label_other: val_other,
                "difference": diff,
                "percent_change": pct_change,
                "better": better if abs(pct_change) > 5 else "similar"  # 5%未満は誤差
            }
        
        # 各指標を比較
        d1_self = self.distinct_n(1)["score"]
        d1_other = other.distinct_n(1)["score"]
        
        sb_self = self.self_bleu()["score"]
        sb_other = other.self_bleu()["score"]
        
        ttr_self = self.vocabulary_richness()["ttr"]
        ttr_other = other.vocabulary_richness()["ttr"]
        
        json_self = self.json_parse_analysis()["success_rate"]
        json_other = other.json_parse_analysis()["success_rate"]
        
        return {
            "distinct_1": compare_metric("distinct_1", d1_self, d1_other, higher_is_better=True),
            "self_bleu": compare_metric("self_bleu", sb_self, sb_other, higher_is_better=False),
            "ttr": compare_metric("ttr", ttr_self, ttr_other, higher_is_better=True),
            "json_success": compare_metric("json_success", json_self, json_other, higher_is_better=True),
            "summary": {
                "total_responses": {label_self: len(self.responses), label_other: len(other.responses)},
                "recommendation": self._recommend(d1_self, d1_other, sb_self, sb_other, json_self, json_other)
            }
        }

    def _recommend(self, d1_s, d1_o, sb_s, sb_o, json_s, json_o) -> str:
        """どちらが良いか総合判定"""
        score_self = 0
        score_other = 0
        
        # Distinct-1 (高い方が良い)
        if d1_s > d1_o * 1.05:
            score_self += 2
        elif d1_o > d1_s * 1.05:
            score_other += 2
        
        # Self-BLEU (低い方が良い)
        if sb_s < sb_o * 0.95:
            score_self += 2
        elif sb_o < sb_s * 0.95:
            score_other += 2
        
        # JSON (高い方が良い)
        if json_s > json_o * 1.02:
            score_self += 1
        elif json_o > json_s * 1.02:
            score_other += 1
        
        if score_self > score_other:
            return "Current model shows better diversity"
        elif score_other > score_self:
            return "Baseline model shows better diversity"
        else:
            return "No significant difference"


# ============= 使用例 =============

if __name__ == "__main__":
    # サンプルデータ
    analyzer = BoilerplateAnalyzer(language="ja")
    
    # 定型的な応答
    boilerplate_responses = [
        "ご質問ありがとうございます。お答えします。",
        "ご質問ありがとうございます。説明します。",
        "ご質問ありがとうございます。回答いたします。",
    ]
    
    # 多様な応答
    diverse_responses = [
        "なるほど、面白い質問ですね！",
        "それについて考えてみましょう。",
        "良いポイントです。詳しく見ていきます。",
    ]
    
    print("=== 定型的な応答の分析 ===")
    analyzer.clear()
    analyzer.add_responses(boilerplate_responses)
    result1 = analyzer.analyze_all()
    print(f"Distinct-1: {result1['diversity']['distinct_1']['score']:.3f}")
    print(f"Self-BLEU: {result1['diversity']['self_bleu']['score']:.3f}")
    print(f"Grade: {result1['grading']}")
    
    print("\n=== 多様な応答の分析 ===")
    analyzer2 = BoilerplateAnalyzer(language="ja")
    analyzer2.add_responses(diverse_responses)
    result2 = analyzer2.analyze_all()
    print(f"Distinct-1: {result2['diversity']['distinct_1']['score']:.3f}")
    print(f"Self-BLEU: {result2['diversity']['self_bleu']['score']:.3f}")
    print(f"Grade: {result2['grading']}")
    
    print("\n=== 比較 ===")
    comparison = analyzer2.compare_with(analyzer, "Diverse", "Boilerplate")
    print(json.dumps(comparison, indent=2, ensure_ascii=False))
import json
import re
import statistics
from collections import Counter
from typing import List, Dict, Any, Optional, Tuple
import warnings


class BoilerplateAnalyzer:
    """
    定型文の多様性・パターンを定量的に分析
    
    主要指標:
    - Distinct-n: 語彙の多様性 (高いほど多様)
    - Self-BLEU: 応答間の類似度 (低いほど多様)
    - TTR: Type-Token Ratio (語彙の豊かさ)
    - JSON成功率: 構造化出力の安定性
    """

    def __init__(self, language: str = "ja"):
        """
        Args:
            language: "ja" (日本語) or "en" (英語)
        """
        self.responses: List[str] = []
        self.language = language
        self._tokenizer = None
        
        if language == "ja":
            try:
                import MeCab
                self._tokenizer = MeCab.Tagger("-Owakati")
            except ImportError:
                warnings.warn(
                    "MeCab not installed. Falling back to character-based tokenization for Japanese."
                )

    def add_response(self, response: str):
        """応答を追加"""
        if not response or not response.strip():
            warnings.warn("Empty response added")
        self.responses.append(response)

    def add_responses(self, responses: List[str]):
        """複数応答を一括追加"""
        self.responses.extend(responses)

    def clear(self):
        """応答をクリア"""
        self.responses = []

    def tokenize(self, text: str) -> List[str]:
        """言語に応じた適切なトークン化"""
        if not text:
            return []
        
        if self.language == "ja":
            if self._tokenizer:
                try:
                    return self._tokenizer.parse(text).strip().split()
                except:
                    # MeCabが失敗したら文字単位にフォールバック
                    return list(text.replace(" ", ""))
            else:
                # MeCabなしの場合は文字単位
                return list(text.replace(" ", ""))
        else:
            # 英語: 単純な空白分割 + 句読点処理
            text = re.sub(r'([.,!?;:])', r' \1 ', text)
            return text.lower().split()

    def distinct_n(self, n: int = 1) -> Dict[str, Any]:
        """
        Distinct-n: 全応答内のユニークなn-gram数 / 全n-gram数
        
        Returns:
            {
                "score": float (0.0~1.0, 高いほど多様),
                "unique_count": int,
                "total_count": int,
                "skipped_responses": int
            }
        """
        unique_ngrams = set()
        total_ngrams = 0
        skipped = 0
        
        for response in self.responses:
            tokens = self.tokenize(response)
            if len(tokens) < n:
                skipped += 1
                continue
            
            for i in range(len(tokens) - n + 1):
                ngram = tuple(tokens[i:i+n])
                unique_ngrams.add(ngram)
                total_ngrams += 1
        
        score = len(unique_ngrams) / total_ngrams if total_ngrams > 0 else 0.0
        
        return {
            "score": score,
            "unique_count": len(unique_ngrams),
            "total_count": total_ngrams,
            "skipped_responses": skipped
        }

    def self_bleu(self, max_n: int = 4, smoothing: bool = True) -> Dict[str, Any]:
        """
        Self-BLEU: 各応答と他の応答との平均BLEU値
        
        低いほど多様（応答が互いに似ていない）
        高いほど定型的（応答が互いに似ている）
        
        Args:
            max_n: n-gramの最大値 (通常4)
            smoothing: ゼロ除算を避けるスムージング
        
        Returns:
            {
                "score": float (0.0~1.0, 低いほど多様),
                "individual_scores": List[float],
                "std_dev": float
            }
        """
        if len(self.responses) < 2:
            return {
                "score": 0.0,
                "individual_scores": [],
                "std_dev": 0.0,
                "error": "Need at least 2 responses"
            }
        
        bleu_scores = []
        
        for i, response in enumerate(self.responses):
            hypothesis = self.tokenize(response)
            if not hypothesis:
                continue
            
            # 他の全応答を参照として使用
            references = [
                self.tokenize(r) 
                for j, r in enumerate(self.responses) 
                if i != j
            ]
            references = [ref for ref in references if ref]  # 空を除外
            
            if not references:
                continue
            
            # BLEU計算
            score = self._compute_bleu(hypothesis, references, max_n, smoothing)
            bleu_scores.append(score)
        
        if not bleu_scores:
            return {
                "score": 0.0,
                "individual_scores": [],
                "std_dev": 0.0,
                "error": "Could not compute BLEU"
            }
        
        return {
            "score": statistics.mean(bleu_scores),
            "individual_scores": bleu_scores,
            "std_dev": statistics.stdev(bleu_scores) if len(bleu_scores) > 1 else 0.0
        }

    def _compute_bleu(
        self, 
        hypothesis: List[str], 
        references: List[List[str]], 
        max_n: int,
        smoothing: bool
    ) -> float:
        """
        Modified BLEU計算 (sentence-level)
        
        BLEU = BP * exp(sum(w_n * log(p_n)))
        """
        # Brevity Penalty
        hyp_len = len(hypothesis)
        ref_lens = [len(ref) for ref in references]
        closest_ref_len = min(ref_lens, key=lambda x: abs(x - hyp_len))
        
        if hyp_len > closest_ref_len:
            bp = 1.0
        elif hyp_len == 0:
            return 0.0
        else:
            bp = statistics.exp(1 - closest_ref_len / hyp_len)
        
        # n-gram precisions
        log_precisions = []
        for n in range(1, max_n + 1):
            hyp_ngrams = self._get_ngrams(hypothesis, n)
            if not hyp_ngrams:
                if smoothing:
                    log_precisions.append(-10)  # 小さな値
                continue
            
            max_counts = Counter()
            for reference in references:
                ref_ngrams = self._get_ngrams(reference, n)
                for ngram in hyp_ngrams:
                    max_counts[ngram] = max(max_counts[ngram], ref_ngrams[ngram])
            
            clipped_counts = {
                ngram: min(count, max_counts[ngram])
                for ngram, count in hyp_ngrams.items()
            }
            
            numerator = sum(clipped_counts.values())
            denominator = sum(hyp_ngrams.values())
            
            if denominator == 0:
                precision = 0.0
            else:
                precision = numerator / denominator
            
            # スムージング (add-1)
            if precision == 0.0 and smoothing:
                precision = 1 / (2 * denominator)
            
            if precision > 0:
                log_precisions.append(statistics.log(precision))
        
        if not log_precisions:
            return 0.0
        
        # 幾何平均
        avg_log_precision = sum(log_precisions) / len(log_precisions)
        bleu = bp * statistics.exp(avg_log_precision)
        
        return bleu

    def _get_ngrams(self, tokens: List[str], n: int) -> Counter:
        """n-gramのカウンタを取得"""
        ngrams = [tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]
        return Counter(ngrams)

    def common_patterns(self, top_k: int = 10, ngram_sizes: List[int] = [3, 5]) -> Dict[str, Any]:
        """
        最頻出フレーズを抽出（定型文の証拠）
        
        Args:
            top_k: 上位何件を返すか
            ngram_sizes: チェックするn-gramサイズ
        
        Returns:
            {
                "3gram": [(phrase, count), ...],
                "5gram": [(phrase, count), ...],
                "total_analyzed": int
            }
        """
        results = {}
        
        for n in ngram_sizes:
            all_ngrams = []
            for response in self.responses:
                tokens = self.tokenize(response)
                if len(tokens) < n:
                    continue
                ngrams = [tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]
                all_ngrams.extend(ngrams)
            
            counter = Counter(all_ngrams)
            # 出現回数2回以上のみ（1回は定型文じゃない）
            patterns = [(self._join_tokens(ngram), count) 
                       for ngram, count in counter.most_common(top_k * 2)
                       if count > 1][:top_k]
            
            results[f"{n}gram"] = patterns
        
        results["total_analyzed"] = len(self.responses)
        return results

    def _join_tokens(self, tokens: Tuple[str, ...]) -> str:
        """トークンを結合（言語に応じて）"""
        if self.language == "ja":
            return "".join(tokens)
        return " ".join(tokens)

    def response_length_stats(self) -> Dict[str, float]:
        """応答長の統計（トークン単位）"""
        lengths = [len(self.tokenize(r)) for r in self.responses]
        
        if not lengths:
            return {
                "mean": 0, "median": 0, "stdev": 0,
                "min": 0, "max": 0, "variance": 0
            }
        
        return {
            "mean": statistics.mean(lengths),
            "median": statistics.median(lengths),
            "stdev": statistics.stdev(lengths) if len(lengths) > 1 else 0,
            "min": min(lengths),
            "max": max(lengths),
            "variance": statistics.variance(lengths) if len(lengths) > 1 else 0,
            "total_responses": len(lengths)
        }

    def json_parse_analysis(self) -> Dict[str, Any]:
        """JSON出力のパース成功率（詳細版）"""
        results = {
            "total": len(self.responses),
            "success": 0,
            "malformed": 0,
            "parse_errors": [],
            "success_rate": 0.0
        }
        
        for i, response in enumerate(self.responses):
            try:
                # より堅牢なJSON抽出（ネスト対応）
                json_match = self._extract_json(response)
                
                if not json_match:
                    results["malformed"] += 1
                    continue
                
                parsed = json.loads(json_match)
                results["success"] += 1
                
            except json.JSONDecodeError as e:
                results["parse_errors"].append({
                    "index": i,
                    "error": str(e),
                    "excerpt": response[:100] + "..." if len(response) > 100 else response
                })
        
        results["success_rate"] = results["success"] / results["total"] if results["total"] > 0 else 0.0
        return results

    def _extract_json(self, text: str) -> Optional[str]:
        """テキストからJSON文字列を抽出（ネスト対応）"""
        # 最初の { を見つける
        start = text.find('{')
        if start == -1:
            return None
        
        # ブレースのバランスを取りながら終了位置を探す
        depth = 0
        in_string = False
        escape = False
        
        for i in range(start, len(text)):
            char = text[i]
            
            if escape:
                escape = False
                continue
            
            if char == '\\':
                escape = True
                continue
            
            if char == '"':
                in_string = not in_string
                continue
            
            if in_string:
                continue
            
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i+1]
        
        return None

    def vocabulary_richness(self) -> Dict[str, Any]:
        """語彙の豊かさ（TTR, Yule's K など）"""
        all_tokens = []
        for response in self.responses:
            tokens = self.tokenize(response)
            all_tokens.extend(tokens)
        
        if not all_tokens:
            return {
                "unique_tokens": 0,
                "total_tokens": 0,
                "ttr": 0.0,
                "log_ttr": 0.0,
                "yules_k": 0.0
            }
        
        unique_tokens = len(set(all_tokens))
        total_tokens = len(all_tokens)
        ttr = unique_tokens / total_tokens
        
        # Log TTR (長いテキストでも安定)
        log_ttr = unique_tokens / statistics.log(total_tokens) if total_tokens > 1 else 0.0
        
        # Yule's K (語彙の偏り: 低いほど均等)
        token_freq = Counter(all_tokens)
        freq_freq = Counter(token_freq.values())
        
        M1 = sum(freq_freq.values())
        M2 = sum(freq * (count ** 2) for freq, count in freq_freq.items())
        
        yules_k = 10000 * (M2 - M1) / (M1 ** 2) if M1 > 0 else 0.0
        
        return {
            "unique_tokens": unique_tokens,
            "total_tokens": total_tokens,
            "ttr": ttr,  # 0.0~1.0, 高いほど多様
            "log_ttr": log_ttr,
            "yules_k": yules_k,  # 低いほど語彙が均等に分布
            "top_10_tokens": token_freq.most_common(10)
        }

    def confidence_interval(
        self, 
        metric_name: str,
        confidence: float = 0.95,
        n_bootstrap: int = 1000
    ) -> Dict[str, Any]:
        """
        ブートストラップ法で信頼区間を計算
        
        Args:
            metric_name: "distinct_1", "distinct_2", "self_bleu" など
            confidence: 信頼水準 (0.95 = 95%)
            n_bootstrap: ブートストラップ回数
        """
        if len(self.responses) < 10:
            return {
                "error": "Need at least 10 responses for reliable confidence intervals"
            }
        
        import random
        
        metric_map = {
            "distinct_1": lambda: self.distinct_n(1)["score"],
            "distinct_2": lambda: self.distinct_n(2)["score"],
            "distinct_3": lambda: self.distinct_n(3)["score"],
            "self_bleu": lambda: self.self_bleu()["score"],
            "ttr": lambda: self.vocabulary_richness()["ttr"],
        }
        
        if metric_name not in metric_map:
            return {"error": f"Unknown metric: {metric_name}"}
        
        bootstrap_scores = []
        original_responses = self.responses.copy()
        
        for _ in range(n_bootstrap):
            # リサンプリング
            sample = random.choices(original_responses, k=len(original_responses))
            self.responses = sample
            
            try:
                score = metric_map[metric_name]()
                bootstrap_scores.append(score)
            except:
                continue
        
        self.responses = original_responses
        
        if not bootstrap_scores:
            return {"error": "Bootstrap failed"}
        
        bootstrap_scores.sort()
        alpha = 1 - confidence
        lower_idx = int(len(bootstrap_scores) * alpha / 2)
        upper_idx = int(len(bootstrap_scores) * (1 - alpha / 2))
        
        return {
            "metric": metric_name,
            "mean": statistics.mean(bootstrap_scores),
            "median": statistics.median(bootstrap_scores),
            "lower_bound": bootstrap_scores[lower_idx],
            "upper_bound": bootstrap_scores[upper_idx],
            "confidence": confidence,
            "n_bootstrap": len(bootstrap_scores)
        }

    def grade_diversity(self) -> Dict[str, str]:
        """
        多様性の総合評価（ベンチマーク比較）
        
        Returns:
            各指標の評価 ("excellent", "good", "fair", "poor")
        """
        BENCHMARKS = {
            "distinct_1": {"excellent": 0.85, "good": 0.70, "fair": 0.50},
            "distinct_2": {"excellent": 0.75, "good": 0.60, "fair": 0.40},
            "self_bleu": {"excellent": 0.30, "good": 0.50, "fair": 0.70},  # 低い方が良い
            "ttr": {"excellent": 0.60, "good": 0.45, "fair": 0.30},
            "json_success": {"excellent": 0.95, "good": 0.85, "fair": 0.70}
        }
        
        def grade(value: float, thresholds: Dict[str, float], inverse: bool = False) -> str:
            if inverse:
                if value <= thresholds["excellent"]:
                    return "excellent"
                elif value <= thresholds["good"]:
                    return "good"
                elif value <= thresholds["fair"]:
                    return "fair"
                else:
                    return "poor"
            else:
                if value >= thresholds["excellent"]:
                    return "excellent"
                elif value >= thresholds["good"]:
                    return "good"
                elif value >= thresholds["fair"]:
                    return "fair"
                else:
                    return "poor"
        
        results = {}
        
        distinct_1 = self.distinct_n(1)["score"]
        results["distinct_1"] = grade(distinct_1, BENCHMARKS["distinct_1"])
        
        distinct_2 = self.distinct_n(2)["score"]
        results["distinct_2"] = grade(distinct_2, BENCHMARKS["distinct_2"])
        
        self_bleu = self.self_bleu()["score"]
        results["self_bleu"] = grade(self_bleu, BENCHMARKS["self_bleu"], inverse=True)
        
        ttr = self.vocabulary_richness()["ttr"]
        results["ttr"] = grade(ttr, BENCHMARKS["ttr"])
        
        json_rate = self.json_parse_analysis()["success_rate"]
        results["json_success"] = grade(json_rate, BENCHMARKS["json_success"])
        
        return results

    def analyze_all(self) -> Dict[str, Any]:
        """全指標を一括計算"""
        if not self.responses:
            return {"error": "No responses to analyze"}
        
        return {
            "meta": {
                "sample_count": len(self.responses),
                "language": self.language,
                "tokenizer": "MeCab" if self._tokenizer else "fallback"
            },
            "diversity": {
                "distinct_1": self.distinct_n(n=1),
                "distinct_2": self.distinct_n(n=2),
                "distinct_3": self.distinct_n(n=3),
                "self_bleu": self.self_bleu(),
                "vocabulary": self.vocabulary_richness(),
            },
            "patterns": self.common_patterns(top_k=10),
            "structure": {
                "response_length": self.response_length_stats(),
                "json_parse": self.json_parse_analysis(),
            },
            "grading": self.grade_diversity()
        }

    def compare_with(self, other: 'BoilerplateAnalyzer', label_self: str = "Current", label_other: str = "Baseline") -> Dict[str, Any]:
        """
        別のアナライザーと比較（A/Bテスト用）
        
        Args:
            other: 比較対象のアナライザー
            label_self: 自分のラベル
            label_other: 相手のラベル
        """
        def compare_metric(name: str, val_self: float, val_other: float, higher_is_better: bool = True) -> Dict:
            diff = val_self - val_other
            pct_change = (diff / val_other * 100) if val_other != 0 else 0
            
            if higher_is_better:
                better = label_self if diff > 0 else label_other
            else:
                better = label_self if diff < 0 else label_other
            
            return {
                label_self: val_self,
                label_other: val_other,
                "difference": diff,
                "percent_change": pct_change,
                "better": better if abs(pct_change) > 5 else "similar"  # 5%未満は誤差
            }
        
        # 各指標を比較
        d1_self = self.distinct_n(1)["score"]
        d1_other = other.distinct_n(1)["score"]
        
        sb_self = self.self_bleu()["score"]
        sb_other = other.self_bleu()["score"]
        
        ttr_self = self.vocabulary_richness()["ttr"]
        ttr_other = other.vocabulary_richness()["ttr"]
        
        json_self = self.json_parse_analysis()["success_rate"]
        json_other = other.json_parse_analysis()["success_rate"]
        
        return {
            "distinct_1": compare_metric("distinct_1", d1_self, d1_other, higher_is_better=True),
            "self_bleu": compare_metric("self_bleu", sb_self, sb_other, higher_is_better=False),
            "ttr": compare_metric("ttr", ttr_self, ttr_other, higher_is_better=True),
            "json_success": compare_metric("json_success", json_self, json_other, higher_is_better=True),
            "summary": {
                "total_responses": {label_self: len(self.responses), label_other: len(other.responses)},
                "recommendation": self._recommend(d1_self, d1_other, sb_self, sb_other, json_self, json_other)
            }
        }

    def _recommend(self, d1_s, d1_o, sb_s, sb_o, json_s, json_o) -> str:
        """どちらが良いか総合判定"""
        score_self = 0
        score_other = 0
        
        # Distinct-1 (高い方が良い)
        if d1_s > d1_o * 1.05:
            score_self += 2
        elif d1_o > d1_s * 1.05:
            score_other += 2
        
        # Self-BLEU (低い方が良い)
        if sb_s < sb_o * 0.95:
            score_self += 2
        elif sb_o < sb_s * 0.95:
            score_other += 2
        
        # JSON (高い方が良い)
        if json_s > json_o * 1.02:
            score_self += 1
        elif json_o > json_s * 1.02:
            score_other += 1
        
        if score_self > score_other:
            return "Current model shows better diversity"
        elif score_other > score_self:
            return "Baseline model shows better diversity"
        else:
            return "No significant difference"


if __name__ == "__main__":
    # サンプルデータ
    analyzer = BoilerplateAnalyzer(language="ja")
    
    # 定型的な応答
    boilerplate_responses = [
        "【感情的トリガー】不安と期待が混在している。【情報的インプット】過去の成功例と現在の状況が似ている。【思考の変遷】迷いながらも前に進もうと決めた。【DECISION】挑戦する。【ACTION】準備を始める。【NUANCE】少し不安な表情。【DIALOGUE】「やってみます」。【BEHAVIOR】深く息を吸った。",
        "【感情的トリガー】焦燥感。【情報的インプット】時間が限られている。【思考の変遷】急いで決断した。【DECISION】急ぐ。【ACTION】すぐに実行する。【NUANCE】急いでいる様子。【DIALOGUE】「急ぎます」。【BEHAVIOR】立ち上がった。",
        "【感情的トリガー】淡々とした事実確認。【情報的インプット】自身の年齢。【思考の変遷】聞かれたことに簡潔に答える。【DECISION】事実を述べる。【ACTION】回答する。【NUANCE】落ち着いた口調。【DIALOGUE】「年齢は16歳です」。【BEHAVIOR】相手の目を軽く見る。",
        "【感情的トリガー】社会的カテゴリーに対する違和感。【情報的インプット】「Z世代」という括りと個人の実態のギャップ。【思考の変遷】集団で評価されることへの抵抗と、個としての努力の必要性を分析した。【DECISION】持論を展開する。【ACTION】分析的な意見を述べる。【NUANCE】少し理屈っぽいが熱意がある。【DIALOGUE】「Z世代ですが、まあ周囲にいる人の性質が現れただけで頑張る人は頑張ってるから集団の評価として個人を見るべきではないという、独自路線とか頑張るならこの人は違うと思われるレベルに頑張らなければいけないことが大変だなって思います。」。【BEHAVIOR】視線を少し宙に浮かせて考えながら話す。",
        "【感情的トリガー】地元への愛着。【情報的インプット】居住地の環境（八王子）。【思考の変遷】都会すぎず田舎すぎないバランスの良さを再確認した。【DECISION】良さを伝える。【ACTION】地元の特徴を挙げる。【NUANCE】リラックスした雰囲気。【DIALOGUE】「割と面積としてはでかい市ですね。大都市とは違うと思うけどそれなりに道は広いし人は温厚だし、それなりに人の雰囲気も好きですね。」。【BEHAVIOR】うんうんと頷く。",
        "【感情的トリガー】現状への納得感。【情報的インプット】高校生としての身分と住環境。【思考の変遷】親に感謝しつつ、現状を説明する。【DECISION】謙虚に答える。【ACTION】立場を明確にする。【NUANCE】感謝の念が含まれる。【DIALOGUE】「私は持ち家に住まさせてもらっている身の高校生です。」。【BEHAVIOR】少し背筋を伸ばす。",
        "【感情的トリガー】将来への展望。【情報的インプット】理想の住環境の条件。【思考の変遷】今の住環境が良いので、将来も似たような条件（自然＋利便性）を求めている。【DECISION】希望を語る。【ACTION】具体的な条件を挙げる。【NUANCE】虫嫌いという個人的な本音。【DIALOGUE】「今みたいな地域に住みたいですね。めちゃくちゃ苦労するとかではないけどそれなりに自然がある不便しないぐらいの環境に住みたいです。虫とか嫌なので。」。【BEHAVIOR】苦笑いをする。",
        "【感情的トリガー】知的好奇心と熱量。【情報的インプット】現在取り組んでいる技術（AI/LLM）。【思考の変遷】自分の専門分野について具体的に説明したい欲求。【DECISION】詳細を語る。【ACTION】技術的な取り組みを説明する。【NUANCE】目が輝く、早口になる。【DIALOGUE】「今やってる分野はコンピューターの中でもAIで、LLMの学習のほかに画像からAIの応答を生成するようにしたりしています。」。【BEHAVIOR】身を乗り出す。",
        "【感情的トリガー】自己定義への戸惑い。【情報的インプット】学生だがアルバイトをしていない状況。【思考の変遷】社会的な職業分類に当てはめようとして少し迷う。【DECISION】自嘲気味に分析する。【ACTION】疑問形で答える。【NUANCE】少し気まずいが論理的。【DIALOGUE】「現在の職業は学生?バイトはしてないから無職になるのかな」。【BEHAVIOR】首を傾げる。",
        "【感情的トリガー】職場環境への不満。【情報的インプット】非効率な上司の態度。【思考の変遷】管理能力不足の上司に対するフラストレーションを思い出した。【DECISION】率直に不満を述べる。【ACTION】批判的な意見を言う。【NUANCE】呆れた様子。【DIALOGUE】「仕事でストレスを感じるのは、うまい管理ができず自分でも動こうとしないやる気がないくせにやる気を押し付けてくる上司」。【BEHAVIOR】ため息をつく。",
        "【感情的トリガー】謙遜と自負。【情報的インプット】これまでの実績。【思考の変遷】大きな実績はないが、今作っているシステムには自信がある。【DECISION】控えめにアピールする。【ACTION】現在の成果物を挙げる。【NUANCE】照れ隠し。【DIALOGUE】「ない。強いていうなら今作っている自己分析可能なAIシステムの構築ぐらい?」。【BEHAVIOR】視線を一度落としてから上げる。",
        "【感情的トリガー】自己認識（金銭感覚）。【情報的インプット】お金を持つと使ってしまう癖。【思考の変遷】自分の弱点を理解し、物理的な対策（持ち歩かない）を講じていることを伝える。【DECISION】弱みを認める。【ACTION】対処法を語る。【NUANCE】苦笑い。【DIALOGUE】「お金の管理は、うーん苦手な部類な気がする。お金を持つと大変すぐ減るので、持ち歩かないようにしてる。」。【BEHAVIOR】頭をかく。",
        "【感情的トリガー】所有欲と合理性。【情報的インプット】デバイスへの出費。【思考の変遷】作業効率や興味のために必要なものには金を惜しまない。【DECISION】使い道を断言する。【ACTION】対象を特定する。【NUANCE】はっきりとした意志。【DIALOGUE】「お金を最も使いのは、欲しいデバイスにだね。基本的に作業とか欲しいものとか、が欲しいものに当たるんだけどそれに使う。」。【BEHAVIOR】手元にあるガジェットを触る。",
        "【感情的トリガー】自己分析。【情報的インプット】自分の性格を表すキーワード。【思考の変遷】自分を客観視し、適切な単語を選定した。【DECISION】キーワードを列挙する。【ACTION】性格を定義する。【NUANCE】分析的で客観的。【DIALOGUE】「自分の性格を5つの言葉で表すと、分析的、研究者、好奇心旺盛、頼りきり、興味で生きるになるかな。」。【BEHAVIOR】指折り数える。",
        "【感情的トリガー】人生哲学。【情報的インプット】人生における優先順位。【思考の変遷】全ての行動の源泉は「知りたい」という欲求にあると確信している。【DECISION】核心を突く。【ACTION】信念を語る。【NUANCE】真剣な眼差し。【DIALOGUE】「私が人生で最も大切にしてのは、好奇心ですね。」。【BEHAVIOR】力強く頷く。",
        "【感情的トリガー】成功への執着と合理主義。【情報的インプット】勝負と目的の関係性。【思考の変遷】形式的な勝利よりも、実利（目的達成）を重視する独自の哲学。【DECISION】定義を語る。【ACTION】成功の再定義を行う。【NUANCE】冷徹だが合理的。【DIALOGUE】「成功とは、目的を達成すること、試合に負けても勝負に勝ったらそれでいい、勝負っていうのは自分の目的を達成するのに近づくかっていう話ね」。【BEHAVIOR】淡々と語る。",
        "【感情的トリガー】個人的なエゴイズム。【情報的インプット】協力よりも独占欲。【思考の変遷】未知の体験を他人に譲りたくない、自分が最初に踏みたいという欲求。【DECISION】本音を漏らす。【ACTION】独走を宣言する。【NUANCE】独占欲と探究心。【DIALOGUE】「他人と協力するよりも一人でやりたい、だって自分が体験できたかもしれないことを他者が受けるのは嫌でしょ。嫌なことは先に体験して先に対策させてから他者に歩かせたい。」。【BEHAVIOR】腕を組む。",
        "【感情的トリガー】信念。【情報的インプット】全力で生きることの重要性。【思考の変遷】後悔（燃え滓）を残さないために、現在の燃焼が必要だと考えている。【DECISION】信条を吐露する。【ACTION】熱く語る。【NUANCE】詩的な表現。【DIALOGUE】「私の信念は今を全力で生きろ、だって全力で生きないとその心のこりが燃え滓として後で苦しくなる理由になるからね。」。【BEHAVIOR】拳を握る。",
        "【感情的トリガー】対人評価への受容。【情報的インプット】他人からの見られ方。【思考の変遷】自分が「質問魔」として認知されていることを自覚している。【DECISION】評価を受け入れる。【ACTION】周囲の認識を述べる。【NUANCE】少しおどけた様子。【DIALOGUE】「他人からは、とりあえず変な聞きまくる人っていう認識だね」。【BEHAVIOR】肩をすくめる。",
        "【感情的トリガー】社会的課題への関心。【情報的インプット】AIの進化と人類の制御能力（2027年問題）。【思考の変遷】技術の進歩に対する懸念と、それに向き合う必要性を感じている。【DECISION】問題提起する。【ACTION】懸念事項を詳しく話す。【NUANCE】真面目で思慮深い。【DIALOGUE】「2027年問題とか? AGIとかのAIが人間の性能の外側に出てその自分より強い道具を果たして人間は扱い切れるのかという問題に対して今向き合ってるからそこについてかな」。【BEHAVIOR】遠くを見る目。",
        "【感情的トリガー】リラックスと安らぎ。【情報的インプット】音楽の好み（ボカロ・ヒーリング系）。【思考の変遷】精神的な安定を求めて音楽を聴いていることを認識。【DECISION】好みを共有する。【ACTION】ジャンルを挙げる。【NUANCE】穏やかな表情。【DIALOGUE】「聞く音楽のジャンルでいうと、ボカロって言われるジャンルかなその中でもヒーリング系のj-popに関係するところ聞きがちな気がする」。【BEHAVIOR】リズムを刻むように指を動かす。",
        "【感情的トリガー】健康意識の単純化。【情報的インプット】食生活のルール。【思考の変遷】細かいことは気にせず、一点（野菜）のみに集中している。【DECISION】簡潔に答える。【ACTION】宣言する。【NUANCE】勢いがある。【DIALOGUE】「食生活で気をつけていることは、野菜を摂ろう以上！！」。【BEHAVIOR】手でバツを作るような仕草（以上、の意）。",
        "【感情的トリガー】興味の対象への没頭。【情報的インプット】人間の心理メカニズム。【思考の変遷】AIを作る上で、人間の「感情」や「恐怖」の原理を知りたくなった。【DECISION】探究心を露わにする。【ACTION】興味の対象を語る。【NUANCE】研究者肌。【DIALOGUE】「最近、最も興味を持っていることは、人間はなぜ恐怖するのか、人間はなぜ感情という処理をするのかとかそういった人間の処理の原理みたいなところが気になる。」。【BEHAVIOR】顎に手を当てる。"
    ]
    
    # 多様な応答
    diverse_responses = [
        "年齢は16歳です",
"性別は男性です",
"私の婚姻状況はなし。",
"同居している家族構成は弟・両親・私です。",
"Z世代ですが、まあ周囲にいる人の性質が現れただけで頑張る人は頑張ってるから集団の評価として個人を見るべきではないという、独自路線とか頑張るならこの人は違うと思われるレベルに頑張らなければいけないことが大変だなって思います。",
"ライフステージは青年期です。",
"家族との関係性は良好です。しかし会話の数は少ないし、私から会話することもあんまりないですが、よくTVとかに行ったりします。",
"私は日本で東京八王子市に住んでいます。",
"割と面積としてはでかい市ですね。大都市とは違うと思うけどそれなりに道は広いし人は温厚だし、それなりに人の雰囲気も好きですね。",
"私は持ち家に住まさせてもらっている身の高校生です。",
"現在の場所には15年ぐらい住んでいます。",
"通勤・通学時間は1時間45分ぐらいかかります。",
"交通手段は電車を利用しています。",
"現在の居住地には非常に満足しています。理由は程よく自然があり、不便にならない程度に店があるので過ごしやすいです。",
"今みたいな地域に住みたいですね。めちゃくちゃ苦労するとかではないけどそれなりに自然がある不便しないぐらいの環境に住みたいです。虫とか嫌なので。",
"地域のコミュニティとの関わりはあるけど薄いですね。祭りとかも参加するくらい",
"私の最終学歴は、今高校在学中だから中卒ですね。",
"今やってる分野はコンピューターの中でもAIで、LLMの学習のほかに画像からAIの応答を生成するようにしたりしています。",
"現在の職業は学生?バイトはしてないから無職になるのかな",
"キャリアにおける目標は、とりあえずAIの仕事をしたい。",
"副業はしてないっていうかcoconaraとかやってるけどそもそも仕事が受注できない。",
"仕事でストレスを感じるのは、うまい管理ができず自分でも動こうとしないやる気がないくせにやる気を押し付けてくる上司",
"今はとりあえず自分のコントロールに使ってるから、他の人がどんなことを欲してるのか、どんな需要があるのかを探してその需要を満たす方法を探せるスキルかな",
"業界の動向についての情報収集は、とりまYoutubeでたまにニュース見てる",
"{'detected_tenses': [{'tense': '現在・習慣・未来', 'pattern': '(る|す)$', 'confidence': '確実（文法的パターン）'}], 'has_temporal_info': True}",
"Q. これまでのキャリアで最も誇りに思うことは何ですか？ A. ない。強いていうなら今作っている自己分析可能なAIシステムの構築ぐらい?",
"現在の収入に満足してる、不自由なく生活させてもらってるのでまあ",
"お金の管理は、うーん苦手な部類な気がする。お金を持つと大変すぐ減るので、持ち歩かないようにしてる。",
"お金を最も使いのは、欲しいデバイスにだね。基本的に作業とか欲しいものとか、が欲しいものに当たるんだけどそれに使う。",
"お金に対する価値観は使うべき時に使う、それ以外はケチれ",
"経済的な目標は、別にないけど欲しいデバイスがあったら買えるぐらいにはお金は欲しいね。それ以外は生きられたらいいかな。",
"ユーザーの価値観、興味、ライフスタイルなど、内面的な特徴を理解するための質問です。",
"自分の性格を5つの言葉で表すと、分析的、研究者、好奇心旺盛、頼りきり、興味で生きるになるかな。",
"私が人生で最も大切にしてのは、好奇心ですね。",
"新しいことにどんどん挑戦したいね、この人生はいろんな種類の意味を繋げておきたい。",
"物事を決める時は、基本的に直感を信じているけど、重要な場合は論理的に考える",
"{'detected_tenses': [{'tense': '現在進行・状態', 'pattern': '(て|で)いる', 'confidence': '確実（文法的パターン）'}, {'tense': '現在・習慣・未来', 'pattern': '(る|す)$', 'confidence': '確実（文法的パターン）'}], 'has_temporal_info': True}",
"成功とは、目的を達成すること、試合に負けても勝負に勝ったらそれでいい、勝負っていうのは自分の目的を達成するのに近づくかっていう話ね",
"幸福とは、今の状態における相対的な+な状態に持っていく体験。",
"リスクとは常にあるものだからそれを優先的に取って先にリターンを得られるようにするから別にいい悪いではなく性質の話だと思うよ",
"他人と協力するよりも一人でやりたい、だって自分が体験できたかもしれないことを他者が受けるのは嫌でしょ。嫌なことは先に体験して先に対策させてから他者に歩かせたい。",
"ストレスは基本的にその目的が達成できない時に出るもの。だから、その道でずっとストレスが溜まるならその歩き方が悪いから、リフレッシュとして歩いたりすることで解消する。",
"目標に向かって走り続けられることが長所、短所は周りが見えなくなること",
"自分の欲求で欲しいとか、そういうった自分の感覚でいいと思ったことに上演つを感じる。",
"私ののロールモデルはいるかわからんけど、強いていうなら、好奇心旺盛に生きろっていうというか発明王のエジソンかな、ただあの人はどっちかっていうと特許王だけど。",
"私の信念は今を全力で生きろ、だって全力で生きないとその心のこりが燃え滓として後で苦しくなる理由になるからね。",
"私は、完璧じゃなくていいし、目的達成できるなら別にいいでしょっていう考え方。",
"私は、間違いなく内向的",
"変化に対しては、知る、仮説立てる、試す、知る、まあPDCAサイクル回すだけで対応する。",
"他人からは、とりあえず変な聞きまくる人っていう認識だね",
"お金はある程度恵んでもらったり助けとして養成することでなんとかなるかもしれんけど、時間はそんな買えないしね。あとお金って信用の具現化したものだから正直、回答するなら時間だけど、それよりも人間関係とかの繋がりの方が大事なんじゃないかなって思ってる",
"{'detected_tenses': [{'tense': '現在・習慣・未来', 'pattern': '(る|す)$', 'confidence': '確実（文法的パターン）'}], 'has_temporal_info': True}",
"2027年問題とか? AGIとかのAIが人間の性能の外側に出てその自分より強い道具を果たして人間は扱い切れるのかという問題に対して今向き合ってるからそこについてかな",
"倫理的に正しい行動ね、うーんAIとかが暴走した時ようにkill switchを残すとかになるのかな。",
"休日は普段、youtube見てる、恥ずかしながらね。",
"趣味や熱中してことはその時々によるけど、たまに思いつたものを3d cg でblenderやったりとかその時々かな、でも一番落ち着くのは散歩だね",
"聞く音楽のジャンルでいうと、ボカロって言われるジャンルかなその中でもヒーリング系のj-popに関係するところ聞きがちな気がする",
"{'detected_tenses': [{'tense': '現在・習慣・未来', 'pattern': '(る|す)$', 'confidence': '確実（文法的パターン）'}], 'has_temporal_info': True}",
"好きな映画やテレビ番組のジャンルは、映画ってなると厳しいけどアニメならよく見てるかな、Dr.stoneとか第七王子とか。その辺の映画だとクレヨンしんちゃんとか、あと名探偵コナンの映画は見てる。",
"よく読む本や雑誌、ウェブサイトって聞かれると難しいけど、本でいうと技術書は見るかな、あと最近哲学の入門の本みた。最近心理学とか哲学とか大きな課題に相対した時にどんな考え方をしたらいいのかとかのそういった分野が好きだからこの情報は非常に助かるんだよね。",
"最近弟と、ソフトボールをするから、スポーツはしてるかも。",
"旅行は好きいろんな見たことないが見つかるからいいよね。",
"健康やウェルネスについては、最近座ってるからストレッチとかは気にしてるかな",
"食生活で気をつけていることは、野菜を摂ろう以上！！",
"ファッションスタイルの好みは、ゆったりとしたものが好き。理由は単純に自分の痩せほそり具合を隠せるから",
"1日のうち、最も好きな時間は、朝で誰もいない静かな5時代が好き。",
"私は、インドア派だね。",
"レストランやカフェはそこまで行かない、なぜなら高いから。強いても友達とか先輩と行く時ぐらいだよ",
"ペットとの時間はないね、だってペットいないから。",
"どのようなスキルを趣味で、学びたいかなら、AIとかITとかで困ってる会社とかの助けになるような仕事とかがしたいからそのスキル。",
"ボランティア活動や地域活動に参加いるかは、割とないけど、ゴミ拾いぐらいならしてる。",
"アートや文化活動（美術館、コンサートなど）に興味が割とあるかな、美術館はあんまいったことないから後で行ってみようかなってぐらい。",
"休暇はリラックスできるものが好きだね。今のうちだから休日にアドベンチャーなことはしてみたさはあるけど場所が遠かったりするんだよねだからそっちの方かな。",
"1日のスクリーンタイムは、8時間。うん長い。",
"どのようなオンラインコミュニティに参加しているかっていったらね。ローカルLLMの会、AI音声の会、学校のプログラミングコミュニティー、ゲームと結構AIと、プログラミングとゲームがメインだね。",
"最近、最も興味を持っていることは、人間はなぜ恐怖するのか、人間はなぜ感情という処理をするのかとかそういった人間の処理の原理みたいなところが気になる。",
"先きんは、AI系のニュースは見るかな最近は心理学系のニュースとか見ても面白かもなって思った。",
"フォローしているインフルエンサーや専門家はいるにはいるけど、ウスタク... っていう最近見てない人とか、いろんな人を見てる前まで3d系でやってたからそれで、3d関係のスクールの人とかフォローしてるかな専門家っていう人はあんまいないかも",
"新しいテクノロジーやガジェットに興味がめっちゃある。VRとかARとか興味あるしなんならmeta quest 3でyoutube見たりARコンテンツやって楽しんでるもん。",
"環境問題については、どれくらいITを進めるべきかっていう回答になるからめっちゃ気にした方がいいと思うけどあんま見てなかったんだよなみよ。",
"政治や経済に関心は、そんなに興味はないけど見ないとなって思う。",
"ブランドに共感は、あんま見てなかったし使ってないかも、ただAnkerっていう製品はある程度やすくいい品質のものをとかで普通にいいなって思ってる同じ理由でユニクロも好き。",
"自己投資として、ジェットを買ってる。",
"学びたいと思っている新しいスキルや知識は、心理学とか人がなぜそのように反応するのとかヒューマンスキルを身に付けたい。",
"世の中のトレンドについては、X(twitter)で得てる。"
    ]
    
    print("=== 定型的な応答の分析 ===")
    analyzer.clear()
    analyzer.add_responses(boilerplate_responses)
    result1 = analyzer.analyze_all()
    print(f"Distinct-1: {result1['diversity']['distinct_1']['score']:.3f}")
    print(f"Self-BLEU: {result1['diversity']['self_bleu']['score']:.3f}")
    print(f"Grade: {result1['grading']}")
    
    print("\n=== 多様な応答の分析 ===")
    analyzer2 = BoilerplateAnalyzer(language="ja")
    analyzer2.add_responses(diverse_responses)
    result2 = analyzer2.analyze_all()
    print(f"Distinct-1: {result2['diversity']['distinct_1']['score']:.3f}")
    print(f"Self-BLEU: {result2['diversity']['self_bleu']['score']:.3f}")
    print(f"Grade: {result2['grading']}")
    
    print("\n=== 比較 ===")
    comparison = analyzer2.compare_with(analyzer, "Diverse", "Boilerplate")
    print(json.dumps(comparison, indent=2, ensure_ascii=False))