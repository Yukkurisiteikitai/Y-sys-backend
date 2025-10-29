
import sys
import json
import importlib.metadata

# トラッカーを設定
imported_modules = set()
original_import = __builtins__.__import__

def track_import(name, *args, **kwargs):
    top_level = name.split('.')[0]
    imported_modules.add(top_level)
    return original_import(name, *args, **kwargs)

__builtins__.__import__ = track_import

# スクリプトを実行
try:
    with open(r'main_api.py', 'r', encoding='utf-8') as f:
        code = f.read()
    exec(code, {'__name__': '__main__', '__file__': r'main_api.py'})
except Exception as e:
    print(f"実行エラー: {e}", file=sys.stderr)

# 結果を出力
print("__IMPORTS_START__")
print(json.dumps(list(imported_modules)))
print("__IMPORTS_END__")
