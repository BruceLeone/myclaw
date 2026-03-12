# 数据库操作
import sqlite3
import os
import json
from datetime import datetime
from config import DATABASE_PATH, IMAGES_DIR


def init_database():
    """初始化数据库"""
    # 确保目录存在
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    os.makedirs(IMAGES_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 创建订单表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'pending',
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建订单图片表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            file_path TEXT NOT NULL,
            file_id TEXT,
            telegram_message_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
        )
    ''')
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_number ON orders(order_number)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_images_order_id ON order_images(order_id)')
    
    conn.commit()
    conn.close()
    print("✅ 数据库初始化完成")


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def search_order(order_number: str):
    """
    根据订单号搜索订单
    返回: 订单信息字典 或 None
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 精确匹配
    cursor.execute('''
        SELECT * FROM orders 
        WHERE order_number = ? COLLATE NOCASE
    ''', (order_number,))
    
    order = cursor.fetchone()
    
    if order:
        order_dict = dict(order)
        # 获取关联的图片
        cursor.execute('''
            SELECT file_path, file_id FROM order_images 
            WHERE order_id = ?
        ''', (order_dict['id'],))
        order_dict['images'] = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return order_dict
    
    conn.close()
    return None


def fuzzy_search_order(keyword: str):
    """
    模糊搜索订单
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM orders 
        WHERE order_number LIKE ? COLLATE NOCASE
        ORDER BY created_at DESC
        LIMIT 5
    ''', (f'%{keyword}%',))
    
    orders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return orders


def save_order_image(order_number: str, file_path: str, file_id: str = None, message_id: int = None):
    """
    保存订单图片
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 先查找订单ID
    cursor.execute('SELECT id FROM orders WHERE order_number = ? COLLATE NOCASE', (order_number,))
    order = cursor.fetchone()
    
    if order:
        cursor.execute('''
            INSERT INTO order_images (order_id, file_path, file_id, telegram_message_id)
            VALUES (?, ?, ?, ?)
        ''', (order['id'], file_path, file_id, message_id))
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False


def create_order(order_number: str, status: str = 'pending', description: str = None):
    """
    创建新订单（用于测试）
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO orders (order_number, status, description)
            VALUES (?, ?, ?)
        ''', (order_number, status, description))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False  # 订单已存在


def get_order_images(order_number: str):
    """
    获取订单的所有图片
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT oi.* FROM order_images oi
        JOIN orders o ON oi.order_id = o.id
        WHERE o.order_number = ? COLLATE NOCASE
    ''', (order_number,))
    
    images = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return images


def get_all_orders(limit: int = 20):
    """
    获取所有订单列表（用于管理）
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT o.*, COUNT(oi.id) as image_count 
        FROM orders o
        LEFT JOIN order_images oi ON o.id = oi.order_id
        GROUP BY o.id
        ORDER BY o.updated_at DESC
        LIMIT ?
    ''', (limit,))
    
    orders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return orders


def delete_order(order_number: str):
    """
    删除订单及其图片
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取订单ID
    cursor.execute('SELECT id FROM orders WHERE order_number = ? COLLATE NOCASE', (order_number,))
    order = cursor.fetchone()
    
    if order:
        # 获取图片路径
        cursor.execute('SELECT file_path FROM order_images WHERE order_id = ?', (order['id'],))
        images = cursor.fetchall()
        
        # 删除物理文件
        for img in images:
            try:
                if os.path.exists(img['file_path']):
                    os.remove(img['file_path'])
            except Exception as e:
                print(f"删除图片失败: {e}")
        
        # 删除数据库记录
        cursor.execute('DELETE FROM orders WHERE id = ?', (order['id'],))
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False


if __name__ == '__main__':
    # 直接运行此文件初始化数据库
    init_database()
    
    # 添加一些测试数据
    create_order('ORD2024001', 'completed', '测试订单1')
    create_order('ORD2024002', 'pending', '测试订单2')
    create_order('ABC123456', 'processing', '测试订单3')
    print("✅ 测试数据已添加")
