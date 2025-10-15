import requests
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any, Optional
from api_test_verifie import create_new_session

# --- 設定 ---
BASE_URL = "http://127.0.0.1:8000"

# 負荷テスト設定
CONCURRENT_USERS = 1  # 同時接続数
TOTAL_REQUESTS = 20   # 合計リクエスト数
TIMEOUT_SECONDS = 600   # タイムアウト時間（秒）

# テスト用メッセージのバリエーション
TEST_MESSAGES = [
    "将来のキャリアについて悩んでいます。ゲーム開発に興味があるのですが、自分のスキルでやっていけるか不安です。",
    "最近、友人関係がうまくいっていません。どうしたらいいでしょうか？",
    "勉強のモチベーションが上がらなくて困っています。",
    "新しい趣味を始めたいのですが、何がおすすめですか？",
    "仕事とプライベートのバランスが取れず、疲れています。"
]

# サーバーのフェーズ定義
EXPECTED_PHASES = [
    "abstract_recognition",
    "concrete_understanding", 
    "response_generation"
]

EXPECTED_EVENTS = [
    "phase_start",
    "abstract_result",
    "phase_complete",
    "concrete_links",
    "thought_process",
    "final_response",
    "stream_end"
]


class SSECounter:
    """SSE接続の追跡と統計情報を管理するクラス"""
    
    SESSION_ID_NOT_CREATED = "[This_id_want_not_come_up]"
    
    def __init__(self) -> None:
        self.connect_data: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
    
    def add_sse_request(self, session_id: str, url: str, payload: Dict[str, Any]) -> None:
        """SSEリクエストを記録"""
        with self._lock:
            data = {
                "connect_type": "request",
                "session_id": session_id,
                "event": "request_start",
                "url": url,
                "timestamp": datetime.now().isoformat(),
                "payload": payload,
                "sender_time": time.time()
            }
            self.connect_data.append(data)
    
    def add_sse_response(self, session_id: str, event: str, url: str, data: Dict[str, Any]) -> None:
        """SSEレスポンスイベントを記録"""
        with self._lock:
            record = {
                "connect_type": "response",
                "session_id": session_id,
                "event": event,
                "url": url,
                "timestamp": datetime.now().isoformat(),
                "payload": data,
                "sender_time": time.time()
            }
            self.connect_data.append(record)
    
    def add_sse_timeout(self, session_id: str, url: str, timeout_duration: float, 
                       last_event: Optional[str], last_phase: Optional[str]) -> None:
        """SSEタイムアウトを記録"""
        with self._lock:
            timeouter_info = {
                "timeout_duration": timeout_duration,
                "last_event": last_event,
                "last_phase": last_phase
            }
            record = {
                "connect_type": "timeout",
                "session_id": session_id,
                "event": "timeout",
                "url": url,
                "timestamp": datetime.now().isoformat(),
                "timeouter": timeouter_info,
                "sender_time": time.time()
            }
            self.connect_data.append(record)
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        with self._lock:
            total_requests = sum(1 for r in self.connect_data if r["connect_type"] == "request")
            total_responses = sum(1 for r in self.connect_data if r["connect_type"] == "response")
            total_timeouts = sum(1 for r in self.connect_data if r["connect_type"] == "timeout")
            
            event_counts = defaultdict(int)
            for record in self.connect_data:
                if record["connect_type"] == "response":
                    event_counts[record["event"]] += 1
            
            return {
                "total_requests": total_requests,
                "total_responses": total_responses,
                "total_timeouts": total_timeouts,
                "timeout_rate": f"{(total_timeouts / max(total_requests, 1) * 100):.2f}%",
                "event_counts": dict(event_counts)
            }
    
    def save_to_file(self, filename: str = "sse_counter_data.json") -> None:
        """データをファイルに保存"""
        with self._lock:
            output = {
                "saved_at": datetime.now().isoformat(),
                "total_records": len(self.connect_data),
                "statistics": self.get_stats(),
                "records": self.connect_data
            }
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)


class RequestResult:
    """リクエストの結果を保持するクラス"""
    def __init__(self, request_id: str):
        self.request_id = request_id
        self.session_id: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.duration: Optional[float] = None
        self.status = "pending"
        self.error_message: Optional[str] = None
        self.phases_started: List[str] = []
        self.phases_completed: List[str] = []
        self.last_phase: Optional[str] = None
        self.last_event: Optional[str] = None
        self.received_stream_end = False
        self.total_events = 0
        self.request_order: Optional[int] = None
        self.events_log: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "status": self.status,
            "error_message": self.error_message,
            "phases_started": self.phases_started,
            "phases_completed": self.phases_completed,
            "last_phase": self.last_phase,
            "last_event": self.last_event,
            "received_stream_end": self.received_stream_end,
            "total_events": self.total_events,
            "request_order": self.request_order,
            "events_log": self.events_log
        }


def send_streaming_request(request_id: str, request_order: int, message: str, 
                          sse_counter: SSECounter) -> RequestResult:
    """単一のストリーミングリクエストを送信し、結果を記録する"""
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
        url = f"{BASE_URL}/api/v1/sessions/{session_id}/messages/stream"
        
        # リクエストを記録
        message_payload = {
            "message": message,
            "sensitivity_level": "medium"
        }
        sse_counter.add_sse_request(session_id, url, message_payload)
        
        # ストリーミングリクエスト
        headers = {"Accept": "text/event-stream"}
        
        with requests.post(
            url, json=message_payload, headers=headers, stream=True, timeout=TIMEOUT_SECONDS
        ) as r:
            r.raise_for_status()
            
            event_name = None
            data_buffer = ""
            
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    if event_name and data_buffer:
                        result.total_events += 1
                        result.last_event = event_name
                        result.events_log.append(event_name)
                        
                        try:
                            data = json.loads(data_buffer)
                            
                            # SSEカウンターに記録
                            sse_counter.add_sse_response(session_id, event_name, url, data)
                            
                            # フェーズの記録
                            if event_name == "phase_start":
                                phase = data.get("phase", "unknown")
                                result.phases_started.append(phase)
                                result.last_phase = phase
                            
                            elif event_name == "phase_complete":
                                phase = data.get("phase", "unknown")
                                result.phases_completed.append(phase)
                            
                            elif event_name == "stream_end":
                                result.received_stream_end = True
                            
                            elif event_name == "error":
                                result.error_message = data.get("message", "Unknown error")
                                result.status = "error"
                        
                        except json.JSONDecodeError:
                            pass
                    
                    event_name = None
                    data_buffer = ""
                    continue
                
                if line.startswith("event:"):
                    event_name = line[len("event:"):].strip()
                elif line.startswith("data:"):
                    data_buffer += line[len("data:"):].strip()
        
        # ステータス判定
        if result.status != "error":
            if result.received_stream_end:
                result.status = "success"
            else:
                result.status = "incomplete"
                result.error_message = "Stream ended without receiving stream_end event"
            
    except requests.exceptions.Timeout:
        result.status = "timeout"
        result.error_message = f"Request timed out after {TIMEOUT_SECONDS} seconds"
        # タイムアウトを記録
        sse_counter.add_sse_timeout(
            result.session_id or "unknown",
            url if result.session_id else "unknown",
            TIMEOUT_SECONDS,
            result.last_event,
            result.last_phase
        )
    except requests.exceptions.RequestException as e:
        result.status = "error"
        result.error_message = str(e)
    except Exception as e:
        result.status = "error"
        result.error_message = f"Unexpected error: {str(e)}"
    
    result.end_time = datetime.now()
    result.duration = (result.end_time - result.start_time).total_seconds()
    
    return result


def analyze_results(results: List[RequestResult]) -> Dict[str, Any]:
    """テスト結果を分析して統計情報を生成する"""
    total = len(results)
    status_counts = defaultdict(int)
    phase_started_stats = defaultdict(int)
    phase_completed_stats = defaultdict(int)
    event_stats = defaultdict(int)
    durations = []
    
    # 前半、中盤、後半の区分
    third = total // 3
    early_results = results[:third]
    mid_results = results[third:2*third]
    late_results = results[2*third:]
    
    def analyze_segment(segment: List[RequestResult], segment_name: str) -> Dict[str, Any]:
        seg_stats: Dict[str, Any] = {
            "name": segment_name,
            "total": len(segment),
            "success": 0,
            "timeout": 0,
            "error": 0,
            "incomplete": 0,
            "avg_duration": 0.0,
            "phases_started": defaultdict(int),
            "phases_completed": defaultdict(int),
            "received_stream_end": 0,
            "phase_dropout": defaultdict(int)  # どのフェーズで脱落したか
        }
        
        seg_durations = []
        for r in segment:
            seg_stats[r.status] += 1
            
            if r.duration:
                seg_durations.append(r.duration)
            
            for phase in r.phases_started:
                seg_stats["phases_started"][phase] += 1
            
            for phase in r.phases_completed:
                seg_stats["phases_completed"][phase] += 1
            
            if r.received_stream_end:
                seg_stats["received_stream_end"] += 1
            
            # 脱落フェーズの記録
            if r.status in ["timeout", "error", "incomplete"]:
                seg_stats["phase_dropout"][r.last_phase or "before_start"] += 1
        
        if seg_durations:
            seg_stats["avg_duration"] = sum(seg_durations) / len(seg_durations)
            seg_stats["min_duration"] = min(seg_durations)
            seg_stats["max_duration"] = max(seg_durations)
        
        # defaultdictを通常のdictに変換
        seg_stats["phases_started"] = dict(seg_stats["phases_started"])
        seg_stats["phases_completed"] = dict(seg_stats["phases_completed"])
        seg_stats["phase_dropout"] = dict(seg_stats["phase_dropout"])
        
        return seg_stats
    
    early_stats = analyze_segment(early_results, "前半")
    mid_stats = analyze_segment(mid_results, "中盤")
    late_stats = analyze_segment(late_results, "後半")
    
    # 全体の統計
    stream_end_count = 0
    for r in results:
        status_counts[r.status] += 1
        if r.duration:
            durations.append(r.duration)
        for phase in r.phases_started:
            phase_started_stats[phase] += 1
        for phase in r.phases_completed:
            phase_completed_stats[phase] += 1
        for event in r.events_log:
            event_stats[event] += 1
        if r.received_stream_end:
            stream_end_count += 1
    
    overall_stats = {
        "total_requests": total,
        "success_count": status_counts['success'],
        "success_rate": f"{(status_counts['success'] / total * 100):.2f}%",
        "timeout_count": status_counts['timeout'],
        "timeout_rate": f"{(status_counts['timeout'] / total * 100):.2f}%",
        "error_count": status_counts['error'],
        "incomplete_count": status_counts['incomplete'],
        "incomplete_rate": f"{(status_counts['incomplete'] / total * 100):.2f}%",
        "stream_end_received": stream_end_count,
        "stream_end_rate": f"{(stream_end_count / total * 100):.2f}%",
        "avg_duration": f"{(sum(durations) / len(durations)):.2f}s" if durations else "N/A",
        "min_duration": f"{min(durations):.2f}s" if durations else "N/A",
        "max_duration": f"{max(durations):.2f}s" if durations else "N/A",
    }
    
    return {
        "overall": overall_stats,
        "phases_started": dict(phase_started_stats),
        "phases_completed": dict(phase_completed_stats),
        "events_received": dict(event_stats),
        "segments": [early_stats, mid_stats, late_stats]
    }


def print_results(analysis: Dict[str, Any]) -> None:
    """分析結果を見やすく出力する"""
    print("\n" + "="*80)
    print("負荷テスト結果サマリー")
    print("="*80)
    
    print("\n【全体統計】")
    for key, value in analysis["overall"].items():
        print(f"  {key}: {value}")
    
    print("\n【受信イベント数】")
    if analysis["events_received"]:
        for event, count in sorted(analysis["events_received"].items()):
            print(f"  {event}: {count}回")
    else:
        print("  ⚠️  イベントが記録されていません")
    
    print("\n【フェーズ開始数】")
    if analysis["phases_started"]:
        for phase, count in sorted(analysis["phases_started"].items()):
            completion_count = analysis["phases_completed"].get(phase, 0)
            completion_rate = (completion_count / count * 100) if count > 0 else 0
            print(f"  {phase}: 開始{count}回 → 完了{completion_count}回 ({completion_rate:.1f}%)")
    else:
        print("  ⚠️  フェーズ開始イベントが記録されていません")
    
    print("\n【時系列分析】")
    for seg in analysis["segments"]:
        print(f"\n  --- {seg['name']} (全{seg['total']}件) ---")
        print(f"    成功: {seg['success']}件, タイムアウト: {seg['timeout']}件")
        print(f"    エラー: {seg['error']}件, 未完了: {seg['incomplete']}件")
        print(f"    stream_end受信: {seg['received_stream_end']}件 ({seg['received_stream_end']/seg['total']*100:.1f}%)")
        if seg['avg_duration'] > 0:
            print(f"    処理時間: 平均 {seg['avg_duration']:.2f}秒, 最小 {seg['min_duration']:.2f}秒, 最大 {seg['max_duration']:.2f}秒")
        
        if seg['phase_dropout']:
            print(f"    脱落フェーズ:")
            for phase, count in sorted(seg['phase_dropout'].items()):
                print(f"      - {phase}: {count}件")
    
    print("\n" + "="*80)


def save_detailed_results(results: List[RequestResult], analysis: Dict[str, Any], 
                         sse_counter: SSECounter, filename: str = "load_test_results.json") -> None:
    """詳細な結果をJSONファイルに保存"""
    output = {
        "test_config": {
            "concurrent_users": CONCURRENT_USERS,
            "total_requests": TOTAL_REQUESTS,
            "timeout_seconds": TIMEOUT_SECONDS,
            "test_time": datetime.now().isoformat()
        },
        "analysis": analysis,
        "sse_statistics": sse_counter.get_stats(),
        "detailed_results": [r.to_dict() for r in results]
    }
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n詳細結果を {filename} に保存しました。")
    
    # SSEカウンターのデータも保存
    sse_counter.save_to_file("sse_detailed_log.json")
    print(f"SSE詳細ログを sse_detailed_log.json に保存しました。")


def run_load_test():
    """負荷テストを実行する"""
    print(f"=== API負荷テスト開始 ===")
    print(f"同時接続数: {CONCURRENT_USERS}")
    print(f"合計リクエスト数: {TOTAL_REQUESTS}")
    print(f"タイムアウト: {TIMEOUT_SECONDS}秒")
    print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    sse_counter = SSECounter()
    results = []
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
        futures = []
        
        for i in range(TOTAL_REQUESTS):
            request_id = f"req_{i+1:04d}"
            message = TEST_MESSAGES[i % len(TEST_MESSAGES)]
            
            future = executor.submit(send_streaming_request, request_id, i+1, message, sse_counter)
            futures.append(future)
            
            if (i + 1) % 10 == 0:
                print(f"リクエスト送信中... {i+1}/{TOTAL_REQUESTS}")
        
        print("\n全リクエスト送信完了。処理を待機中...\n")
        
        # 結果を収集
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            results.append(result)
            
            status_icon = {
                "success": "✓",
                "incomplete": "⚠",
                "timeout": "⏱",
                "error": "✗"
            }.get(result.status, "?")
            
            stream_end_marker = "📨" if result.received_stream_end else "❌"
            phases_info = f"開始:{len(result.phases_started)} 完了:{len(result.phases_completed)}"
            
            print(f"[{i}/{TOTAL_REQUESTS}] {status_icon} {result.request_id}: {result.status} "
                  f"{stream_end_marker} ({result.duration:.2f}s, {phases_info}, 最終:{result.last_phase or 'N/A'})")
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # 結果をリクエスト順にソート
    results.sort(key=lambda x: x.request_order or 0)
    
    # 分析
    analysis = analyze_results(results)
    
    # 結果表示
    print(f"\n全体実行時間: {total_duration:.2f}秒")
    print_results(analysis)
    
    # 詳細結果を保存
    save_detailed_results(results, analysis, sse_counter)


if __name__ == "__main__":
    run_load_test()