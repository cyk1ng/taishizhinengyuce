#!/usr/bin/env python3
"""批量修复工具文件：移除 ToolRuntime 参数，改用 request_context.get()"""
import re
import os

TOOLS_DIR = '/workspace/projects/src/tools'
FILES = [
    'data_fusion.py', 'decision.py', 'prediction.py', 'risk_alert.py',
    'scheduling.py', 'situation_awareness.py', 'staff_prediction.py',
    'weather_manager.py', 'workload_statistics.py',
]

for filename in FILES:
    filepath = os.path.join(TOOLS_DIR, filename)
    with open(filepath, 'r') as f:
        content = f.read()
    
    original = content
    
    # 1. Fix imports
    content = content.replace(
        'from langchain.tools import tool, ToolRuntime',
        'from langchain.tools import tool'
    )
    
    # 2. Add request_context import (after existing new_context import line, or standalone)
    if 'from coze_coding_utils.log.write_log import request_context' not in content:
        content = content.replace(
            'from coze_coding_utils.runtime_ctx.context import new_context',
            'from coze_coding_utils.runtime_ctx.context import new_context\nfrom coze_coding_utils.log.write_log import request_context'
        )
    
    # 3. Remove `runtime: ToolRuntime = None` from function signatures
    # Pattern 1: at end of params: `, runtime: ToolRuntime = None)` → `)`
    content = re.sub(r',\s*runtime\s*:\s*ToolRuntime\s*=\s*None\s*\)', ')', content)
    # Pattern 2: in middle of params: `runtime: ToolRuntime = None, ` → ``
    content = re.sub(r'runtime\s*:\s*ToolRuntime\s*=\s*None\s*,\s*', '', content)
    
    # 4. Replace `runtime.context if runtime else new_context(method="xxx")`
    content = re.sub(
        r'runtime\.context if runtime else new_context\(method="([^"]+)"\)',
        r'request_context.get() or new_context(method="\1")',
        content
    )
    
    # 5. Remove runtime from .invoke() calls: `"runtime": runtime` or `runtime=runtime`
    content = re.sub(r',\s*"runtime"\s*:\s*runtime\s*', '', content)
    
    # 6. Handle case where runtime is used without fallback (like `runtime.context`)
    # but be careful not to match already-replaced patterns
    content = re.sub(
        r'(?<!new_context\()runtime\.context(?! if runtime)',
        'request_context.get()',
        content
    )
    
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        diff_count = content.count('request_context.get()') - original.count('request_context.get()')
        print(f'✅ {filename} (修改了 {diff_count} 处)')
    else:
        print(f'⚠️  {filename} - 未修改')

print('\n批量修改完成!')