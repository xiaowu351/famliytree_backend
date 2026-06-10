#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from wxcloudrun.app import app


client = app.test_client()


def login(code):
    resp = client.post('/api/auth/login', json={'code': code})
    data = resp.get_json()
    return (data.get('data') or {}).get('token', '')


def auth(token):
    return {'Authorization': f'Bearer {token}'}


def main():
    token = login('test_tree_detail_shape')
    assert token

    create_resp = client.post(
        '/api/trees',
        json={
            'surname': 'Zhao',
            'title': 'Zhao Family',
            'hall_name': 'Mingde Hall',
            'region': 'Henan Zhengzhou',
        },
        headers=auth(token),
    )
    assert create_resp.status_code == 201, create_resp.get_json()
    tree_id = create_resp.get_json()['data']['id']

    detail_resp = client.get(f'/api/trees/{tree_id}', headers=auth(token))
    assert detail_resp.status_code == 200, detail_resp.get_json()
    data = detail_resp.get_json()['data']
    tree = data.get('tree') or data

    assert tree['id'] == tree_id, tree
    assert tree['surname'] == 'Zhao', tree
    assert tree['title'] == 'Zhao Family', tree
    assert tree['hall_name'] == 'Mingde Hall', tree
    assert tree['region'] == 'Henan Zhengzhou', tree

    print('tree detail shape ok')


if __name__ == '__main__':
    main()
