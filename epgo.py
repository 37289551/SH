import logging
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from xml.dom import minidom
import time
import os
import yaml
import gzip
import shutil
import difflib

# 默认配置文件路径
DEFAULT_CONFIG_PATH = "config.yaml"

# 读取配置文件
def load_config(config_path=DEFAULT_CONFIG_PATH):
    """
    读取配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        dict: 配置字典
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        logger.error(f"配置文件未找到: {config_path}")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"解析配置文件失败: {e}")
        return {}

# 加载配置
CONFIG = load_config()

# 配置日志
log_level = CONFIG.get('logging', {}).get('level', 'INFO').upper()
log_format = CONFIG.get('logging', {}).get('format', '%(asctime)s - %(levelname)s - %(message)s')
logging.basicConfig(level=getattr(logging, log_level), format=log_format)
logger = logging.getLogger(__name__)

# 添加文件日志
if CONFIG.get('logging', {}).get('file_enabled', True):
    log_file = CONFIG.get('logging', {}).get('file_path', 'epgo.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(getattr(logging, log_level))
    file_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(file_handler)

# 导入频道配置
from channels import CHANNELS

# 导入频道名称映射函数
from channel_mapping import normalize_channel_name

# 导入各个网站的节目单抓取函数
source_functions = {
    'tvsou': None,
    'tvmao': None,
    'cctv': None
}

try:
    from tvsou_epg import fetch_tvsou_programs
    source_functions['tvsou'] = fetch_tvsou_programs
    logger.info("成功导入tvsou_epg模块")
except ImportError as e:
    logger.error(f"导入tvsou_epg模块失败: {e}")

try:
    from tvmao_epg import fetch_tvmao_programs
    source_functions['tvmao'] = fetch_tvmao_programs
    logger.info("成功导入tvmao_epg模块")
except ImportError as e:
    logger.error(f"导入tvmao_epg模块失败: {e}")

try:
    from cctv_epg import fetch_cctv_programs
    source_functions['cctv'] = fetch_cctv_programs
    logger.info("成功导入cctv_epg模块")
except ImportError as e:
    logger.error(f"导入cctv_epg模块失败: {e}")













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

def calculate_success_rate(programs_dict, total_channels):
    """
    计算节目单抓取成功率
    
    Args:
        programs_dict: 节目单字典
        total_channels: 总频道数
        
    Returns:
        float: 成功率（0-100）
    """
    if total_channels == 0:
        return 0.0
    
    # 统计成功获取节目单的频道数量
    success_count = 0
    for channel_id, channel_data in programs_dict.items():
        if len(channel_data['programs']) > 0:
            success_count += 1
    
    success_rate = (success_count / total_channels) * 100
    return round(success_rate, 2)

def merge_programs(existing_programs, new_programs):
    """
    合并节目单数据
    
    Args:
        existing_programs: 已有的节目单
        new_programs: 新的节目单
        
    Returns:
        list: 合并后的节目单
    """
    if not existing_programs:
        return new_programs
    
    if not new_programs:
        return existing_programs
    
    # 合并节目单，去重
    merged = existing_programs.copy()
    
    # 创建已存在节目的集合，用于去重
    existing_set = {(prog['time'], prog['title']) for prog in merged}
    
    for prog in new_programs:
        prog_key = (prog['time'], prog['title'])
        if prog_key not in existing_set:
            merged.append(prog)
            existing_set.add(prog_key)
    
    # 按时间排序
    merged.sort(key=lambda x: x['time'])
    
    return merged

def save_xmltv(xmltv_content, output_file):
    """
    保存XMLTV文件，只生成固定名称的gz压缩文件
    
    Args:
        xmltv_content: XMLTV内容
        output_file: 输出文件路径（不包含扩展名）
    """
    output_dir = CONFIG.get('output', {}).get('dir', 'output')
    
    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 生成固定名称的gz文件，覆盖原有文件
    gz_file = os.path.join(output_dir, "epg.gz")
    
    # 直接将XML内容写入gz文件，不生成中间xml文件
    xml_bytes = xmltv_content.encode('utf-8')
    with gzip.open(gz_file, 'wb') as f_out:
        f_out.write(xml_bytes)
    
    logger.info(f"保存固定名称压缩XMLTV文件: {gz_file}")

def clean_old_files():
    """
    清理旧的输出文件，保留最近N天的文件
    """
    output_dir = CONFIG.get('output', {}).get('dir', 'output')
    keep_days = CONFIG.get('output', {}).get('keep_days', 7)
    
    if not os.path.exists(output_dir):
        return
    
    current_time = time.time()
    cutoff_time = current_time - (keep_days * 24 * 3600)
    
    # 获取所有输出文件
    files = []
    for filename in os.listdir(output_dir):
        file_path = os.path.join(output_dir, filename)
        if os.path.isfile(file_path):
            # 只处理XML和GZ文件
            if filename.endswith('.xml') or filename.endswith('.xml.gz') or filename.endswith('.gz'):
                files.append((file_path, os.path.getmtime(file_path)))
    
    # 清理过期文件
    deleted_count = 0
    for file_path, mtime in files:
        if mtime < cutoff_time:
            os.remove(file_path)
            deleted_count += 1
            logger.info(f"删除过期文件: {file_path}")
    
    if deleted_count > 0:
        logger.info(f"共删除 {deleted_count} 个过期文件")

def match_channel(channel_name):
    """
    优化的频道匹配算法，支持模糊匹配
    
    Args:
        channel_name: 要匹配的频道名称
        
    Returns:
        str: 匹配到的channel_id，如果没有匹配到则返回None
    """
    # 标准化输入频道名称
    standard_input = normalize_channel_name(channel_name)
    
    # 精确匹配
    for channel_id, channel_info in CHANNELS.items():
        standard_channel = normalize_channel_name(channel_info['name'])
        if standard_input == standard_channel:
            return channel_id
    
    # 如果启用了模糊匹配
    if CONFIG.get('channel_matching', {}).get('fuzzy_match', True):
        best_match = None
        best_score = 0
        threshold = CONFIG.get('channel_matching', {}).get('fuzzy_threshold', 0.8)
        
        for channel_id, channel_info in CHANNELS.items():
            channel_name = channel_info['name']
            standard_channel = normalize_channel_name(channel_name)
            
            # 计算相似度
            score = difflib.SequenceMatcher(None, standard_input, standard_channel).ratio()
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = channel_id
        
        if best_match:
            logger.debug(f"模糊匹配成功: {channel_name} -> {CHANNELS[best_match]['name']} (相似度: {best_score:.2f})")
            return best_match
    
    return None

def main():
    """主函数"""
    logger.info("开始生成EPG...")
    
    total_channels = len(CHANNELS)
    logger.info(f"总共有 {total_channels} 个频道需要抓取")
    
    # 初始化结果字典，包含所有配置频道
    final_programs_dict = {}
    # 预先添加所有配置频道，确保成功率计算基于所有频道
    for channel_id, channel_info in CHANNELS.items():
        final_programs_dict[channel_id] = {
            'name': channel_info['name'],
            'programs': []
        }
    
    # 从配置文件读取源优先级
    sources_config = CONFIG.get('sources', [])
    sources = []
    for source_config in sources_config:
        source_name = source_config['name']
        enabled = source_config.get('enabled', True)
        if enabled and source_name in source_functions:
            sources.append((source_name, source_functions[source_name]))
    
    # 如果配置文件中没有指定源，使用默认顺序
    if not sources:
        sources = [
            ('tvsou', source_functions['tvsou']),
            ('tvmao', source_functions['tvmao']),
            ('cctv', source_functions['cctv'])
        ]
    
    # 从配置文件读取成功率阈值
    success_threshold = CONFIG.get('success_threshold', 80.0)
    logger.info(f"成功率阈值: {success_threshold}%")
    
    # 按优先级处理每个源
    for source_name, source_func in sources:
        if not source_func:
            logger.warning(f"跳过不可用的源: {source_name}")
            continue
        
        logger.info(f"\n=== 使用 {source_name} 源抓取节目单 ===")
        
        # 调用源的抓取函数
        try:
            # 根据源类型调用不同的抓取策略
            if source_name == 'cctv':
                # CCTV源只抓取CCTV频道
                source_programs = source_func()
            elif source_name == 'tvmao':
                # 分阶段抓取：先抓取非CCTV频道，再补充CCTV频道
                # 1. 先抓取所有频道
                source_programs = source_func()
                
                # 2. 第一阶段：只处理非CCTV频道
                filtered_programs = {}
                for channel_name, programs in source_programs.items():
                    if not (channel_name.startswith('CCTV') or channel_name.startswith('央视')):
                        filtered_programs[channel_name] = programs
                
                logger.info(f"TVMao源第一阶段，处理 {len(filtered_programs)} 个非CCTV频道")
                
                # 3. 第二阶段：补充处理CCTV频道中没有节目单的频道
                # 查找需要补充的CCTV频道
                cctv_channels_need_supplement = []
                for channel_id, channel_data in final_programs_dict.items():
                    # 检查是否是CCTV频道且没有节目
                    if (channel_data['name'].startswith('CCTV') or channel_data['name'].startswith('央视')) and len(channel_data['programs']) == 0:
                        cctv_channels_need_supplement.append(channel_id)
                
                if cctv_channels_need_supplement:
                    logger.info(f"TVMao源第二阶段，尝试补充 {len(cctv_channels_need_supplement)} 个CCTV频道")
                    # 查找TVMao源中对应的CCTV频道
                    for channel_name, programs in source_programs.items():
                        if (channel_name.startswith('CCTV') or channel_name.startswith('央视')):
                            matched_channel = match_channel(channel_name)
                            if matched_channel in cctv_channels_need_supplement:
                                filtered_programs[channel_name] = programs
                                logger.info(f"  补充 {channel_name} 的节目单")
                
                source_programs = filtered_programs
            else:
                # 其他源正常调用
                source_programs = source_func()
            
            logger.info(f"{source_name} 源抓取完成，获取到 {len(source_programs)} 个频道的节目单")
            
            # 将源返回的节目单转换为标准格式
            standard_programs = {}
            for channel_name, programs in source_programs.items():
                # 优化的频道匹配
                matched_channel = match_channel(channel_name)
                
                if matched_channel:
                    standard_programs[matched_channel] = {
                        'name': CHANNELS[matched_channel]['name'],
                        'programs': programs
                    }
                else:
                    logger.debug(f"未找到匹配的频道: {channel_name}")
            
            logger.info(f"{source_name} 源匹配到 {len(standard_programs)} 个频道")
            
            # 合并到最终结果
            for channel_id, channel_data in standard_programs.items():
                if channel_id in final_programs_dict:
                    # 如果频道已存在，合并节目单
                    final_programs_dict[channel_id]['programs'] = merge_programs(
                        final_programs_dict[channel_id]['programs'],
                        channel_data['programs']
                    )
            
            # 计算当前成功率
            current_rate = calculate_success_rate(final_programs_dict, total_channels)
            logger.info(f"当前成功率: {current_rate}%")
            
            # 如果成功率达到阈值，停止后续源的调用
            if current_rate >= success_threshold:
                logger.info(f"成功率已达到 {success_threshold}% 以上，停止后续源的调用")
                break
            
        except Exception as e:
            logger.error(f"使用 {source_name} 源抓取节目单失败: {e}", exc_info=True)
    
    # 生成XMLTV文件
    xmltv_content = generate_xmltv(final_programs_dict)
    
    # 保存到文件 - 使用固定名称，不包含日期
    output_dir = CONFIG.get('output', {}).get('dir', 'output')
    output_file = os.path.join(output_dir, 'temp')  # 临时文件名，实际会被覆盖为epg.gz
    
    # 保存XMLTV文件，只生成epg.gz
    save_xmltv(xmltv_content, output_file)
    
    # 无需清理旧文件，因为每次都会覆盖epg.gz
    
    logger.info(f"\nEPG生成完成")
    logger.info(f"共处理 {len(final_programs_dict)} 个频道")
    
    # 统计成功抓取的节目数量
    total_programs = 0
    success_channels = 0
    for channel_id, channel_data in final_programs_dict.items():
        program_count = len(channel_data['programs'])
        total_programs += program_count
        if program_count > 0:
            success_channels += 1
        else:
            logger.warning(f"频道 {channel_data['name']} 未抓取到任何节目")
    
    final_rate = calculate_success_rate(final_programs_dict, total_channels)
    logger.info(f"最终成功率: {final_rate}%")
    logger.info(f"共抓取 {total_programs} 个节目")
    
    # 监控告警：如果成功率低于阈值，记录警告
    if final_rate < success_threshold:
        logger.warning(f"最终成功率 {final_rate}% 低于阈值 {success_threshold}%")
    
    logger.info("EPG生成任务完成")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()
