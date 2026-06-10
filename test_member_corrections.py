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
    owner_token = login('test_correction_owner')
    submitter_token = login('test_correction_submitter')
    assert owner_token
    assert submitter_token

    tree_resp = client.post(
        '/api/trees',
        json={'surname': 'Test', 'title': 'Correction Tree'},
        headers=auth(owner_token)
    )
    assert tree_resp.status_code == 201, tree_resp.get_json()
    tree_id = tree_resp.get_json()['data']['id']

    member_resp = client.post(
        '/api/members',
        json={
            'tree_id': tree_id,
            'name': 'Old Name',
            'gender': 'M',
            'birth_date': '1930',
            'desc': 'old desc'
        },
        headers=auth(owner_token)
    )
    assert member_resp.status_code == 201, member_resp.get_json()
    member_id = member_resp.get_json()['data']['member']['id']

    correction_resp = client.post(
        '/api/corrections',
        json={
            'tree_id': tree_id,
            'member_id': member_id,
            'proposed_name': 'New Name',
            'proposed_birth_date': '1925',
            'reason': 'verified against old family record'
        },
        headers=auth(submitter_token)
    )
    assert correction_resp.status_code == 201, correction_resp.get_json()
    correction_id = correction_resp.get_json()['data']['correction']['id']

    list_resp = client.get(f'/api/trees/{tree_id}/corrections', headers=auth(owner_token))
    assert list_resp.status_code == 200, list_resp.get_json()
    corrections = list_resp.get_json()['data']['corrections']
    target = next(item for item in corrections if item['id'] == correction_id)
    changed_fields = {item['field'] for item in target['changes']}
    assert changed_fields == {'name', 'birth_date'}, target['changes']

    handle_resp = client.post(
        f'/api/corrections/{correction_id}/handle',
        json={'action': 'approve'},
        headers=auth(owner_token)
    )
    assert handle_resp.status_code == 200, handle_resp.get_json()
    member = handle_resp.get_json()['data']['member']
    assert member['name'] == 'New Name'
    assert member['birth_date'] == '1925'
    assert member['desc'] == 'old desc'

    repeat_resp = client.post(
        f'/api/corrections/{correction_id}/handle',
        json={'action': 'approve'},
        headers=auth(owner_token)
    )
    assert repeat_resp.status_code == 400, repeat_resp.get_json()

    print('member correction flow ok')


if __name__ == '__main__':
    main()
