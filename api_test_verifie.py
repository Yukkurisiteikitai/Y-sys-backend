import requests

def create_new_session(base_url: str) -> str | None:
    """
    新しいセッションを作成し、セッションIDを返す。
    失敗した場合はNoneを返す。
    """
    try:
        session_payload = {"metadata": {"client_info": "api_test_client"}}
        response = requests.post(f"{base_url}/api/v1/sessions", json=session_payload)
        response.raise_for_status()
        session_id = response.json().get("session_id")
        print(f"Session created successfully: {session_id}")
        return session_id
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to create session: {e}")
        return None
