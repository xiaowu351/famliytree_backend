#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os

# 添加backend目录到path
sys.path.insert(0, os.path.dirname(__file__))

# 导入app并初始化
from wxcloudrun.app import app

if __name__ == '__main__':
    print("正在测试后端API初始化...")
    try:
        with app.test_client() as client:
            # 测试家谱列表接口 (GET /api/trees)
            print("\n测试 GET /api/trees...")
            resp = client.get('/api/trees')
            print(f"状态码: {resp.status_code}")
            data = resp.get_json()
            print(f"响应: {data}")
            
            # 检查响应格式
            if 'code' in data and 'data' in data:
                print("✓ 响应格式正确")
                if data['code'] == 0:
                    print("✓ code=0 (成功)")
                else:
                    print(f"✗ code={data['code']} (应该是0)")
            else:
                print("✗ 响应格式错误")
                
        print("\n✓ 后端API初始化成功！")
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
