#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CCTV API节目单抓取模块
提供与test_cctv.py兼容的函数接口
"""

import requests
import logging
import json
from datetime import datetime, timezone, timedelta

# 配置日志
logger = logging.getLogger(__name__)

# 频道名称映射
CCTV_CHANNELS = {
    'cctv1': 'CCTV-1 综合',
    'cctv2': 'CCTV-2 财经',
    'cctv3': 'CCTV-3 综艺',
    'cctv4': 'CCTV-4 中文国际',
    'cctv5': 'CCTV-5 体育',
    'cctv5plus': 'CCTV-5+ 体育赛事',
    'cctv6': 'CCTV-6 电影',
    'cctv7': 'CCTV-7 国防军事',
    'cctv8': 'CCTV-8 电视剧',
    'cctv9': 'CCTV-9 纪录',
    'cctv10': 'CCTV-10 科教',
    'cctv11': 'CCTV-11 戏曲',
    'cctv12': 'CCTV-12 社会与法',
    'cctv13': 'CCTV-13 新闻',
    'cctv14': 'CCTV-14 少儿',
    'cctv15': 'CCTV-15 音乐',
    'cctv16': 'CCTV-16 奥林匹克',
    'cctv17': 'CCTV-17 农业农村'
}

def validate_date(date_str):
    """
    验证日期格式是否为YYYYMMDD
    
    Args:
        date_str: 要验证的日期字符串
        
    Returns:
        bool: 如果格式正确返回True，否则返回False
    """
    try:
        datetime.strptime(date_str, '%Y%m%d')
        return True
    except ValueError:
        return False

def get_cctv_epg(channel_id, date_str):
    """
    通过CCTV API获取节目单数据
    
    Args:
        channel_id: 频道ID，如'cctv1'
        date_str: 日期字符串，格式为YYYYMMDD
        
    Returns:
        dict: 包含节目单数据的字典，如果获取失败或返回错误码返回None
    """
    # API URL模板
    api_url = f"https://api.cntv.cn/epg/getEpgInfoByChannelNew?c={channel_id}&serviceId=tvcctv&d={date_str}&t=jsonp&cb=callback"
    
    try:
        logger.info(f"请求CCTV API: {api_url}")
        response = requests.get(api_url, timeout=15)
        response.raise_for_status()
        
        # 解析JSONP响应
        jsonp_text = response.text
        json_text = jsonp_text[jsonp_text.index('(') + 1:jsonp_text.rindex(')')]
        data = json.loads(json_text)
        
        logger.info(f"获取{channel_id}的节目单数据成功，返回数据结构: {list(data.keys())}")
        
        # 检查是否返回了错误码
        if 'errcode' in data:
            logger.warning(f"CCTV API返回错误码: {data['errcode']}, 错误信息: {data.get('msg', '无')}")
            return None
        
        # 检查是否包含data字段
        if 'data' not in data:
            logger.warning(f"CCTV API返回的数据中没有包含data字段: {data}")
            return None
        
        return data
    except Exception as e:
        logger.error(f"获取CCTV节目单失败: {e}")
        return None

def generate_xmltv(programs_dict, target_date, timezone):
    """
    生成XMLTV格式的EPG文件
    
    Args:
        programs_dict: 节目单字典，格式为{channel_id: [program1, program2, ...]}
        target_date: 目标日期，格式为YYYYMMDD
        timezone: 时区对象
        
    Returns:
        str: XMLTV格式的字符串
    """
    # 创建XML内容
    xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<tv generator-info-name="CCTV API EPG Generator" generator-info-url="https://tv.cctv.com/">
'''
    
    # 统计节目数量
    total_programs = 0
    
    for channel_id, programs in programs_dict.items():
        channel_name = CCTV_CHANNELS.get(channel_id, channel_id)
        channel_xml_id = channel_name.replace(' ', '_').replace('-', '_')
        
        # 添加频道信息
        xml_content += f'''  <channel id="{channel_xml_id}">
    <display-name>{channel_name}</display-name>
  </channel>
'''
        
        # 添加节目信息
        channel_program_count = 0
        for program in programs:
            try:
                # 解析开始和结束时间，并添加时区信息
                start_time = datetime.fromtimestamp(program['startTime'], timezone)
                end_time = datetime.fromtimestamp(program['endTime'], timezone)
                
                # 格式化时间为XMLTV格式
                start_str = start_time.strftime('%Y%m%d%H%M%S')
                end_str = end_time.strftime('%Y%m%d%H%M%S')
                
                title = program['title']
                
                # 添加节目
                xml_content += f'''  <programme channel="{channel_xml_id}" start="{start_str} +0800" stop="{end_str} +0800">
    <title lang="zh">{title}</title>
  </programme>
'''
                channel_program_count += 1
                total_programs += 1
            except Exception as e:
                logger.warning(f"解析节目失败: {e}")
                continue
        
        logger.info(f"为频道 {channel_name} 生成了 {channel_program_count} 个节目")
    
    logger.info(f"共生成了 {total_programs} 个节目")
    xml_content += '''</tv>
'''
    
    return xml_content
