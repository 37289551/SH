#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPGO主程序测试脚本
用于测试整个EPGO系统的核心功能
"""

import sys
import os
from datetime import datetime
import shutil

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入配置和主程序
try:
    from epgo import main, load_config
    CONFIG = load_config()
except ImportError as e:
    print(f"导入EPGO模块失败: {e}")
    sys.exit(1)

def clear_test_files():
    """清理测试生成的文件"""
    print("=== 清理测试文件 ===")
    
    # 清理输出目录
    output_dir = CONFIG.get('output', {}).get('dir', 'output')
    if os.path.exists(output_dir):
        for filename in os.listdir(output_dir):
            if filename.endswith('.xml') or filename.endswith('.xml.gz'):
                file_path = os.path.join(output_dir, filename)
                os.remove(file_path)
                print(f"已删除: {file_path}")
    
    # 清理日志文件
    log_file = CONFIG.get('logging', {}).get('file_path', 'epgo.log')
    if os.path.exists(log_file):
        os.remove(log_file)
        print(f"已删除: {log_file}")
    
    # 清理缓存目录
    cache_dir = CONFIG.get('cache', {}).get('dir', 'cache')
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
        print(f"已删除: {cache_dir}")
    
    print()

def test_epgo_main():
    """测试EPGO主程序"""
    print("=== EPGO主程序测试 ===")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # 运行主程序
        main()
        
        print(f"\n主程序运行完成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("主程序测试成功！")
        
        # 检查输出文件
        output_dir = CONFIG.get('output', {}).get('dir', 'output')
        if os.path.exists(output_dir):
            output_files = [f for f in os.listdir(output_dir) if f.endswith('.xml') or f.endswith('.xml.gz')]
            if output_files:
                print(f"\n生成的输出文件:")
                for filename in output_files:
                    file_path = os.path.join(output_dir, filename)
                    file_size = os.path.getsize(file_path) / 1024
                    print(f"  {filename}: {file_size:.2f} KB")
            else:
                print("\n警告: 未生成任何输出文件！")
        else:
            print("\n警告: 输出目录不存在！")
            
    except Exception as e:
        print(f"\n主程序测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_config():
    """测试配置文件加载"""
    print("=== 配置文件测试 ===")
    
    try:
        # 加载配置
        CONFIG = load_config()
        
        print("配置文件加载成功！")
        print(f"\n配置摘要:")
        print(f"  源配置: {[source['name'] for source in CONFIG.get('sources', [])]}")
        print(f"  成功率阈值: {CONFIG.get('success_threshold', 80.0)}%")
        print(f"  输出目录: {CONFIG.get('output', {}).get('dir', 'output')}")
        print(f"  GZ压缩: {CONFIG.get('output', {}).get('gzip', True)}")
        print(f"  缓存启用: {CONFIG.get('cache', {}).get('enabled', True)}")
        print(f"  日志级别: {CONFIG.get('logging', {}).get('level', 'INFO')}")
        print(f"  频道模糊匹配: {CONFIG.get('channel_matching', {}).get('fuzzy_match', True)}")
        print()
        
        return True
    except Exception as e:
        print(f"配置文件测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("=== EPGO系统测试套件 ===")
    print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 测试配置文件
    config_ok = test_config()
    
    # 清理测试文件
    clear_test_files()
    
    # 测试主程序
    main_ok = test_epgo_main()
    
    print(f"\n=== 测试完成 ===")
    print(f"测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 汇总测试结果
    test_results = {
        "配置文件测试": "通过" if config_ok else "失败",
        "主程序测试": "通过" if main_ok else "失败"
    }
    
    print("\n测试结果汇总:")
    for test_name, result in test_results.items():
        status = "✓" if result == "通过" else "✗"
        print(f"  {status} {test_name}: {result}")
    
    # 检查是否所有测试都通过
    all_passed = all(result == "通过" for result in test_results.values())
    if all_passed:
        print("\n🎉 所有测试通过！EPGO系统正常工作。")
        return 0
    else:
        print("\n❌ 部分测试失败，请检查日志和配置。")
        return 1

if __name__ == "__main__":
    sys.exit(main())