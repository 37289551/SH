#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入tm2模块
import tm2

def main():
    print("=== TM2卫视频道测试 ===")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        # 获取当前星期几
        current_weekday = tm2.get_current_weekday()
        print(f"当前星期: {current_weekday}")
        print()

        # 测试单个频道
        print("=" * 60)
        print("测试单个频道：安徽卫视")
        print("=" * 60)
        epg_data = tm2.fetch_channel_epg('AHTV1')
        
        if epg_data:
            print(f"\n频道名称: {epg_data['channel']}")
            print(f"频道代码: {epg_data['code']}")
            print(f"节目数量: {len(epg_data['programs'])}")
            
            if epg_data['programs']:
                print("\n前5个节目:")
                for i, prog in enumerate(epg_data['programs'][:5], 1):
                    episode = f"({prog['episode']})" if prog['episode'] else ""
                    print(f"  {i}. {prog['time']} - {prog['title']}{episode}")
            
        print("\n" + "=" * 60)
        print("测试多个卫视频道（前5个）")
        print("=" * 60)
        
        # 测试前5个频道（键为中文名，值为代码）
        test_channels = {
            '安徽卫视': 'AHTV1',
            '北京卫视': 'BTV1',
            '湖南卫视': 'HUNANTV1',
            '江苏卫视': 'JSTV1',
            '浙江卫视': 'ZJTV1'
        }
        
        satellite_programs = tm2.fetch_all_satellite_epg(channel_list=test_channels)
        
        print(f"\n成功获取 {len(satellite_programs)} 个频道的节目单")
        print("\n频道列表:")
        for channel_name in sorted(satellite_programs.keys()):
            program_count = len(satellite_programs[channel_name])
            print(f"  - {channel_name}: {program_count} 个节目")
        
        # 统计总节目数
        total_programs = sum(len(programs) for programs in satellite_programs.values())
        print(f"\n总计: {total_programs} 个节目")
        
        # 生成XMLTV文件
        print("\n" + "=" * 60)
        print("生成XMLTV文件")
        print("=" * 60)
        xmltv_content = tm2.generate_xmltv(satellite_programs)
        
        output_dir = 'output'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        today = datetime.now().strftime('%Y%m%d')
        output_file = os.path.join(output_dir, f'tvmao2_test_{today}.xml')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(xmltv_content)
        
        print(f"XMLTV文件已保存到: {output_file}")
        print(f"文件大小: {os.path.getsize(output_file) / 1024:.2f} KB")
        
        print("\n" + "=" * 60)
        print(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
