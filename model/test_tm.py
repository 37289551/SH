#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from datetime import datetime

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tvmao_epg import fetch_tvmao_programs, generate_xmltv

def main():
    print("=== TM节目测试 ===")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # 调用TVMao节目单抓取函数
        print("1. 央视节目单...")
        cctv_programs = fetch_tvmao_programs('cctv')
        
        print(f"2. 卫视频道节目单...")
        satellite_programs = fetch_tvmao_programs('satellite')
        
        # 合并节目单
        programs_dict = {}
        programs_dict.update(cctv_programs)
        programs_dict.update(satellite_programs)
        
        print(f"完成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"成功 {len(programs_dict)} 个频道的节目单")
        print()
        
        # 打印频道列表
        print("=== 频道列表 ===")
        for channel_name in sorted(programs_dict.keys()):
            program_count = len(programs_dict[channel_name])
            print(f"  {channel_name}: {program_count} 个节目")
        print()
        
        # 统计总节目数
        total_programs = sum(len(programs) for programs in programs_dict.values())
        print(f"总计: {total_programs} 个节目")
        print()
        
        # 生成XMLTV文件
        print("=== 生成XMLTV文件 ===")
        xmltv_content = generate_xmltv(programs_dict)
        
        # 保存XMLTV文件
        output_dir = 'output'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        today = datetime.now().strftime('%Y%m%d')
        output_file = os.path.join(output_dir, f'tvmao_test_{today}.xml')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(xmltv_content)
        
        print(f"XMLTV文件已保存到: {output_file}")
        print(f"文件大小: {os.path.getsize(output_file) / 1024:.2f} KB")
        print()
        
        print("测试完成！")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()