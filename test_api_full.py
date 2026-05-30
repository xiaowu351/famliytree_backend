# -*- coding: utf-8 -*-
"""
Simple integration tests for backend API using Flask test_client.
Run with: python test_api_full.py
"""
import sys
import os
import io
import json

sys.path.insert(0, os.path.dirname(__file__))
from wxcloudrun.app import app

client = app.test_client()

def show(resp):
    try:
        data = resp.get_json()
    except Exception:
        data = resp.data.decode('utf-8')
    print(f"{resp.status_code} -> {data}")
    return data

print('1) GET /api/trees')
resp = client.get('/api/trees')
show(resp)

print('\n2) POST /api/trees')
resp = client.post('/api/trees', json={'surname':'测试','title':'测试谱'})
data = show(resp)
new_tree_id = None
if isinstance(data, dict) and data.get('code') == 0:
    items = data.get('data')
    if isinstance(items, list) and len(items):
        new_tree_id = items[0].get('id')
    else:
        # created returned the created tree object
        created = data.get('data')
        new_tree_id = created.get('id') if isinstance(created, dict) else None

if not new_tree_id:
    print('无法获取新家谱ID，尝试从 Location or data解析')

if new_tree_id:
    print(f'新家谱ID: {new_tree_id}')
    print('\n3) GET /api/trees/<id>')
    show(client.get(f'/api/trees/{new_tree_id}'))

    print('\n4) POST /api/members (创建成员)')
    member_payload = {'tree_id': new_tree_id, 'name': '张三', 'gender': 'M'}
    r = client.post('/api/members', json=member_payload)
    member_data = show(r)
    member_id = None
    if isinstance(member_data, dict) and member_data.get('code') == 0:
        d = member_data.get('data')
        if isinstance(d, dict) and d.get('id'):
            member_id = d.get('id')
        elif isinstance(d, dict) and d.get('member'):
            member_id = d['member'].get('id')

    print('\n5) GET /api/members?tree_id=...')
    show(client.get(f'/api/members?tree_id={new_tree_id}'))

    if member_id:
        print(f'创建成员ID: {member_id}')
        print('\n6) GET /api/members/<id>')
        show(client.get(f'/api/members/{member_id}'))

        print('\n7) PUT /api/members/<id> (更新名字)')
        show(client.put(f'/api/members/{member_id}', json={'name': '李四'}))

        print('\n8) DELETE /api/members/<id>')
        show(client.delete(f'/api/members/{member_id}'))

print('\n9) POST /api/count (inc)')
show(client.post('/api/count', json={'action':'inc'}))

print('\n10) POST /api/upload/avatar')
# use BytesIO to simulate file upload; field name may be `avatar` or `file` depending on implementation
file_content = io.BytesIO(b'PNGDATA')
data = {
    'avatar': (file_content, 'test.png')
}
# Flask test client expects 'data' with files; use content_type
resp = client.post('/api/upload/avatar', data=data, content_type='multipart/form-data')
show(resp)

print('\n测试完成')
