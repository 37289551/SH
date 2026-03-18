import requests
from bs4 import BeautifulSoup
import logging
import re
from datetime import datetime, timedelta, timezone
import time
import os
import random
from channel_mapping import normalize_channel_name

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

file_handler = logging.FileHandler('tmdf_epg.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

B_PROGRAM = os.environ['B_PROGRAM']
TM_REFERER = os.environ['TM_REFERER']

# 支持一个省份多个code映射
# code 可以是单个字符串或字符串列表
PROVINCE_CODES = {
    '天津': {'code': ['TJTV'], 'provId': '120000'},
    '江苏': {'code': ['JSTV'], 'provId': '320000'},
    '江西': {'code': ['JXTV'], 'provId': '360000'},
    '广东': {'code': ['GDTV'], 'provId': '440000'},
    '贵州': {'code': ['GUIZOUTV'], 'provId': '520000'},
    '宁夏': {'code': ['NXTV'], 'provId': '640000'},
    '河北': {'code': ['HEBEI'], 'provId': '130000'},
    '辽宁': {'code': ['LNTV'], 'provId': '210000'},
    '浙江': {'code': ['ZJTV'], 'provId': '330000'},
    '山东': {'code': ['SDTV'], 'provId': '370000'},
    '河南': {'code': ['HNTV'], 'provId': '410000'},
    '广西': {'code': ['GUANXI'], 'provId': '450000'},
    '云南': {'code': ['YNTV'], 'provId': '530000'},
    '陕西': {'code': ['SHXITV'], 'provId': '610000'},
    '新疆': {'code': ['XJTV'], 'provId': '650000'},
    '山西': {'code': ['SXTV'], 'provId': '140000'},
    '吉林': {'code': ['JILIN'], 'provId': '220000'},
    '安徽': {'code': ['AHTV'], 'provId': '340000'},
    '湖北': {'code': ['HUBEI'], 'provId': '420000'},
    '海南': {'code': ['TCTC'], 'provId': '460000'},
    '重庆': {'code': ['CCQTV'], 'provId': '500000'},
    '西藏': {'code': ['XIZANGTV'], 'provId': '540000'},
    '甘肃': {'code': ['GSTV'], 'provId': '620000'},
    '北京': {'code': ['BTV'], 'provId': '110000'},
    '内蒙': {'code': ['NMGTV'], 'provId': '150000'},
    '黑龙': {'code': ['HLJTV'], 'provId': '230000'},
    '上海': {'code': ['SHHAI'], 'provId': '310000'},
    '福建': {'code': ['FJTV'], 'provId': '350000'},
    '湖南': {'code': ['HNETV', 'HNETV2', 'HNETV3'], 'provId': '430000'},
    '四川': {'code': ['SCTV'], 'provId': '510000'},
    '青海': {'code': ['QHTV'], 'provId': '630000'},
}

def make_request(url, session=None, headers=None, retry=0, delay=2):
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
    ]
    
    if headers is None:
        headers = {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Cache-Control': 'max-age=0',
            'Referer': TM_REFERER,
            'DNT': '1',
            'Sec-Fetch-User': '?1',
            'TE': 'trailers',
            'X-Requested-With': 'XMLHttpRequest'
        }
    
    request_func = session.get if session else requests.get
    
    try:
        time.sleep(random.uniform(0.5, 1.5))
        
        if random.random() > 0.5:
            headers['User-Agent'] = random.choice(user_agents)
        
        response = request_func(url, headers=headers, timeout=15, allow_redirects=True)
        
        if response.status_code == 404:
            logger.warning(f"404错误: {url}, 跳过该频道")
            return None
        
        response.raise_for_status()
        
        if len(response.text) < 500:
            logger.warning(f"响应体过小 ({len(response.text)} 字节), 可能被拦截: {url}")
            return None
        
        return response
    except requests.RequestException as e:
        if "404" in str(e):
            logger.warning(f"404错误: {url}, 跳过该频道")
            return None
        
        logger.error(f"请求失败: {url}, 错误: {e}")
        return None

def get_current_weekday():
    return datetime.now(timezone(timedelta(hours=8))).weekday() + 1

def generate_url_with_weekday(province_code, weekday=None):
    url = f"{B_PROGRAM}{province_code}"
    return url

def parse_channel_list(soup, province_name):
    channel_list = {}
    
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
                
                match = re.search(r'/program[^/]*?/([A-Za-z0-9_-]+-w\d+\.html)', href)
                if not match:
                    continue

                channel_code = match.group(1)

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
    h1_tag = soup.find('h1')
    if h1_tag:
        h1_text = h1_tag.get_text().strip()
        logger.debug(f"H1标签内容: {h1_text}")
        
        match = re.search(r'([^，,_，节目表预告\s]+)(卫视|频道|电视台)', h1_text)
        if match:
            channel_name = match.group(0)
            channel_name = re.sub(r'电视台|广播|频道|BRTV', '', channel_name)
            logger.info(f"从H1提取频道名称: {channel_name}")
            return channel_name
    
    title_tag = soup.find('title')
    if title_tag:
        title_text = title_tag.get_text()
        logger.debug(f"title标签内容: {title_text}")
        match = re.search(r'([^，,_，节目表预告\s]+)(卫视|频道)', title_text)
        if match:
            channel_name = match.group(0)
            channel_name = re.sub(r'电视台|广播|频道|BRTV', '', channel_name)
            logger.info(f"从title提取频道名称: {channel_name}")
            return channel_name
    
    logger.warning("所有方法都无法提取频道名称")
    return None

def parse_program_items(soup):
    programs = []

    pgrow = soup.find('ul', id='pgrow')

    if pgrow:
        li_elements = pgrow.find_all('li')
        logger.debug(f"使用精确结构解析，找到 {len(li_elements)} 个节目项")

        for li in li_elements:
            time_span = li.find('span', class_='am') or li.find('span', class_='pm')
            if not time_span:
                continue

            time_str = time_span.get_text().strip()
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
    if province_name not in PROVINCE_CODES:
        logger.error(f"不支持的省份: {province_name}")
        return {}
    
    province_info = PROVINCE_CODES[province_name]
    # 支持单个code或code列表
    codes = province_info['code']
    if isinstance(codes, str):
        codes = [codes]
    
    all_channels = {}
    for province_code in codes:
        url = generate_url_with_weekday(province_code, weekday)
        logger.info(f"正在获取 {province_name} ({province_code}) 的频道列表: {url}")

        response = make_request(url, session=session)
        if not response:
            logger.warning(f"获取失败: {province_name} ({province_code})")
            continue
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        channel_list = parse_channel_list(soup, province_name)
        
        if channel_list:
            all_channels.update(channel_list)
            logger.info(f"{province_name} ({province_code}) 获取到 {len(channel_list)} 个频道")
        else:
            logger.warning(f"未找到 {province_name} ({province_code}) 的频道列表")
    
    return all_channels

def fetch_province_epg(province_name, weekday=None, session=None):
    if province_name not in PROVINCE_CODES:
        logger.error(f"不支持的省份: {province_name}")
        return {}
    
    province_info = PROVINCE_CODES[province_name]
    # 支持单个code或code列表
    codes = province_info['code']
    if isinstance(codes, str):
        codes = [codes]
    
    if weekday is None:
        weekday = get_current_weekday()
    
    all_programs = {}
    
    for province_code in codes:
        url = f"{B_PROGRAM}{province_code}"
        logger.info(f"正在获取 {province_name} ({province_code}) 的EPG数据: {url}")

        response = make_request(url, session=session)
        if not response:
            logger.warning(f"获取失败: {province_name} ({province_code})")
            continue
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        channel_list = parse_channel_list(soup, province_name)
        
        if not channel_list:
            logger.warning(f"未找到 {province_name} ({province_code}) 的频道列表")
            continue
        
        programs_dict = {}
        
        for channel_name, channel_code in channel_list.items():
            channel_url = f"{B_PROGRAM}{channel_code}"
            
            logger.debug(f"获取频道 {channel_name} 的EPG: {channel_url}")
            
            channel_response = make_request(channel_url, session=session)
            if not channel_response:
                continue
            
            channel_soup = BeautifulSoup(channel_response.text, 'html.parser')
            
            parsed_name = parse_channel_name(channel_soup)
            if not parsed_name:
                logger.warning(f"无法提取频道名称: {channel_code}")
                parsed_name = channel_name
            
            programs = parse_program_items(channel_soup)
            
            if programs:
                programs_dict[parsed_name] = programs
                logger.info(f"成功获取 {parsed_name} 的 {len(programs)} 个节目")
            
            time.sleep(1)
        
        all_programs.update(programs_dict)
        logger.info(f"{province_name} ({province_code}) 完成！成功获取 {len(programs_dict)} 个频道的EPG数据")
    
    logger.info(f"{province_name} 总计完成！成功获取 {len(all_programs)} 个频道的EPG数据")
    return all_programs

def fetch_all_provinces_epg(province_list=None, weekday=None):
    if province_list is None:
        province_list = list(PROVINCE_CODES.keys())
    
    all_provinces_epg = {}
    
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

    for province_name in province_list:
        if province_name not in PROVINCE_CODES:
            logger.warning(f"跳过不支持的省份: {province_name}")
            continue
        
        province_epg = fetch_province_epg(province_name, weekday, session)
        if province_epg:
            all_provinces_epg[province_name] = province_epg
        
        time.sleep(2 + (hash(province_name) % 3))
    
    session.close()
    logger.info(f"所有省份完成！共获取 {len(all_provinces_epg)} 个省的EPG数据")
    return all_provinces_epg

def generate_xmltv(provinces_epg_dict):
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
    logger.info("=" * 60)
    logger.info("电视猫地方台EPG爬虫启动")
    logger.info("=" * 60)
    
    all_provinces_epg = fetch_all_provinces_epg(['北京', '安徽', '广东', '浙江'])
    
    if not all_provinces_epg:
        logger.error("未获取到任何EPG数据")
        return
    
    print("\n" + "=" * 60)
    print("EPG数据统计")
    print("=" * 60)
    for province_name, programs_dict in all_provinces_epg.items():
        print(f"\n{province_name}:")
        for channel_name in sorted(programs_dict.keys()):
            print(f"  - {channel_name}: {len(programs_dict[channel_name])} 个节目")
    
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
