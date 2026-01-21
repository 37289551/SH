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

DEFAULT_CONFIG_PATH = "config.yaml"

def load_config(config_path=DEFAULT_CONFIG_PATH):
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

CONFIG = load_config()

log_level = CONFIG.get('logging', {}).get('level', 'INFO').upper()
log_format = CONFIG.get('logging', {}).get('format', '%(asctime)s - %(levelname)s - %(message)s')
logging.basicConfig(level=getattr(logging, log_level), format=log_format)
logger = logging.getLogger(__name__)

if CONFIG.get('logging', {}).get('file_enabled', True):
    log_file = CONFIG.get('logging', {}).get('file_path', 'epgo.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(getattr(logging, log_level))
    file_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(file_handler)

from channels import CHANNELS

from channel_mapping import normalize_channel_name

source_functions = {
    'tvsou': None,
    'tvmao': None,
    'cctv': None
}

try:
    from ts import fetch_tvsou_programs
    source_functions['tvsou'] = fetch_tvsou_programs
    logger.info("成功导入ts模块")
except ImportError as e:
    logger.error(f"导入ts模块失败: {e}")

try:
    from tm import fetch_tvmao_programs
    source_functions['tvmao'] = fetch_tvmao_programs
    logger.info("成功导入tm模块")
except ImportError as e:
    logger.error(f"导入tm模块失败: {e}")

try:
    from ct import fetch_cctv_programs
    source_functions['cctv'] = fetch_cctv_programs
    logger.info("成功导入ct模块")
except ImportError as e:
    logger.error(f"导入ct模块失败: {e}")

def generate_xmltv(programs_dict):
    today = datetime.now().strftime('%Y%m%d')

    tv = ET.Element('tv')
    tv.set('generator-info-name', 'EPGO Generator')
    tv.set('generator-info-url', 'https://github.com/37289551/epgo')
    
    for channel_id, channel_data in programs_dict.items():
        channel_name = channel_data['name']
        channel_programs = channel_data['programs']

        channel = ET.SubElement(tv, 'channel')
        channel.set('id', channel_id)

        display_name = ET.SubElement(channel, 'display-name')
        display_name.text = channel_name

        channel_programs.sort(key=lambda x: x['time'])

        for i, program in enumerate(channel_programs):
            programme = ET.SubElement(tv, 'programme')
            programme.set('channel', channel_id)

            start_time_str = program['time']
            start_hour, start_minute = map(int, start_time_str.split(':'))
            start_datetime = datetime.strptime(f"{today} {start_time_str}", "%Y%m%d %H:%M")

            if i == len(channel_programs) - 1:
                end_datetime = start_datetime.replace(hour=23, minute=59, second=59)
            else:
                next_program = channel_programs[i + 1]
                next_start_time_str = next_program['time']
                next_hour, next_minute = map(int, next_start_time_str.split(':'))
                next_start_datetime = datetime.strptime(f"{today} {next_start_time_str}", "%Y%m%d %H:%M")
                end_datetime = next_start_datetime - timedelta(seconds=1)

            start_time = start_datetime.strftime("%Y%m%d%H%M") + "00"
            end_time = end_datetime.strftime("%Y%m%d%H%M") + "00"
            
            programme.set('start', start_time)
            programme.set('stop', end_time)

            title = ET.SubElement(programme, 'title')
            title.set('lang', 'zh')
            title.text = program['title']

    rough_string = ET.tostring(tv, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")
    
    return pretty_xml

def calculate_success_rate(programs_dict, total_channels):
    if total_channels == 0:
        return 0.0

    success_count = 0
    for channel_id, channel_data in programs_dict.items():
        if len(channel_data['programs']) > 0:
            success_count += 1
    
    success_rate = (success_count / total_channels) * 100
    return round(success_rate, 2)

def merge_programs(existing_programs, new_programs):
    if not existing_programs:
        return new_programs
    
    if not new_programs:
        return existing_programs

    merged = existing_programs.copy()

    existing_set = {(prog['time'], prog['title']) for prog in merged}
    
    for prog in new_programs:
        prog_key = (prog['time'], prog['title'])
        if prog_key not in existing_set:
            merged.append(prog)
            existing_set.add(prog_key)

    merged.sort(key=lambda x: x['time'])
    
    return merged

def save_xmltv(xmltv_content, output_file):
    output_dir = CONFIG.get('output', {}).get('dir', 'output')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    gz_file = os.path.join(output_dir, "epg.gz")
    xml_bytes = xmltv_content.encode('utf-8')
    with gzip.open(gz_file, 'wb') as f_out:
        f_out.write(xml_bytes)
    
    logger.info(f"保存压缩文件: {gz_file}")

def clean_old_files():
    output_dir = CONFIG.get('output', {}).get('dir', 'output')
    keep_days = CONFIG.get('output', {}).get('keep_days', 7)
    
    if not os.path.exists(output_dir):
        return
    
    current_time = time.time()
    cutoff_time = current_time - (keep_days * 24 * 3600)

    files = []
    for filename in os.listdir(output_dir):
        file_path = os.path.join(output_dir, filename)
        if os.path.isfile(file_path):
            if filename.endswith('.xml') or filename.endswith('.xml.gz') or filename.endswith('.gz'):
                files.append((file_path, os.path.getmtime(file_path)))

    deleted_count = 0
    for file_path, mtime in files:
        if mtime < cutoff_time:
            os.remove(file_path)
            deleted_count += 1
            logger.info(f"删除过期文件: {file_path}")
    
    if deleted_count > 0:
        logger.info(f"共删除 {deleted_count} 个过期文件")

def match_channel(channel_name):
    standard_input = normalize_channel_name(channel_name)

    for channel_id, channel_info in CHANNELS.items():
        standard_channel = normalize_channel_name(channel_info['name'])
        if standard_input == standard_channel:
            return channel_id

    if CONFIG.get('channel_matching', {}).get('fuzzy_match', True):
        best_match = None
        best_score = 0
        threshold = CONFIG.get('channel_matching', {}).get('fuzzy_threshold', 0.8)
        
        for channel_id, channel_info in CHANNELS.items():
            channel_name = channel_info['name']
            standard_channel = normalize_channel_name(channel_name)

            score = difflib.SequenceMatcher(None, standard_input, standard_channel).ratio()
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = channel_id
        
        if best_match:
            logger.debug(f"模糊匹配成功: {channel_name} -> {CHANNELS[best_match]['name']} (相似度: {best_score:.2f})")
            return best_match
    
    return None

def main():
    logger.info("开始生成EPG...")
    
    total_channels = len(CHANNELS)
    logger.info(f"总共有 {total_channels} 个频道需要抓取")

    final_programs_dict = {}
    for channel_id, channel_info in CHANNELS.items():
        final_programs_dict[channel_id] = {
            'name': channel_info['name'],
            'programs': []
        }

    sources_config = CONFIG.get('sources', [])
    sources = []
    for source_config in sources_config:
        source_name = source_config['name']
        enabled = source_config.get('enabled', True)
        if enabled and source_name in source_functions:
            sources.append((source_name, source_functions[source_name]))

    if not sources:
        sources = [
            ('tvsou', source_functions['tvsou']),
            ('tvmao', source_functions['tvmao']),
            ('cctv', source_functions['cctv'])
        ]

    success_threshold = CONFIG.get('success_threshold', 80.0)
    logger.info(f"成功率阈值: {success_threshold}%")

    cctv_matched_count = 0

    for source_name, source_func in sources:
        if not source_func:
            logger.warning(f"跳过不可用的源: {source_name}")
            continue
        
        logger.info(f"\n=== 使用 {source_name} 源抓取节目单 ===")

        try:
            if source_name == 'cctv':
                source_programs = source_func()
            elif source_name == 'tvmao':
                logger.info("TM step one，卫视频道")
                satellite_programs = source_func('satellite')
                filtered_programs = {}
                for channel_name, programs in satellite_programs.items():
                    if not (channel_name.startswith('CCTV') or channel_name.startswith('央视')):
                        filtered_programs[channel_name] = programs
                
                logger.info(f"TM STEP ONE，处理 {len(filtered_programs)} 个非CCTV频道")

                skip_cctv_supplement = False
                if cctv_matched_count >= 18:
                    skip_cctv_supplement = True
                    logger.info(f"CCTV已匹配 {cctv_matched_count} 个频道，跳过TM第二阶段CCTV频道抓取")
                
                if not skip_cctv_supplement:
                    cctv_channels_need_supplement = []
                    for channel_id, channel_data in final_programs_dict.items():
                        if (channel_data['name'].startswith('CCTV') or channel_data['name'].startswith('央视')) and len(channel_data['programs']) == 0:
                            cctv_channels_need_supplement.append(channel_id)
                    
                    if cctv_channels_need_supplement:
                        logger.info(f"TM第二阶段，补充CCTV频道")
                        cctv_programs = source_func('cctv')
                        
                        logger.info(f"TM第二阶段，处理 {len(cctv_programs)} 个CCTV频道")
                        for channel_name, programs in cctv_programs.items():
                            if (channel_name.startswith('CCTV') or channel_name.startswith('央视')):
                                matched_channel = match_channel(channel_name)
                                if matched_channel in cctv_channels_need_supplement:
                                    filtered_programs[channel_name] = programs
                                    logger.info(f"  补充 {channel_name} 的节目单")
                
                source_programs = filtered_programs
            else:
                source_programs = source_func()
            
            logger.info(f"{source_name} 源完成，获取到 {len(source_programs)} 个频道的节目单")

            standard_programs = {}
            for channel_name, programs in source_programs.items():
                matched_channel = match_channel(channel_name)
                
                if matched_channel:
                    standard_programs[matched_channel] = {
                        'name': CHANNELS[matched_channel]['name'],
                        'programs': programs
                    }
                else:
                    logger.debug(f"未找到匹配的频道: {channel_name}")
            
            logger.info(f"{source_name} 源匹配到 {len(standard_programs)} 个频道")
            
            if source_name == 'cctv':
                cctv_matched_count = len(standard_programs)
                logger.info(f"CCTV源匹配频道数量: {cctv_matched_count}")
            
            for channel_id, channel_data in standard_programs.items():
                if channel_id in final_programs_dict:
                    final_programs_dict[channel_id]['programs'] = merge_programs(
                        final_programs_dict[channel_id]['programs'],
                        channel_data['programs']
                    )
            
            current_rate = calculate_success_rate(final_programs_dict, total_channels)
            logger.info(f"当前成功率: {current_rate}%")

            if current_rate >= success_threshold:
                logger.info(f"成功率已达到 {success_threshold}% 以上，停止后续源的调用")
                break
            
        except Exception as e:
            logger.error(f"使用 {source_name} 源抓取节目单失败: {e}", exc_info=True)

    xmltv_content = generate_xmltv(final_programs_dict)

    output_dir = CONFIG.get('output', {}).get('dir', 'output')
    output_file = os.path.join(output_dir, 'temp') 

    save_xmltv(xmltv_content, output_file)

    
    logger.info(f"\nEPG生成完成")
    logger.info(f"共处理 {len(final_programs_dict)} 个频道")
    
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
