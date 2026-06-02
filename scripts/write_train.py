"""
训记训练数据 — 写回脚本
将训练数据写入指定日期。成功时静默，仅在失败或异常时记录错误日志。

用法: python write_train.py [日期，默认 2026-06-02]
       python write_train.py [日期] --verbose  显示详细请求/响应信息
错误日志: ReadBack/write_errors.jsonl（仅追加失败记录）

写回规则:
  - 每条训练最多 15 个动作，每个动作最多 20 组
  - 有 localid 时更新原训练；无 localid 时新建
  - 动作只传中文 name，服务端自动回填 key
  - 单次最多 4 条训练，且必须同一天
"""
import sys, os, json, requests, uuid, time, traceback
from pathlib import Path
from datetime import datetime

# === 配置 ===
BASE_URL = "https://trains.xunjiapp.cn"
WRITE_ENDPOINT = "/api_upsert_trains_for_llm_v2"
API_KEY = "xjllm_d42fb46179f672f1e039743c194e9ab51f1ae801bdea92c0"

# 错误日志目录
OUTPUT_DIR = Path(__file__).resolve().parent / "ReadBack"
OUTPUT_DIR.mkdir(exist_ok=True)
ERROR_LOG = OUTPUT_DIR / "write_errors.jsonl"


def build_test_data(datestr: str) -> list[dict]:
    """
    构建测试训练数据。
    包含一条完整的胸部+三头训练，用于测试写回功能。
    """
    now_ms = int(time.time() * 1000)
    day_ts = int(datetime.strptime(datestr, "%Y-%m-%d").timestamp() * 1000)
    # 假设训练在当天 09:00-10:00 进行
    start_ts = day_ts + 9 * 3600 * 1000
    end_ts = start_ts + 3600 * 1000

    return [
        {
            "datestr": datestr,
            "title": "三分化-推日（测试数据）",
            "start": start_ts,
            "end": end_ts,
            "movements": [
                {
                    "name": "杠铃卧推",
                    "sets": [
                        {"done": True, "weight": "60", "unit": "kg", "reps": "12"},
                        {"done": True, "weight": "70", "unit": "kg", "reps": "10"},
                        {"done": True, "weight": "80", "unit": "kg", "reps": "8"},
                        {"done": True, "weight": "80", "unit": "kg", "reps": "8"},
                    ]
                },
                {
                    "name": "哑铃上斜推",
                    "sets": [
                        {"done": True, "weight": "25", "unit": "kg", "reps": "12"},
                        {"done": True, "weight": "27.5", "unit": "kg", "reps": "10"},
                        {"done": True, "weight": "27.5", "unit": "kg", "reps": "10"},
                    ]
                },
                {
                    "name": "器械夹胸",
                    "sets": [
                        {"done": True, "weight": "35", "unit": "kg", "reps": "15"},
                        {"done": True, "weight": "40", "unit": "kg", "reps": "12"},
                        {"done": True, "weight": "40", "unit": "kg", "reps": "12"},
                    ]
                },
                {
                    "name": "龙门下压",
                    "sets": [
                        {"done": True, "weight": "20", "unit": "kg", "reps": "15"},
                        {"done": True, "weight": "22.5", "unit": "kg", "reps": "12"},
                        {"done": True, "weight": "22.5", "unit": "kg", "reps": "12"},
                    ]
                },
                {
                    "name": "龙门卷腹",
                    "sets": [
                        {"done": True, "weight": "25", "unit": "kg", "reps": "15"},
                        {"done": True, "weight": "25", "unit": "kg", "reps": "15"},
                        {"done": True, "weight": "25", "unit": "kg", "reps": "15"},
                    ]
                },
            ]
        }
    ]


def write_training_plan(datestr: str, trains: list[dict], dry_run: bool = False, verbose: bool = False) -> tuple[dict, dict]:
    """
    写回训练计划。
    
    Args:
        datestr: 日期字符串，格式 YYYY-MM-DD
        trains: 训练数据列表（最多 4 条）
        dry_run: True 时仅模拟不实际写入
        verbose: True 时打印请求/响应详情
    
    Returns:
        (response_data, request_payload)
    """
    url = f"{BASE_URL}{WRITE_ENDPOINT}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json; charset=utf-8",
    }

    client_request_id = f"wr-{uuid.uuid4().hex[:12]}"

    payload = {
        "schema_version": "train_open_api_v2",
        "client_request_id": client_request_id,
        "dry_run": dry_run,
        "include_full_data": True,
        "res": trains,
    }

    if verbose:
        print(f"📡 POST {url}")
        print(f"   datestr: {datestr}  dry_run: {dry_run}")
        print(f"   trains: {len(trains)} 条")
        for t in trains:
            print(f"     - {t['title']}: {len(t['movements'])} 动作")

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.encoding = "utf-8"
        data = resp.json()
    except Exception as e:
        # 网络/解析异常
        error_data = {
            "error": str(e),
            "exception_type": type(e).__name__,
            "traceback": traceback.format_exc(),
        }
        if verbose:
            print(f"   ❌ 请求异常: {e}")
        return error_data, payload

    if verbose:
        print(f"   HTTP {resp.status_code}  success: {data.get('success')}")

    return data, payload


def display_change_summary(trains: list[dict]):
    """展示写回变更摘要（写回前确认用）"""
    print("\n📋 变更摘要:")
    print("=" * 40)
    for t in trains:
        print(f"\n🏷️  训练: {t['title']}")
        print(f"   日期: {t['datestr']}")
        if t.get("localid"):
            print(f"   类型: 更新 (localid={t['localid']})")
        else:
            print(f"   类型: 新建")
        
        total_sets = 0
        for m in t.get("movements", []):
            sets = m.get("sets", [])
            total_sets += len(sets)
            done_sets = sum(1 for s in sets if s.get("done"))
            print(f"   🏋️ {m['name']}: {len(sets)} 组 ({done_sets} 组完成)")
        print(f"   📊 总计: {len(t['movements'])} 动作, {total_sets} 组")
    print("=" * 40)


def log_error(datestr: str, error_info: str, response_data: dict = None, request_payload: dict = None):
    """仅在失败时追加错误日志（JSONL 格式）"""
    entry = {
        "datestr": datestr,
        "timestamp": datetime.now().isoformat(),
        "error": error_info,
    }
    if response_data is not None:
        entry["response"] = response_data
    if request_payload is not None:
        entry["request"] = request_payload

    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"❌ {datestr} 写入失败 → 错误已记录: {ERROR_LOG}")


def main():
    datestr = sys.argv[1] if len(sys.argv) > 1 else "2026-06-02"
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    # 构建测试数据
    trains = build_test_data(datestr)

    if verbose:
        display_change_summary(trains)

    # 写回
    data, payload = write_training_plan(datestr, trains, dry_run=False, verbose=verbose)

    # 判断成败
    has_data = data.get("res") is not None
    is_success = data.get("success") or has_data

    if is_success:
        res = data.get("res", {})
        trains_res = res.get("trains", res if isinstance(res, list) else [])
        titles = ", ".join(t.get("title", "?") for t in trains_res)
        print(f"✅ {datestr} — {titles}")
        return

    # 失败：记录错误日志
    err_msg = data.get("error") or data.get("message") or "未知错误"
    log_error(datestr, err_msg, response_data=data, request_payload=payload)
    sys.exit(1)


if __name__ == "__main__":
    main()
