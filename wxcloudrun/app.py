from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
import sys
from datetime import datetime
from werkzeug.utils import secure_filename

# 将 backend 根目录加入 sys.path 以防找不到 config
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
import config

app = Flask(__name__)
# 载入 config.py 中的配置 (如 SQLALCHEMY_DATABASE_URI)
app.config.from_object(config)
CORS(app)

db = SQLAlchemy(app)

# 头像上传配置
UPLOAD_ROOT = os.path.join(os.path.dirname(__file__), 'uploads')
AVATAR_UPLOAD_DIR = os.path.join(UPLOAD_ROOT, 'avatars')
ALLOWED_AVATAR_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
MAX_AVATAR_SIZE = 2 * 1024 * 1024

os.makedirs(AVATAR_UPLOAD_DIR, exist_ok=True)

# ----------------- 数据库模型定义 -----------------

# 家谱模型
class Tree(db.Model):
    __tablename__ = 'trees'
    id = db.Column(db.String(64), primary_key=True)
    surname = db.Column(db.String(64), nullable=False)
    title = db.Column(db.String(128), nullable=False)
    hall_name = db.Column(db.String(128), nullable=True)
    region = db.Column(db.String(255), nullable=True)
    create_time = db.Column(db.String(64), nullable=False)
    update_time = db.Column(db.String(64), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'surname': self.surname,
            'title': self.title,
            'hall_name': self.hall_name or '',
            'region': self.region or '',
            'create_time': self.create_time,
            'update_time': self.update_time
        }

# 成员模型
class Member(db.Model):
    __tablename__ = 'members'
    id = db.Column(db.String(64), primary_key=True)
    tree_id = db.Column(db.String(64), db.ForeignKey('trees.id'), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    is_alive = db.Column(db.Boolean, default=True, nullable=False)
    parent_id = db.Column(db.String(64), default='', nullable=True)
    spouse_id = db.Column(db.String(64), default='', nullable=True)
    desc = db.Column(db.Text, default='', nullable=True)
    create_time = db.Column(db.String(64), nullable=False)
    generation = db.Column(db.Integer, default=1, nullable=False)
    avatar_url = db.Column(db.String(512), default='', nullable=True)
    surname = db.Column(db.String(64), default='', nullable=True)
    rank_type = db.Column(db.String(64), default='', nullable=True)
    marital_status = db.Column(db.String(64), default='', nullable=True)
    birth_order = db.Column(db.String(64), default='', nullable=True)
    alias_name = db.Column(db.String(64), default='', nullable=True)
    other_name = db.Column(db.String(64), default='', nullable=True)
    style_name = db.Column(db.String(64), default='', nullable=True)
    pseudonym = db.Column(db.String(64), default='', nullable=True)
    birth_date = db.Column(db.String(64), default='', nullable=True)
    death_date = db.Column(db.String(64), default='', nullable=True)
    current_residence = db.Column(db.String(255), default='', nullable=True)
    spouse_father = db.Column(db.String(64), default='', nullable=True)
    education_school = db.Column(db.String(128), default='', nullable=True)
    education_major = db.Column(db.String(128), default='', nullable=True)
    education_degree = db.Column(db.String(64), default='', nullable=True)
    occupation = db.Column(db.String(128), default='', nullable=True)
    is_spouse = db.Column(db.Boolean, default=False, nullable=False)
    spouse_type = db.Column(db.String(64), default='配', nullable=True)
    education_status = db.Column(db.String(64), default='毕业', nullable=True)
    adoption_type = db.Column(db.String(64), default='生', nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'tree_id': self.tree_id,
            'name': self.name,
            'gender': self.gender,
            'is_alive': self.is_alive,
            'parent_id': self.parent_id or '',
            'spouse_id': self.spouse_id or '',
            'desc': self.desc or '',
            'create_time': self.create_time,
            'generation': self.generation or 1,
            'avatar_url': self.avatar_url or '',
            'surname': self.surname or '',
            'rank_type': self.rank_type or '',
            'marital_status': self.marital_status or '',
            'birth_order': self.birth_order or '',
            'alias_name': self.alias_name or '',
            'other_name': self.other_name or '',
            'style_name': self.style_name or '',
            'pseudonym': self.pseudonym or '',
            'birth_date': self.birth_date or '',
            'death_date': self.death_date or '',
            'current_residence': self.current_residence or '',
            'spouse_father': self.spouse_father or '',
            'education_school': self.education_school or '',
            'education_major': self.education_major or '',
            'education_degree': self.education_degree or '',
            'occupation': self.occupation or '',
            'is_spouse': self.is_spouse,
            'spouse_type': self.spouse_type or '',
            'education_status': self.education_status or '',
            'adoption_type': self.adoption_type or ''
        }

# 计数模型
class Count(db.Model):
    __tablename__ = 'count'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    count = db.Column(db.Integer, default=0, nullable=False)

# 初始化表结构 (自动在 MySQL / Postgres / SQLite 中建表)
with app.app_context():
    db.create_all()
    # 初始化计数器数据
    cnt = Count.query.get(1)
    if not cnt:
        cnt = Count(id=1, count=0)
        db.session.add(cnt)
        db.session.commit()

# ----------------- 帮助函数 -----------------

# 生成唯一ID
def generate_id(prefix):
    import time
    import random
    return f"{prefix}_{int(time.time() * 1000)}_{os.urandom(4).hex()}"

def allowed_avatar_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AVATAR_EXTENSIONS

def get_file_size(file_storage):
    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    return size

# ----------------- 校验与关系逻辑 -----------------

def has_parent_cycle(member_id, parent_id):
    if not parent_id:
        return False
    if member_id == parent_id:
        return True

    seen = set()
    current_id = parent_id
    while current_id:
        if current_id in seen:
            return True
        if current_id == member_id:
            return True
        seen.add(current_id)
        parent = Member.query.get(current_id)
        if not parent:
            return False
        current_id = parent.parent_id
    return False


def clear_spouse_links(member_id):
    spouses = Member.query.filter_by(spouse_id=member_id).all()
    for spouse in spouses:
        spouse.spouse_id = ''
        spouse.is_spouse = False


def sync_spouse_link(member_id, spouse_id):
    if not spouse_id:
        return
    spouse = Member.query.get(spouse_id)
    if not spouse:
        return
    spouse.spouse_id = member_id
    spouse.is_spouse = True


def validate_member_relation(data, member_id=None):
    tree_id = data.get('tree_id')
    parent_id = data.get('parent_id') or ''
    spouse_id = data.get('spouse_id') or ''
    is_spouse = bool(data.get('is_spouse', False))

    if not tree_id:
        return '保存失败：缺少家谱ID。'

    if not Tree.query.get(tree_id):
        return '保存失败：所属家谱不存在。'

    if member_id and parent_id == member_id:
        return '保存失败：不能将自己设置为自己的父亲或上级。'

    if member_id and spouse_id == member_id:
        return '保存失败：不能将自己设置为自己的配偶。'

    if parent_id and spouse_id and parent_id == spouse_id:
        return '保存失败：配偶不能同时作为父亲或上级。'

    if parent_id:
        parent = Member.query.get(parent_id)
        if not parent:
            return '保存失败：父亲或上级不存在。'
        if parent.tree_id != tree_id:
            return '保存失败：父亲或上级不属于当前家谱。'
        if member_id and parent.is_spouse and parent.spouse_id == member_id:
            return '保存失败：不能把自己的配偶设为父亲或上级。'
        if member_id and has_parent_cycle(member_id, parent_id):
            return '保存失败：不能将自己的子嗣（或后代）设置为自己的父母。'

    if spouse_id:
        spouse_owner = Member.query.get(spouse_id)
        if not spouse_owner:
            return '保存失败：配偶关联的族员不存在。'
        if spouse_owner.tree_id != tree_id:
            return '保存失败：配偶关联的族员不属于当前家谱。'
        if spouse_owner.spouse_id and spouse_owner.spouse_id != member_id:
            return '保存失败：该配偶已绑定其他人，请先解除当前配偶关系。'

    return None

# ----------------- 计数器测试 API -----------------

@app.route('/api/count', methods=['POST'])
def count():
    data = request.get_json() or {}
    action = data.get('action')
    if action == 'inc':
        cnt = Count.query.get(1)
        if not cnt:
            cnt = Count(id=1, count=1)
            db.session.add(cnt)
        else:
            cnt.count += 1
        db.session.commit()
        return jsonify({'code': 0, 'data': {'count': cnt.count}})
    return jsonify({'code': -1, 'message': 'Invalid action'})

# ----------------- 头像静态服务与上传 API -----------------

@app.route('/uploads/avatars/<filename>', methods=['GET'])
def serve_avatar(filename):
    return send_from_directory(AVATAR_UPLOAD_DIR, filename)

@app.route('/api/upload/avatar', methods=['POST'])
def upload_avatar():
    if 'file' not in request.files:
        return jsonify({'code': -1, 'message': '请选择头像文件'})

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({'code': -1, 'message': '请选择头像文件'})

    if not allowed_avatar_file(file.filename):
        return jsonify({'code': -1, 'message': '头像仅支持 jpg、jpeg、png、webp 格式'})

    if get_file_size(file) > MAX_AVATAR_SIZE:
        return jsonify({'code': -1, 'message': '头像大小不能超过 2MB'})

    ext = file.filename.rsplit('.', 1)[1].lower()
    safe_name = secure_filename(file.filename.rsplit('.', 1)[0]) or 'avatar'
    filename = f"{safe_name}_{int(datetime.now().timestamp() * 1000)}_{os.urandom(4).hex()}.{ext}"
    file_path = os.path.join(AVATAR_UPLOAD_DIR, filename)
    file.save(file_path)

    url = f"/uploads/avatars/{filename}"
    return jsonify({'code': 0, 'data': {'url': url}})

# ----------------- 家谱 API -----------------

# 获取所有家谱 (包含各家谱的族员总数)
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
    return jsonify({'code': 0, 'data': tree_list})

# 创建家谱
@app.route('/api/trees', methods=['POST'])
def create_tree():
    data = request.get_json() or {}
    tree_id = generate_id('tree')
    now = datetime.now().isoformat()
    tree = Tree(
        id=tree_id,
        surname=data.get('surname'),
        title=data.get('title'),
        hall_name=data.get('hall_name'),
        region=data.get('region'),
        create_time=now,
        update_time=now
    )
    db.session.add(tree)
    db.session.commit()
    return jsonify({'code': 0, 'data': tree.to_dict()})

# 获取家谱详情
@app.route('/api/trees/<tree_id>', methods=['GET'])
def get_tree(tree_id):
    tree = Tree.query.get(tree_id)
    if tree:
        return jsonify({'code': 0, 'data': tree.to_dict()})
    return jsonify({'code': -1, 'message': 'Tree not found'})

# 更新家谱
@app.route('/api/trees/<tree_id>', methods=['PUT'])
def update_tree(tree_id):
    data = request.get_json() or {}
    tree = Tree.query.get(tree_id)
    if not tree:
        return jsonify({'code': -1, 'message': 'Tree not found'})
    
    if 'surname' in data:
        tree.surname = data.get('surname')
    if 'title' in data:
        tree.title = data.get('title')
    if 'hall_name' in data:
        tree.hall_name = data.get('hall_name')
    if 'region' in data:
        tree.region = data.get('region')
    
    tree.update_time = datetime.now().isoformat()
    db.session.commit()
    return jsonify({'code': 0, 'message': 'Tree updated successfully'})

# 删除家谱 (同时级联删除该谱下的所有成员)
@app.route('/api/trees/<tree_id>', methods=['DELETE'])
def delete_tree(tree_id):
    tree = Tree.query.get(tree_id)
    if not tree:
        return jsonify({'code': -1, 'message': 'Tree not found'})

    try:
        with db.session.begin():
            Member.query.filter_by(tree_id=tree_id).delete(synchronize_session=False)
            db.session.delete(tree)
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': -1, 'message': f'删除失败：{str(e)}'})

    return jsonify({'code': 0, 'message': 'Tree deleted successfully'})

# ----------------- 成员 API -----------------

# 获取成员列表
@app.route('/api/members', methods=['GET'])
def get_members():
    tree_id = request.args.get('tree_id')
    if tree_id:
        members = Member.query.filter_by(tree_id=tree_id).all()
    else:
        members = Member.query.all()
    return jsonify({'code': 0, 'data': [m.to_dict() for m in members]})

# 创建成员
@app.route('/api/members', methods=['POST'])
def create_member():
    data = request.get_json() or {}
    member_id = generate_id('member')
    now = datetime.now().isoformat()

    validation_data = {**data, 'id': member_id}
    validation_error = validate_member_relation(validation_data, member_id)
    if validation_error:
        return jsonify({'code': -1, 'message': validation_error})

    member = Member(
        id=member_id,
        tree_id=data.get('tree_id'),
        name=data.get('name'),
        gender=data.get('gender'),
        is_alive=bool(data.get('is_alive', True)),
        parent_id=data.get('parent_id') or '',
        spouse_id=data.get('spouse_id') or '',
        desc=data.get('desc') or '',
        create_time=now,
        generation=int(data.get('generation', 1)),
        avatar_url=data.get('avatar_url') or '',
        surname=data.get('surname') or '',
        rank_type=data.get('rank_type') or '',
        marital_status=data.get('marital_status') or '',
        birth_order=data.get('birth_order') or '',
        alias_name=data.get('alias_name') or '',
        other_name=data.get('other_name') or '',
        style_name=data.get('style_name') or '',
        pseudonym=data.get('pseudonym') or '',
        birth_date=data.get('birth_date') or '',
        death_date=data.get('death_date') or '',
        current_residence=data.get('current_residence') or '',
        spouse_father=data.get('spouse_father') or '',
        education_school=data.get('education_school') or '',
        education_major=data.get('education_major') or '',
        education_degree=data.get('education_degree') or '',
        occupation=data.get('occupation') or '',
        is_spouse=bool(data.get('is_spouse', False)),
        spouse_type=data.get('spouse_type') or '配',
        education_status=data.get('education_status') or '毕业',
        adoption_type=data.get('adoption_type') or '生'
    )
    try:
        db.session.add(member)
        if member.spouse_id:
            sync_spouse_link(member.id, member.spouse_id)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': -1, 'message': f'保存失败：{str(e)}'})
    return jsonify({'code': 0, 'data': member.to_dict()})

# 获取成员详情
@app.route('/api/members/<member_id>', methods=['GET'])
def get_member(member_id):
    member = Member.query.get(member_id)
    if member:
        return jsonify({'code': 0, 'data': member.to_dict()})
    return jsonify({'code': -1, 'message': 'Member not found'})

# 更新成员
@app.route('/api/members/<member_id>', methods=['PUT'])
def update_member(member_id):
    data = request.get_json() or {}
    member = Member.query.get(member_id)
    if not member:
        return jsonify({'code': -1, 'message': 'Member not found'})

    existing_dict = member.to_dict()
    merged = {**existing_dict, **data}
    validation_error = validate_member_relation(merged, member_id)
    if validation_error:
        return jsonify({'code': -1, 'message': validation_error})

    old_spouse_id = member.spouse_id or ''
    new_spouse_id = data.get('spouse_id') if 'spouse_id' in data else old_spouse_id
    if new_spouse_id is None:
        new_spouse_id = ''
    new_spouse_id = new_spouse_id or ''

    if 'name' in data:
        member.name = data.get('name')
    if 'gender' in data:
        member.gender = data.get('gender')
    if 'is_alive' in data:
        member.is_alive = bool(data.get('is_alive'))
    if 'parent_id' in data:
        member.parent_id = data.get('parent_id') or ''
    if 'spouse_id' in data:
        member.spouse_id = new_spouse_id
    if 'desc' in data:
        member.desc = data.get('desc') or ''
    if 'generation' in data:
        member.generation = int(data.get('generation', 1))
    if 'avatar_url' in data:
        member.avatar_url = data.get('avatar_url') or ''
    if 'surname' in data:
        member.surname = data.get('surname') or ''
    if 'rank_type' in data:
        member.rank_type = data.get('rank_type') or ''
    if 'marital_status' in data:
        member.marital_status = data.get('marital_status') or ''
    if 'birth_order' in data:
        member.birth_order = data.get('birth_order') or ''
    if 'alias_name' in data:
        member.alias_name = data.get('alias_name') or ''
    if 'other_name' in data:
        member.other_name = data.get('other_name') or ''
    if 'style_name' in data:
        member.style_name = data.get('style_name') or ''
    if 'pseudonym' in data:
        member.pseudonym = data.get('pseudonym') or ''
    if 'birth_date' in data:
        member.birth_date = data.get('birth_date') or ''
    if 'death_date' in data:
        member.death_date = data.get('death_date') or ''
    if 'current_residence' in data:
        member.current_residence = data.get('current_residence') or ''
    if 'spouse_father' in data:
        member.spouse_father = data.get('spouse_father') or ''
    if 'education_school' in data:
        member.education_school = data.get('education_school') or ''
    if 'education_major' in data:
        member.education_major = data.get('education_major') or ''
    if 'education_degree' in data:
        member.education_degree = data.get('education_degree') or ''
    if 'occupation' in data:
        member.occupation = data.get('occupation') or ''
    if 'is_spouse' in data:
        member.is_spouse = bool(data.get('is_spouse'))
    if 'spouse_type' in data:
        member.spouse_type = data.get('spouse_type') or '配'
    if 'education_status' in data:
        member.education_status = data.get('education_status') or '毕业'
    if 'adoption_type' in data:
        member.adoption_type = data.get('adoption_type') or '生'

    try:
        if 'spouse_id' in data and old_spouse_id and old_spouse_id != new_spouse_id:
            old_spouse = Member.query.get(old_spouse_id)
            if old_spouse and old_spouse.spouse_id == member.id:
                old_spouse.spouse_id = ''
                old_spouse.is_spouse = False

        if 'spouse_id' in data and new_spouse_id and old_spouse_id != new_spouse_id:
            sync_spouse_link(member.id, new_spouse_id)

        if not new_spouse_id and old_spouse_id:
            clear_spouse_links(member.id)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': -1, 'message': f'保存失败：{str(e)}'})

    return jsonify({'code': 0, 'message': 'Member updated successfully'})

# 删除成员
@app.route('/api/members/<member_id>', methods=['DELETE'])
def delete_member(member_id):
    member = Member.query.get(member_id)
    if not member:
        return jsonify({'code': -1, 'message': 'Member not found'})

    child_exists = Member.query.filter_by(parent_id=member_id).first()
    if child_exists:
        return jsonify({
            'code': -1,
            'message': '该成员下有子嗣，无法直接删除。请先进入其子女的编辑页面，将父亲/母亲关系修改或置空后，再尝试删除。'
        })

    try:
        if member.spouse_id:
            spouse = Member.query.get(member.spouse_id)
            if spouse and spouse.spouse_id == member.id:
                spouse.spouse_id = ''
                spouse.is_spouse = False

        clear_spouse_links(member.id)
        db.session.delete(member)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'code': -1, 'message': f'删除失败：{str(e)}'})

    return jsonify({'code': 0, 'message': 'Member deleted successfully'})

if __name__ == '__main__':
    # 兼容本地和容器部署
    app.run(host='0.0.0.0', port=8080, debug=True)
