#!/usr/bin/env python3
"""
央视频(yangshipin.cn) EPG 提取工具
从 yangshipin.cn 页面提取当天节目单信息
"""

import requests
import gzip
import json
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs
import logging

logger = logging.getLogger(__name__)

# 频道ID映射：从频道名称到 yangshipin 的 pid
CHANNEL_PID_MAP = {
    'CCTV-1': '600001859',
    'CCTV-2': '600001800',
    'CCTV-3': '600001801',
    'CCTV-4': '600001814',
    'CCTV-5': '600001818',
    'CCTV-5+': '600001817',
    'CCTV-6': '600001803',
    'CCTV-7': '600004092',
    'CCTV-8': '600001804',
    'CCTV-9': '600004078',
    'CCTV-10': '600001805',
    'CCTV-11': '600001806',
    'CCTV-12': '600001807',
    'CCTV-13': '600001811',
    'CCTV-14': '600001809',
    'CCTV-15': '600001815',
    'CETV-1': '600171827',
    '湖南卫视': '600002475',
    '浙江卫视': '600002520',
    '江苏卫视': '600002521',
    '东方卫视': '600002483',
    '北京卫视': '600002309',
    '广东卫视': '600002485',
    '四川卫视': '600002516',
    '山东卫视': '600002513',
    '深圳卫视': '600002481',
    '湖北卫视': '600002508',
    '天津卫视': '600152137',
    '河北卫视': '600002493',
    '安徽卫视': '600002532',
    '黑龙江卫视': '600002498',
    '辽宁卫视': '600002505',
    '江西卫视': '600002503',
    '河南卫视': '600002525',
    '福建东南卫视': '600002484',
    '广西卫视': '600002509',
    '陕西卫视': '600190400',
    '云南卫视': '600190402',
    '贵州卫视': '600002490',
    '甘肃卫视': '600002530',
    '宁夏卫视': '600190737',
    '青海卫视': '600190406',
    '新疆卫视': '600152138',
    '西藏卫视': '600190403',
    '内蒙古卫视': '600190401',
    '吉林卫视': '600190405',
    '山西卫视': '600190407',
    '重庆卫视': '600002531',
    '海南卫视': '600002506',
}


def extract_pid_from_url(url):
    """从 yangshipin.cn URL 中提取 pid 参数"""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    return params.get('pid', [None])[0]


def get_epg_from_yangshipin(channel_name, pid, date_str):
    """
    从央视频获取指定频道、指定日期的节目单

    Args:
        channel_name: 频道名称
        pid: 频道ID
        date_str: 日期字符串，格式 YYYYMMDD

    Returns:
        节目列表，每个节目包含 startTime, endTime, title 等字段
    """
    if not pid:
        logger.warning(f"频道 {channel_name} 没有 pid，跳过")
        return None

    # 构造API URL
    #央视频的节目单API
    api_url = f"https://api.yangshipin.cn/content/api/channel/getEpgInfo"

    try:
        params = {
            'pid': pid,
            'date': date_str
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Referer': f'https://yangshipin.cn/tv/home?pid={pid}'
        }

        response = requests.get(api_url, params=params, headers=headers, timeout=15)
        response.raise_for_status()

        data = response.json()

        # 检查响应结构
        if 'data' in data and 'programList' in data['data']:
            programs = data['data']['programList']
            logger.info(f"成功获取 {channel_name} 的节目单，共 {len(programs)} 个节目")
            return programs
        else:
            logger.warning(f"{channel_name} API返回的数据结构不符合预期: {data}")
            return None

    except Exception as e:
        logger.error(f"获取 {channel_name} 节目单失败: {e}")
        return None


def generate_xmltv(programs_dict, target_date):
    """
    生成 XMLTV 格式的 EPG 文件

    Args:
        programs_dict: 字典，键为频道名称，值为节目列表
        target_date: 目标日期字符串

    Returns:
        XMLTV 格式的字符串
    """
    beijing_tz = timezone(timedelta(hours=8))

    xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<tv generator-info-name="Yangshipin EPG Generator" generator-info-url="https://yangshipin.cn">
'''

    total_programs = 0

    for channel_name, programs in programs_dict.items():
        if not programs:
            continue

        # 生成channel ID（用于XMLTV）
        channel_xml_id = channel_name.replace(' ', '_').replace('+', 'plus').replace('-', '')

        xml_content += f'''
  <channel id="{channel_xml_id}">
    <display-name>{channel_name}</display-name>
  </channel>
'''

        channel_program_count = 0
        for program in programs:
            try:
                # 解析时间（通常是毫秒时间戳或格式化的时间字符串）
                start_time = parse_program_time(program.get('startTime'), target_date, beijing_tz)
                end_time = parse_program_time(program.get('endTime'), target_date, beijing_tz)

                if not start_time or not end_time:
                    continue

                start_str = start_time.strftime('%Y%m%d%H%M%S')
                end_str = end_time.strftime('%Y%m%d%H%M%S')

                title = program.get('title', '')

                xml_content += f'''
  <programme channel="{channel_xml_id}" start="{start_str} +0800" stop="{end_str} +0800">
    <title lang="zh">{title}</title>
  </programme>
'''
                channel_program_count += 1
                total_programs += 1
            except Exception as e:
                logger.warning(f"解析节目失败: {e}")
                continue

        logger.info(f"为频道 {channel_name} 生成了 {channel_program_count} 个节目")

    logger.info(f"共生成了 {total_programs} 个节目")
    xml_content += '''</tv>
'''

    return xml_content


def parse_program_time(time_value, date_str, timezone_obj):
    """
    解析节目时间

    Args:
        time_value: 时间值，可能是秒/毫秒时间戳，也可能是 HH:MM 格式
        date_str: 日期字符串 YYYYMMDD
        timezone_obj: 时区对象

    Returns:
        datetime 对象
    """
    try:
        if not time_value:
            return None

        # 如果是时间戳（秒或毫秒）
        if isinstance(time_value, (int, float)):
            # 判断是秒还是毫秒
            if time_value > 10000000000:  # 毫秒时间戳
                return datetime.fromtimestamp(time_value / 1000, timezone_obj)
            else:  # 秒时间戳
                return datetime.fromtimestamp(time_value, timezone_obj)

        # 如果是字符串时间戳
        if isinstance(time_value, str):
            # 尝试解析为数字时间戳
            try:
                timestamp = float(time_value)
                if timestamp > 10000000000:  # 毫秒
                    return datetime.fromtimestamp(timestamp / 1000, timezone_obj)
                else:  # 秒
                    return datetime.fromtimestamp(timestamp, timezone_obj)
            except ValueError:
                pass

            # 尝试解析为 HH:MM 格式
            if ':' in time_value:
                time_parts = time_value.split(':')
                if len(time_parts) >= 2:
                    hour = int(time_parts[0])
                    minute = int(time_parts[1])
                    date_obj = datetime.strptime(date_str, '%Y%m%d')
                    return timezone_obj.localize(datetime(date_obj.year, date_obj.month, date_obj.day, hour, minute))

        return None
    except Exception as e:
        logger.warning(f"解析时间失败: {time_value}, {e}")
        return None


def load_channels_from_file(file_path):
    """
    从文件加载频道列表

    Args:
        file_path: 文件路径

    Returns:
        字典，键为频道名称，值为 yangshipin pid
    """
    channels = {}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split(',')
                if len(parts) >= 2:
                    channel_name = parts[0].strip()
                    yangshipin_url = parts[1].strip()

                    if yangshipin_url:
                        pid = extract_pid_from_url(yangshipin_url)
                        if pid:
                            channels[channel_name] = pid
                            logger.debug(f"加载频道: {channel_name} -> {pid}")
                    else:
                        logger.warning(f"频道 {channel_name} 的 yangshipin URL 为空")

    except Exception as e:
        logger.error(f"加载频道文件失败: {e}")

    return channels


def main():
    import argparse

    parser = argparse.ArgumentParser(description='从央视频提取EPG节目单')
    parser.add_argument('--channels', default='listofsource.txt', help='频道列表文件路径')
    parser.add_argument('--date', type=str, help='指定日期，格式为YYYYMMDD，如20260128')
    parser.add_argument('--output', default='yangshipin_epg.xml', help='输出文件路径')
    parser.add_argument('--gzip', action='store_true', help='输出为gzip压缩格式')

    args = parser.parse_args()

    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 确定目标日期
    beijing_tz = timezone(timedelta(hours=8))
    now_beijing = datetime.now(beijing_tz)

    if args.date:
        target_date = args.date
        logger.info(f"使用指定日期: {target_date}")
    else:
        target_date = now_beijing.strftime('%Y%m%d')
        logger.info(f"使用当前日期: {target_date}")

    # 加载频道列表
    channels = load_channels_from_file(args.channels)
    logger.info(f"加载了 {len(channels)} 个频道")

    # 获取所有频道的节目单
    programs_dict = {}
    success_count = 0
    fail_count = 0

    for channel_name, pid in channels.items():
        programs = get_epg_from_yangshipin(channel_name, pid, target_date)

        if programs:
            programs_dict[channel_name] = programs
            success_count += 1
        else:
            fail_count += 1

        # 避免请求过快
        import time
        time.sleep(0.5)

    logger.info(f"完成：成功获取 {success_count} 个频道，失败 {fail_count} 个频道")

    # 生成XMLTV格式
    if programs_dict:
        xmltv_content = generate_xmltv(programs_dict, target_date)

        # 输出文件
        if args.gzip or args.output.endswith('.gz'):
            output_file = args.output if args.output.endswith('.gz') else args.output + '.gz'
            with gzip.open(output_file, 'wb') as f:
                f.write(xmltv_content.encode('utf-8'))
            logger.info(f"EPG已保存到 {output_file} (gzip格式)")
        else:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(xmltv_content)
            logger.info(f"EPG已保存到 {args.output}")
    else:
        logger.warning("未获取到任何节目单，不生成文件")


if __name__ == '__main__':
    main()
