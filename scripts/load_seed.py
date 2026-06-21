"""通过 API 批量导入种子知识到本地知识库"""
import json, base64, gzip, urllib.request, urllib.parse, os, sys

def load_b64(path):
    with open(path) as f:
        return json.loads(gzip.decompress(base64.b64decode(f.read())))

def add_via_api(entries, api_url="http://localhost:5000/api/knowledge/add"):
    success, fail = 0, 0
    for i, entry in enumerate(entries):
        content = entry.get("content", "")
        source = entry.get("source", "unknown")
        if not content:
            continue
        data = json.dumps({"content": content, "source": source}).encode("utf-8")
        req = urllib.request.Request(api_url, data=data, headers={"Content-Type": "application/json"})
        try:
            resp = urllib.request.urlopen(req)
            result = json.loads(resp.read())
            if result.get("code") == 0:
                success += 1
            else:
                print(f"  ❌ [{i}] {result.get('msg', 'unknown')}")
                fail += 1
        except Exception as e:
            print(f"  ❌ [{i}] {e}")
            fail += 1
        if (i+1) % 10 == 0:
            print(f"  ...已处理 {i+1}/{len(entries)} 条")
    return success, fail

def main():
    root = os.getcwd()
    b64_path = os.path.join(root, "assets", "knowledge", "seed_data.b64")
    
    if not os.path.exists(b64_path):
        print(f"❌ 找不到数据文件: {b64_path}")
        print("请确保 assets/knowledge/seed_data.b64 存在")
        return
    
    print(f"📦 加载种子数据...")
    entries = load_b64(b64_path)
    print(f"   共 {len(entries)} 条 (业务规则: {sum(1 for e in entries if e.get('source')=='业务规则')}, 架构文档: {sum(1 for e in entries if e.get('source')!='业务规则')})")
    
    print(f"\n📤 通过 API 批量导入 (服务器需运行在 localhost:5000)...")
    ok, fail = add_via_api(entries)
    
    print(f"\n✅ 导入完成！成功 {ok} 条，失败 {fail} 条")
    if fail > 0:
        print("失败条目请检查服务器日志")

if __name__ == "__main__":
    main()
