#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import argparse
from datetime import datetime, timezone, timedelta
import json
import tempfile

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入 ctws 模块
import ctws

def test_extract_pid_from_url():
    print(f"\n=== 测试从URL提取PID ===")
    
    # 测试用例
    test_cases = [
        ("https://yangshipin.cn/tv/home?pid=600001859", "600001859"),
        ("https://yangshipin.cn/tv/home?pid=600002521&other=param", "600002521"),
        ("https://yangshipin.cn/tv/home", None),
        ("https://example.com", None)
    ]
    
    all_passed = True
    for url, expected_pid in test_cases:
        result = ctws.extract_pid_from_url(url)
        status = "✅" if result == expected_pid else "❌"
        print(f"{status} {url}")
        print(f"  提取结果: {result}, 预期: {expected_pid}")
        if result != expected_pid:
            all_passed = False
    
    if all_passed:
        print(f"\n✅ 所有URL PID提取测试通过")
    else:
        print(f"\n❌ 部分URL PID提取测试失败")
    
    return all_passed

def test_load_channels_from_file():
    print(f"\n=== 测试加载频道列表 ===")
    
    # 创建临时测试文件
    test_content = """CCTV-1,https://yangshipin.cn/tv/home?pid=600001859
CCTV-2,https://yangshipin.cn/tv/home?pid=600001800
# 这是注释行
江苏卫视,https://yangshipin.cn/tv/home?pid=600002521
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(test_content)
        temp_file = f.name
    
    try:
        channels = ctws.load_channels_from_file(temp_file)
        print(f"✅ 成功加载频道列表")
        print(f"✅ 加载了 {len(channels)} 个频道")
        
        for channel_name, pid in channels.items():
            print(f"  {channel_name}: {pid}")
        
        # 验证结果
        expected_channels = {
            'CCTV-1': '600001859',
            'CCTV-2': '600001800',
            '江苏卫视': '600002521'
        }
        
        if channels == expected_channels:
            print("✅ 频道列表加载正确")
            return True
        else:
            print("❌ 频道列表加载不正确")
            print(f"  预期: {expected_channels}")
            print(f"  实际: {channels}")
            return False
            
    except Exception as e:
        print(f"❌ 加载频道列表失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理临时文件
        if os.path.exists(temp_file):
            os.remove(temp_file)

def test_parse_program_time():
    print(f"\n=== 测试解析节目时间 ===")
    
    beijing_tz = timezone(timedelta(hours=8))
    date_str = "20260310"
    
    # 计算正确的时间戳（2026-03-10 00:00:00 UTC+8）
    test_date = datetime(2026, 3, 10, 0, 0, 0, tzinfo=beijing_tz)
    # 转换为UTC时间戳
    utc_timestamp = int(test_date.timestamp())
    utc_timestamp_ms = utc_timestamp * 1000
    
    # 测试用例
    test_cases = [
        # (time_value, expected_time_str)
        (utc_timestamp, "00:00"),  # 秒时间戳
        (utc_timestamp_ms, "00:00"),  # 毫秒时间戳
        (str(utc_timestamp), "00:00"),  # 字符串秒时间戳
        (str(utc_timestamp_ms), "00:00"),  # 字符串毫秒时间戳
        ("08:30", "08:30"),  # HH:MM 格式
        ("23:59", "23:59"),  # HH:MM 格式
        (None, None),  # 空值
        ("invalid", None)  # 无效值
    ]
    
    all_passed = True
    for time_value, expected_time_str in test_cases:
        result = ctws.parse_program_time(time_value, date_str, beijing_tz)
        if result:
            result_str = result.strftime('%H:%M')
        else:
            result_str = None
        
        status = "✅" if result_str == expected_time_str else "❌"
        print(f"{status} {time_value}")
        print(f"  解析结果: {result_str}, 预期: {expected_time_str}")
        if result_str != expected_time_str:
            all_passed = False
    
    if all_passed:
        print(f"\n✅ 所有时间解析测试通过")
    else:
        print(f"\n❌ 部分时间解析测试失败")
    
    return all_passed

def test_get_epg_from_yangshipin(channel_name, pid, date_str):
    print(f"\n=== 测试从央视频获取节目单: {channel_name} ===")
    try:
        programs = ctws.get_epg_from_yangshipin(channel_name, pid, date_str)
        
        if programs:
            print(f"✅ 成功获取节目单")
            print(f"✅ 共 {len(programs)} 个节目")
            
            if len(programs) > 0:
                print("\n示例节目:")
                for i, program in enumerate(programs[:3]):
                    start_time = ctws.parse_program_time(program.get('startTime'), date_str, timezone(timedelta(hours=8)))
                    end_time = ctws.parse_program_time(program.get('endTime'), date_str, timezone(timedelta(hours=8)))
                    start_str = start_time.strftime('%H:%M') if start_time else 'N/A'
                    end_str = end_time.strftime('%H:%M') if end_time else 'N/A'
                    print(f"  {i+1}. {start_str}-{end_str}: {program.get('title', 'N/A')}")
            return programs
        else:
            print(f"❌ 获取节目单失败: 未返回有效数据")
            return None
    except Exception as e:
        print(f"❌ 获取节目单失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_generate_xmltv():
    print(f"\n=== 测试生成XMLTV ===")
    
    # 创建测试数据
    test_programs = [
        {
            'startTime': '08:00',
            'endTime': '09:00',
            'title': '早间新闻'
        },
        {
            'startTime': '09:00',
            'endTime': '10:00',
            'title': '财经报道'
        }
    ]
    
    programs_dict = {
        'CCTV-1': test_programs
    }
    
    date_str = "20260310"
    
    try:
        xmltv_content = ctws.generate_xmltv(programs_dict, date_str)
        
        if xmltv_content:
            print(f"✅ XMLTV生成成功")
            print(f"✅ XMLTV内容长度: {len(xmltv_content)} 字符")
            
            # 保存XMLTV文件
            output_dir = 'output'
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            output_file = os.path.join(output_dir, f'ctws_test_{date_str}.xml')
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(xmltv_content)
            
            print(f"✅ XMLTV文件已保存到: {output_file}")
            print(f"✅ 文件大小: {os.path.getsize(output_file) / 1024:.2f} KB")
            return True
        else:
            print(f"❌ XMLTV生成失败: 内容为空")
            return False
    except Exception as e:
        print(f"❌ XMLTV生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_discovery():
    """测试新发现的API接口"""
    print(f"\n=== 测试API发现 ===")
    print("测试新发现的央视频API接口...")

    import requests

    # 测试频道
    pid = '600001859'  # CCTV-1
    date_str = datetime.now().strftime('%Y%m%d')

    # 新发现的API列表
    new_apis = [
        {
            'name': 'capi yangshipin yspepg list (GET)',
            'url': 'https://capi.yangshipin.cn/api/yspepg/program/list',
            'params': {'cid': pid, 'date': date_str},
            'method': 'GET'
        },
        {
            'name': 'capi yangshipin yspepg list (POST)',
            'url': 'https://capi.yangshipin.cn/api/yspepg/program/list',
            'data': {'cid': pid, 'date': date_str},
            'method': 'POST'
        },
        {
            'name': 'capi yangshipin yspepg get',
            'url': 'https://capi.yangshipin.cn/api/yspepg/program/get',
            'params': {'cid': pid, 'date': date_str},
            'method': 'GET'
        }
    ]

    working_apis = []

    for api in new_apis:
        print(f"\n测试 {api['name']}...")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Referer': f'https://yangshipin.cn/tv/home?pid={pid}'
            }

            if api['method'] == 'POST':
                response = requests.post(
                    api['url'],
                    json=api['data'],
                    headers=headers,
                    timeout=10
                )
            else:
                response = requests.get(
                    api['url'],
                    params=api['params'],
                    headers=headers,
                    timeout=10
                )

            print(f"  状态码: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()

                    # 检查是否有有效的节目数据
                    has_programs = False
                    if 'data' in data:
                        if 'dataList' in data['data'] and data['data']['dataList']:
                            has_programs = True
                            print(f"  ✅ 找到 dataList: {len(data['data']['dataList'])} 个节目")
                        elif 'programList' in data['data'] and data['data']['programList']:
                            has_programs = True
                            print(f"  ✅ 找到 programList: {len(data['data']['programList'])} 个节目")

                    if has_programs:
                        working_apis.append(api['name'])
                        print(f"  ✅ {api['name']} 可用")
                    else:
                        print(f"  ⚠️  {api['name']} 响应正常但无节目数据")
                except json.JSONDecodeError:
                    print(f"  ❌ JSON解析失败")
            else:
                print(f"  ❌ HTTP错误")

        except Exception as e:
            print(f"  ❌ 请求失败: {e}")

    if working_apis:
        print(f"\n✅ 发现 {len(working_apis)} 个可用的API:")
        for api_name in working_apis:
            print(f"  - {api_name}")
    else:
        print(f"\n⚠️  未发现可用的API接口")

    return len(working_apis) > 0


def test_ci_environment():
    """CI/CD环境测试：快速验证核心功能"""
    print(f"\n=== CI/CD环境测试 ===")
    print("执行快速功能验证...")

    # 只测试核心功能，不进行实际的API调用（避免网络依赖）
    test_results = []

    # 测试1: PID提取
    try:
        result = ctws.extract_pid_from_url("https://yangshipin.cn/tv/home?pid=600001859")
        if result == '600001859':
            test_results.append(('PID提取', True))
        else:
            test_results.append(('PID提取', False))
    except:
        test_results.append(('PID提取', False))

    # 测试2: 时间解析
    try:
        beijing_tz = timezone(timedelta(hours=8))
        result = ctws.parse_program_time("08:30", "20260310", beijing_tz)
        if result and result.strftime('%H:%M') == "08:30":
            test_results.append(('时间解析', True))
        else:
            test_results.append(('时间解析', False))
    except:
        test_results.append(('时间解析', False))

    # 测试3: XMLTV生成
    try:
        test_programs = [{'startTime': '08:00', 'endTime': '09:00', 'title': '测试节目'}]
        xmltv = ctws.generate_xmltv({'CCTV-1': test_programs}, "20260310")
        if xmltv and '<?xml' in xmltv and '<tv>' in xmltv:
            test_results.append(('XMLTV生成', True))
        else:
            test_results.append(('XMLTV生成', False))
    except:
        test_results.append(('XMLTV生成', False))

    # 输出结果
    print()
    for test_name, passed in test_results:
        status = "✅" if passed else "❌"
        print(f"{status} {test_name}")

    all_passed = all(result[1] for result in test_results)

    print(f"\nCI/CD测试结果: {'✅ 通过' if all_passed else '❌ 失败'}")
    return all_passed


def main():
    print("=== CTWS测试 ===")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 创建参数解析器
    parser = argparse.ArgumentParser(description='测试CTWS央视频节目单抓取功能')
    parser.add_argument('--date', type=str, help='指定日期，格式为YYYYMMDD，如20260310')
    parser.add_argument('--channel', type=str, default='江苏卫视', help='指定测试频道名称')
    parser.add_argument('--pid', type=str, default='600002521', help='指定测试频道PID')
    parser.add_argument('--ci', action='store_true', help='CI/CD模式：只测试核心功能，不调用API')
    parser.add_argument('--api-test', action='store_true', help='测试新发现的API接口')
    parser.add_argument('--full', action='store_true', help='完整测试模式（包括API调用）')
    args = parser.parse_args()

    # 处理日期参数
    if args.date:
        date_str = args.date
        print(f"使用指定日期: {date_str}")
    else:
        # 使用当前日期
        date_str = datetime.now().strftime('%Y%m%d')
        print(f"使用当前日期: {date_str}")

    print(f"测试频道: {args.channel}")
    print(f"测试PID: {args.pid}")
    print(f"测试模式: {'CI/CD快速测试' if args.ci else ('API测试' if args.api_test else '完整测试' if args.full else '标准测试')}")
    print()

    # 运行测试
    try:
        # 基础功能测试（所有模式都执行）
        print("=== 基础功能测试 ===")
        test_results = []

        # 1. 测试URL PID提取
        result1 = test_extract_pid_from_url()
        test_results.append(('URL PID提取', result1))

        # 2. 测试加载频道列表
        result2 = test_load_channels_from_file()
        test_results.append(('加载频道列表', result2))

        # 3. 测试时间解析
        result3 = test_parse_program_time()
        test_results.append(('时间解析', result3))

        # CI/CD模式：只测试基础功能
        if args.ci:
            result4 = test_ci_environment()
            test_results.append(('CI/CD环境', result4))

            # 输出总结
            print(f"\n=== 测试总结 ===")
            passed_count = sum(1 for _, passed in test_results if passed)
            total_count = len(test_results)

            for test_name, passed in test_results:
                status = "✅" if passed else "❌"
                print(f"{status} {test_name}")

            all_passed = all(result[1] for result in test_results)
            print(f"\n通过率: {passed_count}/{total_count} ({passed_count/total_count*100:.1f}%)")

            print(f"\n=== 测试完成 ===")
            print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            if not all_passed:
                sys.exit(1)
            return

        # API测试模式：只测试新发现的API
        if args.api_test:
            result5 = test_api_discovery()
            test_results.append(('API发现', result5))

            print(f"\n=== 测试完成 ===")
            print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            return

        # 4. 测试从央视频获取节目单（非CI模式）
        test_programs = test_get_epg_from_yangshipin(args.channel, args.pid, date_str)
        test_results.append(('获取EPG', test_programs is not None))

        # 5. 测试XMLTV生成
        result6 = test_generate_xmltv()
        test_results.append(('XMLTV生成', result6))

        # 完整测试模式：测试多个频道
        if args.full or not args.ci:
            print(f"\n=== 测试完整流程 ===")
            print("开始完整流程测试...")

            # 使用硬编码的测试频道数据，不依赖外部文件
            test_channels_data = {
                'CCTV-1': '600001859',
                'CCTV-2': '600001800',
                'CCTV-3': '600001801',
            }
            print(f"✅ 加载了 {len(test_channels_data)} 个测试频道")

            # 测试所有测试频道
            success_count = 0
            fail_count = 0

            for channel_name, pid in test_channels_data.items():
                print(f"\n正在测试 {channel_name}...")
                programs = ctws.get_epg_from_yangshipin(channel_name, pid, date_str)
                if programs:
                    success_count += 1
                    print(f"✅ 成功获取 {len(programs)} 个节目")
                else:
                    fail_count += 1
                    print(f"❌ 获取节目单失败")

            print(f"\n完整流程测试结果:")
            print(f"✅ 成功频道数: {success_count}")
            print(f"❌ 失败频道数: {fail_count}")

            test_results.append(('完整流程', success_count > 0))

        # 输出总结
        print(f"\n=== 测试总结 ===")
        passed_count = sum(1 for _, passed in test_results if passed)
        total_count = len(test_results)

        for test_name, passed in test_results:
            status = "✅" if passed else "❌"
            print(f"{status} {test_name}")

        all_passed = all(result[1] for result in test_results)
        print(f"\n通过率: {passed_count}/{total_count} ({passed_count/total_count*100:.1f}%)")

        print(f"\n=== 测试完成 ===")
        print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if not all_passed:
            print(f"⚠️  部分测试未通过")
            sys.exit(1)

    except Exception as e:
        print(f"\n=== 测试失败 ===")
        print(f"错误信息: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
