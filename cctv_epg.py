import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime, timedelta
import os
import time
import re
import json
import argparse
import pytz

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
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

def get_cctv_epg(channel_id, date_str):
    """通过CCTV API获取节目单数据"""
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
        
        logger.info(f"成功获取{channel_id}的节目单数据")
        return data
    except Exception as e:
        logger.error(f"获取CCTV节目单失败: {e}")
        return None

def generate_xmltv(programs_dict, target_date, timezone):
    """生成XMLTV格式的EPG文件"""
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

def validate_date(date_str):
    """验证日期格式是否为YYYYMMDD"""
    try:
        datetime.strptime(date_str, '%Y%m%d')
        return True
    except ValueError:
        return False

def main():
    """主函数"""
    logger.info("开始从CCTV API提取节目单...")
    
    # 创建参数解析器
    parser = argparse.ArgumentParser(description='获取CCTV节目单并生成XMLTV格式')
    parser.add_argument('--date', type=str, help='指定日期，格式为YYYYMMDD，如20260120')
    args = parser.parse_args()
    
    # 设置北京时区 (UTC+8)
    beijing_tz = pytz.timezone('Asia/Shanghai')
    
    # 获取当前北京时间
    now_beijing = datetime.now(beijing_tz)
    
    # 处理日期参数
    if args.date:
        if validate_date(args.date):
            target_date = args.date
            logger.info(f"使用指定日期: {target_date}")
        else:
            logger.error(f"日期格式错误: {args.date}，应为YYYYMMDD格式")
            return
    else:
        # 使用当前北京日期，格式为YYYYMMDD
        target_date = now_beijing.strftime('%Y%m%d')
        logger.info(f"使用当前日期: {target_date}")
    
    programs_dict = {}
    
    # 遍历所有CCTV频道
    for channel_id, channel_name in CCTV_CHANNELS.items():
        logger.info(f"获取{channel_name}的节目单...")
        epg_data = get_cctv_epg(channel_id, target_date)
        
        if epg_data and 'data' in epg_data:
            # 提取节目列表
            for key, channel_data in epg_data['data'].items():
                if 'list' in channel_data:
                    programs_dict[channel_id] = channel_data['list']
                    break
        
        # 添加适当延迟，避免请求过快
        time.sleep(1)
    
    logger.info(f"共获取到 {len(programs_dict)} 个频道的节目单")
    
    if programs_dict:
        # 生成XMLTV文件
        xmltv_content = generate_xmltv(programs_dict, target_date, beijing_tz)
        
        # 保存到文件
        output_dir = 'output'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        output_file = os.path.join(output_dir, f'cctv_epg_{target_date}.xml')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(xmltv_content)
        
        logger.info(f"CCTV节目单已保存到 {output_file}")
    else:
        logger.warning("未提取到任何CCTV节目单")

if __name__ == "__main__":
    main()
