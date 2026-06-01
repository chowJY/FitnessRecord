"""
训记训练数据 — 读取脚本
读取指定日期的训练计划 fulldata，并将服务端返回的 res 保存为 UTF-8 JSON 文件。

用法: python read_train.py [日期，默认 2026-06-01]
输出: ReadBack/read_2026-06-01.json
"""
import sys, os, json, requests
from pathlib import Path
from datetime import datetime

# === 配置 ===
BASE_URL = "https://trains.xunjiapp.cn"
READ_ENDPOINT = "/api_trains_for_llm_v2"
API_KEY = "xjllm_d42fb46179f672f1e039743c194e9ab51f1ae801bdea92c0"

# 输出目录
OUTPUT_DIR = Path(__file__).resolve().parent / "ReadBack"
OUTPUT_DIR.mkdir(exist_ok=True)


def read_training_plan(datestr: str, include_full_data: bool = True) -> dict:
    """
    读取指定日期的训练计划。
    
    Args:
        datestr: 日期字符串，格式 YYYY-MM-DD
        include_full_data: 是否获取完整数据（含未打勾组、RPE、备注等）
    
    Returns:
        服务端返回的完整 JSON 响应
    """
    url = f"{BASE_URL}{READ_ENDPOINT}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json; charset=utf-8",
    }
    payload = {
        "schema_version": "train_open_api_v2",
        "datestr": datestr,
        "include_full_data": include_full_data,
    }

    print(f"📡 请求: POST {url}")
    print(f"   datestr: {datestr}")
    print(f"   include_full_data: {include_full_data}")

    # 发送请求（JSON 使用 UTF-8 编码）
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.encoding = "utf-8"
    data = resp.json()

    print(f"   HTTP {resp.status_code}")
    print(f"   success: {data.get('success')}")
    
    # API 返回格式: {"res": {...}} 或 {"success": true, "res": {...}}
    has_data = data.get("res") is not None
    if not has_data and not data.get("success"):
        print(f"   error: {data.get('message', data)}")
    
    return data


def save_response(datestr: str, data: dict):
    """保存服务端响应到 JSON 文件（UTF-8 编码）"""
    filename = f"read_{datestr}.json"
    filepath = OUTPUT_DIR / filename

    # 同时保存请求信息
    saved = {
        "request": {
            "method": "POST",
            "endpoint": READ_ENDPOINT,
            "datestr": datestr,
            "include_full_data": True,
        },
        "response": data,
        "saved_at": datetime.now().isoformat(),
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(saved, f, ensure_ascii=False, indent=2)

    print(f"\n💾 已保存: {filepath}")
    
    # 统计信息
    if data.get("success") and data.get("res"):
        res = data["res"]
        trains = res.get("trains", res if isinstance(res, list) else [])
        if isinstance(trains, list):
            print(f"   📋 训练条数: {len(trains)}")
            for t in trains:
                title = t.get("title", "未命名")
                movements = t.get("movements", [])
                print(f"      - {title}: {len(movements)} 个动作")
    
    return filepath


def main():
    datestr = sys.argv[1] if len(sys.argv) > 1 else "2026-06-01"
    
    print("=" * 60)
    print(f"🔍 读取训记训练计划 — {datestr}")
    print("=" * 60)
    
    # 1. 读取
    data = read_training_plan(datestr, include_full_data=True)
    
    # 2. 保存
    save_response(datestr, data)
    
    # 3. 打印结果摘要
    has_data = data.get("res") is not None
    if has_data or data.get("success"):
        print(f"\n✅ 读取成功")
    else:
        print(f"\n❌ 读取失败: {data.get('message', '未知错误')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
