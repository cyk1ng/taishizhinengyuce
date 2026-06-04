#!/usr/bin/env python3
"""
Ollama连接诊断脚本
"""
import requests
import json
import sys

def test_ollama_connection():
    """测试Ollama连接"""
    print("=" * 60)
    print("Ollama连接诊断")
    print("=" * 60)
    
    # 测试Ollama服务
    print("\n1. 测试Ollama服务...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama服务运行正常")
            data = response.json()
            if "models" in data:
                print(f"   已安装模型: {len(data['models'])}个")
                for model in data["models"]:
                    print(f"   - {model['name']}")
        else:
            print(f"❌ Ollama服务响应异常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到Ollama服务")
        print("   请确认Ollama服务是否启动：")
        print("   运行命令: ollama serve")
        return False
    except Exception as e:
        print(f"❌ 测试Ollama服务失败: {str(e)}")
        return False
    
    # 测试模型生成
    print("\n2. 测试模型生成...")
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5:7b",
                "prompt": "你好",
                "stream": False
            },
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            print("✅ 模型生成正常")
            print(f"   响应: {result.get('response', '')[:50]}...")
        else:
            print(f"❌ 模型生成失败: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到Ollama服务")
        return False
    except Exception as e:
        print(f"❌ 测试模型生成失败: {str(e)}")
        return False
    
    # 检查配置文件
    print("\n3. 检查配置文件...")
    try:
        with open(".env", "r", encoding="utf-8") as f:
            env_content = f.read()
            if "COZE_INTEGRATION_MODEL_BASE_URL=http://localhost:11434/v1" in env_content:
                print("✅ .env配置正确")
            else:
                print("⚠️  .env配置可能不正确")
                print("   当前配置:")
                for line in env_content.split('\n'):
                    if 'COZE_INTEGRATION_MODEL_BASE_URL' in line:
                        print(f"   {line}")
    except FileNotFoundError:
        print("❌ 未找到.env文件")
        return False
    except Exception as e:
        print(f"❌ 读取.env文件失败: {str(e)}")
        return False
    
    try:
        with open("config/agent_llm_config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            model = config.get("config", {}).get("model", "")
            if model:
                print(f"✅ agent_llm_config.json配置正确: {model}")
            else:
                print("❌ agent_llm_config.json配置不正确")
                return False
    except FileNotFoundError:
        print("❌ 未找到config/agent_llm_config.json文件")
        return False
    except Exception as e:
        print(f"❌ 读取config/agent_llm_config.json文件失败: {str(e)}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)
    print("\n下一步：启动项目")
    print("  方法1: 运行快速启动脚本")
    print("    Windows: scripts\\start_with_ollama.bat")
    print("    Linux/Mac: ./scripts/start_with_ollama.sh")
    print("  方法2: 手动启动")
    print("    终端1: python src/main.py")
    print("    终端2: python -m http.server 8000 --directory frontend")
    print("    浏览器: http://localhost:8000")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_ollama_connection()
    sys.exit(0 if success else 1)
