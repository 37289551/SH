import requests
import time
from bs4 import BeautifulSoup
import logging
from datetime import datetime, timedelta
import os
import re

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

file_handler = logging.FileHandler('tvsou_epg.log', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)
def make_request(url, headers=None, retry=2, delay=2):
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    for attempt in range(retry):
        try:
            logger.info(f"请求URL: {url} (尝试 {attempt+1}/{retry})")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            logger.info(f"成功获取URL: {url}，状态码: {response.status_code}")
            return response
        except requests.RequestException as e:
            logger.warning(f"请求失败 (尝试 {attempt+1}/{retry}): {e}")
            if attempt < retry - 1:
                time.sleep(delay)
            else:
                logger.error(f"所有重试均失败: {url}")
                return None

def fetch_tvsou_channel_programs(url, channel_type):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = make_request(url, headers=headers)
    if not response:
        return {}
    
    soup = BeautifulSoup(response.text, 'html.parser')
    programs_dict = {}
    
    try:
        logger.info(f"开始解析{channel_type}页面: {url}")
        channel_links = soup.find_all('a', href=lambda href: href and '/epg/' in href and ('yangshi' in href or 'weishi' in href) and '_w' not in href)
        logger.info(f"找到 {len(channel_links)} 个频道链接")
        unique_channels = {}
        for link in channel_links:
            channel_name = link.text.strip()
            channel_href = link['href']
            
            if channel_name in ['央视', '卫视']:
                continue
            if re.match(r'^(周一|周二|周三|周四|周五|周六|周日)', channel_name):
                continue
            
            if channel_name and channel_href not in unique_channels:
                unique_channels[channel_href] = channel_name
        
        logger.info(f"去重后得到 {len(unique_channels)} 个频道")
        
        for channel_href, channel_name in unique_channels.items():
            if not channel_href.startswith('http'):
                channel_href = f"https://www.tvsou.com{channel_href}"
            logger.info(f"正在提取 {channel_name} 的节目单: {channel_href}")
            channel_response = make_request(channel_href, headers=headers)
            if not channel_response:
                continue
            channel_soup = BeautifulSoup(channel_response.text, 'html.parser')
            programs = []
            program_tables = channel_soup.find_all('table')
            for table in program_tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        time_str = cells[0].text.strip()
                        title = cells[1].text.strip()
                        if time_str and title and ':' in time_str:
                            programs.append({'time': time_str, 'title': title})
            
            unique_programs = []
            seen = set()
            for prog in programs:
                key = f"{prog['time']}_{prog['title']}"
                if key not in seen:
                    seen.add(key)
                    unique_programs.append(prog)
            
            if unique_programs:
                programs_dict[channel_name] = unique_programs
                logger.info(f"  成功提取 {len(unique_programs)} 个节目")
            else:
                logger.warning(f"  未提取到任何节目")
    
    except Exception as e:
        logger.error(f"解析{channel_type}节目单失败: {e}", exc_info=True)
    
    return programs_dict

def fetch_tvsou_programs():
    programs_dict = {}
    cctv_url = "https://www.tvsou.com/epg/yangshi/"
    cctv_programs = fetch_tvsou_channel_programs(cctv_url, "央视")
    programs_dict.update(cctv_programs)
    satellite_url = "https://www.tvsou.com/epg/weishi/"
    satellite_programs = fetch_tvsou_channel_programs(satellite_url, "卫视")
    programs_dict.update(satellite_programs)
    filtered_programs = {}
    for channel_name, programs in programs_dict.items():
        if channel_name in ['央视', '卫视'] or re.match(r'^(周一|周二|周三|周四|周五|周六|周日)\(\d{2}\.\d{2}\)$', channel_name):
            logger.info(f"过滤掉不需要的频道: {channel_name}")
            continue
        if is_cctv_or_satellite(channel_name):
            filtered_programs[channel_name] = programs
        else:
            logger.info(f"过滤掉非央视/卫视频道: {channel_name}")
    
    return filtered_programs

def is_cctv_or_satellite(channel_name):
    cctv_keywords = ['CCTV', '央视', '中央电视台']
    satellite_keywords = ['卫视', '东方', '浙江', '湖南', '江苏', '广东', '北京', '安徽', '山东', 
                         '河南', '湖北', '四川', '重庆', '天津', '江西', '福建', '云南', '贵州',
                         '黑龙江', '吉林', '辽宁', '内蒙古', '山西', '陕西', '甘肃', '青海', '宁夏',
                         '新疆', '西藏', '广西', '海南']
    channel_name_lower = channel_name.lower()
    for keyword in cctv_keywords:
        if keyword in channel_name:
            return True
    for keyword in satellite_keywords:
        if keyword in channel_name:
            return True
    return False

def generate_xmltv(programs_dict):
    today = datetime.now().strftime('%Y%m%d')
    xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<tv generator-info-name="TVSou EPG Generator" generator-info-url="https://www.tvsou.com/epg">
'''
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
                end_time = datetime.combine(datetime.now().date(), datetime.min.time()) + timedelta(hours=hour, minutes=minute+30)
                end_time_str = end_time.strftime(f"{today}%H%M00")
            except:
                continue
            xml_content += f'''
  <programme channel="{channel_id}" start="{start_time}" stop="{end_time_str}">
    <title lang="zh">{title}</title>
  </programme>
'''
    xml_content += f'''
</tv>
'''
    return xml_content

def main():
    logger.info("开始从tvsou.com提取节目单...")
    programs_dict = fetch_tvsou_programs()
    logger.info(f"共提取到 {len(programs_dict)} 个频道的节目单")
    if programs_dict:
        xmltv_content = generate_xmltv(programs_dict)
        output_dir = 'output'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        today = datetime.now().strftime('%Y%m%d')
        output_file = os.path.join(output_dir, f'tvsou_epg_{today}.xml')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(xmltv_content)
        logger.info(f"节目单已保存到 {output_file}")
        total_programs = 0
        for channel_name, programs in programs_dict.items():
            program_count = len(programs)
            total_programs += program_count
            logger.info(f"  {channel_name}: {program_count} 个节目")
        logger.info(f"共提取到 {total_programs} 个节目")
    else:
        logger.warning("未提取到任何节目单")

if __name__ == "__main__":
    import time
    main()
