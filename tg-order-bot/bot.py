#!/usr/bin/env python3
# Telegram 订单查询机器人主程序
import logging
import sys
import os

# 将当前目录添加到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from config import BOT_TOKEN, LOG_LEVEL
from database import init_database
from handlers import (
    start_command,
    check_command,
    help_command,
    add_test_order_command,
    process_order_message
)

# 配置日志
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """错误处理器"""
    logger.error(f"更新 {update} 导致错误: {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ 处理消息时出现错误，请稍后重试或联系管理员。"
        )


def main():
    """主函数"""
    # 检查 Token
    if not BOT_TOKEN or BOT_TOKEN == 'your_bot_token_here':
        print("❌ 错误: 请先在 .env 文件中设置 BOT_TOKEN")
        print("获取方法: 在 Telegram 中搜索 @BotFather，发送 /newbot 创建机器人")
        sys.exit(1)
    
    # 初始化数据库
    print("🔄 正在初始化数据库...")
    init_database()
    
    # 创建应用
    print("🤖 正在启动机器人...")
    application = Application.builder().token(BOT_TOKEN).build()
    
    # 注册命令处理器
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("addtest", add_test_order_command))
    
    # 注册消息处理器 - 监听包含订单关键词的消息
    # 文本消息
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            process_order_message
        )
    )
    
    # 带图片的消息
    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            process_order_message
        )
    )
    
    # 注册错误处理器
    application.add_error_handler(error_handler)
    
    print("✅ 机器人已启动！")
    print("📌 使用 Ctrl+C 停止")
    
    # 运行机器人
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
