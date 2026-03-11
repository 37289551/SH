#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import requests
from bs4 import BeautifulSoup
import logging
import re
from datetime import datetime, timedelta, timezone
import time
import os
import random
from channel_mapping import normalize_channel_name

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

file_handler = logging.FileHandler('tmdf_epg.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# 地方台省份代码映射
PROVINCE_CODES = {
    '天津': {'code': 'TJTV', 'provId': '120000'},
    '江苏': {'code': 'JSTV', 'provId': '320000'},
    '江西': {'code': 'JXTV', 'provId': '360000'},
    '广东': {'code': 'GDTV', 'provId': '440000'},
    '贵州': {'code': 'GUIZOUTV', 'provId': '520000'},
    '宁夏': {'code': 'NXTV', 'provId': '640000'},
    '河北': {'code': 'HEBEI', 'provId': '130000'},
    '辽宁': {'code': 'LNTV', 'provId': '210000'},
    '浙江': {'code': 'ZJTV', 'provId': '330000'},
    '山东': {'code': 'SDTV', 'provId': '370000'},
    '河南': {'code': 'HNTV', 'provId': '410000'},
    '广西': {'code': 'GUANXI', 'provId': '450000'},
    '云南': {'code': 'YNTV', 'provId': '530000'},
    '陕西': {'code': 'SHXITV', 'provId': '610000'},
    '新疆': {'code': 'XJTV', 'provId': '650000'},
    '山西': {'code': 'SXTV', 'provId': '140000'},
    '吉林': {'code': 'JILIN', 'provId': '220000'},
    '安徽': {'code': 'AHTV', 'provId': '340000'},
    '湖北': {'code': 'HUBEI', 'provId': '420000'},
    '海南': {'code': 'TCTC', 'provId': '460000'},
    '重庆': {'code': 'CCQTV', 'provId': '500000'},
    '西藏': {'code': 'XIZANGTV', 'provId': '540000'},
    '甘肃': {'code': 'GSTV', 'provId': '620000'},
    '北京': {'code': 'BTV', 'provId': '110000'},
    '内蒙': {'code': 'NMGTV', 'provId': '150000'},
    '黑龙': {'code': 'HLJTV', 'provId': '230000'},
    '上海': {'code': 'DFMV', 'provId': '310000'},
    '福建': {'code': 'FJTV', 'provId': '350000'},
    '湖南': {'code': 'HUNANTV', 'provId': '430000'},
    '四川': {'code': 'SCTV', 'provId': '510000'},
    '青海': {'code': 'QHTV', 'provId': '630000'},
}

def make_request(url, session=None, headers=None, retry=3, delay=2):
    """发送HTTP请求"""
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.tvmao.com/',
            'DNT': '1',
            'Sec-Fetch-User': '?1',
            'TE': 'trailers'
        }
    
    request_func = session.get if session else requests.get
    
    for attempt in range(retry):
        try:
            # 随机延迟，避免请求过于规律
            if attempt > 0:
                time.sleep(delay * (attempt + 1) + random.uniform(0.5, 1.5))
            
            response = request_func(url, headers=headers, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            # 检查响应体是否过小
            if len(response.text) < 500:
                logger.warning(f"响应体过小 ({len(response.text)} 字节), 可能被拦截: {url}")
                if attempt < retry - 1:
                    wait_time = delay * (attempt + 1)
                    logger.info(f"等待 {wait_time} 秒后重试... ({attempt + 1}/{retry})")
                    continue
                else:
                    logger.error(f"所有重试均失败: {url}")
                    return None
            
            return response
        except requests.RequestException as e:
            if attempt < retry - 1:
                wait_time = delay * (attempt + 1)
                logger.info(f"等待 {wait_time} 秒后重试... ({attempt + 1}/{retry}), 错误: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"所有重试均失败: {url}, 错误: {e}")
                return None

def get_current_weekday():
    """获取当前星期几（北京时间UTC+8）"""
    return datetime.now(timezone(timedelta(hours=8))).weekday() + 1  # 1-7

def generate_url_with_weekday(province_code, weekday=None):
    """
    生成地方台频道URL

    Args:
        province_code: 省份代码，如 'BTV', 'AHTV'
        weekday: 星期几（1-7），默认为当前星期

    Returns:
        完整的URL字符串
    """
    # 直接使用省份代码，不需要星期几参数
    url = f"https://www.tvmao.com/program/{province_code}"
    return url

def parse_channel_list(soup, province_name):
    """
    从地方台首页解析频道列表

    Args:
        soup: BeautifulSoup对象
        province_name: 省份名称

    Returns:
        字典，键为频道名称，值为频道代码
    """
    channel_list = {}
    
    # 查找频道导航列表 (chlsnav ul)
    chlsnav = soup.find('div', class_='chlsnav')
    if chlsnav:
        ul = chlsnav.find('ul')
        if ul:
            links = ul.find_all('a', class_='black_link')
            logger.debug(f"在 {province_name} 频道导航中找到 {len(links)} 个频道")
            
            for link in links:
                href = link.get('href', '')
                title = link.get('title', '')
                text = link.get_text().strip()
                
                # 提取频道代码
                # 例如: /program/JSTV-JSTV3-w3.html -> JSTV-JSTV3-w3.html
                # 只处理带连字符的代码，跳过卫视频道
                match = re.search(r'/program[^/]*?/([A-Za-z0-9_-]+-w\d+\.html)', href)
                if not match:
                    continue

                channel_code = match.group(1)

                # 跳过不带连字符的频道（卫视）
                if '-' not in channel_code:
                    logger.debug(f"跳过卫视频道: {channel_code}")
                    continue

                # 确定频道名称（优先使用title，其次使用text）
                channel_name = title if title else text
                if not channel_name or len(channel_name) < 2:
                    continue

                # 过滤掉"频道节目表"等后缀
                channel_name = re.sub(r'频道节目表$', '', channel_name)
                channel_name = re.sub(r'节目表$', '', channel_name)
                
                channel_list[channel_name] = channel_code
                logger.debug(f"发现频道: {channel_name} -> {channel_code}")
    
    # 如果没有找到频道导航，使用通用方法
    if not channel_list:
        logger.debug(f"{province_name} 未找到频道导航，使用通用方法")
        links = soup.find_all('a', href=re.compile(r'/program[^/]*?/[A-Za-z0-9_-]+-w\d+\.html'))

        for link in links:
            href = link.get('href', '')
            title = link.get('title', '')
            text = link.get_text().strip()

            match = re.search(r'/program[^/]*?/([A-Za-z0-9_-]+-w\d+\.html)', href)
            if not match:
                continue

            channel_code = match.group(1)

            # 跳过不带连字符的频道
            if '-' not in channel_code:
                logger.debug(f"跳过卫视频道: {channel_code}")
                continue

            channel_name = title if title else text
            if not channel_name or len(channel_name) < 2:
                continue

            channel_name = re.sub(r'频道节目表$', '', channel_name)
            channel_name = re.sub(r'节目表$', '', channel_name)
            channel_list[channel_name] = channel_code
            logger.debug(f"发现频道: {channel_name} -> {channel_code}")

    logger.info(f"{province_name} 共找到 {len(channel_list)} 个地方频道（不含卫视）")
    return channel_list

def parse_channel_name(soup):
    """从页面提取频道名称"""
    # 方法1: 从h1标签提取
    h1_tag = soup.find('h1')
    if h1_tag:
        h1_text = h1_tag.get_text().strip()
        logger.debug(f"H1标签内容: {h1_text}")
        
        match = re.search(r'([^，,_，节目表预告\s]+)(卫视|频道|电视台)', h1_text)
        if match:
            channel_name = match.group(0)
            logger.info(f"从H1提取频道名称: {channel_name}")
            return channel_name
    
    # 方法2: 从title标签提取
    title_tag = soup.find('title')
    if title_tag:
        title_text = title_tag.get_text()
        logger.debug(f"title标签内容: {title_text}")
        match = re.search(r'([^，,_，节目表预告\s]+)(卫视|频道)', title_text)
        if match:
            channel_name = match.group(0)
            logger.info(f"从title提取频道名称: {channel_name}")
            return channel_name
    
    logger.warning("所有方法都无法提取频道名称")
    return None

def parse_program_items(soup):
    """
    解析节目单数据

    Returns:
        列表，每个元素为包含时间、节目名称、集数的字典
    """
    programs = []

    # 优先使用精确的HTML结构解析
    pgrow = soup.find('ul', id='pgrow')

    if pgrow:
        li_elements = pgrow.find_all('li')
        logger.debug(f"使用精确结构解析，找到 {len(li_elements)} 个节目项")

        for li in li_elements:
            am_span = li.find('span', class_='am')
            if not am_span:
                continue

            time_str = am_span.get_text().strip()
            if not re.match(r'^\d{2}:\d{2}$', time_str):
                continue

            p_show_span = li.find('span', class_='p_show')
            if not p_show_span:
                continue

            title = p_show_span.get_text().strip()
            title = re.sub(r'\s+', ' ', title)

            episode = None
            episode_match = re.search(r'\((\d+)\)$', title)
            if episode_match:
                episode = episode_match.group(1)
                title = re.sub(r'\(\d+\)$', '', title).strip()

            if title and len(title) > 0:
                programs.append({
                    'time': time_str,
                    'title': title,
                    'episode': episode
                })
    else:
        # 回退方案
        logger.debug("未找到精确结构，使用通用解析")
        li_elements = soup.find_all('li')
        logger.debug(f"找到 {len(li_elements)} 个 <li> 元素")

        for i, li in enumerate(li_elements):
            text = li.get_text().strip()
            if not text or len(text) < 5:
                continue

            if any(x in text for x in ['节目', '播出', '时段', '节目表']):
                continue

            pattern = r'^(\d{2}:\d{2})\s+(.+?)(?:\((\d+)\))?$'
            match = re.match(pattern, text)

            if match:
                time_str = match.group(1)
                title = match.group(2).strip()
                episode = match.group(3) if match.group(3) else None
                title = re.sub(r'\s+', ' ', title)
                programs.append({
                    'time': time_str,
                    'title': title,
                    'episode': episode
                })

    logger.info(f"共解析到 {len(programs)} 个节目")
    return programs

def fetch_province_channels(province_name, weekday=None, session=None):
    """
    获取指定省份的频道列表

    Args:
        province_name: 省份名称，如 '北京', '安徽'
        weekday: 星期几（1-7），默认为当前星期
        session: requests.Session对象

    Returns:
        字典，键为频道名称，值为EPG数据
    """
    if province_name not in PROVINCE_CODES:
        logger.error(f"不支持的省份: {province_name}")
        return {}
    
    province_info = PROVINCE_CODES[province_name]
    province_code = province_info['code']
    
    url = generate_url_with_weekday(province_code, weekday)
    logger.info(f"正在获取 {province_name} 的频道列表: {url}")

    response = make_request(url, session=session)
    if not response:
        logger.warning(f"获取失败: {province_name}")
        return {}
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 解析频道列表
    channel_list = parse_channel_list(soup, province_name)
    
    if not channel_list:
        logger.warning(f"未找到 {province_name} 的频道列表")
        return {}
    
    return channel_list

def fetch_province_epg(province_name, weekday=None, session=None):
    """
    获取指定省份所有频道的EPG数据

    Args:
        province_name: 省份名称，如 '北京', '安徽'
        weekday: 星期几（1-7），默认为当前星期
        session: requests.Session对象

    Returns:
        字典，键为频道名称，值为节目列表
    """
    if province_name not in PROVINCE_CODES:
        logger.error(f"不支持的省份: {province_name}")
        return {}
    
    province_info = PROVINCE_CODES[province_name]
    province_code = province_info['code']
    
    if weekday is None:
        weekday = get_current_weekday()
    
    url = f"https://www.tvmao.com/program/{province_code}"
    logger.info(f"正在获取 {province_name} 的EPG数据: {url}")

    response = make_request(url, session=session)
    if not response:
        logger.warning(f"获取失败: {province_name}")
        return {}
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 解析频道列表
    channel_list = parse_channel_list(soup, province_name)
    
    if not channel_list:
        logger.warning(f"未找到 {province_name} 的频道列表")
        return {}
    
    programs_dict = {}
    
    # 遍历每个频道获取EPG
    # channel_list中的都是带连字符的地方频道，直接使用/program/前缀
    for channel_name, channel_code in channel_list.items():
        # 地方频道格式: JSTV-JSTV2-w3.html -> /program/JSTV-JSTV2-w3.html
        channel_url = f"https://www.tvmao.com/program/{channel_code}"
        
        logger.debug(f"获取频道 {channel_name} 的EPG: {channel_url}")
        
        channel_response = make_request(channel_url, session=session)
        if not channel_response:
            continue
        
        channel_soup = BeautifulSoup(channel_response.text, 'html.parser')
        
        # 提取频道名称
        parsed_name = parse_channel_name(channel_soup)
        if not parsed_name:
            logger.warning(f"无法提取频道名称: {channel_code}")
            # 使用原频道名称
            parsed_name = channel_name
        
        # 提取节目列表
        programs = parse_program_items(channel_soup)
        
        if programs:
            programs_dict[parsed_name] = programs
            logger.info(f"成功获取 {parsed_name} 的 {len(programs)} 个节目")
        
        # 避免请求过快
        time.sleep(1)
    
    logger.info(f"{province_name} 完成！成功获取 {len(programs_dict)} 个频道的EPG数据")
    return programs_dict

def fetch_all_provinces_epg(province_list=None, weekday=None):
    """
    获取多个省份的EPG数据

    Args:
        province_list: 省份列表，如果为None则获取所有省份
        weekday: 星期几（1-7），默认为当前星期

    Returns:
        字典，键为省份名称，值为该省的EPG数据字典
    """
    if province_list is None:
        province_list = list(PROVINCE_CODES.keys())
    
    all_provinces_epg = {}
    
    # 创建Session以保持Cookie
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://www.tvmao.com/',
        'Connection': 'keep-alive'
    })

    try:
        session.get('https://www.tvmao.com/', timeout=10)
        logger.info("已访问首页建立会话")
    except Exception as e:
        logger.warning(f"访问首页失败: {e}")

    for province_name in province_list:
        if province_name not in PROVINCE_CODES:
            logger.warning(f"跳过不支持的省份: {province_name}")
            continue
        
        province_epg = fetch_province_epg(province_name, weekday, session)
        if province_epg:
            all_provinces_epg[province_name] = province_epg
        
        # 避免请求过快
        time.sleep(2 + (hash(province_name) % 3))
    
    session.close()
    logger.info(f"所有省份完成！共获取 {len(all_provinces_epg)} 个省的EPG数据")
    return all_provinces_epg

def generate_xmltv(provinces_epg_dict):
    """生成XMLTV格式数据"""
    today = datetime.now().strftime('%Y%m%d')
    generator_url = os.environ.get('TM_GENERATOR_URL', '')
    
    xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<tv generator-info-name="TMDF EPG Generator" generator-info-url="{generator_url}">
'''
    
    total_programs = 0
    
    for province_name, programs_dict in provinces_epg_dict.items():
        for channel_name, programs in programs_dict.items():
            channel_id = channel_name.replace(' ', '_').replace('-', '_').replace(':', '_')
            
            xml_content += f'''
  <channel id="{channel_id}">
    <display-name>{channel_name}</display-name>
  </channel>
'''
            
            for program in programs:
                time_str = program['time']
                title = program['title']
                
                start_time = f"{today}{time_str.replace(':', '')}00"
                
                try:
                    hour, minute = map(int, time_str.split(':'))
                    end_time = datetime.combine(datetime.now().date(), datetime.min.time()) + \
                              timedelta(hours=hour, minutes=minute+30)
                    end_time_str = end_time.strftime(f"{today}%H%M00")
                    
                    xml_content += f'''
  <programme channel="{channel_id}" start="{start_time}" stop="{end_time_str}">
    <title lang="zh">{title}</title>
  </programme>
'''
                    total_programs += 1
                except Exception as e:
                    logger.warning(f"解析节目时间失败，跳过节目: {title}, 时间: {time_str}, 错误: {e}")
                    continue
    
    logger.info(f"共生成了 {total_programs} 个节目元素")
    xml_content += '''
</tv>
'''
    
    return xml_content

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("电视猫地方台EPG爬虫启动")
    logger.info("=" * 60)
    
    # 获取所有省份的EPG数据
    all_provinces_epg = fetch_all_provinces_epg(['北京', '安徽', '广东', '浙江'])
    
    if not all_provinces_epg:
        logger.error("未获取到任何EPG数据")
        return
    
    # 打印统计信息
    print("\n" + "=" * 60)
    print("EPG数据统计")
    print("=" * 60)
    for province_name, programs_dict in all_provinces_epg.items():
        print(f"\n{province_name}:")
        for channel_name in sorted(programs_dict.keys()):
            print(f"  - {channel_name}: {len(programs_dict[channel_name])} 个节目")
    
    # 生成XMLTV文件
    print("\n" + "=" * 60)
    print("生成XMLTV文件")
    print("=" * 60)
    
    xmltv_content = generate_xmltv(all_provinces_epg)
    
    output_dir = 'output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    today = datetime.now().strftime('%Y%m%d')
    output_file = os.path.join(output_dir, f'tvmao_df_{today}.xml')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(xmltv_content)
    
    print(f"文件已保存: {output_file}")
    print(f"文件大小: {os.path.getsize(output_file) / 1024:.2f} KB")
    
    logger.info("=" * 60)
    logger.info("爬虫执行完成")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
