import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime, timedelta
import os
import time
import re

from channel_mapping import normalize_channel_name

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

file_handler = logging.FileHandler('tvmao_epg.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

def make_request(url, session=None, headers=None, retry=3, delay=2):
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.tvmao.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3'
        }
    
    # 使用会话或直接请求
    request_func = session.get if session else requests.get
    
    for attempt in range(retry):
        try:
            logger.info(f"请求URL: {url} (尝试 {attempt+1}/{retry})")
            response = request_func(url, headers=headers, timeout=15)
            response.raise_for_status()
            logger.info(f"成功获取URL: {url}，状态码: {response.status_code}")
            return response
        except requests.RequestException as e:
            logger.warning(f"请求失败 (尝试 {attempt+1}/{retry}): {e}")
            if attempt < retry - 1:
                logger.info(f"等待 {delay} 秒后重试...")
                time.sleep(delay)
            else:
                logger.error(f"所有重试均失败: {url}")
                return None

def get_current_weekday():
    return datetime.now().weekday() + 1

def generate_time_slots():
    return list(range(0, 24, 2))

def generate_urls(channel_type, weekday=None):
    urls = []
    if weekday is None:
        weekday = get_current_weekday()
    time_slots = generate_time_slots()
    if channel_type == 'cctv':
        url_prefix = "https://a-s1.tvmao.com/program/duration/cctv/"
    elif channel_type == 'satellite':
        url_prefix = "https://a-s1.tvmao.com/program/duration/satellite/"
    else:
        logger.error(f"不支持的频道类型: {channel_type}")
        return urls
    for slot in time_slots:
        url = f"{url_prefix}w{weekday}-h{slot}.html"
        urls.append(url)
    
    logger.info(f"为{channel_type}频道生成了 {len(urls)} 个URL")
    return urls

def parse_program_item(item, channel_name):
    try:
        # 提取时间和标题
        
        # 1. 尝试查找所有span元素，按顺序提取时间和标题
        spans = item.find_all('span')
        if len(spans) >= 2:
            # 通常第一个span是时间，第二个是标题
            time_str = spans[0].text.strip()
            title = spans[1].text.strip()
            if time_str and title and ':' in time_str:
                title_time_match = re.search(r'(\d{2}:\d{2})-(\d{2}:\d{2})', title)
                if title_time_match:
                    time_str = title_time_match.group(1)
                    pure_title = re.sub(r'\s*\d{2}:\d{2}-\d{2}:\d{2}\s*$', '', title).strip()
                    return {'time': time_str, 'title': pure_title}
                return {'time': time_str, 'title': title}
        
        time_elem = item.find(['span', 'div', 'p'], class_=lambda cls: cls and ('time' in cls or 'program-time' in cls or 'start-time' in cls))
        title_elem = item.find(['span', 'div', 'p'], class_=lambda cls: cls and ('title' in cls or 'program-title' in cls or 'name' in cls))
        if time_elem and title_elem:
            time_str = time_elem.text.strip()
            title = title_elem.text.strip()
            if time_str and title and ':' in time_str:
                title_time_match = re.search(r'(\d{2}:\d{2})-(\d{2}:\d{2})', title)
                if title_time_match:
                    time_str = title_time_match.group(1)
                    pure_title = re.sub(r'\s*\d{2}:\d{2}-\d{2}:\d{2}\s*$', '', title).strip()
                    return {'time': time_str, 'title': pure_title}
                return {'time': time_str, 'title': title}
        
        item_text = item.text.strip()
        if item_text:
            time_match = re.search(r'(\d{2}:\d{2})', item_text)
            if time_match:
                time_str = time_match.group(1)
                title = item_text[time_match.end():].strip()
                title_time_match = re.search(r'(\d{2}:\d{2})-(\d{2}:\d{2})', title)
                if title_time_match:
                    time_str = title_time_match.group(1)
                    pure_title = re.sub(r'\s*\d{2}:\d{2}-\d{2}:\d{2}\s*$', '', title).strip()
                    return {'time': time_str, 'title': pure_title}
                if title:
                    return {'time': time_str, 'title': title}
        
        all_text = ' '.join(item.stripped_strings)
        if all_text:
            time_match = re.search(r'(\d{2}:\d{2})', all_text)
            if time_match:
                time_str = time_match.group(1)
                title = all_text[time_match.end():].strip()
                title_time_match = re.search(r'(\d{2}:\d{2})-(\d{2}:\d{2})', title)
                if title_time_match:
                    time_str = title_time_match.group(1)
                    pure_title = re.sub(r'\s*\d{2}:\d{2}-\d{2}:\d{2}\s*$', '', title).strip()
                    return {'time': time_str, 'title': pure_title}
                if title:
                    return {'time': time_str, 'title': title}
        
        return None
    except Exception as e:
        logger.error(f"解析节目项失败: {e}", exc_info=True)
        return None

def fetch_program_items(soup):
    programs = []
    try:
        tables = soup.find_all('table')
        logger.info(f"找到 {len(tables)} 个表格")
        processed_channels = set()
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    channel_name = cells[0].text.strip()
                    if not channel_name:
                        continue
                    standard_channel_name = normalize_channel_name(channel_name)
                    if standard_channel_name in processed_channels:
                        continue
                    processed_channels.add(standard_channel_name)
                    logger.info(f"处理频道: {standard_channel_name}")
                    for i, cell in enumerate(cells[1:], 2):
                        cell_text = cell.text.strip()
                        if not cell_text:
                            continue
                        time_match = re.search(r'(\d{2}:\d{2})-(\d{2}:\d{2})', cell_text)
                        if time_match:
                            start_time = time_match.group(1)
                            end_time = time_match.group(2)
                            pure_title = re.sub(r'\s*\d{2}:\d{2}-\d{2}:\d{2}\s*$', '', cell_text).strip()
                            pure_title = re.sub(r'\s+', ' ', pure_title)
                            if pure_title and start_time and end_time:
                                programs.append((standard_channel_name, {'time': start_time, 'end_time': end_time, 'title': pure_title}))
        
        logger.info(f"成功解析 {len(programs)} 个节目")
    except Exception as e:
        logger.error(f"提取节目列表失败: {e}", exc_info=True)
    
    return programs

def fetch_tvmao_programs(channel_type=None, weekday=None):
    programs_dict = {}
    
    # 生成所有需要抓取的URL
    # 如果没有指定channel_type，抓取所有类型
    if channel_type:
        urls = generate_urls(channel_type, weekday)
    else:
        urls = []
        # 抓取所有类型：cctv和satellite
        urls.extend(generate_urls('cctv', weekday))
        urls.extend(generate_urls('satellite', weekday))
    
    if not urls:
        return programs_dict
    
    # 创建会话对象
    session = requests.Session()
    
    # 抓取每个URL
    for url in urls:
        logger.info(f"正在抓取 {url}")
        response = make_request(url, session=session)
        
        if not response:
            continue
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 提取节目项
        program_items = fetch_program_items(soup)
        
        # 按频道分组
        for channel_name, program in program_items:
            if channel_name not in programs_dict:
                programs_dict[channel_name] = []
            programs_dict[channel_name].append(program)
        
        # 添加适当延迟
        time.sleep(1)
    
    # 去重和排序
    for channel_name in programs_dict:
        # 1. 首先进行基本去重：使用时间和纯标题作为唯一标识
        seen = set()
        unique_programs = []
        
        for prog in programs_dict[channel_name]:
            key = f"{prog['time']}_{prog['title']}"
            if key not in seen:
                seen.add(key)
                unique_programs.append(prog)
        
        # 2. 按时间排序
        unique_programs.sort(key=lambda x: x['time'])
        
        # 3. 进一步优化：只保留每个时间点的一个节目（防止同一时间点多个节目）
        time_map = {}
        for prog in unique_programs:
            # 只保留每个时间点的第一个节目
            if prog['time'] not in time_map:
                time_map[prog['time']] = prog
        
        # 转换回列表
        time_unique_programs = list(time_map.values())
        
        # 4. 再次按时间排序
        time_unique_programs.sort(key=lambda x: x['time'])
        
        # 5. 最后优化：限制每个频道每天的节目数量（最多48个，每小时2个）
        max_programs = 48
        if len(time_unique_programs) > max_programs:
            logger.warning(f"频道 {channel_name} 节目数量过多 ({len(time_unique_programs)} 个)，限制为 {max_programs} 个")
            # 只保留前48个节目（按时间排序后的）
            final_programs = time_unique_programs[:max_programs]
        else:
            final_programs = time_unique_programs
        
        logger.info(f"频道 {channel_name} 最终节目数量：{len(final_programs)} 个")
        programs_dict[channel_name] = final_programs
    
    logger.info(f"{channel_type}频道节目单抓取完成，共获取到 {len(programs_dict)} 个频道")
    return programs_dict

def generate_xmltv(programs_dict):
    """生成XMLTV格式的EPG文件"""
    today = datetime.now().strftime('%Y%m%d')
    
    # 创建XML内容
    xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<tv generator-info-name="TVMao EPG Generator" generator-info-url="https://www.tvmao.com/">
'''
    
    # 统计节目数量
    total_programs = 0
    
    for channel_name, programs in programs_dict.items():
        # 生成频道ID（使用频道名的拼音或缩写）
        channel_id = channel_name.replace(' ', '_').replace('-', '_').replace(':', '_')
        
        # 添加频道信息
        xml_content += f'''
  <channel id="{channel_id}">
    <display-name>{channel_name}</display-name>
  </channel>
'''
        
        # 添加节目信息
        channel_program_count = 0
        for program in programs:
            time_str = program['time']
            title = program['title']
            
            # 构建开始时间
            start_time = f"{today}{time_str.replace(':', '')}00"
            
            try:
                if 'end_time' in program:
                    # 使用实际的结束时间
                    end_time_str = f"{today}{program['end_time'].replace(':', '')}00"
                else:
                    # 简单处理：假设每个节目持续30分钟
                    hour, minute = map(int, time_str.split(':'))
                    end_time = datetime.combine(datetime.now().date(), datetime.min.time()) + timedelta(hours=hour, minutes=minute+30)
                    end_time_str = end_time.strftime(f"{today}%H%M00")
                
                # 添加节目
                xml_content += f'''\n  <programme channel="{channel_id}" start="{start_time}" stop="{end_time_str}">
    <title lang="zh">{title}</title>
  </programme>\n'''
                channel_program_count += 1
                total_programs += 1
            except Exception as e:
                # 如果时间解析失败，记录日志并继续
                logger.warning(f"解析节目时间失败，跳过节目: {title}, 时间: {time_str}, 错误: {e}")
                continue
        
        logger.info(f"为频道 {channel_name} 生成了 {channel_program_count} 个节目元素")
    
    logger.info(f"共生成了 {total_programs} 个节目元素")
    xml_content += '''
</tv>
'''
    
    return xml_content

def main():
    """主函数"""
    logger.info("开始从tvmao.com提取节目单...")
    
    programs_dict = {}
    
    # 抓取央视节目单
    logger.info("=== 开始抓取央视节目单 ===")
    cctv_programs = fetch_tvmao_programs('cctv')
    programs_dict.update(cctv_programs)
    
    # 抓取卫视频道节目单
    logger.info("\n=== 开始抓取卫视频道节目单 ===")
    satellite_programs = fetch_tvmao_programs('satellite')
    programs_dict.update(satellite_programs)
    
    logger.info(f"\n共提取到 {len(programs_dict)} 个频道的节目单")
    
    if programs_dict:
        # 生成XMLTV文件
        xmltv_content = generate_xmltv(programs_dict)
        
        # 保存到文件
        output_dir = 'output'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        today = datetime.now().strftime('%Y%m%d')
        output_file = os.path.join(output_dir, f'tvmao_epg_{today}.xml')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(xmltv_content)
        
        logger.info(f"节目单已保存到 {output_file}")
        
        # 打印统计信息
        total_programs = 0
        for channel_name, programs in programs_dict.items():
            program_count = len(programs)
            total_programs += program_count
            logger.info(f"  {channel_name}: {program_count} 个节目")
        
        logger.info(f"共提取到 {total_programs} 个节目")
    else:
        logger.warning("未提取到任何节目单")

if __name__ == "__main__":
    main()
