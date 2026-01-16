import requests
import logging
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from xml.dom import minidom
import time
import os
import re

# 配置日志 - 设置为DEBUG级别以获取更详细的信息
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入频道配置
from channels import CHANNELS

def make_request(url, headers=None, retry=2, delay=2):
    """带重试机制的HTTP请求"""
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

def fetch_tvmao_programs(soup, channel_name):
    """专门处理tvmao.com的节目抓取"""
    programs = []
    
    try:
        logger.info(f"开始解析tvmao.com节目页面")
        
        # 1. 查找tvmao.com最新的节目列表结构 - 基于实际页面分析
        # 节目列表通常在一个ul或div中，每个节目是一个li元素
        # 查找所有可能的节目项li元素
        program_items = soup.find_all('li', class_=['bg_f7', 'bg_f3', ''])  # 匹配不同的背景色class
        logger.info(f"找到 {len(program_items)} 个li节目项")
        
        # 遍历所有li元素，寻找包含节目信息的项
        for item in program_items:
            try:
                # tvmao.com的节目项结构：
                # <li class="bg_f7">
                #   <div class="over_hide">
                #     <span class="am">07:00</span>
                #     <span class="p_show"><a title="节目名" href="...">节目名</a></span>
                #   </div>
                # </li>
                
                # 查找包含节目信息的div
                over_hide_div = item.find('div', class_='over_hide')
                if over_hide_div:
                    # 查找时间元素 - 使用class="am"或class="pm"
                    time_span = over_hide_div.find('span', class_=['am', 'pm'])
                    # 查找节目名称元素 - 在span.p_show内部的a标签中
                    p_show_span = over_hide_div.find('span', class_='p_show')
                    
                    if time_span and p_show_span:
                        name_a = p_show_span.find('a')
                        if name_a:
                            time_str = time_span.get_text(strip=True)
                            title_str = name_a.get_text(strip=True)
                            
                            if time_str and title_str and len(time_str) >= 4:
                                programs.append({'time': time_str, 'title': title_str})
                                logger.debug(f"找到节目: {time_str} - {title_str}")
            except Exception as e:
                logger.error(f"解析节目项失败: {e}")
        
        # 2. 如果没有找到，尝试另一种可能的结构
        if not programs:
            logger.info("尝试查找另一种tvmao.com节目结构")
            
            # 查找所有包含节目信息的元素组合
            all_am_spans = soup.find_all('span', class_=['am', 'pm'])
            logger.info(f"找到 {len(all_am_spans)} 个时间span元素")
            
            for time_span in all_am_spans:
                try:
                    # 查找相邻的p_show元素
                    p_show_span = time_span.find_next('span', class_='p_show')
                    
                    if p_show_span:
                        name_a = p_show_span.find('a')
                        if name_a:
                            time_str = time_span.get_text(strip=True)
                            title_str = name_a.get_text(strip=True)
                            
                            if time_str and title_str and len(time_str) >= 4:
                                # 去重 - 防止重复添加
                                if not any(p['time'] == time_str and p['title'] == title_str for p in programs):
                                    programs.append({'time': time_str, 'title': title_str})
                                    logger.debug(f"找到节目: {time_str} - {title_str}")
                except Exception as e:
                    logger.error(f"解析时间-标题对失败: {e}")
        
        # 3. 尝试查找旧版结构作为备选
        if not programs:
            logger.info("尝试查找tvmao.com旧版节目结构")
            
            # 查找div.program_list
            program_list = soup.find('div', class_='program_list')
            if program_list:
                logger.info(f"找到div.program_list结构")
                program_items = program_list.find_all('li')
                
                for item in program_items:
                    try:
                        time_elem = item.find('span', class_='time')
                        title_elem = item.find('a', class_='name')
                        
                        if time_elem and title_elem:
                            time_str = time_elem.get_text(strip=True)
                            title_str = title_elem.get_text(strip=True)
                            
                            if time_str and title_str and len(time_str) >= 4:
                                programs.append({'time': time_str, 'title': title_str})
                                logger.debug(f"找到节目: {time_str} - {title_str}")
                    except Exception as e:
                        logger.error(f"解析旧版节目项失败: {e}")
        
        logger.info(f"tvmao.com节目解析完成，共找到 {len(programs)} 个节目")
        
    except Exception as e:
        logger.error(f"解析tvmao.com节目失败: {e}", exc_info=True)
    
    return programs

def fetch_cctv_programs(channel_id, channel_info):
    """抓取央视节目信息"""
    programs = []
    channel_name = channel_info['name']
    
    try:
        # 替换URL中的星期参数
        today = datetime.now()
        weekday = today.weekday() + 1  # 转换为1-7（1=周一）
        
        # 收集所有tvmao.com URL，优先使用
        all_urls = []
        
        # 检查主URL是否为tvmao.com
        main_url = channel_info['url'].replace('w1', f'w{weekday}')
        if 'tvmao.com' in main_url:
            all_urls.append(('主URL', main_url))
        
        # 收集所有tvmao.com备用URL
        if channel_info.get('backup_urls'):
            for backup_url in channel_info['backup_urls']:
                backup_url_with_weekday = backup_url.replace('w1', f'w{weekday}')
                if 'tvmao.com' in backup_url_with_weekday:
                    all_urls.append(('备用URL', backup_url_with_weekday))
        
        # 如果没有tvmao.com URL，添加所有可用URL
        if not all_urls:
            all_urls.append(('主URL', main_url))
            if channel_info.get('backup_urls'):
                for backup_url in channel_info['backup_urls']:
                    all_urls.append(('备用URL', backup_url.replace('w1', f'w{weekday}')))
        
        logger.info(f"优先使用tvmao.com抓取{channel_name}节目")
        
        # 尝试所有URL，最多尝试2个
        for url_type, url in all_urls[:2]:  # 最多尝试2个URL
            logger.info(f"{url_type}抓取{channel_name}节目，URL: {url}")
            response = make_request(url)
            
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 检查是否为tvmao.com URL
                if 'tvmao.com' in url:
                    logger.info(f"使用tvmao.com专用解析器")
                    programs = fetch_tvmao_programs(soup, channel_name)
                else:
                    logger.info(f"使用通用解析器")
                    # 通用解析逻辑
                    selectors = [
                        '.epg-list .epg-item',
                        '.program-list .program-item',
                        'div[class*="epg"] div[class*="item"]',
                        '.epg-item',
                        '.program-item'
                    ]
                    
                    for selector in selectors:
                        program_elements = soup.select(selector)
                        if program_elements:
                            logger.info(f"使用选择器 {selector} 找到 {len(program_elements)} 个节目元素")
                            for item in program_elements:
                                try:
                                    time_elem = item.select_one('.time') or item.select_one('.program-time') or item.select_one('[class*="time"]') or item.find('span')
                                    title_elem = item.select_one('.title') or item.select_one('.program-title') or item.select_one('[class*="title"]') or item.find('a')
                                    
                                    if time_elem and title_elem:
                                        time_str = time_elem.get_text(strip=True)
                                        title = title_elem.get_text(strip=True)
                                        if time_str and title and len(time_str) >= 4:
                                            programs.append({'time': time_str, 'title': title})
                                except Exception as e:
                                    logger.error(f"解析节目元素失败: {e}")
                            break
                
                # 如果获取到节目，停止尝试
                if programs:
                    logger.info(f"成功获取{len(programs)}个节目")
                    break
    except Exception as e:
        logger.error(f"抓取{channel_name}节目失败: {e}", exc_info=True)
    
    if not programs:
        logger.warning(f"   未获取到节目信息")
    
    return programs

def fetch_satellite_programs(channel_id, channel_info):
    """抓取卫视频道节目信息"""
    programs = []
    channel_name = channel_info['name']
    
    try:
        # 替换URL中的星期参数
        today = datetime.now()
        weekday = today.weekday() + 1  # 转换为1-7（1=周一）
        
        # 收集所有tvmao.com URL，优先使用
        all_urls = []
        
        # 检查主URL是否为tvmao.com
        main_url = channel_info['url'].replace('w1', f'w{weekday}')
        if 'tvmao.com' in main_url:
            all_urls.append(('主URL', main_url))
        
        # 收集所有tvmao.com备用URL
        if channel_info.get('backup_urls'):
            for backup_url in channel_info['backup_urls']:
                backup_url_with_weekday = backup_url.replace('w1', f'w{weekday}')
                if 'tvmao.com' in backup_url_with_weekday:
                    all_urls.append(('备用URL', backup_url_with_weekday))
        
        # 如果没有tvmao.com URL，添加所有可用URL
        if not all_urls:
            all_urls.append(('主URL', main_url))
            if channel_info.get('backup_urls'):
                for backup_url in channel_info['backup_urls']:
                    all_urls.append(('备用URL', backup_url.replace('w1', f'w{weekday}')))
        
        logger.info(f"优先使用tvmao.com抓取{channel_name}节目")
        
        # 尝试所有URL，最多尝试2个
        for url_type, url in all_urls[:2]:  # 最多尝试2个URL
            logger.info(f"{url_type}抓取{channel_name}节目，URL: {url}")
            response = make_request(url)
            
            if response:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 检查是否为tvmao.com URL
                if 'tvmao.com' in url:
                    logger.info(f"使用tvmao.com专用解析器")
                    programs = fetch_tvmao_programs(soup, channel_name)
                else:
                    logger.info(f"使用通用解析器")
                    # 通用解析逻辑
                    selectors = [
                        '.program-item',
                        '.epg-item',
                        'div[class*="program"]',
                        'div[class*="epg"]'
                    ]
                    
                    for selector in selectors:
                        program_elements = soup.select(selector)
                        if program_elements:
                            logger.info(f"找到 {len(program_elements)} 个节目元素")
                            for item in program_elements:
                                try:
                                    time_elem = item.select_one('.time') or item.select_one('.program-time') or item.select_one('[class*="time"]')
                                    title_elem = item.select_one('.title') or item.select_one('.program-title') or item.select_one('[class*="title"]')
                                    
                                    if time_elem and title_elem:
                                        time_str = time_elem.get_text(strip=True)
                                        title = title_elem.get_text(strip=True)
                                        if time_str and title:
                                            programs.append({'time': time_str, 'title': title})
                                except Exception as e:
                                    logger.error(f"解析节目元素失败: {e}")
                            break
                
                # 如果获取到节目，停止尝试
                if programs:
                    logger.info(f"成功获取{len(programs)}个节目")
                    break
    except Exception as e:
        logger.error(f"抓取{channel_name}节目失败: {e}", exc_info=True)
    
    if not programs:
        logger.warning(f"   未获取到节目信息")
    
    return programs

def generate_xmltv(programs_dict):
    """生成XMLTV格式的EPG文件"""
    today = datetime.now().strftime('%Y%m%d')
    
    # 创建根元素
    tv = ET.Element('tv')
    tv.set('generator-info-name', 'EPGO Generator')
    tv.set('generator-info-url', 'https://github.com/yourusername/epgo')
    
    for channel_id, channel_data in programs_dict.items():
        channel_name = channel_data['name']
        channel_programs = channel_data['programs']
        
        # 创建频道元素
        channel = ET.SubElement(tv, 'channel')
        channel.set('id', channel_id)
        
        # 添加频道名称
        display_name = ET.SubElement(channel, 'display-name')
        display_name.text = channel_name
        
        # 添加频道节目
        for program in channel_programs:
            # 创建节目元素
            programme = ET.SubElement(tv, 'programme')
            programme.set('channel', channel_id)
            
            # 构建开始和结束时间
            start_time = f"{today}{program['time'].replace(':', '')}00"
            
            # 简单处理：假设每个节目持续30分钟
            end_hour = int(program['time'].split(':')[0])
            end_minute = int(program['time'].split(':')[1]) + 30
            if end_minute >= 60:
                end_hour += 1
                end_minute -= 60
            end_time = f"{today}{end_hour:02d}{end_minute:02d}00"
            
            programme.set('start', start_time)
            programme.set('stop', end_time)
            
            # 添加节目标题
            title = ET.SubElement(programme, 'title')
            title.set('lang', 'zh')
            title.text = program['title']
    
    # 生成XML字符串
    rough_string = ET.tostring(tv, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")
    
    return pretty_xml

def main():
    """主函数"""
    logger.info("开始生成EPG...")
    
    programs_dict = {}
    
    # 只测试CCTV1频道，加快测试速度
    test_channel_id = "CCTV1"
    if test_channel_id in CHANNELS:
        channel_info = CHANNELS[test_channel_id]
        logger.info(f"正在测试抓取 {channel_info['name']}...")
        programs = fetch_cctv_programs(test_channel_id, channel_info)
        programs_dict[test_channel_id] = {
            'name': channel_info['name'],
            'programs': programs
        }
    
    # 生成XMLTV文件
    xmltv_content = generate_xmltv(programs_dict)
    
    # 保存到文件
    output_dir = 'output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    today = datetime.now().strftime('%Y%m%d')
    output_file = os.path.join(output_dir, f'epg_{today}.xml')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(xmltv_content)
    
    logger.info(f"EPG生成完成，保存到 {output_file}")
    logger.info(f"共处理 {len(programs_dict)} 个频道")
    
    # 统计成功抓取的节目数量
    total_programs = 0
    for channel_id, channel_data in programs_dict.items():
        program_count = len(channel_data['programs'])
        total_programs += program_count
        if program_count == 0:
            logger.warning(f"频道 {channel_data['name']} 未抓取到任何节目")
    
    logger.info(f"共抓取 {total_programs} 个节目")

if __name__ == "__main__":
    main()
