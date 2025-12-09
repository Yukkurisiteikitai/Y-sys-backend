#!/usr/bin/env python3
"""
実行時に実際に使用されたモジュールを追跡して、
真に必要なパッケージのみを含むtrue_requirements.txtを生成する
"""

import sys
import os
import subprocess
import importlib.metadata
from pathlib import Path
from typing import Set, Dict
import json

class ImportTracker:
    def __init__(self):
        self.imported_modules: Set[str] = set()
        self.original_import = None
        
    def track_imports(self, name, *args, **kwargs):
        """import文を追跡"""
        # トップレベルのモジュール名を記録
        top_level = name.split('.')[0]
        self.imported_modules.add(top_level)
        
        # 元のimportを実行
        return self.original_import(name, *args, **kwargs)
    
    def start_tracking(self):
        """importの追跡を開始"""
        self.original_import = __builtins__.__import__
        __builtins__.__import__ = self.track_imports
    
    def stop_tracking(self):
        """importの追跡を停止"""
        if self.original_import:
            __builtins__.__import__ = self.original_import

def get_package_name_from_module(module_name: str) -> str:
    """モジュール名からパッケージ名を取得"""
    try:
        # インストール済みパッケージから探す
        for dist in importlib.metadata.distributions():
            # top_levelを確認
            if dist.read_text('top_level.txt'):
                top_levels = dist.read_text('top_level.txt').strip().split('\n')
                if module_name in top_levels:
                    return dist.metadata['Name']
            
            # パッケージ名がモジュール名と一致する場合
            if dist.metadata['Name'].lower().replace('-', '_') == module_name.lower():
                return dist.metadata['Name']
    except Exception:
        pass
    
    return None

def get_package_version(package_name: str) -> str:
    """パッケージのバージョンを取得"""
    try:
        return importlib.metadata.version(package_name)
    except Exception:
        return None

def get_installed_packages() -> Dict[str, str]:
    """インストール済みのすべてのパッケージを取得"""
    packages = {}
    for dist in importlib.metadata.distributions():
        name = dist.metadata['Name']
        version = dist.metadata['Version']
        packages[name.lower()] = (name, version)
    return packages

def parse_requirements(requirements_file: str) -> Set[str]:
    """requirements.txtを解析"""
    packages = set()
    
    if not os.path.exists(requirements_file):
        print(f"警告: {requirements_file} が見つかりません")
        return packages
    
    with open(requirements_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # コメントと空行をスキップ
            if not line or line.startswith('#'):
                continue
            
            # パッケージ名を抽出（バージョン指定を除去）
            package = line.split('==')[0].split('>=')[0].split('<=')[0].split('~=')[0].strip()
            packages.add(package.lower())
    
    return packages

def run_script_and_track(script_path: str, args: list = None) -> Set[str]:
    """
    スクリプトを実行して使用されたモジュールを追跡
    別プロセスで実行して結果を取得
    """
    tracker_code = f'''
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
    with open(r'{script_path}', 'r', encoding='utf-8') as f:
        code = f.read()
    exec(code, {{'__name__': '__main__', '__file__': r'{script_path}'}})
except Exception as e:
    print(f"実行エラー: {{e}}", file=sys.stderr)

# 結果を出力
print("__IMPORTS_START__")
print(json.dumps(list(imported_modules)))
print("__IMPORTS_END__")
'''
    
    # 一時ファイルに保存して実行
    temp_file = Path(script_path).parent / '_tracker_temp.py'
    with open(temp_file, 'w', encoding='utf-8') as f:
        f.write(tracker_code)
    
    try:
        # スクリプトを実行
        cmd = [sys.executable, str(temp_file)]
        if args:
            cmd.extend(args)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(script_path) or '.'
        )
        
        # 出力から追跡結果を抽出
        output = result.stdout
        if '__IMPORTS_START__' in output and '__IMPORTS_END__' in output:
            start = output.index('__IMPORTS_START__') + len('__IMPORTS_START__')
            end = output.index('__IMPORTS_END__')
            imports_json = output[start:end].strip()
            imported_modules = set(json.loads(imports_json))
            return imported_modules
        else:
            print("警告: import追跡データが見つかりませんでした")
            print("標準出力:", result.stdout)
            print("標準エラー:", result.stderr)
            return set()
    
    finally:
        # 一時ファイルを削除
        if temp_file.exists():
            temp_file.unlink()

def generate_true_requirements(
    script_path: str,
    requirements_file: str = 'requirements.txt',
    output_file: str = 'true_requirements.txt',
    script_args: list = None
):
    """メイン処理"""
    
    print(f"📊 スクリプト '{script_path}' の依存関係を分析中...")
    
    # スクリプトを実行して使用されたモジュールを追跡
    print("\n🔍 スクリプトを実行してimportを追跡中...")
    imported_modules = run_script_and_track(script_path, script_args)
    
    if not imported_modules:
        print("⚠️  追跡されたモジュールがありません")
        return
    
    print(f"✅ {len(imported_modules)} 個のモジュールがimportされました")
    
    # モジュールからパッケージ名を解決
    print("\n🔍 モジュールからパッケージを解決中...")
    required_packages = {}
    stdlib_modules = set()
    unknown_modules = set()
    
    for module in imported_modules:
        package_name = get_package_name_from_module(module)
        
        if package_name:
            version = get_package_version(package_name)
            required_packages[package_name] = version
        elif module in sys.stdlib_module_names:
            stdlib_modules.add(module)
        else:
            unknown_modules.add(module)
    
    # 元のrequirements.txtと比較
    original_packages = parse_requirements(requirements_file)
    
    # 結果を表示
    print("\n" + "="*60)
    print("📦 分析結果")
    print("="*60)
    
    print(f"\n✅ 実際に使用されたパッケージ ({len(required_packages)}個):")
    for pkg, ver in sorted(required_packages.items()):
        print(f"  - {pkg}=={ver}")
    
    if stdlib_modules:
        print(f"\n📚 標準ライブラリ ({len(stdlib_modules)}個):")
        for mod in sorted(stdlib_modules):
            print(f"  - {mod}")
    
    if unknown_modules:
        print(f"\n❓ 不明なモジュール ({len(unknown_modules)}個):")
        for mod in sorted(unknown_modules):
            print(f"  - {mod}")
    
    # 不要なパッケージを特定
    if original_packages:
        unused_packages = original_packages - set(pkg.lower() for pkg in required_packages.keys())
        if unused_packages:
            print(f"\n🗑️  使用されていないパッケージ ({len(unused_packages)}個):")
            for pkg in sorted(unused_packages):
                print(f"  - {pkg}")
    
    # true_requirements.txtを生成
    print(f"\n💾 '{output_file}' を生成中...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# 実行時に実際に使用されたパッケージのみ\n")
        f.write(f"# 生成元: {script_path}\n\n")
        
        for pkg, ver in sorted(required_packages.items()):
            f.write(f"{pkg}=={ver}\n")
    
    print(f"✅ '{output_file}' を生成しました")
    
    # 統計情報
    print("\n" + "="*60)
    print("📈 統計情報")
    print("="*60)
    print(f"元のrequirements.txt: {len(original_packages)} パッケージ")
    print(f"実際に使用: {len(required_packages)} パッケージ")
    if original_packages:
        reduction = (1 - len(required_packages) / len(original_packages)) * 100
        print(f"削減率: {reduction:.1f}%")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='実行時に実際に使用されたパッケージのみを含むrequirements.txtを生成'
    )
    parser.add_argument(
        'script',
        help='分析するPythonスクリプト（main.pyなど）'
    )
    parser.add_argument(
        '--requirements',
        default='requirements.txt',
        help='元のrequirements.txtファイル（デフォルト: requirements.txt）'
    )
    parser.add_argument(
        '--output',
        default='true_requirements.txt',
        help='出力ファイル名（デフォルト: true_requirements.txt）'
    )
    parser.add_argument(
        '--args',
        nargs='*',
        help='スクリプトに渡す引数'
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.script):
        print(f"エラー: スクリプト '{args.script}' が見つかりません")
        sys.exit(1)
    
    generate_true_requirements(
        args.script,
        args.requirements,
        args.output,
        args.args
    )