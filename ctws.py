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

    # 尝试多个可能的API接口
    # 从app.js分析发现的真实API结构
    api_candidates = [
        # 方案1: 央视频官方EPG API（基于app.js分析）
        {
            'url': 'https://capi.yangshipin.cn/api/yspepg/program/list',
            'params': {'cid': pid, 'date': date_str},
            'desc': '方案1: capi yangshipin yspepg list接口',
            'method': 'GET'
        },
        # 方案2: 央视频EPG API POST方式
        {
            'url': 'https://capi.yangshipin.cn/api/yspepg/program/list',
            'data': {'cid': pid, 'date': date_str},
            'desc': '方案2: capi yangshipin yspepg list POST接口',
            'method': 'POST'
        },
        # 方案3: 测试环境API
        {
            'url': 'https://appdevteamtest.yangshipin.cn/api/yspepg/program/list',
            'params': {'cid': pid, 'date': date_str},
            'desc': '方案3: 测试环境 yspepg list接口',
            'method': 'GET'
        },
        # 方案4: 新版API接口
        {
            'url': 'https://capi.yangshipin.cn/api/yspepg/program/get',
            'params': {'cid': pid, 'date': date_str},
            'desc': '方案4: capi yangshipin yspepg get接口',
            'method': 'GET'
        },
        # 方案5: 预发布环境
        {
            'url': 'https://precapi.yangshipin.cn/api/yspepg/program/list',
            'params': {'cid': pid, 'date': date_str},
            'desc': '方案5: 预发布环境 yspepg list接口',
            'method': 'GET'
        },
        # 方案6: 保留的推测接口作为备选
        {
            'url': 'https://api.yangshipin.cn/content/api/channel/getEpgInfo',
            'params': {'pid': pid, 'date': date_str},
            'desc': '方案6: getEpgInfo接口',
            'method': 'GET'
        },
        # 方案7: 央视频直播页面API
        {
            'url': 'https://api.yangshipin.cn/content/channel/programList',
            'params': {'pid': pid, 'date': date_str},
            'desc': '方案7: programList接口',
            'method': 'GET'
        },
        # 方案8: 央视官网风格API
        {
            'url': 'https://api.cctv.com/api/epg/epginfo',
            'params': {'serviceId': f'tvcctv', 'c': pid, 'd': date_str, 't': 'json'},
            'desc': '方案8: cctv.com epginfo接口',
            'method': 'GET'
        },
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Referer': f'https://yangshipin.cn/tv/home?pid={pid}',
        'Origin': 'https://yangshipin.cn'
    }

    for api_config in api_candidates:
        try:
            logger.debug(f"尝试 {api_config['desc']}: {api_config['url']}")

            # 根据配置选择请求方法
            if api_config.get('method') == 'POST':
                response = requests.post(
                    api_config['url'],
                    json=api_config.get('data', {}),
                    headers=headers,
                    timeout=15
                )
            else:
                response = requests.get(
                    api_config['url'],
                    params=api_config.get('params', {}),
                    headers=headers,
                    timeout=15
                )
            response.raise_for_status()

            data = response.json()

            # 检查各种可能的响应结构
            programs = None

            # 检查1: 标准的 programList 结构
            if 'data' in data and 'programList' in data['data']:
                programs = data['data']['programList']
                logger.debug(f"找到 programList 结构")

            # 检查2: 直接的 programList 结构
            elif 'programList' in data:
                programs = data['programList']
                logger.debug(f"找到直接 programList 结构")

            # 检查3: dataList 结构（央视频标准）
            elif 'data' in data and 'dataList' in data['data']:
                programs = data['data']['dataList']
                logger.debug(f"找到 dataList 结构")

            # 检查4: 直接 dataList 结构
            elif 'dataList' in data:
                programs = data['dataList']
                logger.debug(f"找到直接 dataList 结构")

            # 检查5: data 是列表
            elif 'data' in data and isinstance(data['data'], list):
                programs = data['data']
                logger.debug(f"找到 data 列表结构")

            # 检查6: 直接是列表
            elif isinstance(data, list):
                programs = data
                logger.debug(f"找到直接列表结构")

            # 检查7: list 结构
            elif 'list' in data:
                programs = data['list']
                logger.debug(f"找到 list 结构")

            # 检查8: programs 结构
            elif 'programs' in data:
                programs = data['programs']
                logger.debug(f"找到 programs 结构")

            # 检查9: epgData 结构
            elif 'epgData' in data:
                programs = data['epgData']
                logger.debug(f"找到 epgData 结构")

            # 检查10: epg_list 结构
            elif 'epg_list' in data:
                programs = data['epg_list']
                logger.debug(f"找到 epg_list 结构")

            # 检查11: data.items 结构
            elif 'data' in data and 'items' in data['data']:
                programs = data['data']['items']
                logger.debug(f"找到 data.items 结构")

            if programs:
                # 转换节目数据为统一格式
                standard_programs = []
                for prog in programs:
                    standard_prog = {
                        'title': prog.get('title') or prog.get('name') or prog.get('programName') or '',
                        'startTime': prog.get('startTime') or prog.get('start_time') or prog.get('start') or prog.get('time'),
                        'endTime': prog.get('endTime') or prog.get('end_time') or prog.get('end')
                    }
                    if standard_prog['title']:
                        standard_programs.append(standard_prog)

                if standard_programs:
                    logger.info(f"✓ {channel_name} 通过 {api_config['desc']} 成功获取，共 {len(standard_programs)} 个节目")
                    return standard_programs
                else:
                    logger.warning(f"{api_config['desc']} 返回数据但无法解析节目列表")

            # 检查是否有错误信息
            if 'error' in data:
                logger.warning(f"{api_config['desc']} 返回错误: {data['error']}")
            elif 'errcode' in data:
                logger.warning(f"{api_config['desc']} 返回错误码: {data.get('errcode')}, 信息: {data.get('msg', '无')}")
            elif 'code' in data and data['code'] != 0:
                logger.warning(f"{api_config['desc']} 返回错误码: {data['code']}, 信息: {data.get('message', data.get('msg', '无'))}")

        except requests.exceptions.RequestException as e:
            logger.debug(f"{api_config['desc']} 请求失败: {e}")
            continue
        except json.JSONDecodeError as e:
            logger.debug(f"{api_config['desc']} JSON解析失败: {e}")
            continue
        except Exception as e:
            logger.debug(f"{api_config['desc']} 处理失败: {e}")
            continue

    logger.error(f"所有API方案均失败，无法获取 {channel_name} 的节目单")
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
                    # 直接创建带时区的 datetime 对象
                    return datetime(date_obj.year, date_obj.month, date_obj.day, hour, minute, tzinfo=timezone_obj)

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
