import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime, timedelta
import os
import time
import re

# 导入频道名称映射表
from channel_mapping import normalize_channel_name

# 配置日志 - 设置为INFO级别，生产环境可改为INFO
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加文件日志记录
file_handler = logging.FileHandler('tvmao_epg.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

def make_request(url, session=None, headers=None, retry=3, delay=2):
    """带重试机制的HTTP请求，支持会话保持"""
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
    """获取当前是一周的第几天（1-7，周一为1）"""
    return datetime.now().weekday() + 1

def generate_time_slots():
    """生成时间槽列表，从0到22，间隔2"""
    return list(range(0, 24, 2))

def generate_urls(base_url, channel_type, weekday=None):
    """生成所有需要抓取的URL列表"""
    urls = []
    
    # 如果没有指定星期几，使用当前星期几
    if weekday is None:
        weekday = get_current_weekday()
    
    # 生成时间槽
    time_slots = generate_time_slots()
    
    # 构建基础URL前缀
    if channel_type == 'cctv':
        url_prefix = "https://a-s1.tvmao.com/program/duration/cctv/"
    elif channel_type == 'satellite':
        url_prefix = "https://a-s1.tvmao.com/program/duration/satellite/"
    else:
        logger.error(f"不支持的频道类型: {channel_type}")
        return urls
    
    # 生成所有URL
    for slot in time_slots:
        url = f"{url_prefix}w{weekday}-h{slot}.html"
        urls.append(url)
    
    logger.info(f"为{channel_type}频道生成了 {len(urls)} 个URL")
    return urls

def parse_program_item(item, channel_name):
    """解析单个节目项"""
    try:
        # 提取时间和标题
        time_elem = item.find('span', class_=['time', 'program-time'])
        title_elem = item.find('span', class_=['title', 'program-title'])
        
        if time_elem and title_elem:
            time_str = time_elem.text.strip()
            title = title_elem.text.strip()
            
            if time_str and title:
                return {'time': time_str, 'title': title}
        
        # 尝试另一种结构
        time_text = item.find(text=re.compile(r'^\d{2}:\d{2}$'))
        if time_text:
            time_str = time_text.strip()
            title_elem = time_text.find_next_sibling()
            if title_elem:
                title = title_elem.text.strip()
                if title:
                    return {'time': time_str, 'title': title}
        
        return None
    except Exception as e:
        logger.error(f"解析节目项失败: {e}", exc_info=True)
        return None

def fetch_program_items(soup):
    """从页面中提取节目列表"""
    programs = []
    
    try:
        # 查找所有节目项
        program_items = soup.find_all(['li', 'div'], class_=lambda cls: cls and ('program' in cls or 'epg' in cls or 'item' in cls))
        logger.info(f"找到 {len(program_items)} 个节目项")
        
        # 解析每个节目项
        for item in program_items:
            # 尝试提取频道名称
            channel_name = item.find(['span', 'div'], class_=lambda cls: cls and ('channel' in cls or 'tv' in cls))
            channel_name = channel_name.text.strip() if channel_name else "未知频道"
            
            # 标准化频道名称
            standard_channel_name = normalize_channel_name(channel_name)
            
            # 解析节目
            program = parse_program_item(item, standard_channel_name)
            if program:
                programs.append((standard_channel_name, program))
        
        # 如果没有找到节目项，尝试查找表格结构
        if not programs:
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        channel_name = cells[0].text.strip() if len(cells) > 2 else "未知频道"
                        time_str = cells[-2].text.strip() if len(cells) > 2 else cells[0].text.strip()
                        title = cells[-1].text.strip()
                        
                        # 标准化频道名称
                        standard_channel_name = normalize_channel_name(channel_name)
                        
                        if time_str and title and ':' in time_str:
                            programs.append((standard_channel_name, {'time': time_str, 'title': title}))
        
        logger.info(f"成功解析 {len(programs)} 个节目")
    except Exception as e:
        logger.error(f"提取节目列表失败: {e}", exc_info=True)
    
    return programs

def fetch_tvmao_programs(channel_type, weekday=None):
    """抓取tvmao.com的节目单"""
    programs_dict = {}
    
    # 生成所有需要抓取的URL
    urls = generate_urls(None, channel_type, weekday)
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
        # 去重
        seen = set()
        unique_programs = []
        for prog in programs_dict[channel_name]:
            key = f"{prog['time']}_{prog['title']}"
            if key not in seen:
                seen.add(key)
                unique_programs.append(prog)
        
        # 按时间排序
        unique_programs.sort(key=lambda x: x['time'])
        
        programs_dict[channel_name] = unique_programs
    
    logger.info(f"{channel_type}频道节目单抓取完成，共获取到 {len(programs_dict)} 个频道")
    return programs_dict

def generate_xmltv(programs_dict):
    """生成XMLTV格式的EPG文件"""
    today = datetime.now().strftime('%Y%m%d')
    
    # 创建XML内容
    xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<tv generator-info-name="TVMao EPG Generator" generator-info-url="https://www.tvmao.com/">
'''
    
    for channel_name, programs in programs_dict.items():
        # 生成频道ID（使用频道名的拼音或缩写）
        channel_id = channel_name.replace(' ', '_').replace('-', '_').replace(':', '_')
        
        # 添加频道信息
        xml_content += f'''\n  <channel id="{channel_id}">
    <display-name>{channel_name}</display-name>
  </channel>
'''
        
        # 添加节目信息
        for program in programs:
            time_str = program['time']
            title = program['title']
            
            # 构建开始时间
            start_time = f"{today}{time_str.replace(':', '')}00"
            
            # 简单处理：假设每个节目持续30分钟
            try:
                hour, minute = map(int, time_str.split(':'))
                end_time = datetime.combine(datetime.now().date(), datetime.min.time()) + timedelta(hours=hour, minutes=minute+30)
                end_time_str = end_time.strftime(f"{today}%H%M00")
            except:
                # 如果时间解析失败，跳过该节目
                continue
            
            # 添加节目
            xml_content += f'''\n  <programme channel="{channel_id}" start="{start_time}" stop="{end_time_str}">
    <title lang="zh">{title}</title>
  </programme>
'''
    
    xml_content += '''\n</tv>\n'''
    
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
