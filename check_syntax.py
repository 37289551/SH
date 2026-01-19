# 检查epgo.py的语法
import ast

try:
    with open('epgo.py', 'r', encoding='utf-8') as f:
        content = f.read()
    ast.parse(content)
    print("✓ epgo.py 语法检查通过")
except SyntaxError as e:
    print(f"✗ epgo.py 语法错误: {e}")
    print(f"  行号: {e.lineno}, 列号: {e.offset}")
    print(f"  错误行: {e.text}")
    print(f"  错误原因: {e.msg}")
except Exception as e:
    print(f"✗ 其他错误: {e}")
    import traceback
    traceback.print_exc()