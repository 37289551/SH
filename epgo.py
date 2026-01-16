
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import time
import logging
import gzip
from channels import CHANNELS

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('epg_generator.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 最大重试次数
MAX_RETRIES = 3
# 重试间隔（秒）
RETRY_DELAY = 3


def make_request(url, headers=None, timeout=15):
    """带重试机制的HTTP请求函数"""
    if headers is None:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    for retry in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()  # 检查HTTP状态码
            return response
        except requests.RequestException as e:
            if retry < MAX_RETRIES - 1:
                logger.warning(f"请求失败，{RETRY_DELAY}秒后重试 ({retry+1}/{MAX_RETRIES}): {e}")
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"请求失败，已达到最大重试次数: {e}")
                raise

def fetch_cctv_programs(channel_id, channel_info):
    """抓取央视频道节目单"""
    try:
        response = make_request(channel_info['url'])
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'lxml')
        
        programs = []
        today = datetime.now().date()
        
        # 适配CCTV网站实际结构 - CCTV节目单通常在特定的表格或列表中
        # 尝试多种可能的选择器
        program_containers = [
            soup.find('div', class_='epg-container'),
            soup.find('div', id='epg-content'),
            soup.find('div', class_='program-list'),
            soup.find('table', class_='epg-table')
        ]
        
        program_items = []
        for container in program_containers:
            if container:
                # 表格结构
                if container.name == 'table':
                    rows = container.find_all('tr')[1:]  # 跳过表头
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 2:
                            time_elem = cells[0]
                            title_elem = cells[1]
                            program_items.append((time_elem, title_elem))
                else:
                    # 列表结构
                    items = container.find_all(['div', 'li'], recursive=True)
                    for item in items:
                        time_elem = item.find(['span', 'div'], class_=['time', 'program-time', 'epg-time'])
                        title_elem = item.find(['span', 'div'], class_=['title', 'program-title', 'epg-title'])
                        if time_elem and title_elem:
                            program_items.append((time_elem, title_elem))
                break
        
        # 如果没有找到，尝试直接搜索所有可能的节目项
        if not program_items:
            program_items = []
            all_divs = soup.find_all('div')
            for div in all_divs:
                time_elem = div.find(['span', 'div'], string=lambda text: text and ':' in text)
                if time_elem:
                    title_elem = div.find_next(['span', 'div'], class_=['title', 'program'])
                    if title_elem:
                        program_items.append((time_elem, title_elem))
        
        for time_elem, title_elem in program_items:
            time_str = time_elem.get_text().strip()
            title = title_elem.get_text().strip()
            
            # 清理时间字符串，只保留HH:MM格式
            time_str = ''.join(c for c in time_str if c.isdigit() or c == ':')
            
            # 解析时间格式
            try:
                if ':' in time_str:
                    hour, minute = map(int, time_str.split(':'))
                    # 处理24小时制和00:00的情况
                    if hour >= 24:
                        hour = 0
                    program_time = datetime.combine(today, datetime.min.time().replace(hour=hour, minute=minute))
                    programs.append({
                        'start': program_time,
                        'title': title,
                        'description': f"{channel_info['name']}节目"
                    })
            except Exception as parse_error:
                logger.warning(f"解析{channel_id}节目时间失败: {parse_error}, 时间字符串: {time_str}")
                continue
        
        return programs
    except requests.RequestException as e:
        logger.error(f"请求{channel_id}失败: {e}")
        return []
    except Exception as e:
        logger.error(f"抓取{channel_id}失败: {e}")
        return []

def fetch_satellite_programs(channel_id, channel_info):
    """抓取卫视频道节目单"""
    try:
        response = make_request(channel_info['url'])
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'lxml')
        
        programs = []
        today = datetime.now().date()
        
        url = channel_info['url']
        
        # 针对不同网站的特殊处理
        site_specific_handlers = {
            'hunantv.com': lambda soup: soup.find_all('div', class_='epg-item'),
            'zjtv.com': lambda soup: soup.find_all('li', class_='program-item'),
            'jstv.com': lambda soup: soup.find_all('tr', class_='epg-row'),
            'dragontv.com': lambda soup: soup.find_all('div', class_='program-block'),
            'btv.com': lambda soup: soup.find_all('div', class_='btv-epg-item'),
            'gdtv.com': lambda soup: soup.find_all('li', class_='gdtv-epg-item'),
            'sztv.com': lambda soup: soup.find_all('div', class_='sztv-program-item'),
            'ahtv.com': lambda soup: soup.find_all('tr', class_='ahtv-epg-row'),
            'sdws.tv': lambda soup: soup.find_all('div', class_='sd-epg-item'),
            'tjtv.com': lambda soup: soup.find_all('li', class_='tjtv-program-item')
        }
        
        program_items = []
        
        # 尝试网站特定处理
        for domain, handler in site_specific_handlers.items():
            if domain in url:
                program_items = handler(soup)
                break
        
        # 如果没有网站特定处理或处理结果为空，尝试通用选择器
        if not program_items:
            # 尝试多种通用选择器
            common_selectors = [
                ('div', ['epg-item', 'program-item', 'program-list-item', 'epg-row']),
                ('li', ['program', 'epg-item', 'program-item']),
                ('tr', ['epg-row', 'program-row']),
                ('div', ['program-block', 'program-container'])
            ]
            
            for tag, classes in common_selectors:
                items = soup.find_all(tag, class_=classes)
                if items:
                    program_items = items
                    break
        
        # 如果仍然没有找到，尝试从表格中提取
        if not program_items:
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')[1:]  # 跳过表头
                if rows:
                    program_items = rows
                    break
        
        # 处理提取到的节目项
        for item in program_items:
            time_elem = None
            title_elem = None
            
            # 根据不同标签类型采用不同的提取策略
            if item.name == 'tr':
                # 表格行
                cells = item.find_all('td')
                if len(cells) >= 2:
                    time_elem = cells[0]
                    title_elem = cells[1]
            else:
                # 其他标签类型
                time_elem = item.find(['span', 'div'], class_=['time', 'epg-time', 'program-time', 'time-info'])
                title_elem = item.find(['span', 'div'], class_=['title', 'epg-title', 'program-title', 'program-name'])
                
                # 如果没有找到，尝试直接在元素内搜索时间和标题文本
                if not time_elem:
                    time_elem = item.find(string=lambda text: text and ':' in text)
                    if time_elem:
                        time_elem = time_elem.parent
            
            if time_elem and title_elem:
                time_str = time_elem.get_text().strip()
                title = title_elem.get_text().strip()
                
                # 清理时间字符串
                time_str = ''.join(c for c in time_str if c.isdigit() or c == ':')
                
                # 解析时间
                try:
                    if ':' in time_str:
                        hour, minute = map(int, time_str.split(':'))
                        # 处理24小时制
                        if hour >= 24:
                            hour = 0
                        program_time = datetime.combine(today, datetime.min.time().replace(hour=hour, minute=minute))
                        programs.append({
                            'start': program_time,
                            'title': title,
                            'description': f"{channel_info['name']}节目"
                        })
                except Exception as parse_error:
                logger.warning(f"解析{channel_id}节目时间失败: {parse_error}, 时间字符串: {time_str}")
                continue
        
        return programs
    except requests.RequestException as e:
        logger.error(f"请求{channel_id}失败: {e}")
        return []
    except Exception as e:
        logger.error(f"抓取{channel_id}失败: {e}")
        return []

def create_xmltv_epg(channels_data):
    """创建XMLTV格式EPG文件，同时生成标准XML和.gz压缩文件"""
    root = ET.Element("tv")
    root.set("generator-info-name", "GitHub EPG Generator")
    root.set("generator-info-url", "https://github.com")
    
    # 添加频道信息
    for channel_id, channel_info in CHANNELS.items():
        channel_elem = ET.SubElement(root, "channel")
        channel_elem.set("id", channel_id)
        
        display_name = ET.SubElement(channel_elem, "display-name")
        display_name.set("lang", "zh")
        display_name.text = channel_info['name']
        
        icon = ET.SubElement(channel_elem, "icon")
        icon.set("src", f"https://example.com/icons/{channel_id.lower()}.png")
    
    # 添加节目信息
    for channel_id, programs in channels_data.items():
        for i, program in enumerate(programs):
            programme = ET.SubElement(root, "programme")
            
            # 计算结束时间
            if i < len(programs) - 1:
                end_time = programs[i+1]['start']
            else:
                # 最后一个节目到第二天0点
                end_time = datetime.combine(program['start'].date() + timedelta(days=1), datetime.min.time())
            
            programme.set("start", program['start'].strftime("%Y%m%d%H%M%S +0800"))
            programme.set("stop", end_time.strftime("%Y%m%d%H%M%S +0800"))
            programme.set("channel", channel_id)
            
            title = ET.SubElement(programme, "title")
            title.set("lang", "zh")
            title.text = program['title']
            
            if program.get('description'):
                desc = ET.SubElement(programme, "desc")
                desc.set("lang", "zh")
                desc.text = program['description']
    
    # 保存XML文件
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0)
    tree.write("epg.xml", encoding="utf-8", xml_declaration=True)
    logger.info("EPG文件生成完成: epg.xml")
    
    # 生成.gz压缩文件
    # 先将XML树转换为字符串
    xml_str = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    with gzip.open("epg.xml.gz", "wb") as f:
        f.write(xml_str)
    logger.info("EPG压缩文件生成完成: epg.xml.gz")

def main():
    """主函数"""
    logger.info("开始生成EPG...")
    
    channels_data = {}
    
    # 抓取央视频道
    for channel_id, channel_info in CHANNELS.items():
        logger.info(f"正在抓取 {channel_info['name']}...")
        if channel_info['source'] == 'cctv':
            programs = fetch_cctv_programs(channel_id, channel_info)
        else:
            programs = fetch_satellite_programs(channel_id, channel_info)
        
        if programs:
            # 按时间排序
            programs.sort(key=lambda x: x['start'])
            channels_data[channel_id] = programs
            logger.info(f"  成功获取 {len(programs)} 个节目")
        else:
            logger.warning(f"  未获取到节目信息")
    
    # 生成XMLTV文件
    if channels_data:
        create_xmltv_epg(channels_data)
    else:
        logger.error("未获取到任何频道数据")

if __name__ == "__main__":
    main()
