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
    token = login('test_book_owner')
    assert token

    tree_resp = client.post(
        '/api/trees',
        json={'surname': 'Zhao', 'title': 'Book Tree', 'hall_name': 'Mingde Hall'},
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
            'rank_type': 'Founder',
            'birth_date': '1900',
            'desc': 'Family founder'
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
            'name': 'Child',
            'gender': 'F',
            'generation': 2,
            'birth_date': '1930'
        },
        headers=auth(token)
    )
    assert child_resp.status_code == 201, child_resp.get_json()

    compile_resp = client.post(
        f'/api/trees/{tree_id}/compile',
        json={'preface': 'A test preface', 'style': 'ink'},
        headers=auth(token)
    )
    assert compile_resp.status_code == 200, compile_resp.get_json()
    data = compile_resp.get_json()['data']
    assert data['filename'].endswith('.pdf'), data
    assert data['download_path'].startswith('/uploads/books/'), data
    assert data['member_count'] == 2, data

    download_resp = client.get(data['download_path'])
    assert download_resp.status_code == 200, download_resp.status_code
    assert download_resp.data.startswith(b'%PDF'), download_resp.data[:20]

    detail_resp = client.get(f'/api/trees/{tree_id}', headers=auth(token))
    assert detail_resp.status_code == 200, detail_resp.get_json()
    tree = detail_resp.get_json()['data']['tree']
    assert tree['preface'] == 'A test preface', tree

    email_resp = client.post(
        '/api/books/send_email',
        json={'tree_id': tree_id, 'email': 'person@example.com'},
        headers=auth(token)
    )
    assert email_resp.status_code in (200, 500), email_resp.get_json()
    if email_resp.status_code == 500:
        assert 'SMTP' in email_resp.get_json()['message'], email_resp.get_json()

    print('book compile flow ok')


if __name__ == '__main__':
    main()
