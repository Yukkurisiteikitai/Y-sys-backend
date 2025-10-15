import requests
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from datetime import datetime
from api_test_verifie import create_new_session

# --- 設定 ---
BASE_URL = "http://127.0.0.1:8000"

# 負荷テスト設定
CONCURRENT_USERS = 50  # 同時接続数
TOTAL_REQUESTS = 200   # 合計リクエスト数
TIMEOUT_SECONDS = 30   # タイムアウト時間（秒）

# テスト用メッセージのバリエーション
TEST_MESSAGES = [
    "将来のキャリアについて悩んでいます。ゲーム開発に興味があるのですが、自分のスキルでやっていけるか不安です。",
    "最近、友人関係がうまくいっていません。どうしたらいいでしょうか？",
    "勉強のモチベーションが上がらなくて困っています。",
    "新しい趣味を始めたいのですが、何がおすすめですか？",
    "仕事とプライベートのバランスが取れず、疲れています。"
]

class RequestResult:
    """リクエストの結果を保持するクラス"""
    def __init__(self, request_id):
        self.request_id = request_id
        self.session_id = None
        self.start_time = None
        self.end_time = None
        self.duration = None
        self.status = "pending"  # pending, success, timeout, error
        self.error_message = None
        self.phases_completed = []
        self.last_phase = None
        self.total_events = 0
        self.request_order = None  # 全体の中で何番目のリクエストか

    def to_dict(self):
        return {
            "request_id": self.request_id,
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "status": self.status,
            "error_message": self.error_message,
            "phases_completed": self.phases_completed,
            "last_phase": self.last_phase,
            "total_events": self.total_events,
            "request_order": self.request_order
        }

def send_streaming_request(request_id, request_order, message):
    """
    単一のストリーミングリクエストを送信し、結果を記録する
    """
    result = RequestResult(request_id)
    result.request_order = request_order
    result.start_time = datetime.now()
    
    try:
        # セッション作成
        session_id = create_new_session(BASE_URL)
        if not session_id:
            result.status = "error"
            result.error_message = "Failed to create session"
            result.end_time = datetime.now()
            result.duration = (result.end_time - result.start_time).total_seconds()
            return result
        
        result.session_id = session_id
        
        # ストリーミングリクエスト
        message_payload = {
            "message": message,
            "sensitivity_level": "medium"
        }
        headers = {"Accept": "text/event-stream"}
        
        with requests.post(
            f"{BASE_URL}/api/v1/sessions/{session_id}/messages/stream",
            json=message_payload,
            headers=headers,
            stream=True,
            timeout=TIMEOUT_SECONDS
        ) as r:
            r.raise_for_status()
            
            event_name = None
            data_buffer = ""
            
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    if event_name and data_buffer:
                        result.total_events += 1
                        
                        # フェーズの記録
                        if event_name == "phase_start":
                            try:
                                data = json.loads(data_buffer)
                                phase = data.get("phase", "unknown")
                                result.last_phase = phase
                            except:
                                pass
                        elif event_name == "phase_complete":
                            try:
                                data = json.loads(data_buffer)
                                phase = data.get("phase", "unknown")
                                result.phases_completed.append(phase)
                            except:
                                pass
                        elif event_name == "stream_end":
                            result.status = "success"
                    
                    event_name = None
                    data_buffer = ""
                    continue
                
                if line.startswith("event:"):
                    event_name = line[len("event:"):].strip()
                elif line.startswith("data:"):
                    data_buffer += line[len("data:"):].strip()
        
        # 正常終了
        if result.status != "success":
            result.status = "incomplete"  # stream_endを受信しなかった場合
            
    except requests.exceptions.Timeout:
        result.status = "timeout"
        result.error_message = f"Request timed out after {TIMEOUT_SECONDS} seconds"
    except requests.exceptions.RequestException as e:
        result.status = "error"
        result.error_message = str(e)
    except Exception as e:
        result.status = "error"
        result.error_message = f"Unexpected error: {str(e)}"
    
    result.end_time = datetime.now()
    result.duration = (result.end_time - result.start_time).total_seconds()
    
    return result

def analyze_results(results):
    """
    テスト結果を分析して統計情報を生成する
    """
    total = len(results)
    status_counts = defaultdict(int)
    phase_stats = defaultdict(int)
    durations = []
    
    # 前半、中盤、後半の区分
    third = total // 3
    early_results = results[:third]
    mid_results = results[third:2*third]
    late_results = results[2*third:]
    
    def analyze_segment(segment, segment_name):
        seg_stats = {
            "name": segment_name,
            "total": len(segment),
            "success": 0,
            "timeout": 0,
            "error": 0,
            "incomplete": 0,
            "avg_duration": 0,
            "phases_reached": defaultdict(int)
        }
        
        seg_durations = []
        for r in segment:
            status_counts[r.status] += 1
            seg_stats[r.status] += 1
            
            if r.duration:
                seg_durations.append(r.duration)
            
            # 到達したフェーズを記録
            if r.last_phase:
                seg_stats["phases_reached"][r.last_phase] += 1
        
        if seg_durations:
            seg_stats["avg_duration"] = sum(seg_durations) / len(seg_durations)
        
        return seg_stats
    
    early_stats = analyze_segment(early_results, "前半")
    mid_stats = analyze_segment(mid_results, "中盤")
    late_stats = analyze_segment(late_results, "後半")
    
    # 全体の統計
    for r in results:
        if r.duration:
            durations.append(r.duration)
        for phase in r.phases_completed:
            phase_stats[phase] += 1
    
    overall_stats = {
        "total_requests": total,
        "success_rate": f"{(status_counts['success'] / total * 100):.2f}%",
        "timeout_count": status_counts['timeout'],
        "timeout_rate": f"{(status_counts['timeout'] / total * 100):.2f}%",
        "error_count": status_counts['error'],
        "incomplete_count": status_counts['incomplete'],
        "avg_duration": f"{(sum(durations) / len(durations)):.2f}s" if durations else "N/A",
        "min_duration": f"{min(durations):.2f}s" if durations else "N/A",
        "max_duration": f"{max(durations):.2f}s" if durations else "N/A",
    }
    
    return {
        "overall": overall_stats,
        "phase_completion": dict(phase_stats),
        "segments": [early_stats, mid_stats, late_stats]
    }

def print_results(analysis):
    """
    分析結果を見やすく出力する
    """
    print("\n" + "="*80)
    print("負荷テスト結果サマリー")
    print("="*80)
    
    print("\n【全体統計】")
    for key, value in analysis["overall"].items():
        print(f"  {key}: {value}")
    
    print("\n【フェーズ完了数】")
    for phase, count in analysis["phase_completion"].items():
        print(f"  {phase}: {count}回")
    
    print("\n【時系列分析】")
    for seg in analysis["segments"]:
        print(f"\n  --- {seg['name']} (全{seg['total']}件) ---")
        print(f"    成功: {seg['success']}件, タイムアウト: {seg['timeout']}件")
        print(f"    エラー: {seg['error']}件, 未完了: {seg['incomplete']}件")
        print(f"    平均処理時間: {seg['avg_duration']:.2f}秒")
        if seg['phases_reached']:
            print(f"    到達フェーズ:")
            for phase, count in seg['phases_reached'].items():
                print(f"      - {phase}: {count}件")
    
    print("\n" + "="*80)

def save_detailed_results(results, analysis, filename="load_test_results.json"):
    """
    詳細な結果をJSONファイルに保存する
    """
    output = {
        "test_config": {
            "concurrent_users": CONCURRENT_USERS,
            "total_requests": TOTAL_REQUESTS,
            "timeout_seconds": TIMEOUT_SECONDS,
            "test_time": datetime.now().isoformat()
        },
        "analysis": analysis,
        "detailed_results": [r.to_dict() for r in results]
    }
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n詳細結果を {filename} に保存しました。")

def run_load_test():
    """
    負荷テストを実行する
    """
    print(f"=== API負荷テスト開始 ===")
    print(f"同時接続数: {CONCURRENT_USERS}")
    print(f"合計リクエスト数: {TOTAL_REQUESTS}")
    print(f"タイムアウト: {TIMEOUT_SECONDS}秒")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = []
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
        futures = []
        
        for i in range(TOTAL_REQUESTS):
            request_id = f"req_{i+1:04d}"
            message = TEST_MESSAGES[i % len(TEST_MESSAGES)]
            
            future = executor.submit(send_streaming_request, request_id, i+1, message)
            futures.append(future)
            
            # 進捗表示
            if (i + 1) % 10 == 0:
                print(f"リクエスト送信中... {i+1}/{TOTAL_REQUESTS}")
        
        print("\n全リクエスト送信完了。処理を待機中...\n")
        
        # 結果を収集
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results.append(result)
            
            # リアルタイム進捗
            status_icon = "✓" if result.status == "success" else "✗"
            print(f"[{i}/{TOTAL_REQUESTS}] {status_icon} {result.request_id}: {result.status} "
                  f"(duration: {result.duration:.2f}s, phases: {len(result.phases_completed)})")
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # 結果をリクエスト順にソート
    results.sort(key=lambda x: x.request_order)
    
    # 分析
    analysis = analyze_results(results)
    
    # 結果表示
    print(f"\n全体実行時間: {total_duration:.2f}秒")
    print_results(analysis)
    
    # 詳細結果を保存
    save_detailed_results(results, analysis)

if __name__ == "__main__":
    run_load_test()