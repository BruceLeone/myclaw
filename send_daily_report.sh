#!/bin/bash
# Daily operation report send script for Feishu
# Timezone: UTC+8, runs at 9 AM daily

# Get date variables
YESTERDAY=$(date -d "yesterday" +"%Y年%m月%d日")
TODAY=$(date +"%Y年%m月%d日")

# Generate dynamic report content (replace with real data API calls later)
REPORT_CONTENT="# 📊 每日运营报告 | ${YESTERDAY}
---
## 一、核心数据统计
| 指标 | 数值 | 日环比 | 说明 |
| --- | --- | --- | --- |
| 新增用户 | $((1000 + RANDOM % 500)) | +$((5 + RANDOM % 10)).$((RANDOM % 10))% | 拉新活动稳定推进 |
| 活跃用户 | $((8 + RANDOM % 2)).$((RANDOM % 100))万 | +$((2 + RANDOM % 5)).$((RANDOM % 10))% | 日活保持稳定增长 |
| 付费转化率 | 3.$((RANDOM % 20))% | $([ $((RANDOM % 2)) -eq 0 ] && echo "+" || echo "-")0.$((RANDOM % 20))% | 正常波动范围 |
| 总营收 | $((10 + RANDOM % 5)).$((RANDOM % 100))万元 | +$((3 + RANDOM % 7)).$((RANDOM % 10))% | 营收稳步提升 |
| 客服响应时长 | $((1 + RANDOM % 2))分$((RANDOM % 60))秒 | $([ $((RANDOM % 2)) -eq 0 ] && echo "+" || echo "-")$((5 + RANDOM % 10))% | 服务质量稳定 |
---
## 二、${YESTERDAY}任务完成进度
✅ 已完成（$((6 + RANDOM % 2))/8，完成率$((75 + RANDOM % 20))%）
1. 日常系统运维巡检 → 100% 无异常
2. 用户反馈处理 → 100% 完结率98%
3. 数据同步备份 → 100% 备份正常
4. 内容更新审核 → 100% 按时完成
5. 商务对接跟进 → $((90 + RANDOM % 10))% 进展顺利
6. 性能优化迭代 → $((80 + RANDOM % 15))% 按计划推进
⏳ 进行中
1. 新版本功能测试 → $((70 + RANDOM % 20))% 预计明日完成
---
## 三、${TODAY}待办清单
🔴 高优先级
1. 系统常规安全更新
2. 今日活动上线检查
3. 周中运营进度同步会
🟡 中优先级
1. 整理本周运营数据
2. 用户留存策略优化
3. 新功能需求评审
🟢 低优先级
1. 内部知识库更新
2. 团队周会安排
---
## 四、数据看板趋势概览
1. 用户增长：近7天复合增长率$((2 + RANDOM % 3)).$((RANDOM % 10))%，表现良好
2. 营收趋势：近30天保持稳定增长，预计月底达目标的$((90 + RANDOM % 10))%
3. 留存数据：7日留存稳定在$((35 + RANDOM % 5))%，高于行业平均
4. 系统可用性：昨日99.9$((7 + RANDOM % 3))%，无重大异常
---
⚠️ 本报告当前为模拟数据，后续对接真实数据源后将自动替换为实际运营数据。"

# Send to Feishu user
openclaw message send --channel feishu --target "user:ou_91a2622ef19d6d15685de34feca7b274" --message "$REPORT_CONTENT"
