import yaml

def load_merged_config() -> dict[str, any]:
    """
    config_defalt.yaml と config.yaml を読み込み、config.yaml の内容で上書きした辞書を返す。
    設定ファイルはUTF-8でエンコードされていると仮定。
    Returns:
        merge_config: dict - merged configuration dictionary

    """
    with open("config_defalt.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    with open("config.yaml","r",encoding="utf-8")as f:
        user_config = yaml.safe_load(f)

    print(config)
    print("-----------------")
    print(user_config)
    
    for key, value in user_config.items():
        print(key,value)
        config[key] = value

    del user_config
    print("-"*20,"merged config","-"*20)
    print(config)
    return config

load_merged_config()