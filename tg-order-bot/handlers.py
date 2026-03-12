# 消息处理器
import re
import os
import aiohttp
from telegram import Update
from telegram.ext import ContextTypes
from config import ORDER_KEYWORDS, ORDER_NUMBER_PATTERNS, IMAGES_DIR
from database import search_order, save_order_image, fuzzy_search_order, create_order


async def download_image(file_id: str, file_path: str, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    下载 Telegram 图片
    """
    try:
        # 获取文件对象
        file_obj = await context.bot.get_file(file_id)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 下载文件
        await file_obj.download_to_drive(file_path)
        return file_path
    except Exception as e:
        print(f"下载图片失败: {e}")
        return None


def extract_order_number(text: str) -> str:
    """
    从消息文本中提取订单号
    """
    if not text:
        return None
    
    text = text.strip()
    
    # 尝试各种模式匹配
    for pattern in ORDER_NUMBER_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip().upper()
    
    return None


def contains_order_keyword(text: str) -> bool:
    """
    检查文本是否包含订单关键词
    """
    if not text:
        return False
    
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in ORDER_KEYWORDS)


async def process_order_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    处理包含订单关键词的消息
    """
    message = update.message or update.channel_post
    if not message:
        return
    
    # 提取文本内容
    text = message.text or message.caption or ""
    
    # 检查是否包含订单关键词
    if not contains_order_keyword(text):
        return
    
    # 提取订单号
    order_number = extract_order_number(text)
    
    if not order_number:
        # 有关键词但没提取到订单号格式
        await message.reply_text(
            "⚠️ 检测到订单关键词，但未识别到有效的订单号格式。\n"
            "支持的格式：订单号:XXX、订单 XXX、order XXX、#XXX"
        )
        return
    
    print(f"🔍 检测到订单号: {order_number}")
    
    # 查询数据库
    order = search_order(order_number)
    
    if order:
        # 订单匹配成功
        await handle_matched_order(update, context, order, message)
    else:
        # 订单未匹配
        await handle_unmatched_order(update, context, order_number, text)


async def handle_matched_order(update: Update, context: ContextTypes.DEFAULT_TYPE, order: dict, message):
    """
    处理匹配成功的订单
    """
    order_number = order['order_number']
    
    # 检查消息中是否有图片
    photos = message.photo if message.photo else []
    
    if photos:
        # 获取最高质量的图片
        photo = photos[-1]  # 最后一个是原图
        file_id = photo.file_id
        
        # 生成保存路径
        timestamp = int(message.date.timestamp())
        file_name = f"{order_number}_{timestamp}_{file_id}.jpg"
        file_path = os.path.join(IMAGES_DIR, file_name)
        
        # 下载图片
        downloaded_path = await download_image(file_id, file_path, context)
        
        if downloaded_path:
            # 保存到数据库
            save_order_image(
                order_number=order_number,
                file_path=downloaded_path,
                file_id=file_id,
                message_id=message.message_id
            )
            
            # 回复确认消息
            existing_images = len(order.get('images', []))
            await message.reply_text(
                f"✅ **订单匹配成功！**\n\n"
                f"📋 订单号: `{order_number}`\n"
                f"📊 状态: {get_status_text(order['status'])}\n"
                f"📸 已保存图片 ({existing_images + 1} 张)\n\n"
                f"📝 {order.get('description', '暂无描述')}",
                parse_mode='Markdown'
            )
        else:
            await message.reply_text(
                f"✅ 订单匹配成功！\n\n"
                f"📋 订单号: {order_number}\n"
                f"📊 状态: {get_status_text(order['status'])}\n\n"
                f"⚠️ 但图片保存失败，请重试。"
            )
    else:
        # 匹配成功但没有图片
        await message.reply_text(
            f"✅ **订单匹配成功！**\n\n"
            f"📋 订单号: `{order_number}`\n"
            f"📊 状态: {get_status_text(order['status'])}\n\n"
            f"💡 如需保存图片，请一并发送图片。",
            parse_mode='Markdown'
        )


async def handle_unmatched_order(update: Update, context: ContextTypes.DEFAULT_TYPE, order_number: str, original_text: str):
    """
    处理未匹配的订单 - 返回错误消息
    """
    message = update.message or update.channel_post
    
    # 尝试模糊搜索建议
    suggestions = fuzzy_search_order(order_number[:6])  # 使用前6位搜索
    
    error_msg = (
        f"❌ **订单查询失败**\n\n"
        f"📋 订单号: `{order_number}`\n"
        f"🔍 在数据库中未找到匹配记录\n\n"
    )
    
    if suggestions:
        error_msg += "🤔 您是否想找:\n"
        for sugg in suggestions[:3]:
            error_msg += f"   • `{sugg['order_number']}` ({get_status_text(sugg['status'])})\n"
        error_msg += "\n"
    
    error_msg += (
        "请检查:\n"
        "   1️⃣ 订单号是否输入正确\n"
        "   2️⃣ 该订单是否已录入系统\n"
        "   3️⃣ 联系管理员添加订单"
    )
    
    await message.reply_text(error_msg, parse_mode='Markdown')


def get_status_text(status: str) -> str:
    """
    获取状态显示文本
    """
    status_map = {
        'pending': '⏳ 待处理',
        'processing': '🔄 处理中',
        'completed': '✅ 已完成',
        'cancelled': '❌ 已取消'
    }
    return status_map.get(status, f'📋 {status}')


# ============== 命令处理器 ==============

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start 命令
    """
    welcome_text = (
        "👋 **欢迎使用订单查询机器人！**\n\n"
        "📌 **功能说明:**\n"
        "   • 自动检测群聊中的订单关键词\n"
        "   • 匹配订单号并保存关联图片\n"
        "   • 支持主动查询订单\n\n"
        "📝 **使用方法:**\n"
        "   • 在消息中包含: 订单号 XXX 或 order XXX\n"
        "   • 主动查询: /check <订单号>\n\n"
        "💡 **示例:**\n"
        "   订单号: ORD2024001\n"
        "   /check ORD2024001"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /check <订单号> 命令 - 主动查询订单
    """
    if not context.args:
        await update.message.reply_text(
            "❌ 请提供订单号\n"
            "用法: `/check <订单号>`\n"
            "示例: `/check ORD2024001`",
            parse_mode='Markdown'
        )
        return
    
    order_number = context.args[0].strip().upper()
    order = search_order(order_number)
    
    if order:
        image_count = len(order.get('images', []))
        response = (
            f"✅ **订单查询成功**\n\n"
            f"📋 订单号: `{order_number}`\n"
            f"📊 状态: {get_status_text(order['status'])}\n"
            f"📸 图片数量: {image_count} 张\n"
            f"🕐 创建时间: {order['created_at']}\n\n"
            f"📝 描述: {order.get('description', '暂无')}\n"
        )
        
        # 如果有图片，发送图片
        if order.get('images'):
            await update.message.reply_text(response, parse_mode='Markdown')
            for img in order['images'][:5]:  # 最多显示5张
                if os.path.exists(img['file_path']):
                    await update.message.reply_photo(photo=open(img['file_path'], 'rb'))
        else:
            await update.message.reply_text(response, parse_mode='Markdown')
    else:
        await update.message.reply_text(
            f"❌ **订单未找到**\n\n"
            f"📋 订单号: `{order_number}`\n"
            f"🔍 数据库中无此订单记录\n\n"
            f"请检查订单号是否正确，或联系管理员添加。",
            parse_mode='Markdown'
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /help 命令
    """
    help_text = (
        "📖 **命令列表**\n\n"
        "/start - 开始使用\n"
        "/check <订单号> - 查询订单\n"
        "/help - 显示帮助\n\n"
        "🔍 **自动检测关键词:**\n"
        "   • 订单号\n"
        "   • 订单\n" 
        "   • order / order#\n\n"
        "📌 **支持的订单号格式:**\n"
        "   • 订单号: ABC123\n"
        "   • 订单 ABC123\n"
        "   • order ABC123\n"
        "   • order#ABC123\n"
        "   • #ABC123"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def add_test_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /addtest <订单号> [状态] [描述] - 添加测试订单（仅管理员）
    """
    # 简单检查 - 实际生产环境应该验证管理员ID
    if not context.args:
        await update.message.reply_text("用法: /addtest <订单号> [状态] [描述]")
        return
    
    order_number = context.args[0].upper()
    status = context.args[1] if len(context.args) > 1 else 'pending'
    description = ' '.join(context.args[2:]) if len(context.args) > 2 else '测试订单'
    
    if create_order(order_number, status, description):
        await update.message.reply_text(f"✅ 测试订单 `{order_number}` 已添加", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"⚠️ 订单 `{order_number}` 已存在或添加失败", parse_mode='Markdown')
