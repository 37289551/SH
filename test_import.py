# 只测试导入部分
print("开始测试导入...")

# 尝试导入epgo模块的各个部分
parts = [
    "logging",
    "datetime",
    "xml.etree.ElementTree",
    "xml.dom.minidom",
    "time",
    "os",
    "yaml",
    "gzip",
    "shutil",
    "difflib"
]

for part in parts:
    try:
        __import__(part)
        print(f"✓ {part} 导入成功")
    except Exception as e:
        print(f"✗ {part} 导入失败: {e}")

# 测试自定义模块
try:
    from channels import CHANNELS
    print(f"✓ channels 导入成功")
except Exception as e:
    print(f"✗ channels 导入失败: {e}")
    import traceback
    traceback.print_exc()

try:
    from channel_mapping import normalize_channel_name
    print(f"✓ channel_mapping 导入成功")
except Exception as e:
    print(f"✗ channel_mapping 导入失败: {e}")
    import traceback
    traceback.print_exc()

print("导入测试完成")