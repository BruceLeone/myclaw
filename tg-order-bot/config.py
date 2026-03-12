# 配置
import os
from dotenv import load_dotenv

load_dotenv()

# Bot Token (从 @BotFather 获取)
BOT_TOKEN = os.getenv('BOT_TOKEN', '')

# 数据库配置
DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/orders.db')
IMAGES_DIR = os.getenv('IMAGES_DIR', 'data/images')

# 订单关键词配置
ORDER_KEYWORDS = ['订单号', '订单', 'order', 'order#', 'orderno']

# 订单号正则匹配模式
ORDER_NUMBER_PATTERNS = [
    r'订单号[\s:：]*(\w+)',       # 订单号: ABC123 / 订单号 ABC123 / 订单号ABC123 / 订单号：ABC123
    r'订单[\s:：]+(\w+)',         # 订单: ABC123 / 订单 ABC123
    r'order[\s:：]+#?(\w+)',      # order ABC123 / order: ABC123 / order #ABC123
    r'order#(\w+)',               # order#ABC123
    r'#(\w{4,})',                 # #ABC123 (至少4位)
    r'\b([A-Z]{2,}\d{4,})\b',     # AB123456 (字母+数字组合)
    r'\b(\d{6,})\b',              # 纯数字至少6位
]

# 日志配置
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# 管理员ID列表（用于调试通知）
ADMIN_IDS = [int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]
