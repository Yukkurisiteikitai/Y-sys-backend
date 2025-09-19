# Gemini Customization

This file helps customize Gemini's behavior for this project.

## Project Overview

(A brief description of the project's purpose, technologies used, and key architectural patterns. This helps Gemini understand the context.)

## Preferences

(Your preferences for interacting with Gemini. For example, preferred language, coding style, or libraries.)

## Important Files

(A list of important files or directories that Gemini should pay attention to.)

## 依存ライブラリの調査記録

### ChromaDB クライアント初期化 (2025/09/19調査)

- **課題:** `RAGStorage`の初期化時に`Chroma init failed`という警告が発生していた。
- **原因:** メモリ内DBの初期化に、古い非推奨の`chromadb.Client`が使われていた。
- **解決策:** 最新の推奨方法である`chromadb.EphemeralClient()`を使用するように`lm_studio_rag/storage.py`を修正。
- **内部アーキテクチャ:**
  - `EphemeralClient`や`PersistentClient`は、実際にはクライアントを生成する**ファクトリ関数**である。
  - これらの関数は、`is_persistent`フラグ（`True`か`False`か）を設定した`Settings`オブジェクトを作成する。
  - この`Settings`オブジェクトが`Client`クラスに渡される。
  - `Client`クラスは、受け取った`Settings`に基づいて`System`（工場）を起動し、`ServerAPI`（エンジン）のインスタンスを取得する。
  - `Settings`に応じて、`ServerAPI`はインメモリで動作したり、ディスクに永続化したりする。`Client`クラス自身は、実際の処理を`ServerAPI`に委譲するプロキシとして機能する。