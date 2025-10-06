
import requests
import json
import uuid
import time

# --- 設定 ---
BASE_URL = "http://127.0.0.1:8000"
OUTPUT_FILE = "stream_response.txt"

def format_and_print(event: str, data: dict):
    """受信したイベントとデータを見やすく整形してコンソールに出力する"""
    
    # フェーズの開始/終了
    if event == "phase_start":
        phase = data.get("phase", "unknown_phase")
        print(f"\n--- [START] Phase: {phase.upper()} ---")
    elif event == "phase_complete":
        phase = data.get("phase", "unknown_phase")
        duration = data.get("duration_ms", 0)
        print(f"--- [END] Phase: {phase.upper()} ({duration:.2f} ms) ---")
    
    # 各フェーズの結果
    elif event == "abstract_result":
        emotions = data.get("emotional_state", [])
        pattern = data.get("cognitive_pattern", "")
        print(f"  [Abstract] Emotions: {emotions}")
        print(f"  [Abstract] Pattern: {pattern}")
    
    elif event == "concrete_links":
        count = data.get("total_retrieved", 0)
        print(f"  [Concrete] Found {count} related episodes.")
        for i, ep in enumerate(data.get("related_episodes", [])):
            snippet = ep.get("text_snippet", "").replace('\n', ' ')[:70]
            score = ep.get("relevance_score", 0)
            print(f"    - Ep{i+1}: \"{snippet}...\" (Score: {score:.2f})")

    elif event == "thought_process":
        decision = data.get("inferred_decision", "")
        action = data.get("inferred_action", "")
        print(f"  [Thinking] Decision: {decision}")
        print(f"  [Thinking] Action: {action}")

    elif event == "final_response":
        dialogue = data.get("response", {}).get("dialogue", "")
        print(f"\n[Final Response] Dialogue: {dialogue}")

    # ストリームの終了
    elif event == "stream_end":
        print("\n--- Stream Ended ---")

    # その他のイベント
    elif event == "error":
        print(f"\n[ERROR] Code: {data.get('error_code')}, Message: {data.get('message')}")

def run_test():
    """
    APIサーバーに接続し、ストリーミング応答をリアルタイムでコンソールに表示する。
    """
    print("--- API Streaming Test Client ---")

    # 1. セッションの作成 (これは通常のHTTPリクエスト)
    try:
        session_payload = {"metadata": {"client_info": "api_test_client_streaming.py"}}
        response = requests.post(f"{BASE_URL}/api/v1/sessions", json=session_payload)
        response.raise_for_status()
        session_id = response.json().get("session_id")
        print(f"Session created: {session_id}")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to create session: {e}")
        return

    # 2. メッセージを送信し、ストリーミング応答をリアルタイムで処理
    print("\nConnecting to stream...")
    try:
        message_payload = {
            "message": "将来のキャリアについて悩んでいます。ゲーム開発に興味があるのですが、自分のスキルでやっていけるか不安です。",
            "sensitivity_level": "medium"
        }
        headers = {"Accept": "text/event-stream"}

        with requests.post(
            f"{BASE_URL}/api/v1/sessions/{session_id}/messages/stream",
            json=message_payload, headers=headers, stream=True
        ) as r, open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            
            r.raise_for_status()
            
            event_name = None
            data_buffer = ""

            for line in r.iter_lines(decode_unicode=True, chunk_size=1):
                if not line: # 空行はメッセージの区切り
                    if event_name and data_buffer:
                        try:
                            data_json = json.loads(data_buffer)
                            format_and_print(event_name, data_json)
                        except json.JSONDecodeError:
                            print(f"[Warning] Failed to parse JSON: {data_buffer}")
                    # バッファをリセット
                    event_name = None
                    data_buffer = ""
                    continue

                f.write(line + "\n") # 生の行をファイルに保存

                if line.startswith("event:"):
                    event_name = line[len("event:"):].strip()
                elif line.startswith("data:"):
                    data_buffer += line[len("data:"):].strip()

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed during streaming: {e}")
    except Exception as e:
        print(f"[UNEXPECTED ERROR] An error occurred: {e}")

if __name__ == "__main__":
    run_test()
