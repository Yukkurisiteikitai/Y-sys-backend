import yaml
import logging
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)


def load_merged_config() -> dict[str, Any]:
    """
    config_defalt.yaml と config.yaml を読み込み、
    config.yaml の内容で上書きした辞書を返す。
    設定ファイルはUTF-8でエンコードされていると仮定。

    Returns:
        dict[str, Any]: merged configuration dictionary

    Raises:
        FileNotFoundError: config_defalt.yaml が見つからない場合
        yaml.YAMLError: YAMLファイルの解析に失敗した場合
    """
    default_path = Path(__file__).parent / "config_defalt.yaml"
    user_path = Path(__file__).parent / "config.yaml"

    # デフォルト設定の読み込み
    if not default_path.exists():
        raise FileNotFoundError(f"Default config not found: {default_path}")

    try:
        with default_path.open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            if config is None:
                config = {}
            if not isinstance(config, dict):
                raise ValueError("Default config must be a dictionary")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Failed to parse default config: {e}") from e

    # ユーザー設定の上書き（存在する場合のみ）
    if user_path.exists():
        try:
            with user_path.open("r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f)
                if user_config is not None and isinstance(user_config, dict):
                    user_config = cast(dict[str, Any], user_config)
                    for key, value in user_config.items():
                        config[key] = value
                    logger.debug("Loaded user config from %s", user_path)
        except yaml.YAMLError as e:
            logger.warning("Failed to parse user config: %s, using default config only", e)

    return cast(dict[str, Any], config)