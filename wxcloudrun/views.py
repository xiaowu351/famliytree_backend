import os
import re
from datetime import datetime, timedelta

from flask import jsonify, request, send_from_directory, g
from werkzeug.utils import secure_filename

from wxcloudrun import db
from wxcloudrun.app import (
    app,
    AVATAR_UPLOAD_DIR,
    BOOK_UPLOAD_DIR,
    ALBUM_UPLOAD_DIR,
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
from wxcloudrun.model import (
    Counters,
    Member,
    Tree,
    User,
    TreeCollaborator,
    CollaboratorInvite,
    MemberReport,
    MemberCorrection,
    TreeAnnouncement,
    AnnouncementLike,
    AnnouncementComment,
    AnnouncementShare,
    TreeVisit,
    OperationLog,
    TreePrivacySetting,
    GenealogyArticle,
    VillageProfile,
    FamilyAlbum,
    FamilyPhoto,
    AlbumSetting,
    MemberBinding,
)
from wxcloudrun.book_compiler import build_book_html, build_book_payload, render_pdf, send_book_email
from wxcloudrun.response import make_fail_response, make_success_response
from wxcloudrun.auth import generate_token, login_required, permission_check, get_current_user
import uuid
import requests

def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AVATAR_EXTENSIONS


def _log_operation(tree_id, action, detail='', user_id=None, category='system'):
    try:
        current_user = getattr(g, 'current_user', None)
        log = OperationLog(
            tree_id=tree_id,
            user_id=user_id if user_id is not None else (current_user.id if current_user else None),
            category=category,
            action=action,
            detail=detail or ''
        )
        db.session.add(log)
    except Exception:
        app.logger.exception('记录操作日志失败')


def _format_time(value):
    if not value:
        return ''
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _get_user_name(user_id, default='匿名用户'):
    if not user_id:
        return default
    user = User.query.get(user_id)
    return user.nickname if user and user.nickname else default


ANNOUNCEMENT_CATEGORIES = {
    'notice': '族务通知',
    'progress': '修谱进展',
    'collection': '资料征集',
}


LOG_CATEGORIES = {
    'content': '内容管理',
    'member': '族员管理',
    'approval': '审核处理',
    'permission': '权限协作',
    'system': '系统记录',
}


PRIVACY_VISIBILITY_VALUES = {'public', 'private'}
PRIVACY_SCOPE_VALUES = {'manager', 'family', 'blood', 'hidden'}
PRIVACY_EDIT_SCOPE_VALUES = {'none', 'bound', 'blood'}

ARTICLE_CATEGORIES = [
    {'key': 'preface', 'label': '序'},
    {'key': 'portrait_praise', 'label': '像赞'},
    {'key': 'rules', 'label': '谱例'},
    {'key': 'theory', 'label': '谱论'},
    {'key': 'origin', 'label': '源流'},
    {'key': 'ancestral_memorial', 'label': '宗祠祭祀'},
    {'key': 'literature', 'label': '艺文著作'},
    {'key': 'generation_poem', 'label': '字辈派语'},
    {'key': 'celebration', 'label': '余庆录'},
    {'key': 'biography', 'label': '传记'},
    {'key': 'family_rules', 'label': '家规祖训'},
    {'key': 'contract_property', 'label': '契据族产'},
    {'key': 'appendix', 'label': '附录'},
    {'key': 'postscript', 'label': '跋文'},
]
ARTICLE_CATEGORY_MAP = {item['key']: item['label'] for item in ARTICLE_CATEGORIES}

NOTABLE_CATEGORIES = [
    {'key': 'editorial', 'label': '编委员'},
    {'key': 'merit', 'label': '功名录'},
    {'key': 'imperial_exam', 'label': '科名录'},
    {'key': 'elite', 'label': '精英录'},
]
NOTABLE_CATEGORY_MAP = {item['key']: item['label'] for item in NOTABLE_CATEGORIES}


def _get_or_create_privacy_setting(tree_id):
    setting = TreePrivacySetting.query.filter_by(tree_id=tree_id).first()
    if setting:
        return setting
    setting = TreePrivacySetting(tree_id=tree_id)
    db.session.add(setting)
    db.session.flush()
    return setting


def _get_or_create_village_profile(tree):
    profile = VillageProfile.query.filter_by(tree_id=tree.id).first()
    if profile:
        return profile
    village_name = tree.region or (f'{tree.surname}氏村庄' if tree.surname else '本庄')
    intro = (
        f'{village_name}与{tree.surname or ""}氏家族传承密切相关。'
        '这里可记录村庄沿革、迁徙源流、祠堂文化、民俗活动和本庄人物。'
    )
    profile = VillageProfile(
        tree_id=tree.id,
        village_name=village_name,
        alias_name='待完善',
        area_text='待完善',
        region=tree.region or '待完善',
        location='待完善',
        famous_people='待完善',
        intro=intro,
        cover_url='',
    )
    db.session.add(profile)
    db.session.flush()
    return profile


DEFAULT_ALBUM_TITLES = ['合影相册', '活动相册', '坟墓位置']


def _get_or_create_album_setting(tree_id):
    setting = AlbumSetting.query.filter_by(tree_id=tree_id).first()
    if setting:
        return setting
    setting = AlbumSetting(tree_id=tree_id)
    db.session.add(setting)
    db.session.flush()
    return setting


def _ensure_default_albums(tree_id):
    existing = FamilyAlbum.query.filter_by(tree_id=tree_id).all()
    if existing:
        return existing
    albums = []
    for title in DEFAULT_ALBUM_TITLES:
        album = FamilyAlbum(tree_id=tree_id, title=title)
        db.session.add(album)
        albums.append(album)
    db.session.flush()
    return albums


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


@app.route('/uploads/albums/<filename>', methods=['GET'])
def serve_album_photo(filename):
    return send_from_directory(ALBUM_UPLOAD_DIR, filename)


@app.route('/api/trees/<tree_id>/albums', methods=['GET'])
def get_tree_albums(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)

    albums = _ensure_default_albums(tree_id)
    setting = _get_or_create_album_setting(tree_id)
    photos = FamilyPhoto.query.filter_by(tree_id=tree_id).order_by(FamilyPhoto.create_time.desc()).all()
    album_items = []
    for album in sorted(albums, key=lambda item: item.id):
        item = album.to_dict()
        album_photos = [photo for photo in photos if photo.album_id == album.id]
        item['photo_count'] = len(album_photos)
        cover = album.cover_url or (album_photos[0].image_url if album_photos else '')
        item['cover_url'] = cover
        album_items.append(item)
    photo_items = [photo.to_dict() for photo in photos]
    db.session.commit()
    return make_success_response({
        'albums': album_items,
        'photos': photo_items,
        'setting': setting.to_dict(),
    }, 'success')


@app.route('/api/trees/<tree_id>/albums', methods=['POST'])
@login_required
@permission_check(action='write')
def create_tree_album(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)
    payload = request.get_json(silent=True) or {}
    title = (payload.get('title') or '').strip()
    if not title:
        return make_fail_response('title is required.', 400)
    album = FamilyAlbum(tree_id=tree_id, title=title[:128])
    db.session.add(album)
    _log_operation(tree_id, '创建相册', title[:120], category='content')
    db.session.commit()
    return make_success_response({'album': album.to_dict()}, 'success', 201)


@app.route('/api/trees/<tree_id>/album_settings', methods=['GET'])
@login_required
@permission_check(action='write')
def get_album_setting(tree_id):
    setting = _get_or_create_album_setting(tree_id)
    db.session.commit()
    return make_success_response({'setting': setting.to_dict()}, 'success')


@app.route('/api/trees/<tree_id>/album_settings', methods=['PUT'])
@login_required
@permission_check(action='write')
def update_album_setting(tree_id):
    setting = _get_or_create_album_setting(tree_id)
    payload = request.get_json(silent=True) or {}
    if 'record_location' in payload:
        setting.record_location = bool(payload.get('record_location'))
    db.session.add(setting)
    _log_operation(tree_id, '更新相册设置', '拍照位置记录设置已更新', category='content')
    db.session.commit()
    return make_success_response({'setting': setting.to_dict()}, 'success')


@app.route('/api/trees/<tree_id>/photos/upload', methods=['POST'])
@login_required
@permission_check(action='write')
def upload_album_photo(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)
    photo_file = request.files.get('photo')
    if not photo_file or photo_file.filename == '':
        return make_fail_response('未找到上传文件。', 400)
    if not _allowed_file(photo_file.filename):
        return make_fail_response('仅支持 JPG/PNG/WEBP 格式。', 400)
    if get_file_size(photo_file) > MAX_AVATAR_SIZE:
        return make_fail_response('文件大小不可超过 2MB。', 400)

    album_id = request.form.get('album_id')
    album = None
    if album_id:
        try:
            album = FamilyAlbum.query.get(int(album_id))
        except (TypeError, ValueError):
            album = None
        if not album or album.tree_id != tree_id:
            return make_fail_response('Album not found.', 404)
    if not album:
        album = _ensure_default_albums(tree_id)[0]

    filename = secure_filename(photo_file.filename)
    if not filename:
        return make_fail_response('文件名无效。', 400)
    storage_name = f'{generate_id("album")}_{filename}'
    file_path = os.path.join(ALBUM_UPLOAD_DIR, storage_name)
    photo_file.save(file_path)
    image_url = f'/uploads/albums/{storage_name}'
    photo = FamilyPhoto(
        tree_id=tree_id,
        album_id=album.id,
        image_url=image_url,
        caption=(request.form.get('caption') or '').strip()[:255],
        location_text=(request.form.get('location_text') or '').strip()[:255],
        uploader_id=g.current_user.id,
    )
    album.cover_url = album.cover_url or image_url
    db.session.add(photo)
    db.session.add(album)
    _log_operation(tree_id, '上传相册照片', album.title, category='content')
    db.session.commit()
    return make_success_response({'photo': photo.to_dict(), 'album': album.to_dict()}, 'success', 201)


def _public_url(path):
    base_url = request.host_url.rstrip('/')
    return f'{base_url}{path}'


def _book_filename(tree_id, style='', unique=False):
    safe_tree_id = re.sub(r'[^a-zA-Z0-9_-]', '_', tree_id)
    if unique:
        safe_style = re.sub(r'[^a-zA-Z0-9_-]', '_', style or 'book')
        return f'book_{safe_tree_id}_{safe_style}_{int(datetime.now().timestamp())}.pdf'
    return f'book_{safe_tree_id}.pdf'


@app.route('/uploads/books/<filename>', methods=['GET'])
def serve_book(filename):
    return send_from_directory(BOOK_UPLOAD_DIR, filename, as_attachment=True)


@app.route('/api/reports', methods=['POST'])
@login_required
def create_member_report():
    payload = request.get_json(silent=True) or {}
    tree_id = payload.get('tree_id', '')
    relation_type = payload.get('relation_type', '')
    name = (payload.get('name') or '').strip()
    gender = payload.get('gender')

    if not tree_id or not name or not gender or not relation_type:
        return make_fail_response('tree_id, name, gender and relation_type are required.', 400)
    if relation_type not in ('child', 'spouse'):
        return make_fail_response('relation_type must be child or spouse.', 400)

    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)

    parent_id = payload.get('parent_id', '') or ''
    spouse_id = payload.get('spouse_id', '') or ''
    if relation_type == 'child':
        if not parent_id:
            return make_fail_response('parent_id is required for child reports.', 400)
        parent = get_member_by_id(parent_id)
        if not parent or parent.tree_id != tree_id:
            return make_fail_response('Target parent member is invalid.', 400)
        spouse_id = ''

    if relation_type == 'spouse':
        if not spouse_id:
            return make_fail_response('spouse_id is required for spouse reports.', 400)
        spouse = get_member_by_id(spouse_id)
        if not spouse or spouse.tree_id != tree_id:
            return make_fail_response('Target spouse member is invalid.', 400)
        if spouse.spouse_id:
            return make_fail_response('Target member already has a spouse.', 400)
        parent_id = ''

    report = MemberReport(
        tree_id=tree_id,
        parent_id=parent_id,
        spouse_id=spouse_id,
        relation_type=relation_type,
        name=name,
        gender=gender,
        is_alive=payload.get('is_alive', True),
        birth_date=payload.get('birth_date', '') or '',
        desc=payload.get('desc', '') or '',
        status='pending',
        submitter_id=g.current_user.id,
    )
    db.session.add(report)
    db.session.commit()
    return make_success_response({'report': report.to_dict()}, 'Report submitted.', 201)


@app.route('/api/trees/<tree_id>/reports', methods=['GET'])
@login_required
@permission_check(action='write')
def get_member_reports(tree_id):
    status = request.args.get('status', 'pending')
    if status not in ('pending', 'approved', 'rejected', 'all'):
        return make_fail_response('status must be pending, approved, rejected or all.', 400)

    query = MemberReport.query.filter_by(tree_id=tree_id)
    if status != 'all':
        query = query.filter_by(status=status)
    reports = query.order_by(MemberReport.create_time.desc()).all()

    report_list = []
    for report in reports:
        item = report.to_dict()
        submitter = User.query.get(report.submitter_id)
        target_member = None
        if report.relation_type == 'child' and report.parent_id:
            target_member = get_member_by_id(report.parent_id)
        elif report.relation_type == 'spouse' and report.spouse_id:
            target_member = get_member_by_id(report.spouse_id)
        item['submitter_name'] = submitter.nickname if submitter and submitter.nickname else 'Anonymous'
        item['submitter_avatar'] = submitter.avatar_url if submitter and submitter.avatar_url else ''
        item['target_name'] = target_member.name if target_member else ''
        report_list.append(item)

    return make_success_response({'reports': report_list}, 'success')


@app.route('/api/reports/<int:report_id>/handle', methods=['POST'])
@login_required
def handle_member_report(report_id):
    payload = request.get_json(silent=True) or {}
    action = payload.get('action')
    if action not in ('approve', 'reject'):
        return make_fail_response('action must be approve or reject.', 400)

    report = MemberReport.query.get(report_id)
    if not report:
        return make_fail_response('Report not found.', 404)

    tree_id = report.tree_id
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)
    if tree.creator_id != g.current_user.id:
        collab = TreeCollaborator.query.filter_by(tree_id=tree_id, user_id=g.current_user.id).first()
        if not collab:
            return make_fail_response('No permission to handle reports for this tree.', 403)

    if report.status != 'pending':
        return make_fail_response('Report has already been handled.', 400)

    if action == 'reject':
        report.status = 'rejected'
        report.handle_time = datetime.now()
        _log_operation(tree_id, '拒绝成员申请', report.name, category='approval')
        db.session.commit()
        return make_success_response({'report': report.to_dict()}, 'Report rejected.')

    parent = None
    spouse = None
    if report.relation_type == 'child':
        parent = get_member_by_id(report.parent_id)
        if not parent or parent.tree_id != tree_id:
            return make_fail_response('Target parent member is missing.', 400)
    elif report.relation_type == 'spouse':
        spouse = get_member_by_id(report.spouse_id)
        if not spouse or spouse.tree_id != tree_id:
            return make_fail_response('Target spouse member is missing.', 400)
        if spouse.spouse_id:
            return make_fail_response('Target member already has a spouse.', 400)

    now = datetime.now().isoformat()
    member = Member(
        id=generate_id('member'),
        tree_id=tree_id,
        name=report.name,
        gender=report.gender,
        is_alive=report.is_alive,
        parent_id=report.parent_id if report.relation_type == 'child' else '',
        spouse_id='',
        desc=report.desc or '',
        create_time=now,
        generation=(parent.generation + 1) if report.relation_type == 'child' and parent and parent.generation else 1,
        birth_date=report.birth_date or '',
        is_spouse=report.relation_type == 'spouse'
    )

    if report.relation_type == 'spouse':
        sync_spouse_link(member, spouse)
        member.generation = spouse.generation or 1

    report.status = 'approved'
    report.handle_time = datetime.now()
    db.session.add(member)
    db.session.add(report)
    _log_operation(tree_id, '通过成员申请', report.name, category='approval')
    db.session.commit()
    return make_success_response({'member': member.to_dict(), 'report': report.to_dict()}, 'Report approved.')


CORRECTION_FIELDS = {
    'name': ('proposed_name', 'Name'),
    'gender': ('proposed_gender', 'Gender'),
    'is_alive': ('proposed_is_alive', 'Alive status'),
    'birth_date': ('proposed_birth_date', 'Birth date'),
    'desc': ('proposed_desc', 'Biography'),
}


def _normalize_correction_value(value):
    if isinstance(value, str):
        return value.strip()
    return value


def _correction_changes(correction, member):
    changes = []
    for member_field, (correction_field, label) in CORRECTION_FIELDS.items():
        proposed = getattr(correction, correction_field)
        if proposed is None:
            continue
        if isinstance(proposed, str) and proposed == '':
            continue
        original = getattr(member, member_field)
        if proposed != original:
            changes.append({
                'field': member_field,
                'label': label,
                'original': original,
                'proposed': proposed,
            })
    return changes


@app.route('/api/corrections', methods=['POST'])
@login_required
def create_member_correction():
    payload = request.get_json(silent=True) or {}
    member_id = payload.get('member_id', '')
    reason = (payload.get('reason') or '').strip()

    if not member_id or not reason:
        return make_fail_response('member_id and reason are required.', 400)

    member = get_member_by_id(member_id)
    if not member:
        return make_fail_response('Member not found.', 404)

    tree_id = payload.get('tree_id') or member.tree_id
    if tree_id != member.tree_id:
        return make_fail_response('tree_id does not match member.', 400)

    proposed_values = {}
    for member_field, (correction_field, _label) in CORRECTION_FIELDS.items():
        if correction_field in payload:
            proposed_values[correction_field] = _normalize_correction_value(payload.get(correction_field))

    correction = MemberCorrection(
        tree_id=tree_id,
        member_id=member_id,
        reason=reason,
        status='pending',
        submitter_id=g.current_user.id,
        **proposed_values
    )

    if not _correction_changes(correction, member):
        return make_fail_response('At least one changed field is required.', 400)

    db.session.add(correction)
    db.session.commit()
    return make_success_response({'correction': correction.to_dict()}, 'Correction submitted.', 201)


@app.route('/api/trees/<tree_id>/corrections', methods=['GET'])
@login_required
@permission_check(action='write')
def get_member_corrections(tree_id):
    status = request.args.get('status', 'pending')
    if status not in ('pending', 'approved', 'rejected', 'all'):
        return make_fail_response('status must be pending, approved, rejected or all.', 400)

    query = MemberCorrection.query.filter_by(tree_id=tree_id)
    if status != 'all':
        query = query.filter_by(status=status)
    corrections = query.order_by(MemberCorrection.create_time.desc()).all()

    result = []
    for correction in corrections:
        member = get_member_by_id(correction.member_id)
        if not member:
            continue
        submitter = User.query.get(correction.submitter_id)
        item = correction.to_dict()
        item['member_name'] = member.name
        item['submitter_name'] = submitter.nickname if submitter and submitter.nickname else 'Anonymous'
        item['changes'] = _correction_changes(correction, member)
        result.append(item)

    return make_success_response({'corrections': result}, 'success')


@app.route('/api/corrections/<int:correction_id>/handle', methods=['POST'])
@login_required
def handle_member_correction(correction_id):
    payload = request.get_json(silent=True) or {}
    action = payload.get('action')
    if action not in ('approve', 'reject'):
        return make_fail_response('action must be approve or reject.', 400)

    correction = MemberCorrection.query.get(correction_id)
    if not correction:
        return make_fail_response('Correction not found.', 404)

    tree = get_tree_by_id(correction.tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)

    if tree.creator_id != g.current_user.id:
        collab = TreeCollaborator.query.filter_by(tree_id=correction.tree_id, user_id=g.current_user.id).first()
        if not collab:
            return make_fail_response('No permission to handle corrections for this tree.', 403)

    if correction.status != 'pending':
        return make_fail_response('Correction has already been handled.', 400)

    member = get_member_by_id(correction.member_id)
    if not member:
        return make_fail_response('Member not found.', 404)

    if action == 'reject':
        correction.status = 'rejected'
        correction.handle_time = datetime.now()
        db.session.commit()
        return make_success_response({'correction': correction.to_dict()}, 'Correction rejected.')

    changes = _correction_changes(correction, member)
    if not changes:
        return make_fail_response('No changed fields to apply.', 400)

    for change in changes:
        setattr(member, change['field'], change['proposed'])

    correction.status = 'approved'
    correction.handle_time = datetime.now()
    db.session.add(member)
    db.session.add(correction)
    _log_operation(correction.tree_id, '通过纠正申请', member.name, category='approval')
    db.session.commit()
    return make_success_response({
        'member': member.to_dict(),
        'correction': correction.to_dict(),
        'changes': changes,
    }, 'Correction approved.')


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
    if tree.creator_id:
        creator = User.query.get(tree.creator_id)
        tree_data['creator_name'] = creator.nickname if creator and creator.nickname else '匿名用户'
        tree_data['creator_avatar'] = creator.avatar_url if creator and creator.avatar_url else ''
    else:
        tree_data['creator_name'] = '匿名用户'
        tree_data['creator_avatar'] = ''

    return make_success_response({'tree': tree_data, 'members': [member.to_dict() for member in members]}, '查询成功。')


@app.route('/api/trees/<tree_id>/stats', methods=['GET'])
@login_required
def get_tree_stats(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)

    members = dao_get_members(tree_id)
    total_count = len(members)
    male_count = len([item for item in members if item.gender == 'M'])
    female_count = len([item for item in members if item.gender == 'F'])
    generation_map = {}
    for member in members:
        generation = member.generation or 1
        generation_map[generation] = generation_map.get(generation, 0) + 1

    generation_distribution = [
        {'generation': generation, 'count': count}
        for generation, count in sorted(generation_map.items(), key=lambda item: item[0])
    ]

    return make_success_response({
        'total_count': total_count,
        'male_count': male_count,
        'female_count': female_count,
        'generation_distribution': generation_distribution
    }, 'success')


def _binding_to_view(binding):
    item = binding.to_dict()
    member = get_member_by_id(binding.member_id)
    applicant = User.query.get(binding.user_id)
    handler = User.query.get(binding.handler_id) if binding.handler_id else None
    item['member_name'] = member.name if member else ''
    item['member_generation'] = member.generation if member else ''
    item['member_avatar'] = member.avatar_url if member else ''
    item['member_gender'] = member.gender if member else ''
    item['applicant_name'] = applicant.nickname if applicant and applicant.nickname else '微信用户'
    item['applicant_avatar'] = applicant.avatar_url if applicant and applicant.avatar_url else ''
    item['handler_name'] = handler.nickname if handler and handler.nickname else ''
    return item


@app.route('/api/trees/<tree_id>/bindings', methods=['GET'])
@login_required
@permission_check(action='write')
def get_tree_bindings(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)

    status = request.args.get('status', 'all')
    keyword = (request.args.get('keyword') or '').strip()
    if status not in ('all', 'pending', 'approved', 'rejected', 'unbound'):
        return make_fail_response('status is invalid.', 400)

    query = MemberBinding.query.filter_by(tree_id=tree_id)
    if status != 'all':
        query = query.filter_by(status=status)
    bindings = query.order_by(MemberBinding.create_time.desc()).all()
    items = [_binding_to_view(binding) for binding in bindings]
    if keyword:
        items = [
            item for item in items
            if keyword in item.get('member_name', '')
            or keyword in item.get('applicant_name', '')
            or keyword in item.get('relation_label', '')
        ]

    summary = {}
    for key in ('pending', 'approved', 'rejected', 'unbound'):
        summary[key] = MemberBinding.query.filter_by(tree_id=tree_id, status=key).count()
    summary['all'] = sum(summary.values())
    return make_success_response({'bindings': items, 'summary': summary}, 'success')


@app.route('/api/trees/<tree_id>/bindings', methods=['POST'])
@login_required
def create_member_binding(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)

    setting = _get_or_create_privacy_setting(tree_id)
    if not setting.allow_branch_binding_application:
        return make_fail_response('当前家谱暂未开放绑定申请。', 403)

    payload = request.get_json(silent=True) or {}
    member_id = payload.get('member_id') or ''
    member = get_member_by_id(member_id)
    if not member or member.tree_id != tree_id:
        return make_fail_response('Member not found.', 404)

    existing = MemberBinding.query.filter(
        MemberBinding.tree_id == tree_id,
        MemberBinding.member_id == member_id,
        MemberBinding.user_id == g.current_user.id,
        MemberBinding.status.in_(('pending', 'approved'))
    ).first()
    if existing:
        return make_success_response({'binding': _binding_to_view(existing)}, '您已提交过绑定申请。')

    binding = MemberBinding(
        tree_id=tree_id,
        member_id=member_id,
        user_id=g.current_user.id,
        relation_label=(payload.get('relation_label') or '').strip()[:64],
        note=(payload.get('note') or '').strip()[:1000],
        status='pending',
    )
    db.session.add(binding)
    _log_operation(tree_id, '提交绑定申请', member.name, category='approval')
    db.session.commit()
    return make_success_response({'binding': _binding_to_view(binding)}, 'success', 201)


@app.route('/api/bindings/<int:binding_id>/handle', methods=['POST'])
@login_required
def handle_member_binding(binding_id):
    binding = MemberBinding.query.get(binding_id)
    if not binding:
        return make_fail_response('Binding not found.', 404)

    tree = get_tree_by_id(binding.tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)
    if tree.creator_id != g.current_user.id:
        collab = TreeCollaborator.query.filter_by(tree_id=tree.id, user_id=g.current_user.id).first()
        if not collab:
            return make_fail_response('您没有该家谱的编辑权限，请联系谱主授权。', 403)

    if binding.status != 'pending':
        return make_fail_response('该绑定申请已处理。', 400)

    payload = request.get_json(silent=True) or {}
    action = payload.get('action')
    if action not in ('approve', 'reject'):
        return make_fail_response('action must be approve or reject.', 400)

    binding.handler_id = g.current_user.id
    binding.handle_time = datetime.now()
    member = get_member_by_id(binding.member_id)
    member_name = member.name if member else binding.member_id
    if action == 'approve':
        binding.status = 'approved'
        binding.reject_reason = ''
        _log_operation(binding.tree_id, '通过绑定申请', member_name, category='approval')
    else:
        binding.status = 'rejected'
        binding.reject_reason = (payload.get('reason') or '').strip()[:255]
        _log_operation(binding.tree_id, '拒绝绑定申请', member_name, category='approval')
    db.session.add(binding)
    db.session.commit()
    return make_success_response({'binding': _binding_to_view(binding)}, 'success')


@app.route('/api/bindings/<int:binding_id>/unbind', methods=['POST'])
@login_required
def unbind_member(binding_id):
    binding = MemberBinding.query.get(binding_id)
    if not binding:
        return make_fail_response('Binding not found.', 404)

    tree = get_tree_by_id(binding.tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)
    if tree.creator_id != g.current_user.id:
        collab = TreeCollaborator.query.filter_by(tree_id=tree.id, user_id=g.current_user.id).first()
        if not collab:
            return make_fail_response('您没有该家谱的编辑权限，请联系谱主授权。', 403)

    if binding.status != 'approved':
        return make_fail_response('只有已绑定记录可以解绑。', 400)
    payload = request.get_json(silent=True) or {}
    binding.status = 'unbound'
    binding.handler_id = g.current_user.id
    binding.handle_time = datetime.now()
    reason = (payload.get('reason') or '').strip()[:255]
    binding.reject_reason = reason
    member = get_member_by_id(binding.member_id)
    _log_operation(binding.tree_id, '解绑族员', member.name if member else binding.member_id, category='permission')
    db.session.add(binding)
    db.session.commit()
    return make_success_response({'binding': _binding_to_view(binding)}, 'success')


@app.route('/api/trees/<tree_id>/notables', methods=['GET'])
@login_required
def get_tree_notables(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)

    category = request.args.get('category', 'all')
    keyword = (request.args.get('keyword') or '').strip()
    if category != 'all' and category not in NOTABLE_CATEGORY_MAP:
        return make_fail_response('category is invalid.', 400)

    query = Member.query.filter_by(tree_id=tree_id, is_notable=True)
    if category != 'all':
        query = query.filter_by(notable_category=category)
    if keyword:
        like = f'%{keyword}%'
        query = query.filter((Member.name.like(like)) | (Member.achievements.like(like)) | (Member.desc.like(like)))
    members = query.order_by(Member.generation.asc(), Member.create_time.asc()).all()

    counts = {item['key']: 0 for item in NOTABLE_CATEGORIES}
    for member in Member.query.filter_by(tree_id=tree_id, is_notable=True).all():
        key = member.notable_category or 'elite'
        if key in counts:
            counts[key] += 1

    result = []
    for member in members:
        item = member.to_dict()
        item['notable_category_text'] = NOTABLE_CATEGORY_MAP.get(item['notable_category'], '精英录')
        result.append(item)
    categories = [{**item, 'count': counts.get(item['key'], 0)} for item in NOTABLE_CATEGORIES]
    return make_success_response({'members': result, 'categories': categories}, 'success')


@app.route('/api/trees/<tree_id>/notables', methods=['PUT'])
@login_required
@permission_check(action='write')
def update_tree_notable(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)

    payload = request.get_json(silent=True) or {}
    member_id = payload.get('member_id')
    notable_category = payload.get('notable_category') or 'elite'
    achievements = (payload.get('achievements') or '').strip()
    is_notable = bool(payload.get('is_notable', True))
    if notable_category not in NOTABLE_CATEGORY_MAP:
        return make_fail_response('notable_category is invalid.', 400)
    if not member_id:
        return make_fail_response('member_id is required.', 400)

    member = get_member_by_id(member_id)
    if not member or member.tree_id != tree_id:
        return make_fail_response('Member not found.', 404)

    member.is_notable = is_notable
    member.notable_category = notable_category
    if achievements:
        member.achievements = achievements[:512]
    elif is_notable and not member.achievements:
        member.achievements = NOTABLE_CATEGORY_MAP[notable_category]
    db.session.add(member)
    action = '加入名人名录' if is_notable else '移出名人名录'
    detail = f'{member.name}：{NOTABLE_CATEGORY_MAP[notable_category]}'
    _log_operation(tree_id, action, detail, category='content')
    db.session.commit()
    item = member.to_dict()
    item['notable_category_text'] = NOTABLE_CATEGORY_MAP.get(item['notable_category'], '精英录')
    return make_success_response({'member': item}, 'success')


@app.route('/api/trees/<tree_id>/privacy', methods=['GET'])
@login_required
@permission_check(action='write')
def get_tree_privacy(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)

    setting = _get_or_create_privacy_setting(tree_id)
    db.session.commit()
    return make_success_response({'privacy': setting.to_dict()}, 'success')


@app.route('/api/trees/<tree_id>/privacy', methods=['PUT'])
@login_required
@permission_check(action='write')
def update_tree_privacy(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)

    payload = request.get_json(silent=True) or {}
    setting = _get_or_create_privacy_setting(tree_id)

    visibility = payload.get('visibility', setting.visibility)
    if visibility not in PRIVACY_VISIBILITY_VALUES:
        return make_fail_response('visibility is invalid.', 400)

    tree_view_scope = payload.get('tree_view_scope', setting.tree_view_scope)
    birth_date_scope = payload.get('birth_date_scope', setting.birth_date_scope)
    death_date_scope = payload.get('death_date_scope', setting.death_date_scope)
    contact_scope = payload.get('contact_scope', setting.contact_scope)
    for field_value in (tree_view_scope, birth_date_scope, death_date_scope, contact_scope):
        if field_value not in PRIVACY_SCOPE_VALUES:
            return make_fail_response('privacy scope is invalid.', 400)

    bound_member_edit_scope = payload.get('bound_member_edit_scope', setting.bound_member_edit_scope)
    if bound_member_edit_scope not in PRIVACY_EDIT_SCOPE_VALUES:
        return make_fail_response('bound_member_edit_scope is invalid.', 400)

    setting.visibility = visibility
    setting.allow_qr_access = bool(payload.get('allow_qr_access', setting.allow_qr_access))
    setting.allow_password_access = bool(payload.get('allow_password_access', setting.allow_password_access))
    setting.access_password = (payload.get('access_password', setting.access_password) or '').strip()[:64]
    setting.allow_name_relation_access = bool(payload.get('allow_name_relation_access', setting.allow_name_relation_access))
    setting.auto_join_by_name_relation = bool(payload.get('auto_join_by_name_relation', setting.auto_join_by_name_relation))
    setting.allow_name_birth_access = bool(payload.get('allow_name_birth_access', setting.allow_name_birth_access))
    setting.auto_join_by_name_birth = bool(payload.get('auto_join_by_name_birth', setting.auto_join_by_name_birth))
    setting.allow_member_application = bool(payload.get('allow_member_application', setting.allow_member_application))
    setting.allow_branch_binding_application = bool(payload.get('allow_branch_binding_application', setting.allow_branch_binding_application))
    setting.show_in_public_list = bool(payload.get('show_in_public_list', setting.show_in_public_list))
    setting.tree_view_scope = tree_view_scope
    setting.birth_date_scope = birth_date_scope
    setting.death_date_scope = death_date_scope
    setting.contact_scope = contact_scope
    setting.bound_member_edit_scope = bound_member_edit_scope

    if setting.allow_password_access and not setting.access_password:
        return make_fail_response('开启密码访问时需要设置访问密码。', 400)

    db.session.add(setting)
    _log_operation(tree_id, '更新隐私设置', '家族访问与谱员信息可见范围已更新', category='permission')
    db.session.commit()
    return make_success_response({'privacy': setting.to_dict()}, 'success')


@app.route('/api/trees/<tree_id>/articles', methods=['GET'])
@login_required
@permission_check(action='write')
def get_tree_articles(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)

    category = request.args.get('category', 'all')
    if category != 'all' and category not in ARTICLE_CATEGORY_MAP:
        return make_fail_response('category is invalid.', 400)

    query = GenealogyArticle.query.filter_by(tree_id=tree_id)
    if category != 'all':
        query = query.filter_by(category=category)
    articles = query.order_by(GenealogyArticle.sort_order.asc(), GenealogyArticle.update_time.desc()).all()

    items = []
    counts = {item['key']: 0 for item in ARTICLE_CATEGORIES}
    for article in GenealogyArticle.query.filter_by(tree_id=tree_id).all():
        if article.category in counts:
            counts[article.category] += 1
    for article in articles:
        item = article.to_dict()
        item['category_text'] = ARTICLE_CATEGORY_MAP.get(item['category'], '谱文')
        item['author_name'] = _get_user_name(article.author_id)
        items.append(item)

    categories = [
        {**item, 'count': counts.get(item['key'], 0)}
        for item in ARTICLE_CATEGORIES
    ]
    return make_success_response({'articles': items, 'categories': categories}, 'success')


@app.route('/api/trees/<tree_id>/articles', methods=['POST'])
@login_required
@permission_check(action='write')
def create_tree_article(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)

    payload = request.get_json(silent=True) or {}
    category = payload.get('category') or 'preface'
    title = (payload.get('title') or '').strip()
    content = (payload.get('content') or '').strip()
    sort_order = payload.get('sort_order', 0)
    if category not in ARTICLE_CATEGORY_MAP:
        return make_fail_response('category is invalid.', 400)
    if not title:
        return make_fail_response('title is required.', 400)
    try:
        sort_order = int(sort_order)
    except (TypeError, ValueError):
        sort_order = 0

    article = GenealogyArticle(
        tree_id=tree_id,
        category=category,
        title=title[:128],
        content=content,
        sort_order=sort_order,
        author_id=g.current_user.id,
    )
    db.session.add(article)
    _log_operation(tree_id, '新建谱文', f'{ARTICLE_CATEGORY_MAP[category]}：{title[:100]}', category='content')
    db.session.commit()
    item = article.to_dict()
    item['category_text'] = ARTICLE_CATEGORY_MAP.get(item['category'], '谱文')
    item['author_name'] = _get_user_name(article.author_id)
    return make_success_response({'article': item}, 'success', 201)


@app.route('/api/articles/<int:article_id>', methods=['PUT'])
@login_required
def update_tree_article(article_id):
    article = GenealogyArticle.query.get(article_id)
    if not article:
        return make_fail_response('Article not found.', 404)

    tree = get_tree_by_id(article.tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)
    if tree.creator_id != g.current_user.id:
        collab = TreeCollaborator.query.filter_by(tree_id=article.tree_id, user_id=g.current_user.id).first()
        if not collab:
            return make_fail_response('您没有该家谱的编辑权限，请联系谱主授权。', 403)

    payload = request.get_json(silent=True) or {}
    category = payload.get('category') or article.category or 'preface'
    title = (payload.get('title') or article.title).strip()
    content = (payload.get('content') if 'content' in payload else article.content) or ''
    if category not in ARTICLE_CATEGORY_MAP:
        return make_fail_response('category is invalid.', 400)
    if not title:
        return make_fail_response('title is required.', 400)

    article.category = category
    article.title = title[:128]
    article.content = str(content).strip()
    if 'sort_order' in payload:
        try:
            article.sort_order = int(payload.get('sort_order'))
        except (TypeError, ValueError):
            article.sort_order = 0
    db.session.add(article)
    _log_operation(article.tree_id, '编辑谱文', f'{ARTICLE_CATEGORY_MAP[category]}：{article.title[:100]}', category='content')
    db.session.commit()
    item = article.to_dict()
    item['category_text'] = ARTICLE_CATEGORY_MAP.get(item['category'], '谱文')
    item['author_name'] = _get_user_name(article.author_id)
    return make_success_response({'article': item}, 'success')


@app.route('/api/articles/<int:article_id>', methods=['DELETE'])
@login_required
def delete_tree_article(article_id):
    article = GenealogyArticle.query.get(article_id)
    if not article:
        return make_fail_response('Article not found.', 404)

    tree = get_tree_by_id(article.tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)
    if tree.creator_id != g.current_user.id:
        collab = TreeCollaborator.query.filter_by(tree_id=article.tree_id, user_id=g.current_user.id).first()
        if not collab:
            return make_fail_response('您没有该家谱的编辑权限，请联系谱主授权。', 403)

    tree_id = article.tree_id
    title = article.title
    category_label = ARTICLE_CATEGORY_MAP.get(article.category, '谱文')
    db.session.delete(article)
    _log_operation(tree_id, '删除谱文', f'{category_label}：{title[:100]}', category='content')
    db.session.commit()
    return make_success_response({'id': article_id}, 'success')


@app.route('/api/trees/<tree_id>/village', methods=['GET'])
def get_tree_village(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)

    profile = _get_or_create_village_profile(tree)
    members = dao_get_members(tree_id)
    local_members = [
        member.to_dict()
        for member in members
        if (member.current_residence and profile.village_name and profile.village_name in member.current_residence)
    ]
    if not local_members:
        local_members = [member.to_dict() for member in members[:6]]

    db.session.commit()
    return make_success_response({
        'village': profile.to_dict(),
        'members': local_members[:12],
        'ranking': {
            'member_count': len(members),
            'notable_count': len([item for item in members if item.is_notable]),
            'generation_count': len({item.generation or 1 for item in members}),
        }
    }, 'success')


@app.route('/api/trees/<tree_id>/village', methods=['PUT'])
@login_required
@permission_check(action='write')
def update_tree_village(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)

    payload = request.get_json(silent=True) or {}
    profile = _get_or_create_village_profile(tree)
    for field in ('village_name', 'alias_name', 'area_text', 'region', 'location', 'famous_people', 'cover_url'):
        if field in payload:
            setattr(profile, field, (payload.get(field) or '').strip()[:512])
    if 'intro' in payload:
        profile.intro = (payload.get('intro') or '').strip()

    db.session.add(profile)
    _log_operation(tree_id, '更新庄志', profile.village_name or '本庄', category='content')
    db.session.commit()
    return make_success_response({'village': profile.to_dict()}, 'success')


@app.route('/api/trees/<tree_id>/announcements', methods=['GET'])
def get_tree_announcements(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)

    current_user = get_current_user()
    announcements = TreeAnnouncement.query.filter_by(tree_id=tree_id)\
        .order_by(TreeAnnouncement.is_pinned.desc(), TreeAnnouncement.create_time.desc())\
        .all()
    items = []
    for announcement in announcements:
        item = announcement.to_dict()
        item['author_name'] = _get_user_name(announcement.author_id)
        item['role'] = '管理员' if tree.creator_id == announcement.author_id else '协作修谱人'
        item['category_text'] = ANNOUNCEMENT_CATEGORIES.get(item['category'], '族务通知')
        items.append(item)
    return make_success_response({'announcements': items}, 'success')


@app.route('/api/trees/<tree_id>/announcements', methods=['POST'])
@login_required
@permission_check(action='write')
def create_tree_announcement(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)

    payload = request.get_json(silent=True) or {}
    title = (payload.get('title') or '').strip()
    content = (payload.get('content') or '').strip()
    category = payload.get('category') or 'notice'
    is_pinned = bool(payload.get('is_pinned', False))
    if not title or not content:
        return make_fail_response('title and content are required.', 400)
    if category not in ANNOUNCEMENT_CATEGORIES:
        return make_fail_response('category is invalid.', 400)

    announcement = TreeAnnouncement(
        tree_id=tree_id,
        category=category,
        title=title[:128],
        content=content,
        author_id=g.current_user.id,
        is_pinned=is_pinned,
    )
    db.session.add(announcement)
    _log_operation(tree_id, '发布动态', f'{ANNOUNCEMENT_CATEGORIES[category]}：{title[:100]}', category='content')
    db.session.commit()
    item = announcement.to_dict()
    item['author_name'] = g.current_user.nickname or '微信用户'
    item['role'] = '管理员' if tree.creator_id == g.current_user.id else '协作修谱人'
    item['category_text'] = ANNOUNCEMENT_CATEGORIES.get(item['category'], '族务通知')
    return make_success_response({'announcement': item}, 'success', 201)


@app.route('/api/announcements/<int:announcement_id>', methods=['DELETE'])
@login_required
def delete_tree_announcement(announcement_id):
    announcement = TreeAnnouncement.query.get(announcement_id)
    if not announcement:
        return make_fail_response('Announcement not found.', 404)

    tree = get_tree_by_id(announcement.tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)
    if tree.creator_id != g.current_user.id:
        collab = TreeCollaborator.query.filter_by(tree_id=announcement.tree_id, user_id=g.current_user.id).first()
        if not collab:
            return make_fail_response('您没有该家谱的编辑权限，请联系谱主授权。', 403)

    title = announcement.title
    tree_id = announcement.tree_id
    db.session.delete(announcement)
    _log_operation(tree_id, '删除动态', title[:120], category='content')
    db.session.commit()
    return make_success_response({'id': announcement_id}, 'success')


@app.route('/api/announcements/<int:announcement_id>', methods=['PUT'])
@login_required
def update_tree_announcement(announcement_id):
    announcement = TreeAnnouncement.query.get(announcement_id)
    if not announcement:
        return make_fail_response('Announcement not found.', 404)

    tree = get_tree_by_id(announcement.tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)
    if tree.creator_id != g.current_user.id:
        collab = TreeCollaborator.query.filter_by(tree_id=announcement.tree_id, user_id=g.current_user.id).first()
        if not collab:
            return make_fail_response('您没有该家谱的编辑权限，请联系谱主授权。', 403)

    payload = request.get_json(silent=True) or {}
    title = (payload.get('title') or announcement.title).strip()
    content = (payload.get('content') or announcement.content).strip()
    category = payload.get('category') or announcement.category or 'notice'
    if not title or not content:
        return make_fail_response('title and content are required.', 400)
    if category not in ANNOUNCEMENT_CATEGORIES:
        return make_fail_response('category is invalid.', 400)

    announcement.title = title[:128]
    announcement.content = content
    announcement.category = category
    if 'is_pinned' in payload:
        announcement.is_pinned = bool(payload.get('is_pinned'))
    _log_operation(announcement.tree_id, '编辑动态', announcement.title[:120], category='content')
    db.session.add(announcement)
    db.session.commit()
    item = announcement.to_dict()
    item['author_name'] = _get_user_name(announcement.author_id)
    item['role'] = '管理员' if tree.creator_id == announcement.author_id else '协作修谱人'
    item['category_text'] = ANNOUNCEMENT_CATEGORIES.get(item['category'], '族务通知')
    return make_success_response({'announcement': item}, 'success')


@app.route('/api/announcements/<int:announcement_id>/like', methods=['POST'])
@login_required
def toggle_announcement_like(announcement_id):
    announcement = TreeAnnouncement.query.get(announcement_id)
    if not announcement:
        return make_fail_response('Announcement not found.', 404)

    like = AnnouncementLike.query.filter_by(
        announcement_id=announcement_id,
        user_id=g.current_user.id
    ).first()
    liked = False
    if like:
        db.session.delete(like)
    else:
        db.session.add(AnnouncementLike(announcement_id=announcement_id, user_id=g.current_user.id))
        liked = True
    db.session.commit()
    like_count = AnnouncementLike.query.filter_by(announcement_id=announcement_id).count()
    return make_success_response({'liked': liked, 'like_count': like_count}, 'success')


@app.route('/api/announcements/<int:announcement_id>/comments', methods=['POST'])
@login_required
def create_announcement_comment(announcement_id):
    announcement = TreeAnnouncement.query.get(announcement_id)
    if not announcement:
        return make_fail_response('Announcement not found.', 404)
    payload = request.get_json(silent=True) or {}
    content = (payload.get('content') or '').strip()
    if not content:
        return make_fail_response('content is required.', 400)
    comment = AnnouncementComment(
        announcement_id=announcement_id,
        user_id=g.current_user.id,
        content=content[:500],
    )
    db.session.add(comment)
    _log_operation(announcement.tree_id, '评论家族动态', announcement.title[:120], category='content')
    db.session.commit()
    item = comment.to_dict()
    item['user_name'] = g.current_user.nickname or '微信用户'
    comment_count = AnnouncementComment.query.filter_by(announcement_id=announcement_id).count()
    return make_success_response({'comment': item, 'comment_count': comment_count}, 'success', 201)


@app.route('/api/announcement_comments/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_announcement_comment(comment_id):
    comment = AnnouncementComment.query.get(comment_id)
    if not comment:
        return make_fail_response('Comment not found.', 404)
    announcement = TreeAnnouncement.query.get(comment.announcement_id)
    if not announcement:
        return make_fail_response('Announcement not found.', 404)
    tree = get_tree_by_id(announcement.tree_id)
    can_manage = tree and tree.creator_id == g.current_user.id
    if not can_manage and tree:
        can_manage = bool(TreeCollaborator.query.filter_by(tree_id=tree.id, user_id=g.current_user.id).first())
    if comment.user_id != g.current_user.id and not can_manage:
        return make_fail_response('No permission to delete this comment.', 403)
    announcement_id = comment.announcement_id
    db.session.delete(comment)
    db.session.commit()
    comment_count = AnnouncementComment.query.filter_by(announcement_id=announcement_id).count()
    return make_success_response({'id': comment_id, 'comment_count': comment_count}, 'success')


@app.route('/api/announcements/<int:announcement_id>/share', methods=['POST'])
def record_announcement_share(announcement_id):
    announcement = TreeAnnouncement.query.get(announcement_id)
    if not announcement:
        return make_fail_response('Announcement not found.', 404)
    current_user = get_current_user()
    share = AnnouncementShare(
        announcement_id=announcement_id,
        user_id=current_user.id if current_user else None,
    )
    db.session.add(share)
    db.session.commit()
    share_count = AnnouncementShare.query.filter_by(announcement_id=announcement_id).count()
    return make_success_response({'share_count': share_count}, 'success')


@app.route('/api/trees/<tree_id>/visits', methods=['POST'])
def record_tree_visit(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)

    current_user = get_current_user()
    payload = request.get_json(silent=True) or {}
    page = (payload.get('page') or 'tree_space')[:64]
    visitor_name = payload.get('visitor_name') or ''
    if current_user:
        visitor_name = current_user.nickname or '微信用户'
    visitor_name = (visitor_name or '访客')[:128]

    visit = TreeVisit(
        tree_id=tree_id,
        user_id=current_user.id if current_user else None,
        openid=current_user.openid if current_user else '',
        visitor_name=visitor_name,
        page=page,
    )
    db.session.add(visit)
    db.session.commit()
    return make_success_response({'visit': visit.to_dict()}, 'success', 201)


@app.route('/api/trees/<tree_id>/visitors', methods=['GET'])
@login_required
@permission_check(action='write')
def get_tree_visitors(tree_id):
    visits = TreeVisit.query.filter_by(tree_id=tree_id)\
        .order_by(TreeVisit.create_time.desc())\
        .limit(200)\
        .all()
    visitor_map = {}
    for visit in visits:
        key = visit.user_id or visit.openid or f'guest_{visit.id}'
        if key not in visitor_map:
            visitor_map[key] = {
                'id': visit.id,
                'user_id': visit.user_id,
                'visitor_name': visit.visitor_name or _get_user_name(visit.user_id, '访客'),
                'page': visit.page or '',
                'visit_count': 0,
                'last_visit_time': '',
            }
        visitor_map[key]['visit_count'] += 1
        if not visitor_map[key]['last_visit_time']:
            visitor_map[key]['last_visit_time'] = _format_time(visit.create_time)
    visitors = list(visitor_map.values())
    return make_success_response({
        'visitors': visitors,
        'summary': {
            'visitor_count': len(visitors),
            'visit_count': len(visits),
            'latest_visit_time': _format_time(visits[0].create_time) if visits else '',
        }
    }, 'success')


@app.route('/api/trees/<tree_id>/operation_logs', methods=['GET'])
@login_required
@permission_check(action='write')
def get_tree_operation_logs(tree_id):
    category = request.args.get('category', 'all')
    if category != 'all' and category not in LOG_CATEGORIES:
        return make_fail_response('category is invalid.', 400)

    query = OperationLog.query.filter_by(tree_id=tree_id)
    if category != 'all':
        query = query.filter_by(category=category)
    logs = query\
        .order_by(OperationLog.create_time.desc())\
        .limit(200)\
        .all()
    items = []
    for log in logs:
        item = log.to_dict()
        item['operator_name'] = _get_user_name(log.user_id, '系统')
        item['category_text'] = LOG_CATEGORIES.get(item['category'], '系统记录')
        items.append(item)
    return make_success_response({
        'logs': items,
        'categories': [{'key': key, 'label': label} for key, label in LOG_CATEGORIES.items()]
    }, 'success')


@app.route('/api/trees/<tree_id>/collaborators', methods=['GET'])
@login_required
@permission_check(action='write')
def get_tree_collaborators(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)

    collaborators = TreeCollaborator.query.filter_by(tree_id=tree_id)\
        .order_by(TreeCollaborator.create_time.desc())\
        .all()
    items = []
    for collab in collaborators:
        user = User.query.get(collab.user_id)
        data = collab.to_dict()
        data['nickname'] = user.nickname if user and user.nickname else '微信用户'
        data['avatar_url'] = user.avatar_url if user and user.avatar_url else ''
        data['role_text'] = '协管理员'
        items.append(data)

    pending_invites = CollaboratorInvite.query.filter_by(tree_id=tree_id, is_used=False)\
        .order_by(CollaboratorInvite.expire_time.desc())\
        .all()
    invite_items = [invite.to_dict() for invite in pending_invites if invite.expire_time >= datetime.now()]
    return make_success_response({
        'collaborators': items,
        'invites': invite_items,
        'owner_name': _get_user_name(tree.creator_id),
    }, 'success')


@app.route('/api/tree_collaborators/<int:collaborator_id>', methods=['DELETE'])
@login_required
def delete_tree_collaborator(collaborator_id):
    collab = TreeCollaborator.query.get(collaborator_id)
    if not collab:
        return make_fail_response('Collaborator not found.', 404)

    tree = get_tree_by_id(collab.tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)
    if tree.creator_id != g.current_user.id:
        return make_fail_response('只有谱主才能移除协管理员。', 403)

    user_name = _get_user_name(collab.user_id)
    tree_id = collab.tree_id
    db.session.delete(collab)
    _log_operation(tree_id, '移除协管理员', user_name, category='permission')
    db.session.commit()
    return make_success_response({'id': collaborator_id}, 'success')


@app.route('/api/trees/<tree_id>/compile', methods=['POST'])
@login_required
@permission_check(action='write')
def compile_genealogy_book(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)

    payload = request.get_json(silent=True) or {}
    preface = (payload.get('preface') or '').strip()
    style = payload.get('style') or 'ink'
    if style not in ('ink', 'royal'):
        style = 'ink'

    if preface:
        tree.preface = preface
    elif not tree.preface:
        tree.preface = '凡国必有史，有家必有谱。族谱延续着家族的血脉，传承着祖上的遗训和期待。'

    members = dao_get_members(tree_id)
    html_content = build_book_html(tree, members, tree.preface, style)
    book_payload = build_book_payload(tree, members, tree.preface, style)
    filename = _book_filename(tree_id, style, unique=True)
    output_path = os.path.join(BOOK_UPLOAD_DIR, filename)
    engine = render_pdf(html_content, output_path, book_payload)

    db.session.add(tree)
    db.session.commit()

    download_path = f'/uploads/books/{filename}'
    return make_success_response({
        'tree_id': tree_id,
        'filename': filename,
        'download_url': _public_url(download_path),
        'download_path': download_path,
        'engine': engine,
        'member_count': len(members)
    }, 'success')


@app.route('/api/trees/<tree_id>/books', methods=['GET'])
def get_genealogy_books(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)

    safe_prefix = f'book_{re.sub(r"[^a-zA-Z0-9_-]", "_", tree_id)}_'
    books = []
    if os.path.exists(BOOK_UPLOAD_DIR):
        for filename in os.listdir(BOOK_UPLOAD_DIR):
            if not filename.startswith(safe_prefix) or not filename.endswith('.pdf'):
                continue
            file_path = os.path.join(BOOK_UPLOAD_DIR, filename)
            style = 'book'
            parts = filename[:-4].split('_')
            if len(parts) >= 3:
                style = parts[-2]
            created_at = datetime.fromtimestamp(os.path.getmtime(file_path))
            download_path = f'/uploads/books/{filename}'
            books.append({
                'filename': filename,
                'title': f'{tree.surname or ""}氏{tree.title or "族谱"}',
                'style': style,
                'style_text': '典雅金砂版' if style == 'royal' else '欧式标准版',
                'download_url': _public_url(download_path),
                'download_path': download_path,
                'create_time': created_at.isoformat(),
            })

    books.sort(key=lambda item: item['create_time'], reverse=True)
    return make_success_response({'books': books}, 'success')


@app.route('/api/books/send_email', methods=['POST'])
@login_required
def send_genealogy_book_email():
    payload = request.get_json(silent=True) or {}
    tree_id = payload.get('tree_id', '')
    email = (payload.get('email') or '').strip()
    if not tree_id or not email:
        return make_fail_response('tree_id and email are required.', 400)
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return make_fail_response('Invalid email address.', 400)

    tree = get_tree_by_id(tree_id)
    if not tree:
        return make_fail_response('Tree not found.', 404)
    if tree.creator_id != g.current_user.id:
        collab = TreeCollaborator.query.filter_by(tree_id=tree_id, user_id=g.current_user.id).first()
        if not collab:
            return make_fail_response('No permission to send this book.', 403)

    filename = _book_filename(tree_id)
    requested_filename = payload.get('filename') or ''
    if requested_filename:
        safe_prefix = f'book_{re.sub(r"[^a-zA-Z0-9_-]", "_", tree_id)}_'
        if not requested_filename.startswith(safe_prefix) or '/' in requested_filename or '\\' in requested_filename:
            return make_fail_response('Invalid book filename.', 400)
        filename = requested_filename
    attachment_path = os.path.join(BOOK_UPLOAD_DIR, filename)
    if not os.path.exists(attachment_path) and not requested_filename:
        safe_prefix = f'book_{re.sub(r"[^a-zA-Z0-9_-]", "_", tree_id)}_'
        candidates = [
            item for item in os.listdir(BOOK_UPLOAD_DIR)
            if item.startswith(safe_prefix) and item.endswith('.pdf')
        ]
        if candidates:
            filename = max(candidates, key=lambda item: os.path.getmtime(os.path.join(BOOK_UPLOAD_DIR, item)))
            attachment_path = os.path.join(BOOK_UPLOAD_DIR, filename)
    if not os.path.exists(attachment_path):
        return make_fail_response('Book PDF has not been generated yet.', 404)

    ok, message = send_book_email(
        email,
        f'百家有谱 - 您的{tree.surname or ""}氏电子谱书已送达',
        '您好，附件是您在百家有谱生成的电子谱书，请查收。',
        attachment_path,
        filename
    )
    if not ok:
        return make_fail_response(message, 500)
    return make_success_response({'email': email}, 'success')

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
        preface=payload.get('preface', ''),
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
    tree.preface = payload.get('preface', tree.preface)
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
        is_notable=payload.get('is_notable', False),
        notable_category=payload.get('notable_category', 'elite'),
        achievements=payload.get('achievements', ''),
    )

    if spouse_id:
        spouse = get_member_by_id(spouse_id)
        if spouse:
            sync_spouse_link(member, spouse)
        else:
            return make_fail_response('指定配偶不存在。', 400)
    db.session.add(member)
    _log_operation(tree_id, '录入族员', name, category='member')
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
    relation_update = 'parent_id' in payload or 'spouse_id' in payload
    parent_id = payload.get('parent_id', member.parent_id)
    spouse_id = payload.get('spouse_id', member.spouse_id)

    if relation_update:
        ok, message = validate_member_relation(tree_id, parent_id, spouse_id, current_member_id=member_id)
        if not ok:
            return make_fail_response(message, 400)

        if parent_id and has_parent_cycle(member_id, parent_id):
            return make_fail_response('Parent relation would create a cycle.', 400)

        if member.spouse_id and member.spouse_id != spouse_id:
            clear_spouse_links(member)

        if spouse_id:
            spouse = get_member_by_id(spouse_id)
            if spouse:
                sync_spouse_link(member, spouse)
            else:
                return make_fail_response('Target spouse member does not exist.', 400)
    member.name = payload.get('name', member.name)
    member.gender = payload.get('gender', member.gender)
    member.is_alive = payload.get('is_alive', member.is_alive)
    if relation_update:
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
    member.is_notable = payload.get('is_notable', member.is_notable)
    member.notable_category = payload.get('notable_category', member.notable_category)
    member.achievements = payload.get('achievements', member.achievements)

    member.desc = payload.get('desc', member.desc)
    _log_operation(tree_id, '编辑族员', member.name, category='member')
    db.session.commit()
    return make_success_response({'member': member.to_dict()}, '族员信息更新成功。')


@app.route('/api/members/<member_id>', methods=['DELETE'])
@login_required
@permission_check(action='write')
def delete_member(member_id):
    member = get_member_by_id(member_id)
    if not member:
        return make_fail_response('未找到指定族员。', 404)

    tree_id = member.tree_id
    member_name = member.name
    deleted, message = delete_member_safe(member_id)
    if not deleted:
        return make_fail_response(message, 400)
    _log_operation(tree_id, '删除族员', member_name, category='member')
    db.session.commit()
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
    _log_operation(tree_id, '生成协作邀请', '7天有效', category='permission')
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
    _log_operation(invite.tree_id, '接受协作邀请', g.current_user.nickname or '微信用户', category='permission')
    
    # 微信云开发可以允许多人使用一个邀请，或者标记已被使用，此处标记为已被使用
    invite.is_used = True
    db.session.commit()

    return make_success_response({}, '接受邀请成功，已成为本家谱协作修谱人！')
