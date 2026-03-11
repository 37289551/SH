#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电视猫新版卫视频道EPG爬虫
基于新的URL格式：https://www.tvmao.com/program_satellite/{频道代号}-w{星期几}.html
"""

import requests
from bs4 import BeautifulSoup
import logging
import re
from datetime import datetime, timedelta, timezone
import time
import os
from channel_mapping import normalize_channel_name

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

file_handler = logging.FileHandler('tm2_epg.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# 常见卫视频道代号映射
CHANNEL_CODES = {
    # 央视频道
    'CCTV1': 'CCTV1',
    'CCTV2': 'CCTV2',
    'CCTV3': 'CCTV3',
    'CCTV4': 'CCTV4',
    'CCTV5': 'CCTV5',
    'CCTV5+': 'CCTV5P',
    'CCTV6': 'CCTV6',
    'CCTV7': 'CCTV7',
    'CCTV8': 'CCTV8',
    'CCTV9': 'CCTV9',
    'CCTV10': 'CCTV10',
    'CCTV11': 'CCTV11',
    'CCTV12': 'CCTV12',
    'CCTV13': 'CCTV13',
    'CCTV14': 'CCTV14',
    'CCTV15': 'CCTV15',
    'CCTV16': 'CCTV16',
    'CCTV17': 'CCTV17',
    
    # 省级卫视（按拼音排序）
    '安徽卫视': 'AHTV1',
    '北京卫视': 'BTV1',
    '兵团卫视': 'BTVWS',
    '重庆卫视': 'CQTV',
    '东南卫视': 'FJTV1',
    '甘肃卫视': 'GSTV',
    '广东卫视': 'GDTV',
    '广西卫视': 'GXTV',
    '贵州卫视': 'GZTV',
    '海南卫视': 'HNTV2',
    '河北卫视': 'HEBTV1',
    '黑龙江卫视': 'HLJTV',
    '湖北卫视': 'HUBEITV',
    '湖南卫视': 'HUNANTV',
    '吉林卫视': 'JLTV1',
    '江苏卫视': 'JSTV',
    '江西卫视': 'JXTV1',
    '辽宁卫视': 'LNTV',
    '内蒙古卫视': 'NMGTV',
    '宁夏卫视': 'NXTV',
    '青海卫视': 'QHTV',
    '山东卫视': 'SDTV',
    '山西卫视': 'SXRTV1',
    '陕西卫视': 'SXTV',
    '上海卫视': 'STV',
    '深圳卫视': 'SZTVHD',
    '四川卫视': 'SCTV1',
    '天津卫视': 'TJTV1',
    '西藏卫视': 'XZTV',
    '新疆卫视': 'XJTV',
    '云南卫视': 'YNTV1',
    '浙江卫视': 'ZJTV',
}

def make_request(url, session=None, headers=None, retry=3, delay=2):
    """发送HTTP请求"""
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.tvmao.com/'
        }
    
    request_func = session.get if session else requests.get
    
    for attempt in range(retry):
        try:
            response = request_func(url, headers=headers, timeout=15)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            if attempt < retry - 1:
                logger.info(f"等待 {delay} 秒后重试... ({attempt + 1}/{retry})")
                time.sleep(delay)
            else:
                logger.error(f"所有重试均失败: {url}, 错误: {e}")
                return None

def get_current_weekday():
    """获取当前星期几（北京时间UTC+8）"""
    return datetime.now(timezone(timedelta(hours=8))).weekday() + 1  # 1-7

def generate_url(channel_code, weekday=None):
    """
    生成电视猫新版卫视频道URL
    
    Args:
        channel_code: 频道代号，如 'AHTV1', 'BTV1'
        weekday: 星期几，默认为当前星期
    
    Returns:
        完整的URL字符串
    """
    if weekday is None:
        weekday = get_current_weekday()
    
    # 新版URL格式
    url = f"https://www.tvmao.com/program_satellite/{channel_code}-w{weekday}.html"
    return url

def parse_channel_name(soup):
    """从页面提取频道名称"""
    # 方法1: 从h1标签提取（最可靠）
    h1_tag = soup.find('h1')
    if h1_tag:
        h1_text = h1_tag.get_text().strip()
        # 格式: "安徽卫视节目表"
        logger.debug(f"H1标签内容: {h1_text}")
        
        # 提取"xxx卫视"或"xxx频道"
        match = re.search(r'([^，,_，节目表预告\s]+)(卫视|频道)', h1_text)
        if match:
            channel_name = match.group(0)
            logger.info(f"从H1提取频道名称: {channel_name}")
            return channel_name
    
    # 方法2: 从title标签提取
    title_tag = soup.find('title')
    if title_tag:
        title_text = title_tag.get_text()
        # 格式: "安徽卫视节目表,安徽卫视节目预告_电视猫"
        logger.debug(f"title标签内容: {title_text}")
        match = re.search(r'([^，,_，节目表预告\s]+)(卫视|频道)', title_text)
        if match:
            channel_name = match.group(0)
            logger.info(f"从title提取频道名称: {channel_name}")
            return channel_name
    
    # 方法3: 从面包屑导航提取
    breadcrumb = soup.find('div', class_='breadcrumb')
    if breadcrumb:
        links = breadcrumb.find_all('a')
        for link in links:
            text = link.get_text().strip()
            logger.debug(f"面包屑链接: {text}")
            if '卫视' in text or '频道' in text:
                logger.info(f"从面包屑提取频道名称: {text}")
                return text
    
    # 方法4: 查找页面中的所有文本，尝试匹配
    all_text = soup.get_text()
    # 尝试匹配第一个出现的 "xxx卫视" 或 "xxx频道"
    patterns = [r'([^\s，,_]+卫视)', r'([^\s，,_]+频道)']
    for pattern in patterns:
        match = re.search(pattern, all_text)
        if match:
            channel_name = match.group(0)
            # 排除一些非频道名称的匹配
            if not any(x in channel_name for x in ['节目表', '节目预告', '电视猫', '卫视网']):
                logger.info(f"从页面文本提取频道名称: {channel_name}")
                return channel_name
    
    logger.warning("所有方法都无法提取频道名称")
    # 调试输出页面结构
    if h1_tag:
        logger.warning(f"H1: {h1_tag}")
    if title_tag:
        logger.warning(f"title: {title_tag}")
    
    return None

def parse_program_items(soup):
    """
    解析节目单数据
    
    Returns:
        列表，每个元素为包含时间、节目名称、集数的字典
    """
    programs = []
    
    # 查找所有包含节目的li元素
    # 根据网页结构，节目通常在class包含"program"或"item"的容器中
    li_elements = soup.find_all('li')
    
    logger.debug(f"找到 {len(li_elements)} 个 <li> 元素")
    
    for i, li in enumerate(li_elements):
        text = li.get_text().strip()
        if not text:
            continue
        
        # 跳过明显不是节目的内容
        if len(text) < 5:
            continue
        
        # 跳过时间段分组标题（如"凌晨节目"、"午间节目"、"晚间节目"等）
        if any(x in text for x in ['节目', '播出', '时段', '节目表']):
            continue
        
        # 使用正则表达式匹配节目信息
        # 格式: "HH:MM 节目名称(集数)" 或 "HH:MM 节目名称"
        pattern = r'^(\d{2}:\d{2})\s+(.+?)(?:\((\d+)\))?$'
        match = re.match(pattern, text)
        
        if match:
            time_str = match.group(1)
            title = match.group(2).strip()
            episode = match.group(3) if match.group(3) else None
            
            # 清理标题中的多余内容
            title = re.sub(r'\s+', ' ', title)
            title = re.sub(r'^正在播出\s+', '', title)
            
            programs.append({
                'time': time_str,
                'title': title,
                'episode': episode
            })
            
            logger.debug(f"解析到节目 {i+1}: {time_str} - {title}")
    
    logger.info(f"共解析到 {len(programs)} 个节目")
    return programs

def fetch_channel_epg(channel_code, weekday=None):
    """
    获取指定频道的EPG数据
    
    Args:
        channel_code: 频道代号
        weekday: 星期几，默认为当前星期
    
    Returns:
        字典，包含频道名称和节目列表
    """
    url = generate_url(channel_code, weekday)
    logger.info(f"正在获取: {url}")
    
    response = make_request(url)
    if not response:
        logger.warning(f"获取失败: {channel_code}")
        return None
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 提取频道名称
    channel_name = parse_channel_name(soup)
    if not channel_name:
        logger.warning(f"无法提取频道名称: {channel_code}")
        return None
    
    # 提取节目列表
    programs = parse_program_items(soup)
    
    if programs:
        logger.info(f"成功获取 {channel_name} 的 {len(programs)} 个节目")
    else:
        logger.warning(f"未找到节目数据: {channel_name}")
    
    return {
        'channel': channel_name,
        'code': channel_code,
        'weekday': weekday if weekday else get_current_weekday(),
        'programs': programs
    }

def fetch_all_satellite_epg(weekday=None, channel_list=None):
    """
    获取所有卫视频道的EPG数据
    
    Args:
        weekday: 星期几，默认为当前星期
        channel_list: 指定频道列表，如果为None则获取所有频道
    
    Returns:
        字典，键为频道名称，值为节目列表
    """
    programs_dict = {}
    
    if channel_list is None:
        channel_list = CHANNEL_CODES
    
    total_channels = len(channel_list)
    logger.info(f"开始获取 {total_channels} 个卫视频道的EPG数据")
    
    success_count = 0
    for channel_name, channel_code in channel_list.items():
        epg_data = fetch_channel_epg(channel_code, weekday)
        
        if epg_data and epg_data['programs']:
            programs_dict[epg_data['channel']] = epg_data['programs']
            success_count += 1
        
        # 避免请求过快
        time.sleep(0.5)
    
    logger.info(f"完成！成功获取 {success_count}/{total_channels} 个频道的EPG数据")
    return programs_dict

def generate_xmltv(programs_dict):
    """生成XMLTV格式数据"""
    today = datetime.now().strftime('%Y%m%d')
    generator_url = os.environ.get('TM_GENERATOR_URL', '')
    
    xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<tv generator-info-name="TMEPG2 Generator" generator-info-url="{generator_url}">
'''
    
    total_programs = 0
    
    for channel_name, programs in programs_dict.items():
        channel_id = channel_name.replace(' ', '_').replace('-', '_').replace(':', '_')
        
        xml_content += f'''
  <channel id="{channel_id}">
    <display-name>{channel_name}</display-name>
  </channel>
'''
        
        channel_program_count = 0
        for program in programs:
            time_str = program['time']
            title = program['title']
            
            start_time = f"{today}{time_str.replace(':', '')}00"
            
            try:
                # 计算结束时间
                hour, minute = map(int, time_str.split(':'))
                end_time = datetime.combine(datetime.now().date(), datetime.min.time()) + \
                          timedelta(hours=hour, minutes=minute+30)
                end_time_str = end_time.strftime(f"{today}%H%M00")
                
                xml_content += f'''
  <programme channel="{channel_id}" start="{start_time}" stop="{end_time_str}">
    <title lang="zh">{title}</title>
  </programme>
'''
                channel_program_count += 1
                total_programs += 1
            except Exception as e:
                logger.warning(f"解析节目时间失败，跳过节目: {title}, 时间: {time_str}, 错误: {e}")
                continue
        
        logger.info(f"为频道 {channel_name} 生成了 {channel_program_count} 个节目元素")
    
    logger.info(f"共生成了 {total_programs} 个节目元素")
    xml_content += '''
</tv>
'''
    
    return xml_content

def debug_page(channel_code, weekday=None):
    """
    调试模式：详细分析页面结构
    
    Args:
        channel_code: 频道代号
        weekday: 星期几，默认为当前星期
    """
    url = generate_url(channel_code, weekday)
    print(f"\n{'='*60}")
    print(f"调试模式: {url}")
    print(f"{'='*60}")
    
    response = make_request(url)
    if not response:
        print(f"❌ 页面请求失败")
        return
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 输出页面基本信息
    print(f"\n📄 页面基本信息:")
    print(f"  URL: {url}")
    print(f"  状态码: {response.status_code}")
    print(f"  页面大小: {len(response.text)} 字节")
    
    # 输出title
    title_tag = soup.find('title')
    if title_tag:
        print(f"\n🏷️  Title标签: {title_tag.get_text()}")
    
    # 输出h1
    h1_tags = soup.find_all('h1')
    print(f"\n📌 H1标签 (共{len(h1_tags)}个):")
    for i, h1 in enumerate(h1_tags, 1):
        print(f"  {i}. {h1.get_text().strip()}")
    
    # 输出面包屑
    breadcrumb = soup.find('div', class_='breadcrumb')
    if breadcrumb:
        print(f"\n🧭 面包屑导航:")
        links = breadcrumb.find_all('a')
        for link in links:
            print(f"  - {link.get_text().strip()}: {link.get('href', '')}")
    
    # 提取频道名称
    channel_name = parse_channel_name(soup)
    print(f"\n✅ 提取的频道名称: {channel_name}")
    
    # 输出所有li元素（前10个）
    li_elements = soup.find_all('li')
    print(f"\n📋 LI元素 (共{len(li_elements)}个，显示前10个):")
    for i, li in enumerate(li_elements[:10], 1):
        text = li.get_text().strip()
        if text:
            print(f"  {i}. {text[:100]}")
    
    # 输出包含时间的li
    print(f"\n⏰ 包含时间的节目 (前5个):")
    time_pattern = re.compile(r'^\d{2}:\d{2}')
    count = 0
    for li in li_elements:
        text = li.get_text().strip()
        if time_pattern.match(text) and count < 5:
            print(f"  {count+1}. {text}")
            count += 1

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("电视猫新版卫视频道EPG爬虫启动")
    logger.info("=" * 60)
    
    # 获取EPG数据
    programs_dict = fetch_all_satellite_epg()
    
    if not programs_dict:
        logger.error("未获取到任何EPG数据")
        return
    
    # 打印统计信息
    print("\n" + "=" * 60)
    print("EPG数据统计")
    print("=" * 60)
    print(f"频道数量: {len(programs_dict)}")
    print(f"总节目数: {sum(len(programs) for programs in programs_dict.values())}")
    print("\n频道列表:")
    for channel_name in sorted(programs_dict.keys()):
        print(f"  - {channel_name}: {len(programs_dict[channel_name])} 个节目")
    
    # 生成XMLTV文件
    print("\n" + "=" * 60)
    print("生成XMLTV文件")
    print("=" * 60)
    
    xmltv_content = generate_xmltv(programs_dict)
    
    output_dir = 'output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    today = datetime.now().strftime('%Y%m%d')
    output_file = os.path.join(output_dir, f'tvmao2_satellite_{today}.xml')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(xmltv_content)
    
    print(f"文件已保存: {output_file}")
    print(f"文件大小: {os.path.getsize(output_file) / 1024:.2f} KB")
    
    logger.info("=" * 60)
    logger.info("爬虫执行完成")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
