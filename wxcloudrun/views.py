import os
from datetime import datetime, timedelta

from flask import jsonify, request, send_from_directory, g
from werkzeug.utils import secure_filename

from wxcloudrun import db
from wxcloudrun.app import (
    app,
    AVATAR_UPLOAD_DIR,
    ALLOWED_AVATAR_EXTENSIONS,
    MAX_AVATAR_SIZE,
    generate_id,
    get_file_size,
)
from wxcloudrun.dao import (
    delete_counterbyid,
    query_counterbyid,
    insert_counter,
    update_counterbyid,
    delete_tree_with_members,
    delete_member_safe,
    get_tree_by_id,
    get_member_by_id,
    get_members as dao_get_members,
    has_parent_cycle,
    clear_spouse_links,
    sync_spouse_link,
    validate_member_relation,
)
from wxcloudrun.model import Counters, Member, Tree, User, TreeCollaborator, CollaboratorInvite
from wxcloudrun.response import make_fail_response, make_success_response
from wxcloudrun.auth import generate_token, login_required, permission_check, get_current_user
import uuid
import requests

def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AVATAR_EXTENSIONS


@app.route('/api/auth/login', methods=['POST'])
def wx_login():
    payload = request.get_json(silent=True) or {}
    code = payload.get('code')
    if not code:
        return make_fail_response('缺少 code 参数。', 400)

    # 1. 微信静默登录、云托管 openid 或本地万能测试
    # 为方便测试，如果 code 是 test_xxx，我们不请求微信后台，直接以该 code 作为 openid 处理
    cloud_openid = request.headers.get('X-WX-OPENID') or request.headers.get('x-wx-openid')
    if cloud_openid:
        openid = cloud_openid
    elif code.startswith('test_'):
        openid = f"openid_{code}"
    else:
        # 正式微信登录
        # 微信小程序 appid 和 secret 由环境变量获取，或者在未配置时降级到测试 openid 逻辑
        appid = os.environ.get('WX_APPID')
        secret = os.environ.get('WX_SECRET')
        
        if not appid or not secret:
            # 降级模式：没有配置云开发环境变量，自动降级为本地测试模式
                app.logger.warning("WX_APPID 或 WX_SECRET 未配置，自动降级为测试 openid 分配。")
                openid = payload.get('dev_openid') or f"openid_mock_{code}"
        else:
            wx_url = f"https://api.weixin.qq.com/sns/jscode2session?appid={appid}&secret={secret}&js_code={code}&grant_type=authorization_code"
            try:
                res = requests.get(wx_url, timeout=5).json()
                openid = res.get('openid')
                if not openid:
                    app.logger.warning("WX_APPID 或 WX_SECRET 配置不对，微信登录失败。")
                    return make_fail_response(res.get('errmsg', '微信登录失败'), 400)
            except Exception as e:
                app.logger.exception("请求微信接口失败")
                return make_fail_response(f'请求微信接口失败: {str(e)}', 500)

    # 2. 查库或插入用户
    user = User.query.filter_by(openid=openid).first()
    if not user:
        user = User(openid=openid, nickname=payload.get('nickname', '微信用户'), avatar_url=payload.get('avatar_url', ''))
        db.session.add(user)
        db.session.commit()
    else:
        nickname = payload.get('nickname')
        avatar_url = payload.get('avatar_url')
        if nickname:
            user.nickname = nickname
        if avatar_url:
            user.avatar_url = avatar_url
        db.session.commit()

    # 3. 生成 JWT Token
    token = generate_token(user.id, openid)
    return make_success_response({
        'token': token,
        'user': user.to_dict()
    }, '登录成功')


@app.route('/api/count', methods=['POST'])
def count():
    counter = insert_counter()
    return make_success_response({'id': counter.id, 'count': counter.count}, '计数器创建成功。', 201)


@app.route('/api/upload/avatar', methods=['POST'])
def upload_avatar():
    avatar_file = request.files.get('avatar')
    if not avatar_file or avatar_file.filename == '':
        return make_fail_response('未找到上传文件。', 400)
    if not _allowed_file(avatar_file.filename):
        return make_fail_response('仅支持 JPG/PNG/WEBP 格式。', 400)
    if get_file_size(avatar_file) > MAX_AVATAR_SIZE:
        return make_fail_response('文件大小不可超过 2MB。', 400)

    filename = secure_filename(avatar_file.filename)
    if not filename:
        return make_fail_response('文件名无效。', 400)

    storage_name = f'{generate_id("avatar")}_{filename}'
    file_path = os.path.join(AVATAR_UPLOAD_DIR, storage_name)
    avatar_file.save(file_path)
    avatar_url = f'/uploads/avatars/{storage_name}'
    return make_success_response({'avatarUrl': avatar_url}, '头像上传成功。')


@app.route('/uploads/avatars/<filename>', methods=['GET'])
def serve_avatar(filename):
    return send_from_directory(AVATAR_UPLOAD_DIR, filename)


@app.route('/api/trees', methods=['GET'])
def get_trees():
    from sqlalchemy import func
    results = db.session.query(
        Tree,
        func.count(Member.id).label('member_count')
    ).outerjoin(Member, Tree.id == Member.tree_id)\
     .group_by(Tree.id)\
     .order_by(Tree.update_time.desc())\
     .all()
    
    tree_list = []
    for tree, member_count in results:
        t_dict = tree.to_dict()
        t_dict['member_count'] = member_count
        tree_list.append(t_dict)
    return make_success_response(tree_list, '查询成功。')


@app.route('/api/trees/<tree_id>', methods=['GET'])
def get_tree(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('未找到指定家谱。', 404)
    members = dao_get_members(tree_id)
    
    # 动态确定当前用户的权限角色
    role = 'guest'
    current_user = get_current_user()
    if current_user:
        if tree.creator_id == current_user.id:
            role = 'owner'
        else:
            collab = TreeCollaborator.query.filter_by(tree_id=tree_id, user_id=current_user.id).first()
            if collab:
                role = 'editor'

    tree_data = tree.to_dict()
    tree_data['role'] = role

    return make_success_response({'tree': tree_data, 'members': [member.to_dict() for member in members]}, '查询成功。')


@app.route('/api/trees', methods=['POST'])
@login_required
def create_tree():
    payload = request.get_json(silent=True) or {}
    surname = payload.get('surname')
    title = payload.get('title')
    if not surname or not title:
        return make_fail_response('surname 和 title 为必填字段。', 400)

    tree_id = generate_id('tree')
    now = datetime.now().isoformat()
    tree = Tree(
        id=tree_id,
        surname=surname,
        title=title,
        hall_name=payload.get('hall_name', ''),
        region=payload.get('region', ''),
        create_time=now,
        update_time=now,
        creator_id=g.current_user.id
    )
    db.session.add(tree)
    db.session.commit()
    return make_success_response({'id': tree.id}, '家谱创建成功。', 201)


@app.route('/api/trees/<tree_id>', methods=['PUT'])
@login_required
@permission_check(action='write')
def update_tree(tree_id):
    payload = request.get_json(silent=True) or {}
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('未找到指定家谱。', 404)

    tree.surname = payload.get('surname', tree.surname)
    tree.title = payload.get('title', tree.title)
    tree.hall_name = payload.get('hall_name', tree.hall_name)
    tree.region = payload.get('region', tree.region)
    tree.update_time = datetime.now().isoformat()
    db.session.commit()
    return make_success_response(tree.to_dict(), '家谱更新成功。')


@app.route('/api/trees/<tree_id>', methods=['DELETE'])
@login_required
@permission_check(action='delete')
def delete_tree(tree_id):
    success = delete_tree_with_members(tree_id)
    if not success:
        return make_fail_response('未找到指定家谱或家谱已被删除。', 404)
    return make_success_response({}, '家谱已永久删除，旗下所有族员数据已成功清空。')


@app.route('/api/members', methods=['GET'])
def list_members():
    tree_id = request.args.get('tree_id', '')
    if not tree_id:
        return make_fail_response('tree_id 为必填查询参数。', 400)
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('未找到指定家谱。', 404)
    members = dao_get_members(tree_id)
    return make_success_response({'members': [member.to_dict() for member in members]}, '查询成功。')


@app.route('/api/members', methods=['POST'])
@login_required
@permission_check(action='write')
def create_member():
    payload = request.get_json(silent=True) or {}
    tree_id = payload.get('tree_id', '')
    if not tree_id:
        return make_fail_response('tree_id 为必填字段。', 400)
    
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('未找到指定家谱。', 404)

    name = payload.get('name')
    gender = payload.get('gender')
    if not name or not gender:
        return make_fail_response('name 和 gender 为必填字段。', 400)

    parent_id = payload.get('parent_id', '') or ''
    spouse_id = payload.get('spouse_id', '') or ''
    ok, message = validate_member_relation(tree_id, parent_id, spouse_id)
    if not ok:
        return make_fail_response(message, 400)

    if has_parent_cycle(None, parent_id):
        return make_fail_response('父节点关系会导致循环。', 400)

    member_id = generate_id('member')
    now = datetime.now().isoformat()
    member = Member(
        id=member_id,
        tree_id=tree_id,
        name=name,
        gender=gender,
        is_alive=payload.get('is_alive', True),
        parent_id=parent_id,
        spouse_id='',
        desc=payload.get('desc', ''),
        create_time=now,
        generation=payload.get('generation', 1),
        avatar_url=payload.get('avatar_url', ''),
        surname=payload.get('surname', ''),
        rank_type=payload.get('rank_type', ''),
        marital_status=payload.get('marital_status', ''),
        birth_order=payload.get('birth_order', ''),
        alias_name=payload.get('alias_name', ''),
        other_name=payload.get('other_name', ''),
        style_name=payload.get('style_name', ''),
        pseudonym=payload.get('pseudonym', ''),
        birth_date=payload.get('birth_date', ''),
        death_date=payload.get('death_date', ''),
        current_residence=payload.get('current_residence', ''),
        spouse_father=payload.get('spouse_father', ''),
        education_school=payload.get('education_school', ''),
        education_major=payload.get('education_major', ''),
        education_degree=payload.get('education_degree', ''),
        occupation=payload.get('occupation', ''),
        is_spouse=False,
        spouse_type=payload.get('spouse_type', '配'),
        education_status=payload.get('education_status', '毕业'),
        adoption_type=payload.get('adoption_type', '生'),
    )

    if spouse_id:
        spouse = get_member_by_id(spouse_id)
        if spouse:
            sync_spouse_link(member, spouse)
        else:
            return make_fail_response('指定配偶不存在。', 400)
    db.session.add(member)
    db.session.commit()
    return make_success_response({'member': member.to_dict()}, '族员创建成功。', 201)


@app.route('/api/members/<member_id>', methods=['GET'])
def get_member(member_id):
    member = get_member_by_id(member_id)
    if not member:
        return make_fail_response('未找到指定族员。', 404)
    return make_success_response({'member': member.to_dict()}, '查询成功。')


@app.route('/api/members/<member_id>', methods=['PUT'])
@login_required
@permission_check(action='write')
def update_member(member_id):
    member = get_member_by_id(member_id)
    if not member:
        return make_fail_response('未找到指定族员。', 404)

    payload = request.get_json(silent=True) or {}
    tree_id = member.tree_id
    parent_id = payload.get('parent_id', member.parent_id)
    spouse_id = payload.get('spouse_id', member.spouse_id)
    ok, message = validate_member_relation(tree_id, parent_id, spouse_id, current_member_id=member_id)
    if not ok:
        return make_fail_response(message, 400)

    if parent_id and has_parent_cycle(member_id, parent_id):
        return make_fail_response('父节点关系会导致循环。', 400)

    if member.spouse_id and member.spouse_id != spouse_id:
        clear_spouse_links(member)

    if spouse_id:
        spouse = get_member_by_id(spouse_id)
        if spouse:
            sync_spouse_link(member, spouse)
        else:
            return make_fail_response('指定配偶不存在。', 400)

    member.name = payload.get('name', member.name)
    member.gender = payload.get('gender', member.gender)
    member.is_alive = payload.get('is_alive', member.is_alive)
    member.parent_id = parent_id
    member.desc = payload.get('desc', member.desc)
    member.generation = payload.get('generation', member.generation)
    member.avatar_url = payload.get('avatar_url', member.avatar_url)
    member.surname = payload.get('surname', member.surname)
    member.rank_type = payload.get('rank_type', member.rank_type)
    member.marital_status = payload.get('marital_status', member.marital_status)
    member.birth_order = payload.get('birth_order', member.birth_order)
    member.alias_name = payload.get('alias_name', member.alias_name)
    member.other_name = payload.get('other_name', member.other_name)
    member.style_name = payload.get('style_name', member.style_name)
    member.pseudonym = payload.get('pseudonym', member.pseudonym)
    member.birth_date = payload.get('birth_date', member.birth_date)
    member.death_date = payload.get('death_date', member.death_date)
    member.current_residence = payload.get('current_residence', member.current_residence)
    member.spouse_father = payload.get('spouse_father', member.spouse_father)
    member.education_school = payload.get('education_school', member.education_school)
    member.education_major = payload.get('education_major', member.education_major)
    member.education_degree = payload.get('education_degree', member.education_degree)
    member.occupation = payload.get('occupation', member.occupation)
    member.spouse_type = payload.get('spouse_type', member.spouse_type)
    member.education_status = payload.get('education_status', member.education_status)
    member.adoption_type = payload.get('adoption_type', member.adoption_type)

    member.desc = payload.get('desc', member.desc)
    db.session.commit()
    return make_success_response({'member': member.to_dict()}, '族员信息更新成功。')


@app.route('/api/members/<member_id>', methods=['DELETE'])
@login_required
@permission_check(action='write')
def delete_member(member_id):
    member = get_member_by_id(member_id)
    if not member:
        return make_fail_response('未找到指定族员。', 404)

    deleted, message = delete_member_safe(member_id)
    if not deleted:
        return make_fail_response(message, 400)
    return make_success_response({'id': member_id}, '族员删除成功。')


@app.route('/api/trees/<tree_id>/invite', methods=['POST'])
@login_required
def create_invite(tree_id):
    # 只有家谱所有者 (Owner) 才能生成协作邀请
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('家谱不存在。', 404)
    if tree.creator_id != g.current_user.id:
        return make_fail_response('只有谱主才能生成协作邀请链接。', 403)

    invite_code = str(uuid.uuid4())
    # 设置 7 天有效期
    expire_time = datetime.now() + timedelta(days=7)
    
    invite = CollaboratorInvite(
        tree_id=tree_id,
        invite_code=invite_code,
        is_used=False,
        expire_time=expire_time
    )
    db.session.add(invite)
    db.session.commit()

    return make_success_response({'invite_code': invite_code}, '邀请码创建成功')


@app.route('/api/trees/accept_invite', methods=['POST'])
@login_required
def accept_invite():
    payload = request.get_json(silent=True) or {}
    invite_code = payload.get('invite_code')
    if not invite_code:
        return make_fail_response('缺少 invite_code 参数。', 400)

    invite = CollaboratorInvite.query.filter_by(invite_code=invite_code).first()
    if not invite:
        return make_fail_response('该协作邀请链接不存在。', 404)
    
    if invite.is_used:
        return make_fail_response('该邀请链接已被使用或已被接受。', 400)
    
    if invite.expire_time < datetime.now():
        return make_fail_response('该邀请链接已失效。', 400)

    tree = get_tree_by_id(invite.tree_id)
    if not tree:
        return make_fail_response('对应家谱已不存在。', 404)

    # 1. 检查是否是创建者
    if tree.creator_id == g.current_user.id:
        return make_success_response({}, '您是该家谱的创建者，无需再次绑定。')

    # 2. 检查是否已经是协作修谱人
    collab = TreeCollaborator.query.filter_by(tree_id=invite.tree_id, user_id=g.current_user.id).first()
    if collab:
        return make_success_response({}, '您已是该家谱的协作修谱人，无需重复接受。')

    # 3. 写入关联表
    new_collab = TreeCollaborator(tree_id=invite.tree_id, user_id=g.current_user.id)
    db.session.add(new_collab)
    
    # 微信云开发可以允许多人使用一个邀请，或者标记已被使用，此处标记为已被使用
    invite.is_used = True
    db.session.commit()

    return make_success_response({}, '接受邀请成功，已成为本家谱协作修谱人！')
