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
    token = login('test_stats_owner')
    assert token

    tree_resp = client.post(
        '/api/trees',
        json={'surname': 'Test', 'title': 'Stats Tree'},
        headers=auth(token)
    )
    assert tree_resp.status_code == 201, tree_resp.get_json()
    tree_id = tree_resp.get_json()['data']['id']

    parent_resp = client.post(
        '/api/members',
        json={
            'tree_id': tree_id,
            'name': 'Ancestor',
            'gender': 'M',
            'generation': 1,
            'is_notable': True,
            'achievements': 'Founder'
        },
        headers=auth(token)
    )
    assert parent_resp.status_code == 201, parent_resp.get_json()
    parent_id = parent_resp.get_json()['data']['member']['id']

    child_resp = client.post(
        '/api/members',
        json={
            'tree_id': tree_id,
            'parent_id': parent_id,
            'name': 'Daughter',
            'gender': 'F',
            'generation': 2
        },
        headers=auth(token)
    )
    assert child_resp.status_code == 201, child_resp.get_json()
    child_id = child_resp.get_json()['data']['member']['id']

    update_resp = client.put(
        f'/api/members/{child_id}',
        json={
            'name': 'Daughter',
            'gender': 'F',
            'is_notable': True,
            'achievements': 'Local teacher'
        },
        headers=auth(token)
    )
    assert update_resp.status_code == 200, update_resp.get_json()
    updated_child = update_resp.get_json()['data']['member']
    assert updated_child['parent_id'] == parent_id, updated_child

    stats_resp = client.get(f'/api/trees/{tree_id}/stats', headers=auth(token))
    assert stats_resp.status_code == 200, stats_resp.get_json()
    stats = stats_resp.get_json()['data']
    assert stats['total_count'] == 2, stats
    assert stats['male_count'] == 1, stats
    assert stats['female_count'] == 1, stats
    assert stats['generation_distribution'] == [
        {'generation': 1, 'count': 1},
        {'generation': 2, 'count': 1},
    ], stats

    notables_resp = client.get(f'/api/trees/{tree_id}/notables', headers=auth(token))
    assert notables_resp.status_code == 200, notables_resp.get_json()
    members = notables_resp.get_json()['data']['members']
    assert len(members) == 2, members
    notable_by_name = {member['name']: member for member in members}
    assert notable_by_name['Ancestor']['achievements'] == 'Founder'
    assert notable_by_name['Daughter']['achievements'] == 'Local teacher'
    assert notable_by_name['Daughter']['parent_id'] == parent_id

    print('stats and notables flow ok')


if __name__ == '__main__':
    main()
