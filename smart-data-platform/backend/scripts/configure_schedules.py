#!/usr/bin/env python3
"""Configure ETL pipeline schedules."""

import requests
import json

# Login
login_resp = requests.post("http://localhost:3101/api/v1/auth/login", json={
    "email": "admin@example.com",
    "password": "admin123456"
})
token = login_resp.json()["access_token"]

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Pipeline schedules
schedules = {
    "a135cb11-087e-40bc-8d4a-b15f00ab72e6": ("0 2 * * *", "金融交易日汇总 - 每天2AM"),
    "b921cca9-67e3-42a8-b0f1-6d543175edf1": ("0 3 1 * *", "员工薪资月度 - 每月1号3AM"),
    "7df913ae-f3c2-4a34-983a-102fd8270c8c": ("0 1 * * *", "告警统计 - 每天1AM"),
}

print("=" * 60)
print("Configuring Pipeline Schedules")
print("=" * 60)

for pipeline_id, (cron, desc) in schedules.items():
    resp = requests.patch(
        f"http://localhost:3101/api/v1/etl/pipelines/{pipeline_id}",
        headers=headers,
        json={"is_scheduled": True, "schedule_cron": cron}
    )

    if resp.status_code == 200:
        p = resp.json()
        print(f"  ✅ {p['name']}")
        print(f"     Cron: {p['schedule_cron']}")
    else:
        print(f"  ❌ Failed: {resp.text}")

print("-" * 60)
print("All Scheduled Pipelines:")
print("-" * 60)

resp = requests.get("http://localhost:3101/api/v1/etl/pipelines", headers=headers)
pipelines = resp.json()

for p in pipelines:
    if p.get("is_scheduled"):
        print(f"  🕐  {p['name'][:30]} | {p['schedule_cron']}")

print("=" * 60)
