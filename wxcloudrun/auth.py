import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, g, current_app
from wxcloudrun import db
from wxcloudrun.model import User, Tree, TreeCollaborator, Member
from wxcloudrun.response import make_fail_response

def generate_token(user_id, openid):
    """
    生成 JWT Token，有效期 30 天
    """
    secret = current_app.config.get('JWT_SECRET_KEY', 'bjyp_secret_key_2026')
    payload = {
        'exp': datetime.utcnow() + timedelta(days=30),
        'iat': datetime.utcnow(),
        'sub': str(user_id),
        'openid': openid
    }
    return jwt.encode(payload, secret, algorithm='HS256')

def decode_token(token):
    """
    解码并校验 JWT Token
    """
    secret = current_app.config.get('JWT_SECRET_KEY', 'bjyp_secret_key_2026')
    try:
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token 已过期
    except jwt.InvalidTokenError:
        return None  # Token 无效

def get_current_user():
    """
    尝试从请求的 Authorization 头解析当前登录用户，不抛出异常。
    供可选登录的获取接口使用。
    """
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        payload = decode_token(token)
        if payload:
            try:
                user_id = int(payload.get('sub'))
            except (TypeError, ValueError):
                return None
            return User.query.get(user_id)
    return None

def login_required(f):
    """
    登录拦截装饰器。若未登录或 Token 失效，返回 401。
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return make_fail_response('请先登录。', 401)
        
        token = auth_header[7:]
        payload = decode_token(token)
        if not payload:
            return make_fail_response('登录状态已失效，请重新登录。', 401)
        
        try:
            user_id = int(payload.get('sub'))
        except (TypeError, ValueError):
            return make_fail_response('登录状态已失效，请重新登录。', 401)
        user = User.query.get(user_id)
        if not user:
            return make_fail_response('用户不存在。', 401)
        
        g.current_user = user
        return f(*args, **kwargs)
    return decorated

def permission_check(action='write'):
    """
    权限检查装饰器，适用于修改家谱、成员的接口。
    如果是 write/delete，校验当前用户是否为家谱所有者 (Owner) 或协作修谱人 (Collaborator)。
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # 获取当前用户
            user = getattr(g, 'current_user', None)
            if not user:
                # 尝试在此处获取
                user = get_current_user()
                if not user:
                    return make_fail_response('请先登录。', 401)
                g.current_user = user
            
            # 确定 tree_id
            tree_id = kwargs.get('tree_id') or request.args.get('tree_id')
            
            # 如果是操作成员，通过 member_id 换取 tree_id
            member_id = kwargs.get('member_id')
            if not tree_id and member_id:
                member = Member.query.get(member_id)
                if member:
                    tree_id = member.tree_id
            
            # 如果是请求体内含 tree_id
            if not tree_id and request.is_json:
                payload = request.get_json(silent=True) or {}
                tree_id = payload.get('tree_id')
            
            if not tree_id:
                return make_fail_response('未能关联到特定的家谱，权限校验失败。', 400)
            
            # 校验权限
            tree = Tree.query.get(tree_id)
            if not tree:
                return make_fail_response('家谱不存在。', 404)
            
            # 1. 检查是否为谱主
            if tree.creator_id == user.id:
                return f(*args, **kwargs)
            
            # 2. 检查是否为协作人
            collab = TreeCollaborator.query.filter_by(tree_id=tree_id, user_id=user.id).first()
            if collab:
                # 只有 Owner 能执行删除家谱的操作
                if action == 'delete' and request.path.startswith(f'/api/trees/{tree_id}'):
                    return make_fail_response('只有谱主才能删除该家谱。', 403)
                return f(*args, **kwargs)
            
            return make_fail_response('您没有该家谱的编辑权限，请联系谱主授权。', 403)
        return decorated
    return decorator
