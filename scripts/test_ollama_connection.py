#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试本地Ollama连接
"""

import requests
import json
import sys
import os

def test_ollama_connection():
    """测试Ollama服务连接"""
    print("=" * 60)
    print("测试本地Ollama连接")
    print("=" * 60)
    
    # 1. 测试Ollama服务是否运行
    print("\n1. 测试Ollama服务...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama服务运行正常")
            data = response.json()
            print(f"   服务版本：{data.get('version', 'unknown')}")
            
            # 显示已安装的模型
            models = data.get('models', [])
            if models:
                print(f"\n   已安装的模型（{len(models)}个）：")
                for model in models:
                    name = model.get('name', 'unknown')
                    size = model.get('size', 0)
                    print(f"   - {name} ({size/1024/1024/1024:.2f}GB)")
            else:
                print("   ⚠️  尚未安装任何模型")
        else:
            print(f"❌ Ollama服务响应异常：{response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到Ollama服务")
        print("   请确认：")
        print("   1. Ollama是否已启动（运行：ollama serve）")
        print("   2. 服务地址是否为 http://localhost:11434")
        return False
    except requests.exceptions.Timeout:
        print("❌ 连接Ollama服务超时")
        return False
    except Exception as e:
        print(f"❌ 连接Ollama服务时出错：{str(e)}")
        return False
    
    # 2. 测试项目配置
    print("\n2. 检查项目配置...")
    
    # 检查.env文件
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        print(f"✅ 找到配置文件：{env_path}")
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'COZE_INTEGRATION_MODEL_BASE_URL=http://localhost:11434/v1' in content:
                print("✅ 配置正确：BASE_URL指向本地Ollama")
            else:
                print("⚠️  配置可能不正确，请检查BASE_URL设置")
    else:
        print(f"❌ 未找到配置文件：{env_path}")
        return False
    
    # 检查agent_llm_config.json
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'agent_llm_config.json')
    if os.path.exists(config_path):
        print(f"✅ 找到配置文件：{config_path}")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            model = config.get('config', {}).get('model', 'unknown')
            print(f"   配置模型：{model}")
            
            # 检查模型是否已安装
            model_installed = False
            if models:
                for installed_model in models:
                    if model in installed_model.get('name', ''):
                        model_installed = True
                        break
            
            if model_installed:
                print(f"✅ 模型 {model} 已安装")
            else:
                print(f"⚠️  模型 {model} 未安装")
                print(f"   请运行：ollama pull {model}")
                return False
    else:
        print(f"❌ 未找到配置文件：{config_path}")
        return False
    
    # 3. 测试模型调用
    print("\n3. 测试模型调用...")
    try:
        url = "http://localhost:11434/v1/chat/completions"
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "model": config.get('config', {}).get('model', 'qwen2.5:7b'),
            "messages": [
                {
                    "role": "user",
                    "content": "你好，请回复'测试成功'"
                }
            ],
            "stream": False
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            print(f"✅ 模型调用成功")
            print(f"   模型响应：{content}")
        else:
            print(f"❌ 模型调用失败：{response.status_code}")
            print(f"   响应内容：{response.text}")
            return False
    except Exception as e:
        print(f"❌ 调用模型时出错：{str(e)}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！项目可以正常使用本地Ollama")
    print("=" * 60)
    
    # 4. 提供启动指南
    print("\n🚀 启动项目：")
    print("   1. 确保Ollama服务正在运行：ollama serve")
    print("   2. 启动后端服务：python src/main.py")
    print("   3. 启动前端服务：python -m http.server 8000 --directory frontend")
    print("   4. 访问界面：http://localhost:8000")
    
    print("\n📚 更多信息：")
    print("   查看文档：README_本地模型.md")
    print("   快速开始：本地模型快速开始.md")
    print("   配置详情：本地模型配置总结.md")
    
    return True

if __name__ == "__main__":
    success = test_ollama_connection()
    sys.exit(0 if success else 1)
