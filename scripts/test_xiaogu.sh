#!/bin/bash
# 小股股票提醒测试脚本
# 用法: ./test_xiaogu.sh [morning|noon]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORT_TYPE="${1:-morning}"

echo "================================"
echo "🧪 小股股票提醒测试"
echo "类型: ${REPORT_TYPE}"
echo "================================"
echo ""

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python3"
    exit 1
fi

# 运行测试
cd /root/.openclaw/workspace
python3 scripts/xiaogu_stock_report.py --type "${REPORT_TYPE}" --dry-run

echo ""
echo "================================"
echo "✅ 测试完成"
echo "================================"
