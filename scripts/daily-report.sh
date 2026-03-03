#!/bin/bash
# 每日8点发送主管日报脚本

# 生成日报内容
REPORT="📋 主管日报 $(date +'%Y-%m-%d')
━━━━━━━━━━━━━━━━━━━━━━━━
🎯 昨日动态:
  • My bro群: 暂无数据（新系统启动）
  • 财务记录: 暂无数据
  • 新处理文件: 0份
  • 失败任务: 0个

📊 系统状态:
  • 活跃角色: 小股、小财、小处
  • Token消耗: 0
  • 运行状态: 正常

⏰ 今日待办:
  • 等待用户指令
"

# 发送到飞书
openclaw message send --channel feishu --target "ou_91a2622ef19d6d15685de34feca7b274" --message "$REPORT"
