#!/bin/bash

# 監視したいファイル名を設定
OUTPUT_FILE="stream_response.txt"

# ファイルが存在するか確認
if [ ! -f "$OUTPUT_FILE" ]; then
    echo "エラー: ファイル '$OUTPUT_FILE' が見つかりません。"
    echo "先にPythonスクリプトを実行してファイルを作成してください。"
    exit 1
fi

# 1秒ごとに画面をクリアしてcatコマンドを実行
# watchコマンドの-dオプションで変更箇所がハイライト表示されます
watch -n 1 -d cat "$OUTPUT_FILE"