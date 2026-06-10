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
    owner_token = login('test_report_owner')
    submitter_token = login('test_report_submitter')
    assert owner_token
    assert submitter_token

    tree_resp = client.post(
        '/api/trees',
        json={'surname': 'Test', 'title': 'Report Tree'},
        headers=auth(owner_token)
    )
    assert tree_resp.status_code == 201, tree_resp.get_json()
    tree_id = tree_resp.get_json()['data']['id']

    parent_resp = client.post(
        '/api/members',
        json={'tree_id': tree_id, 'name': 'Parent', 'gender': 'M'},
        headers=auth(owner_token)
    )
    assert parent_resp.status_code == 201, parent_resp.get_json()
    parent_id = parent_resp.get_json()['data']['member']['id']

    report_resp = client.post(
        '/api/reports',
        json={
            'tree_id': tree_id,
            'parent_id': parent_id,
            'relation_type': 'child',
            'name': 'Reported Child',
            'gender': 'F',
            'birth_date': '2000-01-01',
            'desc': 'submitted by relative'
        },
        headers=auth(submitter_token)
    )
    assert report_resp.status_code == 201, report_resp.get_json()
    report_id = report_resp.get_json()['data']['report']['id']

    list_resp = client.get(f'/api/trees/{tree_id}/reports', headers=auth(owner_token))
    assert list_resp.status_code == 200, list_resp.get_json()
    reports = list_resp.get_json()['data']['reports']
    assert any(item['id'] == report_id for item in reports)

    handle_resp = client.post(
        f'/api/reports/{report_id}/handle',
        json={'action': 'approve'},
        headers=auth(owner_token)
    )
    assert handle_resp.status_code == 200, handle_resp.get_json()
    member = handle_resp.get_json()['data']['member']
    assert member['name'] == 'Reported Child'
    assert member['parent_id'] == parent_id

    pending_after_resp = client.get(f'/api/trees/{tree_id}/reports', headers=auth(owner_token))
    assert pending_after_resp.status_code == 200, pending_after_resp.get_json()
    pending_reports = pending_after_resp.get_json()['data']['reports']
    assert not any(item['id'] == report_id for item in pending_reports), pending_reports

    approved_resp = client.get(
        f'/api/trees/{tree_id}/reports?status=approved',
        headers=auth(owner_token)
    )
    assert approved_resp.status_code == 200, approved_resp.get_json()
    approved_reports = approved_resp.get_json()['data']['reports']
    approved_report = next(item for item in approved_reports if item['id'] == report_id)
    assert approved_report['status'] == 'approved', approved_report
    assert approved_report['handle_time'], approved_report

    reject_resp = client.post(
        '/api/reports',
        json={
            'tree_id': tree_id,
            'parent_id': parent_id,
            'relation_type': 'child',
            'name': 'Rejected Child',
            'gender': 'M',
        },
        headers=auth(submitter_token)
    )
    assert reject_resp.status_code == 201, reject_resp.get_json()
    reject_id = reject_resp.get_json()['data']['report']['id']
    reject_handle_resp = client.post(
        f'/api/reports/{reject_id}/handle',
        json={'action': 'reject'},
        headers=auth(owner_token)
    )
    assert reject_handle_resp.status_code == 200, reject_handle_resp.get_json()
    rejected_resp = client.get(
        f'/api/trees/{tree_id}/reports?status=rejected',
        headers=auth(owner_token)
    )
    assert rejected_resp.status_code == 200, rejected_resp.get_json()
    rejected_reports = rejected_resp.get_json()['data']['reports']
    rejected_report = next(item for item in rejected_reports if item['id'] == reject_id)
    assert rejected_report['status'] == 'rejected', rejected_report

    repeat_resp = client.post(
        f'/api/reports/{report_id}/handle',
        json={'action': 'approve'},
        headers=auth(owner_token)
    )
    assert repeat_resp.status_code == 400, repeat_resp.get_json()

    print('member report flow ok')


if __name__ == '__main__':
    main()
