from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# SQLite 连接配置
DB_PATH = os.path.join(os.path.dirname(__file__), './data/genealogy.db')
UPLOAD_ROOT = os.path.join(os.path.dirname(__file__), 'uploads')
AVATAR_UPLOAD_DIR = os.path.join(UPLOAD_ROOT, 'avatars')
ALLOWED_AVATAR_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
MAX_AVATAR_SIZE = 2 * 1024 * 1024

os.makedirs(AVATAR_UPLOAD_DIR, exist_ok=True)

# 初始化数据库
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 创建 trees 表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trees (
        id TEXT PRIMARY KEY,
        surname TEXT NOT NULL,
        title TEXT NOT NULL,
        hall_name TEXT,
        region TEXT,
        create_time TEXT NOT NULL,
        update_time TEXT NOT NULL
    )
    ''')
    
    # 创建 members 表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS members (
        id TEXT PRIMARY KEY,
        tree_id TEXT NOT NULL,
        name TEXT NOT NULL,
        gender TEXT NOT NULL,
        is_alive INTEGER DEFAULT 1,
        parent_id TEXT DEFAULT '',
        spouse_id TEXT DEFAULT '',
        desc TEXT DEFAULT '',
        create_time TEXT NOT NULL,
        FOREIGN KEY (tree_id) REFERENCES trees (id)
    )
    ''')
    
    # 创建 count 表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS count (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        count INTEGER DEFAULT 0
    )
    ''')
    
    # 初始化 count 表
    cursor.execute('SELECT * FROM count')
    if cursor.fetchone() is None:
        cursor.execute('INSERT INTO count (count) VALUES (0)')
    
    conn.commit()
    conn.close()

def auto_upgrade_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    columns = [
        ("spouse_type", "'配'"),
        ("education_status", "'毕业'"),
        ("adoption_type", "'生'"),
        ("death_date", "''"),
        ("current_residence", "''")
    ]
    for col, default in columns:
        try:
            cursor.execute(f"ALTER TABLE members ADD COLUMN {col} TEXT DEFAULT {default}")
            print(f"Auto-added column {col}.")
        except:
            pass
    conn.commit()
    conn.close()

auto_upgrade_db()

# 注意：数据库初始化已移至独立脚本 init_db.py
# 如需初始化数据库，请运行：python init_db.py

# 测试接口
@app.route('/api/count', methods=['POST'])
def count():
    data = request.get_json()
    action = data.get('action')
    if action == 'inc':
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT count FROM count WHERE id = 1')
        count_data = cursor.fetchone()
        if count_data:
            new_count = count_data[0] + 1
            cursor.execute('UPDATE count SET count = ? WHERE id = 1', (new_count,))
        else:
            new_count = 1
            cursor.execute('INSERT INTO count (count) VALUES (?)', (new_count,))
        conn.commit()
        conn.close()
        return jsonify({'code': 0, 'data': {'count': new_count}})
    return jsonify({'code': -1, 'message': 'Invalid action'})

# 生成唯一ID
def generate_id(prefix):
    return f"{prefix}_{int(datetime.now().timestamp() * 1000)}_{os.urandom(4).hex()}"

def allowed_avatar_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AVATAR_EXTENSIONS

def get_file_size(file_storage):
    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    return size

def get_table_columns(cursor, table_name):
    cursor.execute(f'PRAGMA table_info({table_name})')
    return [row[1] for row in cursor.fetchall()]

def row_to_member(row, columns):
    data = dict(zip(columns, row))
    return {
        'id': data.get('id', ''),
        'tree_id': data.get('tree_id', ''),
        'name': data.get('name', ''),
        'gender': data.get('gender', ''),
        'is_alive': bool(data.get('is_alive', 1)),
        'parent_id': data.get('parent_id', '') or '',
        'spouse_id': data.get('spouse_id', '') or '',
        'desc': data.get('desc', '') or '',
        'create_time': data.get('create_time', ''),
        'generation': data.get('generation', 1) or 1,
        'avatar_url': data.get('avatar_url', '') or '',
        'surname': data.get('surname', '') or '',
        'rank_type': data.get('rank_type', '') or '',
        'marital_status': data.get('marital_status', '') or '',
        'birth_order': data.get('birth_order', '') or '',
        'alias_name': data.get('alias_name', '') or '',
        'other_name': data.get('other_name', '') or '',
        'style_name': data.get('style_name', '') or '',
        'pseudonym': data.get('pseudonym', '') or '',
        'birth_date': data.get('birth_date', '') or '',
        'death_date': data.get('death_date', '') or '',
        'current_residence': data.get('current_residence', '') or '',
        'spouse_father': data.get('spouse_father', '') or '',
        'education_school': data.get('education_school', '') or '',
        'education_major': data.get('education_major', '') or '',
        'education_degree': data.get('education_degree', '') or '',
        'occupation': data.get('occupation', '') or '',
        'is_spouse': bool(data.get('is_spouse', 0)),
        'spouse_type': data.get('spouse_type', '') or '',
        'education_status': data.get('education_status', '') or '',
        'adoption_type': data.get('adoption_type', '') or ''
    }

def get_member_by_id(cursor, member_id):
    columns = get_table_columns(cursor, 'members')
    cursor.execute('SELECT * FROM members WHERE id = ?', (member_id,))
    row = cursor.fetchone()
    return row_to_member(row, columns) if row else None

def has_parent_cycle(cursor, member_id, parent_id):
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
        parent = get_member_by_id(cursor, current_id)
        if not parent:
            return False
        current_id = parent.get('parent_id', '')
    return False

def validate_member_relation(cursor, data, member_id=None):
    tree_id = data.get('tree_id')
    parent_id = data.get('parent_id') or ''
    spouse_id = data.get('spouse_id') or ''
    is_spouse = bool(data.get('is_spouse', False))

    if member_id and parent_id == member_id:
        return '不能把自己设为自己的父亲或上级'

    if member_id and spouse_id == member_id:
        return '不能把自己设为自己的配偶'

    if parent_id and spouse_id and parent_id == spouse_id:
        return '配偶不能同时作为父亲或上级'

    if parent_id:
        parent = get_member_by_id(cursor, parent_id)
        if not parent:
            return '父亲或上级不存在'
        if tree_id and parent.get('tree_id') != tree_id:
            return '父亲或上级不属于当前家谱'
        if member_id and parent.get('is_spouse') and parent.get('spouse_id') == member_id:
            return '不能把自己的配偶设为父亲或上级'
        if member_id and has_parent_cycle(cursor, member_id, parent_id):
            return '不能形成父子循环关系'

    if spouse_id:
        spouse_owner = get_member_by_id(cursor, spouse_id)
        if not spouse_owner:
            return '配偶关联的族员不存在'
        if tree_id and spouse_owner.get('tree_id') != tree_id:
            return '配偶关联的族员不属于当前家谱'

    if is_spouse and spouse_id:
        spouse_name = (data.get('name') or '').strip()
        params = [spouse_id, spouse_name]
        sql = 'SELECT id FROM members WHERE is_spouse = 1 AND spouse_id = ? AND name = ?'
        if member_id:
            sql += ' AND id != ?'
            params.append(member_id)
        cursor.execute(sql, params)
        if cursor.fetchone():
            return '该族员已存在同名配偶，请勿重复添加'

    return None

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

# 家谱相关接口

# 获取家谱列表
@app.route('/api/trees', methods=['GET'])
def get_trees():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    SELECT t.id, t.surname, t.title, t.hall_name, t.region, t.create_time, t.update_time,
           COUNT(m.id) AS member_count
    FROM trees t
    LEFT JOIN members m ON m.tree_id = t.id
    GROUP BY t.id, t.surname, t.title, t.hall_name, t.region, t.create_time, t.update_time
    ORDER BY t.update_time DESC
    ''')
    trees = cursor.fetchall()
    conn.close()
    
    tree_list = []
    for tree in trees:
        tree_list.append({
            'id': tree[0],
            'surname': tree[1],
            'title': tree[2],
            'hall_name': tree[3],
            'region': tree[4],
            'create_time': tree[5],
            'update_time': tree[6],
            'member_count': tree[7]
        })
    return jsonify({'code': 0, 'data': tree_list})

# 创建家谱
@app.route('/api/trees', methods=['POST'])
def create_tree():
    data = request.get_json()
    tree_id = generate_id('tree')
    now = datetime.now().isoformat()
    tree_data = {
        'id': tree_id,
        'surname': data.get('surname'),
        'title': data.get('title'),
        'hall_name': data.get('hall_name'),
        'region': data.get('region'),
        'create_time': now,
        'update_time': now
    }
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO trees (id, surname, title, hall_name, region, create_time, update_time)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (tree_id, tree_data['surname'], tree_data['title'], tree_data['hall_name'], tree_data['region'], now, now))
    conn.commit()
    conn.close()
    
    return jsonify({'code': 0, 'data': tree_data})

# 获取家谱详情
@app.route('/api/trees/<tree_id>', methods=['GET'])
def get_tree(tree_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM trees WHERE id = ?', (tree_id,))
    tree = cursor.fetchone()
    conn.close()
    
    if tree:
        tree_data = {
            'id': tree[0],
            'surname': tree[1],
            'title': tree[2],
            'hall_name': tree[3],
            'region': tree[4],
            'create_time': tree[5],
            'update_time': tree[6]
        }
        return jsonify({'code': 0, 'data': tree_data})
    return jsonify({'code': -1, 'message': 'Tree not found'})

# 更新家谱
@app.route('/api/trees/<tree_id>', methods=['PUT'])
def update_tree(tree_id):
    data = request.get_json()
    now = datetime.now().isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE trees SET surname = ?, title = ?, hall_name = ?, region = ?, update_time = ?
    WHERE id = ?
    ''', (data.get('surname'), data.get('title'), data.get('hall_name'), data.get('region'), now, tree_id))
    
    if cursor.rowcount > 0:
        conn.commit()
        conn.close()
        return jsonify({'code': 0, 'message': 'Tree updated successfully'})
    conn.close()
    return jsonify({'code': -1, 'message': 'Tree not found'})

# 删除家谱
@app.route('/api/trees/<tree_id>', methods=['DELETE'])
def delete_tree(tree_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 删除关联的成员
    cursor.execute('DELETE FROM members WHERE tree_id = ?', (tree_id,))
    # 删除家谱
    cursor.execute('DELETE FROM trees WHERE id = ?', (tree_id,))
    
    if cursor.rowcount > 0:
        conn.commit()
        conn.close()
        return jsonify({'code': 0, 'message': 'Tree deleted successfully'})
    conn.close()
    return jsonify({'code': -1, 'message': 'Tree not found'})

# 成员相关接口

# 获取成员列表
@app.route('/api/members', methods=['GET'])
def get_members():
    tree_id = request.args.get('tree_id')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    columns = get_table_columns(cursor, 'members')
    
    if tree_id:
        cursor.execute('SELECT * FROM members WHERE tree_id = ?', (tree_id,))
    else:
        cursor.execute('SELECT * FROM members')
    
    members = cursor.fetchall()
    conn.close()
    
    member_list = []
    for member in members:
        member_list.append(row_to_member(member, columns))
    return jsonify({'code': 0, 'data': member_list})

# 创建成员
@app.route('/api/members', methods=['POST'])
def create_member():
    data = request.get_json()
    member_id = generate_id('member')
    now = datetime.now().isoformat()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    validation_data = {**data, 'id': member_id}
    validation_error = validate_member_relation(cursor, validation_data, member_id)
    if validation_error:
        conn.close()
        return jsonify({'code': -1, 'message': validation_error})

    cursor.execute('''
    INSERT INTO members (id, tree_id, name, gender, is_alive, parent_id, spouse_id, desc, create_time,
                         generation, avatar_url, surname, rank_type, marital_status, birth_order,
                         alias_name, other_name, style_name, pseudonym, birth_date, spouse_father,
                         education_school, education_major, education_degree, occupation, is_spouse,
                         spouse_type, education_status, adoption_type, death_date, current_residence)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (member_id, data.get('tree_id'), data.get('name'), data.get('gender'), 
          1 if data.get('is_alive', True) else 0, data.get('parent_id', ''), data.get('spouse_id', ''), 
          data.get('desc', ''), now,
          data.get('generation', 1), data.get('avatar_url', ''), data.get('surname', ''),
          data.get('rank_type', ''), data.get('marital_status', ''), data.get('birth_order', ''),
          data.get('alias_name', ''), data.get('other_name', ''), data.get('style_name', ''),
          data.get('pseudonym', ''), data.get('birth_date', ''), data.get('spouse_father', ''),
          data.get('education_school', ''), data.get('education_major', ''),
          data.get('education_degree', ''), data.get('occupation', ''),
          1 if data.get('is_spouse', False) else 0, data.get('spouse_type', ''),
          data.get('education_status', ''), data.get('adoption_type', ''),
          data.get('death_date', ''), data.get('current_residence', '')))
    conn.commit()
    conn.close()
    
    data['id'] = member_id
    data['create_time'] = now
    return jsonify({'code': 0, 'data': data})

# 获取成员详情
@app.route('/api/members/<member_id>', methods=['GET'])
def get_member(member_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    member_data = get_member_by_id(cursor, member_id)
    conn.close()
    
    if member_data:
        return jsonify({'code': 0, 'data': member_data})
    return jsonify({'code': -1, 'message': 'Member not found'})

# 更新成员
@app.route('/api/members/<member_id>', methods=['PUT'])
def update_member(member_id):
    data = request.get_json() or {}
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    existing = get_member_by_id(cursor, member_id)
    if not existing:
        conn.close()
        return jsonify({'code': -1, 'message': 'Member not found'})

    merged = {**existing, **data}
    validation_error = validate_member_relation(cursor, merged, member_id)
    if validation_error:
        conn.close()
        return jsonify({'code': -1, 'message': validation_error})

    cursor.execute('''
    UPDATE members SET name = ?, gender = ?, is_alive = ?, parent_id = ?, spouse_id = ?, desc = ?,
                       generation = ?, avatar_url = ?, surname = ?, rank_type = ?, marital_status = ?,
                       birth_order = ?, alias_name = ?, other_name = ?, style_name = ?, pseudonym = ?,
                       birth_date = ?, spouse_father = ?, education_school = ?, education_major = ?,
                       education_degree = ?, occupation = ?, is_spouse = ?, spouse_type = ?,
                       education_status = ?, adoption_type = ?, death_date = ?, current_residence = ?
    WHERE id = ?
    ''', (merged.get('name'), merged.get('gender'), 1 if merged.get('is_alive') else 0, 
          merged.get('parent_id', ''), merged.get('spouse_id', ''), merged.get('desc', ''),
          merged.get('generation', 1), merged.get('avatar_url', ''), merged.get('surname', ''), 
          merged.get('rank_type', ''), merged.get('marital_status', ''), merged.get('birth_order', ''),
          merged.get('alias_name', ''), merged.get('other_name', ''), merged.get('style_name', ''),
          merged.get('pseudonym', ''), merged.get('birth_date', ''), merged.get('spouse_father', ''),
          merged.get('education_school', ''), merged.get('education_major', ''),
          merged.get('education_degree', ''), merged.get('occupation', ''), 
          1 if merged.get('is_spouse', False) else 0, merged.get('spouse_type', ''),
          merged.get('education_status', ''), merged.get('adoption_type', ''),
          merged.get('death_date', ''), merged.get('current_residence', ''),
          member_id))
    
    if cursor.rowcount > 0:
        conn.commit()
        conn.close()
        return jsonify({'code': 0, 'message': 'Member updated successfully'})
    conn.close()
    return jsonify({'code': -1, 'message': 'Member not found'})

# 删除成员
@app.route('/api/members/<member_id>', methods=['DELETE'])
def delete_member(member_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM members WHERE id = ?', (member_id,))
    
    if cursor.rowcount > 0:
        conn.commit()
        conn.close()
        return jsonify({'code': 0, 'message': 'Member deleted successfully'})
    conn.close()
    return jsonify({'code': -1, 'message': 'Member not found'})

if __name__ == '__main__':
    app.run(host='localhost', port=8080, debug=True)
