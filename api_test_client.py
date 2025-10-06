
import requests
import json
import uuid

# --- 設定 ---
BASE_URL = "http://127.0.0.1:8000"
SESSION_ID = str(uuid.uuid4())
OUTPUT_FILE = "stream_response.txt"

def run_test():
    """
    APIサーバーに対してセッション作成からメッセージ送信、ストリーミング受信までの一連のテストを実行する。
    """
    print("--- API Test Client ---")

    # 1. セッションの作成
    try:
        print(f"1. Creating a new session...")
        session_payload = {
            "metadata": {
                "client_info": "api_test_client.py",
                "timestamp": "2025-10-06T12:00:00Z"
            }
        }
        response = requests.post(f"{BASE_URL}/api/v1/sessions", json=session_payload)
        response.raise_for_status()
        session_data = response.json()
        session_id = session_data.get("session_id")
        print(f"   => Session created successfully: {session_id}")

    except requests.exceptions.RequestException as e:
        print(f"   [ERROR] Failed to create session: {e}")
        return

    # 2. メッセージを送信し、ストリーミング応答を受信
    try:
        print(f"\n2. Sending message and receiving stream...")
        message_payload = {
            "message": "将来のキャリアについて悩んでいます。ゲーム開発に興味があるのですが、自分のスキルでやっていけるか不安です。",
            "sensitivity_level": "medium"
        }
        
        headers = {
            "Accept": "text/event-stream"
        }

        with requests.post(
            f"{BASE_URL}/api/v1/sessions/{session_id}/messages/stream",
            json=message_payload,
            headers=headers,
            stream=True
        ) as r:
            r.raise_for_status()
            print(f"   => Connected to stream. Writing response to {OUTPUT_FILE}")
            
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                for line in r.iter_lines(decode_unicode=True):
                    if line:
                        f.write(line + "\n")
                        print(f"   | {line}")
            
            print(f"\n   => Stream finished. Full response saved to {OUTPUT_FILE}")

    except requests.exceptions.RequestException as e:
        print(f"   [ERROR] Failed during streaming: {e}")
    except Exception as e:
        print(f"   [UNEXPECTED ERROR] An error occurred: {e}")


if __name__ == "__main__":
    run_test()
