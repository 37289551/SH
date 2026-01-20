#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CCTV API节目单抓取测试脚本
用于测试cctv_api_epg.py脚本的功能
"""

import sys
import os
import argparse
from datetime import datetime
import json
import tempfile

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入新的CCTV API模块
from cctv_api_epg import get_cctv_epg, generate_xmltv, CCTV_CHANNELS, validate_date

def test_api_call(channel_id, date_str):
    """测试API调用功能"""
    print(f"\n=== 测试API调用: {channel_id} ===")
    try:
        # 调用API获取节目单
        data = get_cctv_epg(channel_id, date_str)
        
        if data and 'data' in data:
            print(f"✅ API调用成功")
            
            # 检查返回数据结构
            for key, channel_data in data['data'].items():
                if 'list' in channel_data:
                    program_count = len(channel_data['list'])
                    print(f"✅ 成功获取 {program_count} 个节目")
                    
                    # 打印前3个节目作为示例
                    if program_count > 0:
                        print("\n示例节目:")
                        for i, program in enumerate(channel_data['list'][:3]):
                            start_time = datetime.fromtimestamp(program['startTime']).strftime('%H:%M')
                            end_time = datetime.fromtimestamp(program['endTime']).strftime('%H:%M')
                            print(f"  {i+1}. {start_time}-{end_time}: {program['title']}")
                    return channel_data['list']
        else:
            print(f"❌ API调用失败: 未返回有效数据")
            return None
    except Exception as e:
        print(f"❌ API调用失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_xmltv_generation(programs_dict, date_str):
    """测试XMLTV生成功能"""
    print(f"\n=== 测试XMLTV生成 ===")
    try:
        # 生成XMLTV内容
        from datetime import timezone, timedelta
        beijing_tz = timezone(timedelta(hours=8))
        xmltv_content = generate_xmltv(programs_dict, date_str, beijing_tz)
        
        if xmltv_content:
            print(f"✅ XMLTV生成成功")
            print(f"✅ XMLTV内容长度: {len(xmltv_content)} 字符")
            
            # 保存XMLTV文件
            output_dir = 'output'
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            output_file = os.path.join(output_dir, f'cctv_test_{date_str}.xml')
            
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

def test_date_validation():
    """测试日期验证功能"""
    print(f"\n=== 测试日期验证 ===")
    
    # 测试用例
    test_cases = [
        ("20260120", True),
        ("2026-01-20", False),
        ("2026/01/20", False),
        ("20260132", False),
        ("20261320", False),
        ("invalid", False)
    ]
    
    all_passed = True
    for date_str, expected in test_cases:
        result = validate_date(date_str)
        status = "✅" if result == expected else "❌"
        print(f"{status} {date_str}: {result} (预期: {expected})")
        if result != expected:
            all_passed = False
    
    if all_passed:
        print(f"\n✅ 所有日期验证测试通过")
    else:
        print(f"\n❌ 部分日期验证测试失败")
    
    return all_passed

def main():
    """主函数"""
    print("=== CCTV API节目单抓取测试 ===")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 创建参数解析器
    parser = argparse.ArgumentParser(description='测试CCTV API节目单抓取功能')
    parser.add_argument('--date', type=str, help='指定日期，格式为YYYYMMDD，如20260120')
    parser.add_argument('--channel', type=str, default='cctv1', help='指定测试频道，如cctv1')
    args = parser.parse_args()
    
    # 处理日期参数
    if args.date:
        if validate_date(args.date):
            date_str = args.date
            print(f"使用指定日期: {date_str}")
        else:
            print(f"日期格式错误: {args.date}，应为YYYYMMDD格式")
            sys.exit(1)
    else:
        # 使用当前日期
        date_str = datetime.now().strftime('%Y%m%d')
        print(f"使用当前日期: {date_str}")
    
    # 验证频道参数
    if args.channel not in CCTV_CHANNELS:
        print(f"无效频道: {args.channel}，可用频道: {', '.join(CCTV_CHANNELS.keys())}")
        sys.exit(1)
    
    print(f"测试频道: {CCTV_CHANNELS[args.channel]}")
    print()
    
    # 运行测试
    try:
        # 1. 测试日期验证
        test_date_validation()
        
        # 2. 测试API调用
        test_programs = test_api_call(args.channel, date_str)
        
        if test_programs:
            # 3. 测试XMLTV生成
            test_programs_dict = {args.channel: test_programs}
            test_xmltv_generation(test_programs_dict, date_str)
        
        # 4. 完整测试 - 获取所有频道
        print(f"\n=== 完整测试: 获取所有频道节目单 ===")
        print("开始获取所有频道节目单...")
        
        full_programs_dict = {}
        success_count = 0
        fail_count = 0
        
        # 只测试前5个频道以节省时间
        test_channels = list(CCTV_CHANNELS.keys())[:5]
        for channel_id in test_channels:
            print(f"\n正在测试 {CCTV_CHANNELS[channel_id]}...")
            programs = get_cctv_epg(channel_id, date_str)
            if programs and 'data' in programs:
                for key, channel_data in programs['data'].items():
                    if 'list' in channel_data:
                        full_programs_dict[channel_id] = channel_data['list']
                        success_count += 1
                    else:
                        fail_count += 1
            else:
                fail_count += 1
        
        print(f"\n完整测试结果:")
        print(f"✅ 成功频道数: {success_count}")
        print(f"❌ 失败频道数: {fail_count}")
        
        if full_programs_dict:
            # 生成完整XMLTV文件
            print(f"\n=== 生成完整XMLTV文件 ===")
            from datetime import timezone, timedelta
            beijing_tz = timezone(timedelta(hours=8))
            full_xmltv = generate_xmltv(full_programs_dict, date_str, beijing_tz)
            
            output_dir = 'output'
            output_file = os.path.join(output_dir, f'cctv_test_full_{date_str}.xml')
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(full_xmltv)
            
            print(f"✅ 完整XMLTV文件已保存到: {output_file}")
        
        print(f"\n=== 测试完成 ===")
        print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试结果: {'✅ 成功' if success_count > 0 else '❌ 失败'}")
        
    except Exception as e:
        print(f"\n=== 测试失败 ===")
        print(f"错误信息: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()