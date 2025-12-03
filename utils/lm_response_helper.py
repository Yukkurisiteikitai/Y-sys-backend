"""
LMStudioクライアントの応答処理ユーティリティ

generate_response()の戻り値から安全にテキストを抽出するための
ヘルパー関数を提供します。
"""

from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def extract_answer(response: Dict[str, Any]) -> str:
    """
    LM Studio のレスポンスから 'answer' キーを安全に抽出します。

    Args:
        response: LMStudioClient.generate_response() の戻り値

    Returns:
        'answer' キーの値

    Raises:
        ValueError: レスポンスが辞書でない、または'answer'キーが見つからない場合
    """
    if "answer" not in response:
        error_msg = f"Invalid LM response: missing 'answer' key. Response: {response}"
        logger.error(error_msg)
        raise KeyError(error_msg)

    answer = response["answer"]
    if not isinstance(answer, str):
        logger.warning("Expected string answer, got %s: %s", type(answer).__name__, answer)
        return str(answer)

    return answer


def extract_answer_or_default(
    response: Optional[Dict[str, Any]], default: str = ""
) -> str:
    """
    LM Studio のレスポンスから 'answer' キーを安全に抽出します。
    エラーが発生した場合はデフォルト値を返します。

    Args:
        response: LMStudioClient.generate_response() の戻り値
        default: エラーが発生した場合のデフォルト値

    Returns:
        'answer' キーの値、またはエラー時はデフォルト値
    """
    try:
        if response is None:
            logger.warning("Response is None, returning default value")
            return default
        return extract_answer(response)
    except (ValueError, KeyError, TypeError) as e:
        logger.error("Failed to extract answer from response: %s", e)
        return default


def validate_response_structure(response: Dict[str, Any]) -> bool:
    """
    LM Studio レスポンスの構造を検証します。

    Args:
        response: 検証するレスポンス

    Returns:
        構造が正しい場合True、そうでない場合False
    """
    required_keys = {"answer"}
    optional_keys = {"evidence", "confidence", "reason"}

    if not required_keys.issubset(response.keys()):
        missing = required_keys - set(response.keys())
        logger.error("Response missing required keys: %s", missing)
        return False

    # キー名のチェック（予期しないキーがないか）
    all_valid_keys = required_keys | optional_keys
    invalid_keys = set(response.keys()) - all_valid_keys
    if invalid_keys:
        logger.warning("Response has unexpected keys: %s", invalid_keys)

    return True
