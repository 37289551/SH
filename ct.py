import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime, timedelta, timezone
import os
import time
import re
import json
import argparse

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

def get_cctv_epg(channel_id, date_str):
    api_url = os.environ.get('CCTV_API_URL')
    if not api_url:
        logger.error("未设置CCTV_API_URL")
        return None

    api_url = api_url.format(channel_id=channel_id, date_str=date_str)
    
    try:
        response = requests.get(api_url, timeout=15)
        response.raise_for_status()
        
        jsonp_text = response.text
        json_text = jsonp_text[jsonp_text.index('(') + 1:jsonp_text.rindex(')')]
        data = json.loads(json_text)
        
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

def validate_date(date_str):
    try:
        datetime.strptime(date_str, '%Y%m%d')
        return True
    except ValueError:
        return False

def main():
    logger.info("开始从CCTV API提取节目单...")

    parser = argparse.ArgumentParser(description='获取CCTV节目单并生成XMLTV格式')
    parser.add_argument('--date', type=str, help='指定日期，格式为YYYYMMDD，如20260120')
    args = parser.parse_args()
    
    beijing_tz = timezone(timedelta(hours=8))

    now_beijing = datetime.now(beijing_tz)

    if args.date:
        if validate_date(args.date):
            target_date = args.date
            logger.info(f"使用指定日期: {target_date}")
        else:
            logger.error(f"日期格式错误: {args.date}，应为YYYYMMDD格式")
            return
    else:
        target_date = now_beijing.strftime('%Y%m%d')
        logger.info(f"使用当前日期: {target_date}")
    
    programs_dict = {}

    for channel_id, channel_name in CCTV_CHANNELS.items():
        epg_data = get_cctv_epg(channel_id, target_date)
        
        if epg_data and 'data' in epg_data:
            for key, channel_data in epg_data['data'].items():
                if 'list' in channel_data:
                    programs_dict[channel_id] = channel_data['list']
                    break

        time.sleep(1)
    
    logger.info(f"共获取到 {len(programs_dict)} 个频道的节目单")
    
    if programs_dict:
        xmltv_content = generate_xmltv(programs_dict, target_date, beijing_tz)

        output_dir = 'output'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        output_file = os.path.join(output_dir, f'cctv_epg_{target_date}.xml')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(xmltv_content)
        
        logger.info(f"CCTV节目单已保存到 {output_file}")
    else:
        logger.warning("未提取到任何CCTV节目单")

from capi import get_cctv_epg as api_get_cctv_epg
from capi import CCTV_CHANNELS as API_CCTV_CHANNELS

def fetch_cctv_programs():
    from datetime import timezone, timedelta

    beijing_tz = timezone(timedelta(hours=8))

    target_date = datetime.now(beijing_tz).strftime('%Y%m%d')
    
    programs_dict = {}
    success_count = 0
    fail_count = 0

    for channel_id, channel_name in API_CCTV_CHANNELS.items():
        epg_data = api_get_cctv_epg(channel_id, target_date)
        
        if epg_data and 'data' in epg_data:
            for key, channel_data in epg_data['data'].items():
                if 'list' in channel_data:
                    formatted_programs = []
                    for program in channel_data['list']:
                        start_time = datetime.fromtimestamp(program['startTime'], beijing_tz).strftime('%H:%M')
                        formatted_programs.append({
                            'time': start_time,
                            'title': program['title']
                        })

                    programs_dict[channel_name] = formatted_programs
                    success_count += 1
                    logger.info(f"成功获取到{channel_name}的节目单，共{len(formatted_programs)}个节目")
                    break
        else:
            fail_count += 1
            logger.warning(f"未能获取到{channel_name}的节目单")

        time.sleep(0.5)
    
    logger.info(f"完成，成功获取到 {success_count} 个频道的节目单，{fail_count} 个频道失败")
    return programs_dict

if __name__ == "__main__":
    main()