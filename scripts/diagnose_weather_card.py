#!/usr/bin/env python3
"""
天气卡片问题诊断脚本
"""

import re
import sys

def check_javascript_function(file_path):
    """检查JavaScript函数定义"""
    print(f"正在检查 {file_path}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查showWeatherModal函数
    if 'function showWeatherModal' not in content:
        print("❌ 错误：showWeatherModal 函数未定义")
        return False
    else:
        print("✅ showWeatherModal 函数已定义")

    # 检查函数签名
    pattern = r'function showWeatherModal\((.*?)\)'
    match = re.search(pattern, content)
    if match:
        params = match.group(1)
        print(f"✅ 函数参数：{params}")
        if 'event' not in params:
            print("⚠️  警告：函数没有event参数")
            return False
    else:
        print("❌ 错误：无法解析函数签名")
        return False

    # 检查函数体中的event处理
    if 'event.preventDefault()' not in content:
        print("⚠️  警告：未找到event.preventDefault()")
    if 'event.stopPropagation()' not in content:
        print("⚠️  警告：未找到event.stopPropagation()")

    # 检查语法错误（括号匹配）
    lines = content.split('\n')
    open_braces = 0
    function_started = False
    function_line = 0

    for i, line in enumerate(lines):
        if 'function showWeatherModal' in line:
            function_started = True
            function_line = i + 1
            open_braces = line.count('{') - line.count('}')
        elif function_started:
            open_braces += line.count('{') - line.count('}')
            if open_braces == 0:
                print(f"✅ 函数正确闭合（第 {function_line}-{i+1} 行）")
                break

    if open_braces != 0:
        print(f"❌ 错误：函数未正确闭合（未闭合的大括号数：{open_braces}）")
        return False

    return True

def check_html_binding(file_path):
    """检查HTML中的事件绑定"""
    print(f"\n正在检查 {file_path}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找weather-card
    if 'weather-card' not in content:
        print("❌ 错误：未找到weather-card元素")
        return False
    else:
        print("✅ weather-card元素存在")

    # 检查onclick属性
    if 'onclick="showWeatherModal(event)"' in content or "onclick='showWeatherModal(event)'" in content:
        print("✅ onclick事件绑定正确")
    else:
        print("⚠️  警告：onclick事件绑定可能不正确")
        print("   请确认HTML中是否正确绑定了showWeatherModal(event)")

    return True

def check_js_import(file_path):
    """检查JavaScript文件是否正确引入"""
    print(f"\n正在检查 {file_path}...")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'app.js' in content:
        print("✅ app.js文件已引入")
        return True
    else:
        print("❌ 错误：app.js文件未引入")
        return False

def main():
    print("=" * 60)
    print("天气卡片问题诊断")
    print("=" * 60)

    # 检查JavaScript函数
    js_ok = check_javascript_function('/workspace/projects/frontend/js/app.js')

    # 检查HTML事件绑定
    html_ok = check_html_binding('/workspace/projects/frontend/index.html')

    # 检查JS引入
    import_ok = check_js_import('/workspace/projects/frontend/index.html')

    print("\n" + "=" * 60)
    print("诊断结果")
    print("=" * 60)

    if js_ok and html_ok and import_ok:
        print("✅ 所有检查通过！")
        print("\n可能的问题：")
        print("1. 浏览器缓存问题 - 请尝试清除缓存并刷新页面")
        print("2. JavaScript加载时机问题 - 请确保DOMContentLoaded后再调用")
        print("3. 其他JavaScript错误 - 请检查浏览器控制台")
        return True
    else:
        print("❌ 存在问题，请根据上述提示修复")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
