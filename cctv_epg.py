import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime, timedelta
import os
import time

# 导入频道名称映射表
from channel_mapping import normalize_channel_name

# 配置日志 - 设置为INFO级别，生产环境可改为INFO
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加文件日志记录
file_handler = logging.FileHandler('cctv_epg.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

def make_request(url, session=None, headers=None, retry=3, delay=2):
    """带重试机制的HTTP请求，支持会话保持"""
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://tv.cctv.com/',
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

def fetch_cctv_channels():
    """获取CCTV所有频道列表"""
    # 已知的CCTV频道列表（作为备用）
    known_cctv_channels = [
        "CCTV-1 综合", "CCTV-2 财经", "CCTV-3 综艺", "CCTV-4 中文国际",
        "CCTV-5 体育", "CCTV-5+ 体育赛事", "CCTV-6 电影", "CCTV-7 国防军事",
        "CCTV-8 电视剧", "CCTV-9 纪录", "CCTV-10 科教", "CCTV-11 戏曲",
        "CCTV-12 社会与法", "CCTV-13 新闻", "CCTV-14 少儿", "CCTV-15 音乐",
        "CCTV-16 奥林匹克", "CCTV-17 农业农村"
    ]
    
    base_url = "https://tv.cctv.com/epg/index.shtml"
    channels = []
    
    # 创建会话对象，保持Cookie
    session = requests.Session()
    response = make_request(base_url, session=session)
    
    try:
        if response:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找频道列表，央视网频道通常在特定的导航或列表中
            # 尝试多种可能的选择器
            channel_selectors = [
                '.channel-list a',
                '.cctv-channel a',
                'a[href*="/epg/"]',
                'a[title*="CCTV"]',
                '#channel-nav a',
                'li > a[href*="/epg/"]',
                '.nav a',
                '.menu a'
            ]
            
            found_channels = []
            for selector in channel_selectors:
                channel_links = soup.select(selector)
                if channel_links:
                    found_channels = channel_links
                    logger.info(f"使用选择器 {selector} 找到 {len(channel_links)} 个频道链接")
                    break
            
            if not found_channels:
                # 尝试查找所有包含CCTV的链接
                all_links = soup.find_all('a')
                found_channels = [link for link in all_links if 'CCTV' in link.text or '央视' in link.text]
                logger.info(f"通过文本匹配找到 {len(found_channels)} 个CCTV频道链接")
            
            # 提取唯一的频道信息
            unique_channels = {}
            for link in found_channels:
                channel_name = link.text.strip()
                if not channel_name or len(channel_name) < 3:
                    continue
                
                channel_href = link.get('href', '')
                if not channel_href:
                    continue
                
                # 确保是完整URL
                if not channel_href.startswith('http'):
                    if channel_href.startswith('/'):
                        channel_href = f"https://tv.cctv.com{channel_href}"
                    else:
                        channel_href = f"https://tv.cctv.com/{channel_href}"
                
                # 只保留CCTV相关频道
                if 'CCTV' in channel_name or '央视' in channel_name:
                    unique_channels[channel_name] = channel_href
            
            # 转换为列表格式
            channels = [{"name": name, "url": url} for name, url in unique_channels.items()]
            logger.info(f"从网页共获取到 {len(channels)} 个唯一的CCTV频道")
        
        # 如果从网页获取的频道数量不足，使用已知频道列表作为补充
        if len(channels) < 5:
            logger.info("从网页获取的频道数量不足，使用已知频道列表作为补充")
            # 为已知频道生成标准的EPG URL
            for channel_name in known_cctv_channels:
                # 检查频道是否已存在
                channel_exists = any(channel["name"] in channel_name or channel_name in channel["name"] for channel in channels)
                if not channel_exists:
                    # 生成频道的EPG URL
                    # 提取频道号，如 "CCTV-1" 或 "CCTV-5+"
                    if "CCTV-" in channel_name:
                        channel_code = channel_name.split()[0]
                        # 替换 "CCTV-" 为 "epg/index_" 生成URL
                        url_code = channel_code.replace("CCTV-", "epg/index_")
                        # 处理CCTV-5+的特殊情况
                        url_code = url_code.replace("5+", "5p")
                        channel_url = f"https://tv.cctv.com/{url_code}.shtml"
                        channels.append({"name": channel_name, "url": channel_url})
        
        # 去重
        unique_channels_dict = {}
        for channel in channels:
            # 使用标准化名称作为键去重
            standard_name = normalize_channel_name(channel["name"])
            if standard_name not in unique_channels_dict:
                unique_channels_dict[standard_name] = channel
        
        # 转换回列表
        channels = list(unique_channels_dict.values())
        logger.info(f"最终获取到 {len(channels)} 个唯一的CCTV频道")
        
        # 排序频道，便于后续处理
        channels.sort(key=lambda x: x["name"])
        
    except Exception as e:
        logger.error(f"解析CCTV频道列表失败: {e}", exc_info=True)
        # 如果解析失败，直接使用已知频道列表
        logger.info("解析失败，直接使用已知频道列表")
        channels = []
        for channel_name in known_cctv_channels:
            if "CCTV-" in channel_name:
                channel_code = channel_name.split()[0]
                url_code = channel_code.replace("CCTV-", "epg/index_")
                url_code = url_code.replace("5+", "5p")
                channel_url = f"https://tv.cctv.com/{url_code}.shtml"
                channels.append({"name": channel_name, "url": channel_url})
    
    return channels, session

def fetch_channel_programs(channel, session):
    """获取单个频道的节目单"""
    channel_name = channel["name"]
    channel_url = channel["url"]
    
    # 标准化频道名称
    standard_channel_name = normalize_channel_name(channel_name)
    programs = []
    
    logger.info(f"正在提取 {channel_name} (标准化: {standard_channel_name}) 的节目单: {channel_url}")
    
    # 请求频道节目单页面
    response = make_request(channel_url, session=session)
    if not response:
        return programs
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    try:
        # 尝试多种方式提取节目单
        
        # 1. 查找节目表格（最常见的形式）
        program_tables = soup.find_all('table')
        for table in program_tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    time_str = cells[0].text.strip()
                    title = cells[1].text.strip()
                    if time_str and title and ':' in time_str:
                        programs.append({'time': time_str, 'title': title})
        
        # 2. 如果表格没找到，尝试查找包含节目信息的div
        if not programs:
            program_containers = soup.find_all('div', class_=lambda cls: cls and ('program' in cls or 'epg' in cls or 'schedule' in cls))
            for container in program_containers:
                program_items = container.find_all('div', recursive=False)
                for item in program_items:
                    time_elem = item.find(class_=lambda cls: cls and ('time' in cls or 'schedule-time' in cls))
                    title_elem = item.find(class_=lambda cls: cls and ('title' in cls or 'program-title' in cls))
                    
                    if time_elem and title_elem:
                        time_str = time_elem.text.strip()
                        title = title_elem.text.strip()
                        if time_str and title:
                            programs.append({'time': time_str, 'title': title})
        
        # 3. 如果还是没找到，尝试从文本中直接提取
        if not programs:
            content = soup.text
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line and len(line) >= 5 and ':' in line[:5]:
                    time_str = line[:5]
                    title = line[5:].strip()
                    if time_str and title:
                        programs.append({'time': time_str, 'title': title})
        
        # 4. 尝试查找特定的节目列表结构
        if not programs:
            # 央视网可能使用特定的class命名节目项
            program_items = soup.find_all('div', class_=['epg-item', 'program-item', 'cctv-program'])
            for item in program_items:
                time_elem = item.find(class_=['item-time', 'program-time', 'time'])
                title_elem = item.find(class_=['item-title', 'program-title', 'title'])
                
                if time_elem and title_elem:
                    time_str = time_elem.text.strip()
                    title = title_elem.text.strip()
                    if time_str and title:
                        programs.append({'time': time_str, 'title': title})
        
        # 去重节目
        unique_programs = []
        seen = set()
        for prog in programs:
            key = f"{prog['time']}_{prog['title']}"
            if key not in seen:
                seen.add(key)
                unique_programs.append(prog)
        
        programs = unique_programs
        logger.info(f"  {standard_channel_name}: 成功提取 {len(programs)} 个节目")
        
    except Exception as e:
        logger.error(f"解析 {channel_name} 节目单失败: {e}", exc_info=True)
    
    # 添加适当延迟，避免请求过快
    time.sleep(1)
    
    return programs

def fetch_cctv_programs():
    """从CCTV官网提取所有央视频道节目单"""
    programs_dict = {}
    
    # 获取频道列表
    channels, session = fetch_cctv_channels()
    if not channels:
        logger.error("未能获取到CCTV频道列表")
        return programs_dict
    
    # 提取每个频道的节目单
    for channel in channels:
        channel_name = channel["name"]
        programs = fetch_channel_programs(channel, session)
        if programs:
            # 标准化频道名称
            standard_channel_name = normalize_channel_name(channel_name)
            programs_dict[standard_channel_name] = programs
    
    logger.info(f"CCTV节目单提取完成，共获取到 {len(programs_dict)} 个频道的节目单")
    return programs_dict

def generate_xmltv(programs_dict):
    """生成XMLTV格式的EPG文件"""
    today = datetime.now().strftime('%Y%m%d')
    
    # 创建XML内容
    xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<tv generator-info-name="CCTV EPG Generator" generator-info-url="https://tv.cctv.com/epg/">
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
    logger.info("开始从CCTV官网提取节目单...")
    
    # 抓取节目单
    programs_dict = fetch_cctv_programs()
    
    logger.info(f"共提取到 {len(programs_dict)} 个频道的节目单")
    
    if programs_dict:
        # 生成XMLTV文件
        xmltv_content = generate_xmltv(programs_dict)
        
        # 保存到文件
        output_dir = 'output'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        today = datetime.now().strftime('%Y%m%d')
        output_file = os.path.join(output_dir, f'cctv_epg_{today}.xml')
        
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
