#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
import logging
import re
from datetime import datetime, timedelta, timezone
import time
import os
from channel_mapping import normalize_channel_name

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

file_handler = logging.FileHandler('tm2_epg.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

B_PROGRAM = os.environ.get('B_PROGRAM', 'https://www.tvmao.com/program/')
B_WS = os.environ.get('B_WS', 'https://www.tvmao.com/program_satellite/')
TM_REFERER = os.environ.get('TM_REFERER', 'https://www.tvmao.com/')

CHANNEL_CODES = {
    'CCTV-1综合': 'CCTV-CCTV1',
    'CCTV-2财经': 'CCTV-CCTV2',
    'CCTV-3综艺': 'CCTV-CCTV3',
    'CCTV-4国际': 'CCTV-CCTV4',
    'CCTV-4欧洲': 'CCTV-CCTVEUROPE',
    'CCTV-4美洲': 'CCTV-CCTVAMERICAS',
    'CCTV-5体育': 'CCTV-CCTV5',
    'CCTV-5加': 'CCTV-CCTV5-PLUS',
    'CCTV-6电影': 'CCTV-CCTV6',
    'CCTV-7国防军事': 'CCTV-CCTV7',
    'CCTV-8电视剧': 'CCTV-CCTV8',
    'CCTV-9纪录': 'CCTV-CCTV9',
    'CCTV-10科教': 'CCTV-CCTV10',
    'CCTV-11戏曲': 'CCTV-CCTV11',
    'CCTV-12法制': 'CCTV-CCTV12',
    'CCTV-13新闻': 'CCTV-CCTV13',
    'CCTV-14少儿': 'CCTV-CCTV15',
    'CCTV-15音乐': 'CCTV-CCTV16',
    'CCTV-16奥林匹克': 'CCTV-CCTVOLY',
    'CCTV-17农业': 'CCTV-CCTV17',
    'CGTN 西语': 'CCTV-CCTV17',
    'CGTN 纪录(英)': 'CCTV-CCTV18',
    'CGTN': 'CCTV-CCTV19',
    'CGTN 法语': 'CCTV-CCTVF',
    'CGTN 阿语': 'CCTV-CCTVA',
    'CGTN 俄语': 'CCTV-CCTVR',
    '中国电影频道北美版': 'CCTV-CHINA-MOVIE-CHANNEL-NA',
    '安徽卫视': 'AHTV1',
    '北京卫视': 'BTV1',
    '重庆卫视': 'CCQTV1',
    '东南卫视': 'FJTV2',
    '甘肃卫视': 'GSTV1',
    '广东卫视': 'GDTV1',
    '广西卫视': 'GUANXI1',
    '贵州卫视': 'GUIZOUTV1',
    '海南卫视': 'TCTC1',
    '河北卫视': 'HEBEI1',
    '黑龙江卫视': 'HLJTV1',
    '河南卫视': 'HNTV1',
    '湖北卫视': 'HUBEI1',
    '湖南卫视': 'HUNANTV1',
    '吉林卫视': 'JILIN1',
    '江苏卫视': 'JSTV1',
    '江西卫视': 'JXTV1',
    '辽宁卫视': 'LNTV1',
    '内蒙古卫视': 'NMGTV1',
    '宁夏卫视': 'NXTV2',
    '青海卫视': 'QHTV1',
    '山东卫视': 'SDTV1',
    '山西卫视': 'SXTV1',
    '陕西卫视': 'SHXITV1',
    '东方卫视': 'DONGFANG1',
    '上海卫视': 'STV',
    '深圳卫视': 'SZTV1',
    '四川卫视': 'SCTV1',
    '天津卫视': 'TJTV1',
    '西藏卫视': 'XIZANGTV2',
    '新疆卫视': 'XJTV1',
    '云南卫视': 'YNTV1',
    '浙江卫视': 'ZJTV1',
    '兵团卫视': 'BINGTUAN',
    '海峡卫视': 'HXTV',
    '黄河卫视': 'HHWS',
    '康巴卫视': 'KAMBA-TV',
    '三沙卫视': 'SANSHATV',
    '延边卫视': 'YANBIAN1',
    '卡酷少儿': 'BTV10',
    '金鹰卡通': 'HUNANTV2',
    '哈哈炫动': 'TOONMAX1',
    '南方卫视': 'NANFANG2',
    '藏语卫视': 'XIZANGTV1',
}

def make_request(url, session=None, headers=None, retry=3, delay=2):
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
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
            'Referer': TM_REFERER,
            'DNT': '1'
        }
    
    request_func = session.get if session else requests.get
    
    for attempt in range(retry):
        try:
            response = request_func(url, headers=headers, timeout=15, allow_redirects=True)
            response.raise_for_status()
            
            if '/ccp/' in response.url and '/ccp/' not in url:
                logger.warning(f"检测到反爬虫重定向: {url} -> {response.url}")
                if attempt < retry - 1:
                    wait_time = delay * (attempt + 1)
                    logger.info(f"等待 {wait_time} 秒后重试... ({attempt + 1}/{retry})")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"所有重试均失败: {url}")
                    return None
            
            if len(response.text) < 500:
                logger.warning(f"响应体过小 ({len(response.text)} 字节), 可能被拦截: {url}")
                if attempt < retry - 1:
                    wait_time = delay * (attempt + 1)
                    logger.info(f"等待 {wait_time} 秒后重试... ({attempt + 1}/{retry})")
                    time.sleep(wait_time)
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
    return datetime.now(timezone(timedelta(hours=8))).weekday() + 1

def generate_url(channel_code):
    return generate_url_with_weekday(channel_code)

def generate_url_with_weekday(channel_code, weekday=None):
    if weekday is None:
        weekday = get_current_weekday()

    if channel_code.startswith('CCTV-'):
        url = f"{B_PROGRAM}{channel_code}-w{weekday}.html"
    else:
        url = f"{B_WS}{channel_code}-w{weekday}.html"
    return url

def parse_channel_name(soup):
    h1_tag = soup.find('h1')
    if h1_tag:
        h1_text = h1_tag.get_text().strip()
        logger.debug(f"H1标签内容: {h1_text}")
        
        match = re.search(r'([^，,_，节目表预告\s]+)(卫视|频道)', h1_text)
        if match:
            channel_name = match.group(0)
            logger.info(f"从H1提取频道名称: {channel_name}")
            return channel_name
    
    title_tag = soup.find('title')
    if title_tag:
        title_text = title_tag.get_text()
        logger.debug(f"title标签内容: {title_text}")
        match = re.search(r'([^，,_，节目表预告\s]+)(卫视|频道)', title_text)
        if match:
            channel_name = match.group(0)
            logger.info(f"从title提取频道名称: {channel_name}")
            return channel_name
    
    breadcrumb = soup.find('div', class_='breadcrumb')
    if breadcrumb:
        links = breadcrumb.find_all('a')
        for link in links:
            text = link.get_text().strip()
            logger.debug(f"面包屑链接: {text}")
            if '卫视' in text or '频道' in text:
                logger.info(f"从面包屑提取频道名称: {text}")
                return text
    
    all_text = soup.get_text()
    patterns = [r'([^\s，,_]+卫视)', r'([^\s，,_]+频道)']
    for pattern in patterns:
        match = re.search(pattern, all_text)
        if match:
            channel_name = match.group(0)
            if not any(x in channel_name for x in ['节目表', '节目预告', '电视猫', '卫视网']):
                logger.info(f"从页面文本提取频道名称: {channel_name}")
                return channel_name
    
    logger.warning("所有方法都无法提取频道名称")
    if h1_tag:
        logger.warning(f"H1: {h1_tag}")
    if title_tag:
        logger.warning(f"title: {title_tag}")
    
    return None

def parse_program_items(soup):
    programs = []

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
                logger.debug(f"解析到节目: {time_str} - {title}{f'({episode})' if episode else ''}")
    else:
        logger.debug("未找到精确结构，使用通用解析")
        li_elements = soup.find_all('li')
        logger.debug(f"找到 {len(li_elements)} 个 <li> 元素")

        for i, li in enumerate(li_elements):
            text = li.get_text().strip()
            if not text:
                continue

            if len(text) < 5:
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
                title = re.sub(r'^正在播出\s+', '', title)

                programs.append({
                    'time': time_str,
                    'title': title,
                    'episode': episode
                })

                logger.debug(f"解析到节目 {i+1}: {time_str} - {title}")

    logger.info(f"共解析到 {len(programs)} 个节目")
    return programs

def fetch_channel_epg(channel_code, weekday=None, session=None):
    url = generate_url_with_weekday(channel_code, weekday)
    logger.info(f"正在获取: {url}")

    response = make_request(url, session=session)
    if not response:
        logger.warning(f"获取失败: {channel_code}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    channel_name = parse_channel_name(soup)
    if not channel_name:
        logger.warning(f"无法提取频道名称: {channel_code}")
        return None

    programs = parse_program_items(soup)

    if programs:
        logger.info(f"成功获取 {channel_name} 的 {len(programs)} 个节目")
    else:
        logger.warning(f"未找到节目数据: {channel_name}")

    return {
        'channel': channel_name,
        'code': channel_code,
        'programs': programs
    }

def fetch_all_satellite_epg(channel_list=None, weekday=None):
    programs_dict = {}

    if channel_list is None:
        channel_list = CHANNEL_CODES

    total_channels = len(channel_list)
    logger.info(f"开始获取 {total_channels} 个卫视频道的EPG数据")

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': TM_REFERER,
        'Connection': 'keep-alive'
    })

    try:
        session.get(TM_REFERER, timeout=10)
        logger.info("已访问首页建立会话")
    except Exception as e:
        logger.warning(f"访问首页失败: {e}")

    success_count = 0
    for channel_name, channel_code in channel_list.items():
        epg_data = fetch_channel_epg(channel_code, weekday, session=session)

        if epg_data and epg_data['programs']:
            programs_dict[epg_data['channel']] = epg_data['programs']
            success_count += 1

        time.sleep(2 + (hash(channel_code) % 3))

    session.close()
    logger.info(f"完成！成功获取 {success_count}/{total_channels} 个频道的EPG数据")
    return programs_dict

def generate_xmltv(programs_dict):
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
    url = generate_url_with_weekday(channel_code, weekday)
    print(f"\n{'='*60}")
    print(f"调试模式: {url}")
    print(f"{'='*60}")

    response = make_request(url)
    if not response:
        print(f"❌ 页面请求失败")
        return

    soup = BeautifulSoup(response.text, 'html.parser')

    print(f"\n📄 页面基本信息:")
    print(f"  URL: {url}")
    print(f"  状态码: {response.status_code}")
    print(f"  页面大小: {len(response.text)} 字节")

    title_tag = soup.find('title')
    if title_tag:
        print(f"\n🏷️  Title标签: {title_tag.get_text()}")

    h1_tags = soup.find_all('h1')
    print(f"\n📌 H1标签 (共{len(h1_tags)}个):")
    for i, h1 in enumerate(h1_tags, 1):
        print(f"  {i}. {h1.get_text().strip()}")

    breadcrumb = soup.find('div', class_='breadcrumb')
    if breadcrumb:
        print(f"\n🧭 面包屑导航:")
        links = breadcrumb.find_all('a')
        for link in links:
            print(f"  - {link.get_text().strip()}: {link.get('href', '')}")

    channel_name = parse_channel_name(soup)
    print(f"\n✅ 提取的频道名称: {channel_name}")

    li_elements = soup.find_all('li')
    print(f"\n📋 LI元素 (共{len(li_elements)}个，显示前10个):")
    for i, li in enumerate(li_elements[:10], 1):
        text = li.get_text().strip()
        if text:
            print(f"  {i}. {text[:100]}")

    print(f"\n⏰ 包含时间的节目 (前5个):")
    time_pattern = re.compile(r'^\d{2}:\d{2}')
    count = 0
    for li in li_elements:
        text = li.get_text().strip()
        if time_pattern.match(text) and count < 5:
            print(f"  {count+1}. {text}")
            count += 1

def main():
    logger.info("=" * 60)
    logger.info("电视猫新版卫视频道EPG爬虫启动")
    logger.info("=" * 60)
    
    programs_dict = fetch_all_satellite_epg()
    
    if not programs_dict:
        logger.error("未获取到任何EPG数据")
        return
    
    print("\n" + "=" * 60)
    print("EPG数据统计")
    print("=" * 60)
    print(f"频道数量: {len(programs_dict)}")
    print(f"总节目数: {sum(len(programs) for programs in programs_dict.values())}")
    print("\n频道列表:")
    for channel_name in sorted(programs_dict.keys()):
        print(f"  - {channel_name}: {len(programs_dict[channel_name])} 个节目")
    
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
