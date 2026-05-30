import os
from datetime import datetime

from flask import jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

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
from wxcloudrun.model import Counters, Member, Tree
from wxcloudrun.response import make_fail_response, make_success_response


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AVATAR_EXTENSIONS


@app.route('/counter/<int:counter_id>', methods=['GET'])
def get_counter(counter_id):
    counter = query_counterbyid(counter_id)
    if not counter:
        return make_fail_response('指定计数器未找到。', 404)
    return make_success_response({'id': counter.id, 'count': counter.count}, '查询成功。')


@app.route('/counter', methods=['POST'])
def create_counter():
    counter = insert_counter()
    return make_success_response({'id': counter.id, 'count': counter.count}, '计数器创建成功。', 201)


@app.route('/counter/<int:counter_id>', methods=['PUT'])
def update_counter(counter_id):
    payload = request.get_json(silent=True) or {}
    count = payload.get('count')
    if count is None or not isinstance(count, int):
        return make_fail_response('请求参数 count 必须为整数。', 400)
    counter = update_counterbyid(counter_id, count)
    if not counter:
        return make_fail_response('指定计数器未找到。', 404)
    return make_success_response({'id': counter.id, 'count': counter.count}, '更新成功。')


@app.route('/counter/<int:counter_id>', methods=['DELETE'])
def delete_counter(counter_id):
    if not delete_counterbyid(counter_id):
        return make_fail_response('指定计数器未找到。', 404)
    return make_success_response({}, '计数器删除成功。')


@app.route('/upload/avatar', methods=['POST'])
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


@app.route('/trees/<tree_id>', methods=['GET'])
def get_tree(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('未找到指定家谱。', 404)
    members = dao_get_members(tree_id)
    return make_success_response({'tree': tree.to_dict(), 'members': [member.to_dict() for member in members]}, '查询成功。')


@app.route('/trees', methods=['POST'])
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
    )
    from wxcloudrun import db
    db.session.add(tree)
    db.session.commit()
    return make_success_response({'id': tree.id}, '家谱创建成功。', 201)


@app.route('/trees/<tree_id>', methods=['PUT'])
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
    from wxcloudrun import db
    db.session.commit()
    return make_success_response(tree.to_dict(), '家谱更新成功。')


@app.route('/trees/<tree_id>', methods=['DELETE'])
def delete_tree(tree_id):
    success = delete_tree_with_members(tree_id)
    if not success:
        return make_fail_response('未找到指定家谱或家谱已被删除。', 404)
    return make_success_response({}, '家谱已永久删除，旗下所有族员数据已成功清空。')


@app.route('/trees/<tree_id>/members', methods=['GET'])
def list_members(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('未找到指定家谱。', 404)
    members = dao_get_members(tree_id)
    return make_success_response({'members': [member.to_dict() for member in members]}, '查询成功。')


@app.route('/trees/<tree_id>/members', methods=['POST'])
def create_member(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('未找到指定家谱。', 404)

    payload = request.get_json(silent=True) or {}
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
    from wxcloudrun import db
    db.session.add(member)
    db.session.commit()
    return make_success_response({'member': member.to_dict()}, '族员创建成功。', 201)


@app.route('/trees/<tree_id>/members/<member_id>', methods=['GET'])
def get_member(tree_id, member_id):
    member = get_member_by_id(member_id)
    if not member or member.tree_id != tree_id:
        return make_fail_response('未找到指定族员。', 404)
    return make_success_response({'member': member.to_dict()}, '查询成功。')


@app.route('/trees/<tree_id>/members/<member_id>', methods=['PUT'])
def update_member(tree_id, member_id):
    member = get_member_by_id(member_id)
    if not member or member.tree_id != tree_id:
        return make_fail_response('未找到指定族员。', 404)

    payload = request.get_json(silent=True) or {}
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
    from wxcloudrun import db
    db.session.commit()
    return make_success_response({'member': member.to_dict()}, '族员信息更新成功。')


@app.route('/trees/<tree_id>/members/<member_id>', methods=['DELETE'])
def delete_member(tree_id, member_id):
    member = get_member_by_id(member_id)
    if not member or member.tree_id != tree_id:
        return make_fail_response('未找到指定族员。', 404)

    deleted, message = delete_member_safe(member_id)
    if not deleted:
        return make_fail_response(message, 400)
    return make_success_response({'id': member_id}, '族员删除成功。')
