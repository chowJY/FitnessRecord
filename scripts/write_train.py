"""
训记训练数据 — 写回脚本
将测试训练数据写入指定日期，并将服务端返回的 res 保存为 UTF-8 JSON 文件。

用法: python write_train.py [日期，默认 2026-06-02]
输出: ReadBack/write_2026-06-02.json

写回规则:
  - 每条训练最多 15 个动作，每个动作最多 20 组
  - 有 localid 时更新原训练；无 localid 时新建
  - 动作只传中文 name，服务端自动回填 key
  - 单次最多 4 条训练，且必须同一天
"""
import sys, os, json, requests, uuid, time
from pathlib import Path
from datetime import datetime

# === 配置 ===
BASE_URL = "https://trains.xunjiapp.cn"
WRITE_ENDPOINT = "/api_upsert_trains_for_llm_v2"
API_KEY = "xjllm_d42fb46179f672f1e039743c194e9ab51f1ae801bdea92c0"

# 输出目录
OUTPUT_DIR = Path(__file__).resolve().parent / "ReadBack"
OUTPUT_DIR.mkdir(exist_ok=True)


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


def write_training_plan(datestr: str, trains: list[dict], dry_run: bool = False) -> dict:
    """
    写回训练计划。
    
    Args:
        datestr: 日期字符串，格式 YYYY-MM-DD
        trains: 训练数据列表（最多 4 条）
        dry_run: True 时仅模拟不实际写入
    
    Returns:
        服务端返回的完整 JSON 响应
    """
    url = f"{BASE_URL}{WRITE_ENDPOINT}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json; charset=utf-8",
    }

    client_request_id = f"test-{uuid.uuid4().hex[:12]}"

    payload = {
        "schema_version": "train_open_api_v2",
        "client_request_id": client_request_id,
        "dry_run": dry_run,
        "include_full_data": True,
        "res": trains,
    }

    print(f"📡 请求: POST {url}")
    print(f"   datestr: {datestr}")
    print(f"   client_request_id: {client_request_id}")
    print(f"   dry_run: {dry_run}")
    print(f"   训练条数: {len(trains)}")
    for t in trains:
        print(f"     - {t['title']}: {len(t['movements'])} 个动作")

    # 发送请求（JSON 使用 UTF-8 编码）
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.encoding = "utf-8"
    data = resp.json()

    print(f"   HTTP {resp.status_code}")
    print(f"   success: {data.get('success')}")
    
    has_data = data.get("res") is not None
    if not has_data and not data.get("success"):
        print(f"   error: {data.get('message', data)}")
    
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


def save_response(datestr: str, response_data: dict, request_payload: dict):
    """保存服务端响应和请求数据到 JSON 文件（UTF-8 编码）"""
    filename = f"write_{datestr}.json"
    filepath = OUTPUT_DIR / filename

    saved = {
        "request": {
            "method": "POST",
            "endpoint": WRITE_ENDPOINT,
            "payload": request_payload,
        },
        "response": response_data,
        "saved_at": datetime.now().isoformat(),
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(saved, f, ensure_ascii=False, indent=2)

    print(f"\n💾 已保存: {filepath}")
    return filepath


def main():
    datestr = sys.argv[1] if len(sys.argv) > 1 else "2026-06-02"

    print("=" * 60)
    print(f"✏️  写回训记测试数据 — {datestr}")
    print("=" * 60)

    # 1. 构建测试数据
    trains = build_test_data(datestr)

    # 2. 展示变更摘要
    display_change_summary(trains)

    # 3. 直接写回（dry_run 仍会实际写入，不单独调用）
    print(f"\n📤 正式写回...")
    data, payload = write_training_plan(datestr, trains, dry_run=False)

    # 4. 保存
    save_response(datestr, data, payload)

    # 5. 结果
    has_data = data.get("res") is not None
    if has_data or data.get("success"):
        print(f"\n✅ 写回成功")
        res = data.get("res", {})
        trains_res = res.get("trains", res if isinstance(res, list) else [])
        if isinstance(trains_res, list):
            for t in trains_res:
                print(f"   🏷️  {t.get('title', '?')} (localid={t.get('localid', 'new')})")
    else:
        err = data.get('error', data.get('message', '未知错误'))
        print(f"\n❌ 写回失败: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
