#!/bin/bash
# 性能压测执行脚本

echo "==================================="
echo "性能压测"
echo "==================================="

# 检查 locust 是否安装
if ! command -v locust &> /dev/null; then
    echo "错误: locust 未安装"
    echo "请安装: pip install locust"
    exit 1
fi

# 检查服务状态
echo "检查服务状态..."
if ! curl -s http://localhost:8010/health > /dev/null; then
    echo "警告: Portal 服务未启动 (http://localhost:8010)"
    echo "请先启动服务: make services-up"
    read -p "是否继续? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 默认参数
USERS=${USERS:-100}
SPAWN_RATE=${SPAWN_RATE:-10}
RUN_TIME=${RUN_TIME:-60s}
HOST=${HOST:-http://localhost:8010}
REPORT_FILE=${REPORT_FILE:-report.html}

echo ""
echo "压测配置:"
echo "  并发用户数: $USERS"
echo "  启动速率: $SPAWN_RATE 用户/秒"
echo "  运行时间: $RUN_TIME"
echo "  目标主机: $HOST"
echo ""

# 运行压测
echo "开始压测..."
locust -f tests/performance/locustfile.py \
    --headless \
    --users "$USERS" \
    --spawn-rate "$SPAWN_RATE" \
    --run-time "$RUN_TIME" \
    --host "$HOST" \
    --html "$REPORT_FILE"

echo ""
echo "==================================="
echo "压测完成"
echo "报告文件: $REPORT_FILE"
echo "==================================="
