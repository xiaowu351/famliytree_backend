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

    pending_after_resp = client.get(f'/api/trees/{tree_id}/corrections', headers=auth(owner_token))
    assert pending_after_resp.status_code == 200, pending_after_resp.get_json()
    pending_corrections = pending_after_resp.get_json()['data']['corrections']
    assert not any(item['id'] == correction_id for item in pending_corrections), pending_corrections

    approved_resp = client.get(
        f'/api/trees/{tree_id}/corrections?status=approved',
        headers=auth(owner_token)
    )
    assert approved_resp.status_code == 200, approved_resp.get_json()
    approved_corrections = approved_resp.get_json()['data']['corrections']
    approved_correction = next(item for item in approved_corrections if item['id'] == correction_id)
    assert approved_correction['status'] == 'approved', approved_correction
    assert approved_correction['handle_time'], approved_correction

    reject_resp = client.post(
        '/api/corrections',
        json={
            'tree_id': tree_id,
            'member_id': member_id,
            'proposed_desc': 'rejected desc',
            'reason': 'not enough proof'
        },
        headers=auth(submitter_token)
    )
    assert reject_resp.status_code == 201, reject_resp.get_json()
    reject_id = reject_resp.get_json()['data']['correction']['id']
    reject_handle_resp = client.post(
        f'/api/corrections/{reject_id}/handle',
        json={'action': 'reject'},
        headers=auth(owner_token)
    )
    assert reject_handle_resp.status_code == 200, reject_handle_resp.get_json()
    rejected_resp = client.get(
        f'/api/trees/{tree_id}/corrections?status=rejected',
        headers=auth(owner_token)
    )
    assert rejected_resp.status_code == 200, rejected_resp.get_json()
    rejected_corrections = rejected_resp.get_json()['data']['corrections']
    rejected_correction = next(item for item in rejected_corrections if item['id'] == reject_id)
    assert rejected_correction['status'] == 'rejected', rejected_correction

    repeat_resp = client.post(
        f'/api/corrections/{correction_id}/handle',
        json={'action': 'approve'},
        headers=auth(owner_token)
    )
    assert repeat_resp.status_code == 400, repeat_resp.get_json()

    print('member correction flow ok')


if __name__ == '__main__':
    main()
