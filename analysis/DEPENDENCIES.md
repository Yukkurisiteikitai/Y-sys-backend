# 分析モジュール依存関係ドキュメント

## near_word_checker.py: BoilerplateAnalyzer

`BoilerplateAnalyzer` クラスは、LLMの応答における定型文パターンと多様性を定量的に分析するためのユーティリティです。

### 主要機能

- **Distinct-n 分析**: n-gram の語彙多様性を計測（高いほど多様性が高い）
- **Self-BLEU 計測**: 応答間の類似度を計測（低いほど多様性が高い）
- **TTR（Type-Token Ratio）**: 語彙の豊かさを計測
- **JSON成功率**: 構造化出力の安定性を計測
- **ボキャブラリー分析**: 使用語彙の統計分析

### 言語サポート

#### 日本語（デフォルト）

**依存パッケージ**: `MeCab` + `mecab-ipadic`

MeCab は形態素解析器で、日本語テキストを単語単位に分割するために使用されます。

**インストール手順**:

```bash
# macOS (Homebrew)
brew install mecab mecab-ipadic

# Ubuntu/Debian
sudo apt-get install mecab libmecab-dev mecab-ipadic mecab-ipadic-utf8

# Windows
# 公式インストーラーをダウンロード: https://taku910.github.io/mecab/
```

**Python バイディング**:

```bash
# すでに requirements.txt には含まれていません
# 必要に応じて手動インストール:
pip install mecab-python3
```

**フォールバック処理**:

MeCab がインストールされていない場合、自動的に文字単位のトークン化にフォールバックします。
この場合、分析の精度は低下しますが、機能は動作し続けます。

#### 英語

英語の場合、組み込みの正規表現ベースのトークナイザーを使用します。
追加の依存関係は不要です。

### 使用例

```python
from analysis.near_word_checker import BoilerplateAnalyzer

# 初期化（日本語）
analyzer = BoilerplateAnalyzer(language="ja")

# 応答データを追加
analyzer.add_response("【感情的トリガー】不安と期待が混在している。...")
analyzer.add_response("【感情的トリガー】焦燥感。...")

# 多様性分析を実行
metrics = analyzer.analyze_diversity()

print(f"Distinct-1: {metrics['distinct_1']}")
print(f"Distinct-2: {metrics['distinct_2']}")
print(f"Self-BLEU: {metrics['self_bleu']}")
print(f"TTR: {metrics['ttr']}")
```

### 既知の制限

1. **MeCab 非インストール時**: 文字単位の分析となるため、n-gram が小さくなります
2. **言語混在テキスト**: 日本語・英語が混在すると、トークン化の精度が低下する可能性があります
3. **特殊フォーマット**: JSON等の構造化データが含まれると、トークン化に失敗する可能性があります

### 推奨構成

本番環境では以下の構成を推奨します：

```bash
# 依存パッケージをインストール
pip install -r requirements.txt

# MeCab を別途インストール（Linuxの場合）
sudo apt-get install mecab libmecab-dev mecab-ipadic mecab-ipadic-utf8
pip install mecab-python3

# インストール確認
python -c "import MeCab; print(MeCab.Tagger())"
```

### 統合テスト

分析モジュール全体のテストは以下のコマンドで実行できます：

```bash
python analysis/test_boilerplate_analysis.py
```

エラーが発生する場合は、MeCab のインストールを確認してください。
