from wxcloudrun.app import app


client = app.test_client()


def login(code):
    resp = client.post('/api/auth/login', json={'code': code})
    assert resp.status_code == 200, resp.get_data(as_text=True)
    return resp.get_json()['data']['token']


def auth(token):
    return {'Authorization': f'Bearer {token}'}


def test_tree_admin_modules_flow():
    owner_token = login('test_admin_owner')
    collaborator_token = login('test_admin_collab')

    tree_resp = client.post(
        '/api/trees',
        json={'surname': '管', 'title': '后台测试谱'},
        headers=auth(owner_token),
    )
    assert tree_resp.status_code == 201, tree_resp.get_data(as_text=True)
    tree_id = tree_resp.get_json()['data']['id']

    visit_resp = client.post(f'/api/trees/{tree_id}/visits', json={'page': 'tree_space'})
    assert visit_resp.status_code == 201

    invite_resp = client.post(f'/api/trees/{tree_id}/invite', headers=auth(owner_token))
    assert invite_resp.status_code == 200, invite_resp.get_data(as_text=True)
    invite_code = invite_resp.get_json()['data']['invite_code']

    accept_resp = client.post(
        '/api/trees/accept_invite',
        json={'invite_code': invite_code},
        headers=auth(collaborator_token),
    )
    assert accept_resp.status_code == 200, accept_resp.get_data(as_text=True)

    collab_resp = client.get(f'/api/trees/{tree_id}/collaborators', headers=auth(owner_token))
    assert collab_resp.status_code == 200, collab_resp.get_data(as_text=True)
    collaborators = collab_resp.get_json()['data']['collaborators']
    assert len(collaborators) >= 1

    announcement_resp = client.post(
        f'/api/trees/{tree_id}/announcements',
        json={'title': '修谱启动', 'content': '请大家补充资料。'},
        headers=auth(owner_token),
    )
    assert announcement_resp.status_code == 201, announcement_resp.get_data(as_text=True)
    announcement_id = announcement_resp.get_json()['data']['announcement']['id']

    list_announcements = client.get(f'/api/trees/{tree_id}/announcements')
    assert list_announcements.status_code == 200
    assert list_announcements.get_json()['data']['announcements'][0]['id'] == announcement_id

    visitors_resp = client.get(f'/api/trees/{tree_id}/visitors', headers=auth(owner_token))
    assert visitors_resp.status_code == 200, visitors_resp.get_data(as_text=True)
    assert len(visitors_resp.get_json()['data']['visitors']) >= 1

    logs_resp = client.get(f'/api/trees/{tree_id}/operation_logs', headers=auth(owner_token))
    assert logs_resp.status_code == 200, logs_resp.get_data(as_text=True)
    actions = [item['action'] for item in logs_resp.get_json()['data']['logs']]
    assert '生成协作邀请' in actions
    assert '发布动态' in actions

    delete_resp = client.delete(f'/api/announcements/{announcement_id}', headers=auth(owner_token))
    assert delete_resp.status_code == 200, delete_resp.get_data(as_text=True)
