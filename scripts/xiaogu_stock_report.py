#!/usr/bin/env python3
"""
小股股票分析提醒脚本 - 基于新浪财经/东方财富公开API
作者：小股
功能：获取当日财经热点、板块涨跌、北向资金流向、大盘行情，生成专业分析并发送到Feishu群
"""

import requests
import json
import sys
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time

# Feishu群ID
FEISHU_GROUP_ID = "oc_68a232050ed9787d0245ae6929b1d429"

# ============ 配置 ============
# 请求超时设置
TIMEOUT = 15
# 重试次数
MAX_RETRIES = 3
# 重试延迟
RETRY_DELAY = 1

# 大盘指数代码映射
INDEX_CODES = {
    "sh000001": {"name": "上证指数", "market": "1"},
    "sz399001": {"name": "深证成指", "market": "0"},
    "sz399006": {"name": "创业板指", "market": "0"},
    "sh000300": {"name": "沪深300", "market": "1"},
    "sh000016": {"name": "上证50", "market": "1"},
    "sz399005": {"name": "中小板指", "market": "0"},
}

# ============ 工具函数 ============
def retry_request(func, *args, **kwargs) -> Optional[Dict]:
    """带重试的请求包装器"""
    for attempt in range(MAX_RETRIES):
        try:
            result = func(*args, **kwargs)
            if result:
                return result
        except Exception as e:
            print(f"请求失败 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
    return None

def format_change(change_pct: float) -> str:
    """格式化涨跌幅，带颜色标识"""
    if change_pct > 0:
        return f"📈 +{change_pct:.2f}%"
    elif change_pct < 0:
        return f"📉 {change_pct:.2f}%"
    else:
        return f"➖ {change_pct:.2f}%"

def format_money(amount: float) -> str:
    """格式化金额（亿为单位）"""
    return f"{amount:.2f}亿"

# ============ 数据获取接口 ============
class StockDataAPI:
    """股票数据获取类"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://quote.eastmoney.com',
        })
    
    def get_index_quotes(self) -> List[Dict]:
        """
        获取大盘指数行情 - 东方财富API（主要）+ 新浪财经（降级）
        """
        try:
            # 使用东方财富API获取指数行情
            url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
            params = {
                'fltt': '2',
                'invt': '2',
                'fields': 'f1,f2,f3,f4,f12,f13,f14,f20,f104,f105,f106,f107',
                'secids': '1.000001,0.399001,0.399006,1.000300',
                '_': int(time.time() * 1000)
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://quote.eastmoney.com/',
            }
            
            resp = self.session.get(url, params=params, headers=headers, timeout=TIMEOUT)
            data = resp.json()
            
            result = []
            if 'data' in data and 'diff' in data['data']:
                code_map = {
                    '000001': '上证指数',
                    '399001': '深证成指', 
                    '399006': '创业板指',
                    '000300': '沪深300'
                }
                
                for item in data['data']['diff']:
                    code = item.get('f12', '')
                    name = code_map.get(code, item.get('f14', ''))
                    # f2=最新价, f3=涨跌幅%, f4=涨跌额, f104=成交量(手)
                    price = item.get('f2', 0)
                    change_pct = item.get('f3', 0)
                    change_amount = item.get('f4', 0)
                    
                    # 东财返回的价格和涨跌幅需要除以100
                    if price:
                        price = price / 100
                    if change_pct:
                        change_pct = change_pct / 100
                    if change_amount:
                        change_amount = change_amount / 100
                    
                    result.append({
                        'name': name,
                        'price': price,
                        'change_pct': change_pct,
                        'change_amount': change_amount,
                        'volume': item.get('f104', 0) / 10000 if item.get('f104') else 0
                    })
            
            return result
        except Exception as e:
            print(f"获取指数行情失败: {e}")
            return []
    
    def get_sector_ranking(self, top_n: int = 5) -> Tuple[List[Dict], List[Dict]]:
        """
        获取板块涨幅榜/跌幅榜 - 东方财富API
        """
        try:
            # 使用东方财富行业板块接口
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'pn': '1',
                'pz': '100',
                'po': '1',
                'np': '1',
                'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                'fltt': '2',
                'invt': '2',
                'fid': 'f20',  # 按成交额排序获取活跃板块
                'fs': 'm:90+t:2',  # 行业板块
                'fields': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f26,f22,f33,f11,f62,f128,f136,f115,f152',
                '_': int(time.time() * 1000)
            }
            
            resp = self.session.get(url, params=params, timeout=TIMEOUT)
            data = resp.json()
            
            sectors = []
            if 'data' in data and data['data'] and 'diff' in data['data']:
                for item in data['data']['diff']:
                    name = item.get('f14', '')
                    change_pct = item.get('f3', 0) / 100 if item.get('f3') else 0
                    # f128是领涨股名称，f136是领涨股涨幅
                    main_stock = item.get('f128', '') if item.get('f128') else ''
                    main_stock_change = item.get('f136', 0) / 100 if item.get('f136') else 0
                    
                    if name:
                        sectors.append({
                            'name': name,
                            'change_pct': change_pct,
                            'main_stock': main_stock,
                            'main_stock_change': main_stock_change
                        })
            
            # 排序并分离涨跌
            sectors_sorted = sorted(sectors, key=lambda x: x['change_pct'], reverse=True)
            gainers = [s for s in sectors_sorted if s['change_pct'] > 0][:top_n]
            losers = [s for s in sectors_sorted if s['change_pct'] < 0][-top_n:]
            losers.reverse()
            
            return gainers, losers
        except Exception as e:
            print(f"获取板块排行失败: {e}")
            return self._get_sector_ranking_concept(top_n)
    
    def _get_sector_ranking_concept(self, top_n: int = 5) -> Tuple[List[Dict], List[Dict]]:
        """使用概念板块作为降级方案"""
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'pn': '1',
                'pz': '100',
                'po': '1',
                'np': '1',
                'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
                'fltt': '2',
                'invt': '2',
                'fid': 'f20',
                'fs': 'm:90+t:3',  # 概念板块
                'fields': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f20,f128,f136',
                '_': int(time.time() * 1000)
            }
            resp = self.session.get(url, params=params, timeout=TIMEOUT)
            data = resp.json()
            
            sectors = []
            if 'data' in data and data['data'] and 'diff' in data['data']:
                for item in data['data']['diff']:
                    sectors.append({
                        'name': item.get('f14', ''),
                        'change_pct': item.get('f3', 0) / 100 if item.get('f3') else 0,
                        'main_stock': item.get('f128', ''),
                        'main_stock_change': item.get('f136', 0) / 100 if item.get('f136') else 0
                    })
            
            sectors_sorted = sorted(sectors, key=lambda x: x['change_pct'], reverse=True)
            gainers = [s for s in sectors_sorted if s['change_pct'] > 0][:top_n]
            losers = [s for s in sectors_sorted if s['change_pct'] < 0][-top_n:]
            losers.reverse()
            return gainers, losers
        except Exception as e:
            print(f"概念板块也失败: {e}")
            return [], []
    
    def get_northbound_flow(self) -> Dict:
        """
        获取北向资金流向 - 东方财富API
        s2n数据格式: ['时间,沪股通流入,深股通流入,总流入,沪股通累计,深股通累计,...', ...]
        """
        try:
            url = "https://push2.eastmoney.com/api/qt/kamt.rtmin/get"
            params = {
                'fields1': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65',
                'ut': 'b2884a393a59ad64002292a3e90d46a5',
                '_': int(time.time() * 1000)
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://quote.eastmoney.com/',
            }
            
            resp = self.session.get(url, params=params, headers=headers, timeout=TIMEOUT)
            data = resp.json()
            
            result = {
                'sh_inflow': 0,
                'sz_inflow': 0,
                'total_inflow': 0,
                'sh_cum_inflow': 0,
                'sz_cum_inflow': 0,
                'total_cum_inflow': 0,
                'data_time': ''
            }
            
            if data and 'data' in data and 's2n' in data['data']:
                s2n_list = data['data']['s2n']
                if s2n_list and isinstance(s2n_list, list):
                    # 获取最后一条数据（最新）
                    latest = s2n_list[-1]
                    parts = latest.split(',')
                    # 格式: 时间,沪股通流入,深股通流入,总流入,沪股通累计,深股通累计
                    if len(parts) >= 6:
                        result['data_time'] = parts[0]
                        result['sh_inflow'] = float(parts[1]) if parts[1] else 0
                        result['sz_inflow'] = float(parts[2]) if parts[2] else 0
                        result['total_inflow'] = float(parts[3]) if parts[3] else 0
                        result['sh_cum_inflow'] = float(parts[4]) if parts[4] else 0
                        result['sz_cum_inflow'] = float(parts[5]) if parts[5] else 0
                        result['total_cum_inflow'] = result['sh_cum_inflow'] + result['sz_cum_inflow']
            
            # 如果获取的数据都是0，可能是非交易时间
            if result['total_inflow'] == 0:
                print("北向资金数据为0，可能是非交易时间")
            
            return result
        except Exception as e:
            print(f"获取北向资金失败: {e}")
            return self._get_northbound_flow_alternative()
    
    def _get_northbound_flow_alternative(self) -> Dict:
        """北向资金备选接口"""
        try:
            # 使用另一个东财接口获取北向资金
            url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
            params = {
                'sortColumns': 'TRADE_DATE',
                'sortTypes': '-1',
                'pageSize': '1',
                'pageNumber': '1',
                'reportName': 'RPT_MUTUAL_DEAL_HISTORY',
                'columns': 'ALL',
                'source': 'WEB',
                'client': 'WEB',
            }
            resp = self.session.get(url, params=params, timeout=TIMEOUT)
            data = resp.json()
            
            result = {
                'sh_inflow': 0,
                'sz_inflow': 0,
                'total_inflow': 0,
                'sh_cum_inflow': 0,
                'sz_cum_inflow': 0,
                'total_cum_inflow': 0
            }
            
            if data and 'result' in data and 'data' in data['result']:
                item = data['result']['data'][0]
                result['sh_inflow'] = float(item.get('NET_DEAL_AMT_SH', 0))
                result['sz_inflow'] = float(item.get('NET_DEAL_AMT_SZ', 0))
                result['total_inflow'] = result['sh_inflow'] + result['sz_inflow']
            
            return result
        except Exception as e:
            print(f"备选接口也失败: {e}")
            return {
                'sh_inflow': 0,
                'sz_inflow': 0,
                'total_inflow': 0,
                'sh_cum_inflow': 0,
                'sz_cum_inflow': 0,
                'total_cum_inflow': 0
            }
    
    def get_market_overview(self) -> Dict:
        """
        获取市场概况 - 涨跌家数统计
        """
        try:
            # 使用东方财富行情中心API
            url = "https://push2ex.eastmoney.com/getTopicZDFRank"
            params = {
                'ut': '7eea3edcaed734bea9cbfc24409ed989',
                'dpt': 'wz.ztzt',
                'Pageindex': '0',
                'pagesize': '1',
            }
            
            resp = self.session.get(url, params=params, timeout=TIMEOUT)
            data = resp.json()
            
            result = {
                'up_count': 0,
                'down_count': 0,
                'limit_up': 0,
                'limit_down': 0
            }
            
            if data and 'data' in data:
                result['up_count'] = data['data'].get('up', 0)
                result['down_count'] = data['data'].get('down', 0)
                result['limit_up'] = data['data'].get('ztt', 0)
                result['limit_down'] = data['data'].get('dtt', 0)
            
            return result
        except Exception as e:
            print(f"获取市场概况失败: {e}")
            return self._get_market_overview_simple()
    
    def _get_market_overview_simple(self) -> Dict:
        """简单的市场概况降级"""
        try:
            # 使用涨跌停统计接口
            url = "https://push2ex.eastmoney.com/getTodayZDF"
            params = {
                'ut': '7eea3edcaed734bea9cbfc24409ed989',
                'dpt': 'wz.ztzt',
            }
            resp = self.session.get(url, params=params, timeout=TIMEOUT)
            data = resp.json()
            
            result = {'up_count': 0, 'down_count': 0, 'limit_up': 0, 'limit_down': 0}
            
            if data and 'data' in data:
                # 统计涨跌家数
                for key in ['up', 'up5', 'down', 'down5']:
                    if key in data['data']:
                        count = len(data['data'][key]) if isinstance(data['data'][key], list) else 0
                        if 'up' in key:
                            result['up_count'] += count
                        else:
                            result['down_count'] += count
            
            return result
        except Exception as e:
            print(f"降级方案失败: {e}")
            return {'up_count': 0, 'down_count': 0, 'limit_up': 0, 'limit_down': 0}


# ============ 分析生成器 ============
class StockAnalyzer:
    """股票分析报告生成器"""
    
    def __init__(self, api: StockDataAPI):
        self.api = api
    
    def generate_morning_report(self) -> str:
        """生成早盘分析报告"""
        # 获取数据
        indices = self.api.get_index_quotes()
        gainers, losers = self.api.get_sector_ranking(5)
        northbound = self.api.get_northbound_flow()
        market = self.api.get_market_overview()
        
        now = datetime.now().strftime('%m月%d日')
        weekday = ['一', '二', '三', '四', '五', '六', '日'][datetime.now().weekday()]
        
        # 构建报告
        lines = [
            f"📊 【小股早盘提醒】{now} (周{weekday})",
            "━━━━━━━━━━━━━━━━━━━━━━",
            ""
        ]
        
        # 大盘行情
        lines.append("🏛️ **大盘指数**")
        if indices:
            for idx in indices[:4]:
                emoji = "🔴" if idx['change_pct'] > 0 else "🟢" if idx['change_pct'] < 0 else "⚪"
                lines.append(f"  {emoji} {idx['name']}: {idx['price']:.2f} {format_change(idx['change_pct'])}")
        else:
            lines.append("  📡 数据获取中...")
        lines.append("")
        
        # 市场情绪
        if market['up_count'] > 0 or market['down_count'] > 0:
            total = market['up_count'] + market['down_count']
            lines.append("📈 **市场情绪**")
            lines.append(f"  📊 涨跌分布: 🔴{market['up_count']} | 🟢{market['down_count']} (平{max(0, total-market['up_count']-market['down_count'])})")
            if market['limit_up'] > 0 or market['limit_down'] > 0:
                lines.append(f"  🚀 涨停: {market['limit_up']}家 | 📉 跌停: {market['limit_down']}家")
            lines.append("")
        
        # 热点板块
        lines.append("🔥 **领涨板块**")
        if gainers:
            for i, sector in enumerate(gainers[:5], 1):
                leader = f" [{sector['main_stock']}]" if sector['main_stock'] else ""
                lines.append(f"  {i}. {sector['name']}{leader} {format_change(sector['change_pct'])}")
        else:
            lines.append("  📡 数据获取中...")
        lines.append("")
        
        # 弱势板块
        if losers:
            lines.append("❄️ **领跌板块**")
            for i, sector in enumerate(losers[:3], 1):
                lines.append(f"  {i}. {sector['name']} {format_change(sector['change_pct'])}")
            lines.append("")
        
        # 北向资金
        lines.append("💰 **北向资金**")
        if northbound['total_inflow'] != 0:
            flow_emoji = "🟢流入" if northbound['total_inflow'] > 0 else "🔴流出"
            lines.append(f"  {flow_emoji}: {abs(northbound['total_inflow']):.2f}亿")
            lines.append(f"  📊 沪股通: {format_change(northbound['sh_inflow'])} | 深股通: {format_change(northbound['sz_inflow'])}")
        else:
            lines.append("  📡 数据获取中或今日暂无数据")
        lines.append("")
        
        # 小股简评
        trend = self._analyze_trend(indices, northbound, market)
        lines.append("💡 **小股简评**")
        lines.append(f"  {trend}")
        
        lines.append("")
        lines.append("━" * 24)
        lines.append("⚠️ 以上仅供参考，不构成投资建议")
        
        return '\n'.join(lines)
    
    def generate_noon_report(self) -> str:
        """生成午盘分析报告"""
        # 获取数据（与早盘相同，但分析角度不同）
        indices = self.api.get_index_quotes()
        gainers, losers = self.api.get_sector_ranking(5)
        northbound = self.api.get_northbound_flow()
        market = self.api.get_market_overview()
        
        now = datetime.now().strftime('%m月%d日')
        weekday = ['一', '二', '三', '四', '五', '六', '日'][datetime.now().weekday()]
        
        # 判断上午走势
        trend_direction = "震荡"
        if indices and len(indices) > 0:
            avg_change = sum(idx['change_pct'] for idx in indices[:3]) / 3
            if avg_change > 1:
                trend_direction = "强势上涨"
            elif avg_change > 0.5:
                trend_direction = "温和上涨"
            elif avg_change > 0:
                trend_direction = "小幅上涨"
            elif avg_change > -0.5:
                trend_direction = "小幅调整"
            elif avg_change > -1:
                trend_direction = "温和调整"
            else:
                trend_direction = "弱势调整"
        
        lines = [
            f"🌤️ 【小股午盘提醒】{now} (周{weekday})",
            "━━━━━━━━━━━━━━━━━━━━━━",
            ""
        ]
        
        # 上午回顾
        lines.append("📊 **上午盘回顾**")
        if indices:
            for idx in indices[:3]:
                emoji = "🔴" if idx['change_pct'] > 0 else "🟢" if idx['change_pct'] < 0 else "⚪"
                lines.append(f"  {emoji} {idx['name']}: {idx['price']:.2f} {format_change(idx['change_pct'])}")
        lines.append(f"  📌 整体走势: {trend_direction}")
        lines.append("")
        
        # 资金流向
        lines.append("💸 **资金流向**")
        if northbound['total_inflow'] != 0:
            flow_desc = "净流入" if northbound['total_inflow'] > 0 else "净流出"
            flow_emoji = "🟢" if northbound['total_inflow'] > 0 else "🔴"
            lines.append(f"  {flow_emoji} 北向资金{flow_desc} {abs(northbound['total_inflow']):.2f}亿")
            lines.append(f"  📊 沪股通: {northbound['sh_inflow']:.2f}亿 | 深股通: {northbound['sz_inflow']:.2f}亿")
        else:
            lines.append("  📡 北向资金数据获取中")
        
        if market['up_count'] > 0:
            lines.append(f"  📈 涨跌比: {market['up_count']}:{market['down_count']}")
        lines.append("")
        
        # 活跃板块
        lines.append("🔥 **上午活跃板块**")
        if gainers:
            for i, sector in enumerate(gainers[:5], 1):
                leader = f" [{sector['main_stock']}]" if sector['main_stock'] else ""
                lines.append(f"  {i}. {sector['name']}{leader} {format_change(sector['change_pct'])}")
        else:
            lines.append("  📡 数据获取中...")
        lines.append("")
        
        # 午后关注
        afternoon_focus = self._get_afternoon_focus(gainers, losers, northbound)
        lines.append("👀 **午后关注点**")
        for point in afternoon_focus:
            lines.append(f"  ▶ {point}")
        lines.append("")
        
        # 小股策略
        strategy = self._get_afternoon_strategy(trend_direction, northbound)
        lines.append("💡 **小股策略**")
        lines.append(f"  {strategy}")
        
        lines.append("")
        lines.append("━" * 24)
        lines.append("⚠️ 以上仅供参考，不构成投资建议")
        
        return '\n'.join(lines)
    
    def _analyze_trend(self, indices: List[Dict], northbound: Dict, market: Dict) -> str:
        """分析市场趋势，生成简评"""
        if not indices:
            return "数据获取中，开盘初期建议观望为主，等待市场方向明朗后再做决策。"
        
        avg_change = sum(idx['change_pct'] for idx in indices[:3]) / 3 if indices else 0
        northbound_flow = northbound.get('total_inflow', 0)
        up_count = market.get('up_count', 0)
        down_count = market.get('down_count', 0)
        
        # 构建分析
        if avg_change > 0.5:
            if northbound_flow > 15:
                return "市场情绪积极🔥，外资大幅加仓，可重点关注科技、新能源等成长赛道，但需注意追高风险。"
            elif northbound_flow > 0:
                return "大盘高开，外资温和流入，建议精选个股参与，控制仓位在7成左右。"
            else:
                return "内资主导上涨，外资观望，关注量能能否持续，避免追高，关注补涨机会。"
        elif avg_change > 0:
            if northbound_flow > 5:
                return "温和上涨，外资稳步流入，适合持仓观望或逢低布局业绩确定性强的标的。"
            else:
                return "窄幅震荡，热点轮动较快，建议关注低估值蓝筹和高股息策略防御配置。"
        elif avg_change > -0.5:
            if northbound_flow < -10:
                return "市场调整，外资净流出明显，建议减仓观望，等待企稳信号，关注避险资产。"
            else:
                return "小幅调整，逢低可关注低估值蓝筹和高股息策略，控制仓位在5成左右等待企稳。"
        else:
            return "市场回调，避险情绪升温，建议减仓至3成以内，多看少动，等待明确的企稳信号再介入。"
    
    def _get_afternoon_focus(self, gainers: List[Dict], losers: List[Dict], northbound: Dict) -> List[str]:
        """生成午后关注点"""
        focus = []
        
        # 根据北向资金流向
        northbound_flow = northbound.get('total_inflow', 0)
        if northbound_flow > 30:
            focus.append("北向资金大幅流入，关注外资偏好的消费白马和科技股")
        elif northbound_flow > 15:
            focus.append("北向资金持续流入，关注蓝筹股表现")
        elif northbound_flow < -20:
            focus.append("北向资金大幅流出，警惕外资重仓股回调风险")
        elif northbound_flow < -10:
            focus.append("北向资金净流出，关注是否有企稳迹象")
        
        # 根据板块表现
        if gainers and gainers[0]['change_pct'] > 3:
            focus.append(f"{gainers[0]['name']}领涨{format_change(gainers[0]['change_pct'])}，关注热点持续性")
        
        # 一般性建议
        focus.append("成交量变化，放量上攻则持股，缩量调整需谨慎")
        
        return focus[:3]
    
    def _get_afternoon_strategy(self, trend: str, northbound: Dict) -> str:
        """生成午后策略"""
        northbound_flow = northbound.get('total_inflow', 0)
        
        if trend == "强势上涨":
            if northbound_flow > 15:
                return "市场强势，外资看好，可持股待涨，但不宜追涨涨幅过大的个股，关注补涨机会。"
            else:
                return "内资推动上涨，午后关注量能配合，若缩量建议适当减仓锁定利润。"
        elif trend in ["温和上涨", "小幅上涨"]:
            return "震荡向上，适合高抛低吸，关注轮动补涨的机会，仓位控制在6-7成。"
        elif trend in ["小幅调整", "温和调整"]:
            return "调整中寻找机会，逢低布局优质标的，控制仓位五成左右，等待企稳信号。"
        else:
            return "弱势调整，以防守为主，多看少动，减仓至3成以内，等待明确的企稳信号再介入。"


# ============ 发送功能 ============
def send_to_feishu(message: str) -> bool:
    """发送消息到Feishu群"""
    try:
        import subprocess
        result = subprocess.run(
            ['openclaw', 'message', 'send', '--channel', 'feishu', 
             '--target', FEISHU_GROUP_ID, '--message', message],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print("消息发送成功")
            return True
        else:
            print(f"发送失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"发送异常: {e}")
        return False


# ============ 主程序 ============
def main():
    """主程序入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='小股股票分析提醒脚本')
    parser.add_argument('--type', choices=['morning', 'noon'], required=True,
                       help='报告类型: morning=早盘, noon=午盘')
    parser.add_argument('--dry-run', action='store_true',
                       help='仅生成报告，不发送')
    
    args = parser.parse_args()
    
    print(f"🚀 小股启动 - 生成{'早盘' if args.type == 'morning' else '午盘'}报告...")
    print(f"⏰ 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 50)
    
    # 初始化API
    api = StockDataAPI()
    analyzer = StockAnalyzer(api)
    
    # 生成报告
    if args.type == 'morning':
        report = analyzer.generate_morning_report()
    else:
        report = analyzer.generate_noon_report()
    
    print("\n生成的报告:")
    print("=" * 50)
    print(report)
    print("=" * 50)
    
    # 发送报告
    if not args.dry_run:
        print("\n📤 正在发送到Feishu群...")
        if send_to_feishu(report):
            print("✅ 任务完成")
        else:
            print("❌ 发送失败")
            sys.exit(1)
    else:
        print("\n📝 试运行模式，不发送消息")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
