# 测试脚本，用于逐步导入epgo.py的各个部分
print("开始测试...")

# 测试基本导入
try:
    import logging
    print("✓ logging导入成功")
except Exception as e:
    print(f"✗ logging导入失败: {e}")

try:
    from datetime import datetime, timedelta
    print("✓ datetime导入成功")
except Exception as e:
    print(f"✗ datetime导入失败: {e}")

try:
    import xml.etree.ElementTree as ET
    print("✓ xml.etree.ElementTree导入成功")
except Exception as e:
    print(f"✗ xml.etree.ElementTree导入失败: {e}")

try:
    from xml.dom import minidom
    print("✓ xml.dom.minidom导入成功")
except Exception as e:
    print(f"✗ xml.dom.minidom导入失败: {e}")

try:
    import time
    print("✓ time导入成功")
except Exception as e:
    print(f"✗ time导入失败: {e}")

try:
    import os
    print("✓ os导入成功")
except Exception as e:
    print(f"✗ os导入失败: {e}")

try:
    import yaml
    print("✓ yaml导入成功")
except Exception as e:
    print(f"✗ yaml导入失败: {e}")

try:
    import gzip
    print("✓ gzip导入成功")
except Exception as e:
    print(f"✗ gzip导入失败: {e}")

try:
    import shutil
    print("✓ shutil导入成功")
except Exception as e:
    print(f"✗ shutil导入失败: {e}")

try:
    import difflib
    print("✓ difflib导入成功")
except Exception as e:
    print(f"✗ difflib导入失败: {e}")

# 测试channels.py导入
try:
    from channels import CHANNELS
    print("✓ channels.py导入成功")
    print(f"  频道数量: {len(CHANNELS)}")
except Exception as e:
    print(f"✗ channels.py导入失败: {e}")
    import traceback
    traceback.print_exc()

# 测试channel_mapping.py导入
try:
    from channel_mapping import normalize_channel_name
    print("✓ channel_mapping.py导入成功")
except Exception as e:
    print(f"✗ channel_mapping.py导入失败: {e}")
    import traceback
    traceback.print_exc()

# 测试模块导入
try:
    from tvsou_epg import fetch_tvsou_programs
    print("✓ tvsou_epg.py导入成功")
except Exception as e:
    print(f"✗ tvsou_epg.py导入失败: {e}")
    import traceback
    traceback.print_exc()

try:
    from tvmao_epg import fetch_tvmao_programs
    print("✓ tvmao_epg.py导入成功")
except Exception as e:
    print(f"✗ tvmao_epg.py导入失败: {e}")
    import traceback
    traceback.print_exc()

try:
    from cctv_epg import fetch_cctv_programs
    print("✓ cctv_epg.py导入成功")
except Exception as e:
    print(f"✗ cctv_epg.py导入失败: {e}")
    import traceback
    traceback.print_exc()

# 最后测试完整的epgo.py导入
print("\n测试完整的epgo.py导入...")
try:
    import epgo
    print("✓ epgo.py导入成功")
except Exception as e:
    print(f"✗ epgo.py导入失败: {e}")
    import traceback
    traceback.print_exc()

print("测试完成")
