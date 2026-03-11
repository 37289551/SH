#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入tmdf模块
import tmdf

def main():
    print("=== TMDF地方台测试 ===")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    try:
        # 获取当前星期几
        current_weekday = tmdf.get_current_weekday()
        print(f"当前星期: {current_weekday}")
        print()

        # 测试1：获取江苏省频道列表
        print("=" * 60)
        print("测试1：获取江苏省频道列表")
        print("=" * 60)

        # 创建Session
        session = tmdf.requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.tvmao.com/',
            'Connection': 'keep-alive'
        })

        # 访问首页建立会话
        try:
            session.get('https://www.tvmao.com/', timeout=10)
            print("已访问首页建立会话")
        except Exception as e:
            print(f"访问首页失败: {e}")

        channel_list = tmdf.fetch_province_channels('江苏', session=session)

        print(f"\n找到 {len(channel_list)} 个地方频道（不含卫视）:")
        for channel_name, channel_code in sorted(channel_list.items()):
            print(f"  - {channel_name}: {channel_code}")

        session.close()

        # 测试2：获取江苏省所有频道的EPG
        print("\n" + "=" * 60)
        print("测试2：获取江苏省所有频道EPG")
        print("=" * 60)

        jiangsu_epg = tmdf.fetch_province_epg('江苏', session=None)

        print(f"\n成功获取 {len(jiangsu_epg)} 个频道的节目单:")
        for channel_name in sorted(jiangsu_epg.keys()):
            program_count = len(jiangsu_epg[channel_name])
            print(f"  - {channel_name}: {program_count} 个节目")

        # 统计总节目数
        total_programs = sum(len(programs) for programs in jiangsu_epg.values())
        print(f"\n总计: {total_programs} 个节目")

        # 测试3：获取多个省份的EPG
        print("\n" + "=" * 60)
        print("测试3：获取多个省份EPG（江苏、北京）")
        print("=" * 60)

        provinces_epg = tmdf.fetch_all_provinces_epg(['江苏', '北京'])

        print(f"\n成功获取 {len(provinces_epg)} 个省的节目单:")
        for province_name, epg_dict in provinces_epg.items():
            print(f"\n{province_name}:")
            for channel_name in sorted(epg_dict.keys()):
                print(f"  - {channel_name}: {len(epg_dict[channel_name])} 个节目")

        # 统计所有节目数
        all_programs = sum(len(programs) for epg_dict in provinces_epg.values() for programs in epg_dict.values())
        print(f"\n总计: {all_programs} 个节目")

        # 生成XMLTV文件
        print("\n" + "=" * 60)
        print("生成XMLTV文件")
        print("=" * 60)

        xmltv_content = tmdf.generate_xmltv(provinces_epg)

        output_dir = os.path.join(project_root, 'output')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        today = datetime.now().strftime('%Y%m%d')
        output_file = os.path.join(output_dir, f'tvmao_df_test_{today}.xml')

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(xmltv_content)

        file_size_kb = os.path.getsize(output_file) / 1024
        print(f"XMLTV文件已保存到: {output_file}")
        print(f"文件大小: {file_size_kb:.2f} KB")

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
