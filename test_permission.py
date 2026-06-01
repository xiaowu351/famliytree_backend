#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
权限系统集成测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from wxcloudrun.app import app

client = app.test_client()

def check(label, actual, expected):
    ok = actual == expected
    mark = '✓' if ok else '✗'
    print(f"  {mark} {label}: {actual} (期望: {expected})")
    return ok

passed = 0
failed = 0

print("=" * 50)
print("Step 3 权限系统集成测试")
print("=" * 50)

# ===== 1. 静默登录 =====
print("\n[1] 微信静默登录")
r = client.post('/api/auth/login', json={'code': 'test_perm_a'})
d = r.get_json()
ok = check("登录状态码", r.status_code, 200) and check("code=0", d.get('code'), 0)
token_a = (d.get('data') or {}).get('token', '')
if ok and token_a:
    passed += 1
    print(f"  ✓ Token A 获取成功: {token_a[:30]}...")
else:
    failed += 1

r_b = client.post('/api/auth/login', json={'code': 'test_perm_b'})
token_b = (r_b.get_json().get('data') or {}).get('token', '')
if token_b:
    passed += 1
    print(f"  ✓ Token B 获取成功: {token_b[:30]}...")
else:
    failed += 1
    print("  ✗ Token B 获取失败")

# ===== 2. 未登录被拒绝 =====
print("\n[2] 未登录访问写入接口")
r2 = client.post('/api/trees', json={'surname': '权', 'title': '权限测试谱'})
if check("未登录创建家谱 -> 401", r2.status_code, 401):
    passed += 1
else:
    failed += 1

# ===== 3. Owner 创建家谱 =====
print("\n[3] Owner(A) 创建家谱")
r3 = client.post('/api/trees', json={'surname': '权', 'title': '权限测试谱'},
                 headers={'Authorization': f'Bearer {token_a}'})
d3 = r3.get_json()
tree_id = (d3.get('data') or {}).get('id', '')
if check("Owner 创建家谱 -> 201", r3.status_code, 201) and tree_id:
    passed += 1
    print(f"  ✓ 新家谱 ID: {tree_id}")
else:
    failed += 1

# ===== 4. 游客查看权限 =====
print("\n[4] 角色 (role) 返回")
if tree_id:
    r4a = client.get(f'/api/trees/{tree_id}', headers={'Authorization': f'Bearer {token_a}'})
    role_a = (r4a.get_json().get('data') or {}).get('tree', {}).get('role', '')
    if check("Owner A role=owner", role_a, 'owner'):
        passed += 1
    else:
        failed += 1

    r4b = client.get(f'/api/trees/{tree_id}', headers={'Authorization': f'Bearer {token_b}'})
    role_b = (r4b.get_json().get('data') or {}).get('tree', {}).get('role', '')
    if check("User B (非授权) role=guest", role_b, 'guest'):
        passed += 1
    else:
        failed += 1

    r4n = client.get(f'/api/trees/{tree_id}')
    role_n = (r4n.get_json().get('data') or {}).get('tree', {}).get('role', '')
    if check("未登录 role=guest", role_n, 'guest'):
        passed += 1
    else:
        failed += 1

# ===== 5. 非授权修改被拒绝 =====
print("\n[5] 非授权 User B 修改 Owner A 的家谱")
if tree_id:
    r5 = client.put(f'/api/trees/{tree_id}', json={'region': '北京'},
                    headers={'Authorization': f'Bearer {token_b}'})
    if check("User B 修改 A 的家谱 -> 403", r5.status_code, 403):
        passed += 1
    else:
        failed += 1

# ===== 6. 邀请码流程 =====
print("\n[6] 邀请码协作授权流程")
if tree_id:
    # A 生成邀请码
    r6 = client.post(f'/api/trees/{tree_id}/invite',
                     headers={'Authorization': f'Bearer {token_a}'})
    d6 = r6.get_json()
    invite_code = (d6.get('data') or {}).get('invite_code', '')
    if check("Owner 生成邀请码 -> 200", r6.status_code, 200) and invite_code:
        passed += 1
        print(f"  ✓ 邀请码: {invite_code}")
    else:
        failed += 1

    # B 接受邀请
    if invite_code:
        r7 = client.post('/api/trees/accept_invite', json={'invite_code': invite_code},
                         headers={'Authorization': f'Bearer {token_b}'})
        if check("User B 接受邀请 -> 200", r7.status_code, 200):
            passed += 1
        else:
            failed += 1
            print(f"  ✗ 接受邀请返回: {r7.get_json()}")

        # B 再次查看权限应变为 editor
        r8 = client.get(f'/api/trees/{tree_id}', headers={'Authorization': f'Bearer {token_b}'})
        role_b2 = (r8.get_json().get('data') or {}).get('tree', {}).get('role', '')
        if check("User B 接受邀请后 role=editor", role_b2, 'editor'):
            passed += 1
        else:
            failed += 1

        # B 修改家谱（有权限）
        r9 = client.put(f'/api/trees/{tree_id}', json={'region': '上海'},
                        headers={'Authorization': f'Bearer {token_b}'})
        if check("User B (editor) 修改家谱 -> 200", r9.status_code, 200):
            passed += 1
        else:
            failed += 1
            print(f"  ✗ 返回: {r9.get_json()}")

print("\n" + "=" * 50)
total = passed + failed
print(f"测试结果：{passed}/{total} 通过")
if failed == 0:
    print("✅ 所有测试通过！")
else:
    print(f"❌ {failed} 项测试失败")
print("=" * 50)
