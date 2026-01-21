#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import requests
import logging
import json
from datetime import datetime, timezone, timedelta
import os

logger = logging.getLogger(__name__)

CCTV_CHANNELS = {
    'cctv1': 'CCTV-1 综合',
    'cctv2': 'CCTV-2 财经',
    'cctv3': 'CCTV-3 综艺',
    'cctv4': 'CCTV-4 中文国际',
    'cctveurope': 'CCTV-4 欧洲',
    'cctvamerica': 'CCTV-4 美洲',
    'cctv5': 'CCTV-5 体育',
    'cctv5plus': 'CCTV-5+ 体育赛事',
    'cctv6': 'CCTV-6 电影',
    'cctv7': 'CCTV-7 国防军事',
    'cctv8': 'CCTV-8 电视剧',
    'cctvjilu': 'CCTV-9 纪录',
    'cctv10': 'CCTV-10 科教',
    'cctv11': 'CCTV-11 戏曲',
    'cctv12': 'CCTV-12 社会与法',
    'cctv13': 'CCTV-13 新闻',
    'cctvchild': 'CCTV-14 少儿',
    'cctv15': 'CCTV-15 音乐',
    'cctv16': 'CCTV-16 奥林匹克',
    'cctv17': 'CCTV-17 农业农村'
}

def validate_date(date_str):
    try:
        datetime.strptime(date_str, '%Y%m%d')
        return True
    except ValueError:
        return False

def get_cctv_epg(channel_id, date_str):
    api_url = os.environ.get('CCTV_API_URL')
    if not api_url:
        logger.error("未找到入口CCTV_API_URL")
        return None

    api_url = api_url.format(channel_id=channel_id, date_str=date_str)
    
    try:
        response = requests.get(api_url, timeout=15)
        response.raise_for_status()
        
        jsonp_text = response.text
        json_text = jsonp_text[jsonp_text.index('(') + 1:jsonp_text.rindex(')')]
        data = json.loads(json_text)
        
        if 'errcode' in data:
            logger.warning(f"CCTV API返回错误码: {data['errcode']}, 错误信息: {data.get('msg', '无')}")
            return None
        
        if 'data' not in data:
            logger.warning(f"CCTV API返回的数据中没有包含data字段: {data}")
            return None
        
        return data
    except Exception as e:
        logger.error(f"获取CCTV节目单失败: {e}")
        return None

def generate_xmltv(programs_dict, target_date, timezone):
    generator_url = os.environ.get('CCTV_GENERATOR_URL', '')
    xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<tv generator-info-name="CCTV API EPG Generator" generator-info-url="{generator_url}">
'''    
    total_programs = 0
    
    for channel_id, programs in programs_dict.items():
        channel_name = CCTV_CHANNELS.get(channel_id, channel_id)
        channel_xml_id = channel_name.replace(' ', '_').replace('-', '_')
        
        xml_content += f'''
  <channel id="{channel_xml_id}">
    <display-name>{channel_name}</display-name>
  </channel>
'''
        
        channel_program_count = 0
        for program in programs:
            try:
                start_time = datetime.fromtimestamp(program['startTime'], timezone)
                end_time = datetime.fromtimestamp(program['endTime'], timezone)
                
                start_str = start_time.strftime('%Y%m%d%H%M%S')
                end_str = end_time.strftime('%Y%m%d%H%M%S')
                
                title = program['title']
                
                xml_content += f'''
  <programme channel="{channel_xml_id}" start="{start_str} +0800" stop="{end_str} +0800">
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
