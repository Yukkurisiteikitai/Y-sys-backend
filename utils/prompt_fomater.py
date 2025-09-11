import re
import logging
from typing import Dict, List, Tuple, Any, Optional
from enum import Enum
from .log import logger
class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class PromptTemplateChecker():
    """
    テンプレートの変数チェックをログ出力で行うクラス
    """
    
    def __init__(self):
        """
        初期化
        """
        self.logger = logger
        
        
    
    def check_template_variables(self, template: str, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        テンプレート文字列の{}で囲まれた変数をチェック
        
        Args:
            template (str): テンプレート文字列
            variables (Dict[str, Any]): format()に渡す変数の辞書
            
        Returns:
            Dict[str, Any]: チェック結果の詳細情報
        """
        
        self.logger.info("🔍 テンプレート変数チェックを開始")
        
        # テンプレート内の{}で囲まれた変数を抽出（位置情報も含む）
        pattern = r'\{([^{}]+)\}'
        template_matches = list(re.finditer(pattern, template))
        template_vars = [match.group(1) for match in template_matches]
        
        self.logger.debug(f"📝 テンプレート内で発見された変数: {template_vars}")
        
        # 各変数の使用箇所を記録
        var_locations = {}
        for match in template_matches:
            var_name = match.group(1)
            if var_name not in var_locations:
                var_locations[var_name] = []
            
            # 該当箇所の前後の文脈を取得（前後20文字）
            start_pos = max(0, match.start() - 20)
            end_pos = min(len(template), match.end() + 20)
            context = template[start_pos:end_pos].replace('\n', '\\n')
            
            var_locations[var_name].append({
                'position': match.start(),
                'context': context,
                'line_number': template[:match.start()].count('\n') + 1
            })
        
        # 重複を除去して集合に変換
        template_vars_set = set(template_vars)
        provided_vars_set = set(variables.keys())
        
        self.logger.debug(f"📦 提供された変数: {list(provided_vars_set)}")
        
        # 未代入の変数（テンプレートにあるが、variablesにない）
        missing_vars = template_vars_set - provided_vars_set
        
        # 余分な変数（variablesにあるが、テンプレートで使われていない）
        unused_vars = provided_vars_set - template_vars_set
        
        # 正常に使用される変数
        used_vars = template_vars_set & provided_vars_set
        
        # ログ出力
        self._log_check_results(missing_vars, unused_vars, used_vars, var_locations, variables)
        
        # 未代入変数の詳細情報を作成
        missing_var_details = {}
        for var_name in missing_vars:
            missing_var_details[var_name] = {
                'locations': var_locations[var_name],
                'usage_count': len(var_locations[var_name]),
                'suggestions': self._generate_variable_suggestions(var_name, provided_vars_set)
            }
        
        # 結果をまとめる
        result = {
            'status': 'ok' if not missing_vars else 'error',
            'template_variables': list(template_vars_set),
            'provided_variables': list(provided_vars_set),
            'missing_variables': list(missing_vars),
            'missing_variable_details': missing_var_details,
            'unused_variables': list(unused_vars),
            'used_variables': list(used_vars),
            'variable_locations': var_locations,
            'error_message': None
        }
        
        # エラーメッセージの生成
        if missing_vars:
            details = []
            for var in missing_vars:
                usage_count = missing_var_details[var]['usage_count']
                details.append(f"'{var}' ({usage_count}箇所)")
            
            result['error_message'] = f"未代入の変数があります: {', '.join(details)}"
            self.logger.error(f"❌ {result['error_message']}")
        else:
            self.logger.info("✅ テンプレートチェック完了: 問題なし")
        
        return result
    
    def _log_check_results(self, missing_vars: set, unused_vars: set, used_vars: set, 
                          var_locations: Dict, variables: Dict):
        """
        チェック結果をログ出力
        """
        
        # 正常な変数をログ出力
        if used_vars:
            self.logger.info(f"✅ 正常に使用される変数 ({len(used_vars)}個): {sorted(used_vars)}")
            for var in sorted(used_vars):
                usage_count = len(var_locations[var])
                self.logger.debug(f"  - '{var}': {usage_count}箇所で使用")
        
        # 未使用変数の警告
        if unused_vars:
            self.logger.warning(f"⚠️  未使用の変数 ({len(unused_vars)}個): {sorted(unused_vars)}")
            self.logger.warning("   これらの変数は削除を検討してください")
        
        # 未代入変数の詳細エラー
        if missing_vars:
            self.logger.error(f"❌ 未代入の変数 ({len(missing_vars)}個)が検出されました")
            
            for var_name in sorted(missing_vars):
                locations = var_locations[var_name]
                self.logger.error(f"🔍 変数 '{var_name}' が {len(locations)}箇所で必要:")
                
                for i, location in enumerate(locations, 1):
                    self.logger.error(f"  {i}. 行{location['line_number']}: ...{location['context']}...")
                
                # 類似変数の提案をログ出力
                suggestions = self._generate_variable_suggestions(var_name, set(variables.keys()))
                if suggestions:
                    self.logger.warning(f"💡 '{var_name}'の類似変数候補:")
                    for suggestion in suggestions:
                        self.logger.warning(f"  - {suggestion}")
                else:
                    self.logger.info(f"💡 '{var_name}': 類似する変数名が見つかりませんでした")
                
                # 修正方法をログ出力
                self.logger.info(f"🔧 修正方法: variables['{var_name}'] = '適切な値' を追加してください")
    
    def _generate_variable_suggestions(self, missing_var: str, available_vars: set) -> List[str]:
        """
        未代入変数に対して、利用可能な変数から類似した名前を提案する
        """
        suggestions = []
        missing_lower = missing_var.lower()
        
        for var in available_vars:
            var_lower = var.lower()
            
            # 完全一致（大文字小文字違い）
            if missing_lower == var_lower and missing_var != var:
                suggestions.append(f"'{var}' (大文字小文字の違い)")
            
            # 部分一致
            elif missing_lower in var_lower or var_lower in missing_lower:
                suggestions.append(f"'{var}' (部分的に類似)")
            
            # アンダースコア/ハイフンの違い
            elif missing_lower.replace('_', '-') == var_lower.replace('_', '-'):
                suggestions.append(f"'{var}' (区切り文字の違い)")
        
        return suggestions[:3]  # 最大3つまで
    
    def safe_format_template(self, template: str, **kwargs) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        テンプレートを安全にフォーマットし、エラーがあれば詳細情報を返す
        
        Args:
            template (str): テンプレート文字列
            **kwargs: format()に渡す変数
            
        Returns:
            Tuple[Optional[str], Dict]: (フォーマット結果またはNone, チェック結果)
        """
        
        self.logger.info("🚀 テンプレートフォーマット処理を開始")
        
        # まずチェックを実行
        check_result = self.check_template_variables(template, kwargs)
        
        if check_result['status'] == 'error':
            self.logger.error("❌ 変数チェックでエラーが発生したため、フォーマット処理を中止")
            return None, check_result
        
        try:
            formatted_text = template.format(**kwargs)
            self.logger.info("✅ テンプレートフォーマット完了")
            self.logger.debug(f"📄 フォーマット結果の長さ: {len(formatted_text)}文字")
            return formatted_text, check_result
            
        except Exception as e:
            check_result['status'] = 'format_error'
            check_result['error_message'] = f"フォーマット実行時エラー: {str(e)}"
            self.logger.critical(f"🚨 フォーマット実行時に予期しないエラー: {str(e)}")
            return None, check_result
    
    def log_fix_code(self, check_result: Dict[str, Any], variables_dict_name: str = "variables"):
        """
        未代入変数を修正するためのコードをログ出力
        """
        
        if not check_result['missing_variables']:
            self.logger.info("✅ 修正が必要な変数はありません")
            return
        
        self.logger.info("🔧 修正用コードを生成:")
        
        for var_name in sorted(check_result['missing_variables']):
            details = check_result['missing_variable_details'][var_name]
            self.logger.info(f"# 変数 '{var_name}' を追加 ({details['usage_count']}箇所で使用)")
            self.logger.info(f"{variables_dict_name}['{var_name}'] = 'ここに適切な値を設定'")
            
            if details['suggestions']:
                candidates = [s.split(' ')[0].strip("'") for s in details['suggestions']]
                self.logger.info(f"# 候補: {', '.join(candidates)}")

# 使用しやすいファクトリー関数
def create_template_checker() -> PromptTemplateChecker:
    """
    PromptTemplateCheckerのインスタンスを作成
    
    Returns:
        PromptTemplateChecker: チェッカーのインスタンス
    """
    return PromptTemplateChecker()

# テスト関数
def test_logger_checker():
    """
    ログ方式チェッカーの動作テスト
    """
    
    print("🧪 ログ方式テンプレートチェッカーのテスト")
    print("=" * 60)
    
    # チェッカーを作成（DEBUGレベルで詳細ログを出力）
    checker = create_template_checker()
    
    # テスト用のテンプレート
    template = """
    あなたは{role}です。
    以下の状況について考えてください：
    {situation_text}
    
    参考情報：
    {integrated_knowledge}
    
    成功パターン：
    {successful_patterns}
    
    失敗パターン：
    {failure_patterns}
    
    追加で{role}として{situation_text}を分析してください。
    """
    
    # テストケース1: 正常なケース
    print("\n🧪 テストケース1: 正常なケース")
    print("-" * 40)
    variables1 = {
        'role': 'AIアシスタント',
        'situation_text': 'ユーザーからの質問',
        'integrated_knowledge': '関連する知識',
        'successful_patterns': '成功事例',
        'failure_patterns': '失敗事例'
    }
    
    result, check_result = checker.safe_format_template(template, **variables1)
    
    # テストケース2: 未代入の変数があるケース
    print("\n🧪 テストケース2: 未代入の変数があるケース")
    print("-" * 40)
    variables2 = {
        'role': 'AIアシスタント',
        'Situation_Text': 'ユーザーからの質問',  # 大文字小文字が違う
        # integrated_knowledge が不足
        'success_patterns': '成功事例',  # 名前が似ているが違う
        'failure_patterns': '失敗事例',
        'extra_var': '余分な変数'  # 余分な変数
    }
    
    result, check_result = checker.safe_format_template(template, **variables2)
    checker.log_fix_code(check_result)

# 実用的な使用例関数
def example_usage():
    """
    実際の使用例
    """
    print("\n📚 実用的な使用例")
    print("=" * 60)
    
    # INFO レベルで作成（本番用）
    checker = create_template_checker(log_level="INFO")
    
    # あなたの実際のケースを再現
    instruction_prompt_template = """
    指示: {instruction}
    状況: {situation_text}  
    知識: {integrated_knowledge}
    成功パターン: {successful_patterns}
    失敗パターン: {failure_patterns}
    """
    
    user_input = "ユーザーの質問"
    context = "関連する文脈情報"
    
    variables = {
        'situation_text': user_input,
        'integrated_knowledge': context,
        'successful_patterns': "・比喻を用いると理解が深まる傾向がある。",
        'failure_patterns': "・専門用語の多用は避けるべき。"
        # 'instruction' が不足している
    }
    
    # 安全にフォーマット実行
    final_prompt, check_info = checker.safe_format_template(
        instruction_prompt_template, **variables
    )
    
    if final_prompt is None:
        checker.log_fix_code(check_info, "variables")
        print("エラーが発生したため、処理を中止しました")
    else:
        print("成功! final_promptが生成されました")

if __name__ == "__main__":
    test_logger_checker()
    example_usage()