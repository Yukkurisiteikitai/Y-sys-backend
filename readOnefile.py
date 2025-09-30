import ast
import os
import sys

def get_module_source(module_name, current_dir):
    """
    モジュール名からソースコードを取得しようと試みる。
    ローカルファイル、またはsys.pathを通じてアクセス可能なモジュールを優先。
    """
    try:
        # ローカルファイルとして存在するか確認
        if os.path.exists(os.path.join(current_dir, f"{module_name}.py")):
            with open(os.path.join(current_dir, f"{module_name}.py"), 'r', encoding='utf-8') as f:
                return f.read(), os.path.join(current_dir, f"{module_name}.py")
        
        # パッケージ内のモジュールの場合
        parts = module_name.split('.')
        package_path = os.path.join(current_dir, *parts[:-1])
        if os.path.exists(os.path.join(package_path, f"{parts[-1]}.py")):
            with open(os.path.join(package_path, f"{parts[-1]}.py"), 'r', encoding='utf-8') as f:
                return f.read(), os.path.join(package_path, f"{parts[-1]}.py")
        
        # sys.pathからモジュールを探す (inspect.getsourceは読み込まれたモジュールにのみ有効)
        # より一般的な探索ロジックが必要だが、ここでは簡略化
        spec = __import__(module_name, fromlist=[''])._ _spec_ _
        if spec and spec.origin and os.path.exists(spec.origin):
            with open(spec.origin, 'r', encoding='utf-8') as f:
                return f.read(), spec.origin
        
    except (ImportError, FileNotFoundError, AttributeError):
        pass # モジュールが見つからない、またはソースコードが取得できない場合
    return None, None


class ImportExtractor(ast.NodeVisitor):
    def __init__(self, base_path):
        self.imports = set()
        self.base_path = base_path

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node) # 子ノードも走査

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.add(node.module)
        self.generic_visit(node) # 子ノードも走査

def analyze_and_extract(main_file_path, output_file_path):
    collected_code = []
    processed_files = set()
    files_to_process = [(main_file_path, os.path.dirname(main_file_path))]

    while files_to_process:
        current_file, current_dir = files_to_process.pop(0)
        
        if current_file in processed_files:
            continue
        processed_files.add(current_file)

        try:
            with open(current_file, 'r', encoding='utf-8') as f:
                source_code = f.read()
            collected_code.append(f"# --- Source from: {current_file} ---\n")
            collected_code.append(source_code)
            collected_code.append("\n\n")

            tree = ast.parse(source_code)
            extractor = ImportExtractor(current_dir)
            extractor.visit(tree)

            for imported_module_name in extractor.imports:
                # 組み込みモジュールや、site-packagesにある外部ライブラリはスキップする例
                # これらを全て集めると非常に大きくなる可能性があるため
                if imported_module_name in sys.builtin_module_names or \
                   any(s in imported_module_name for s in ['os', 'sys', 'math', 'json', 're']): # よく使われる標準ライブラリの例
                    continue
                
                module_source, module_path = get_module_source(imported_module_name, current_dir)
                if module_source and module_path not in processed_files:
                    # 見つかったローカルモジュールを処理対象に追加
                    files_to_process.append((module_path, os.path.dirname(module_path)))

        except FileNotFoundError:
            print(f"警告: ファイルが見つかりません - {current_file}")
        except Exception as e:
            print(f"エラー: ファイル {current_file} の解析中に問題が発生しました - {e}")

    with open(output_file_path, 'w', encoding='utf-8') as out_f:
        out_f.writelines(collected_code)
    
    print(f"全ての関連コードが {output_file_path} に書き出されました。")

# 使用例
if __name__ == "__main__":
    # main.py と同じディレクトリに my_module.py があると仮定
    # my_module.py の中には import another_module があるかもしれない
    
    # テスト用のダミーファイルを作成
    with open("main_app.py", "w", encoding="utf-8") as f:
        f.write("import my_module\n")
        f.write("import os\n")
        f.write("def main():\n")
        f.write("    print('Hello from main!')\n")
        f.write("    my_module.greet('World')\n")

    with open("my_module.py", "w", encoding="utf-8") as f:
        f.write("import datetime\n")
        f.write("def greet(name):\n")
        f.write("    print(f'Hello, {name}! Today is {datetime.date.today()}')\n")

    main_file = "main_app.py"
    output_file = "consolidated_code.py"
    
    analyze_and_extract(main_file, output_file)

    # クリーンアップ
    os.remove("main_app.py")
    os.remove("my_module.py")