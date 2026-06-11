from datetime import datetime

from wxcloudrun import db


class Tree(db.Model):
    __tablename__ = 'trees'
    id = db.Column(db.String(64), primary_key=True)
    surname = db.Column(db.String(64), nullable=False)
    title = db.Column(db.String(128), nullable=False)
    hall_name = db.Column(db.String(128), nullable=True)
    region = db.Column(db.String(255), nullable=True)
    preface = db.Column(db.Text, default='', nullable=True)
    create_time = db.Column(db.String(64), nullable=False)
    update_time = db.Column(db.String(64), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'surname': self.surname,
            'title': self.title,
            'hall_name': self.hall_name or '',
            'region': self.region or '',
            'preface': self.preface or '',
            'create_time': self.create_time,
            'update_time': self.update_time,
            'creator_id': self.creator_id,
        }


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    openid = db.Column(db.String(128), unique=True, nullable=False, index=True)
    nickname = db.Column(db.String(128), nullable=True)
    avatar_url = db.Column(db.String(512), nullable=True)
    create_time = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            'id': self.id,
            'openid': self.openid,
            'nickname': self.nickname or '微信用户',
            'avatar_url': self.avatar_url or '',
        }


class TreeCollaborator(db.Model):
    __tablename__ = 'tree_collaborators'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tree_id = db.Column(db.String(64), db.ForeignKey('trees.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        comments = []
        if self.id:
            for comment in reversed(
                AnnouncementComment.query.filter_by(announcement_id=self.id)
                .order_by(AnnouncementComment.create_time.desc())
                .limit(3)
                .all()
            ):
                comment_item = comment.to_dict()
                user = User.query.get(comment.user_id)
                comment_item['user_name'] = user.nickname if user and user.nickname else '微信用户'
                comments.append(comment_item)
        return {
            'id': self.id,
            'tree_id': self.tree_id,
            'user_id': self.user_id,
            'create_time': self.create_time.isoformat() if self.create_time else '',
        }


class CollaboratorInvite(db.Model):
    __tablename__ = 'collaborator_invites'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tree_id = db.Column(db.String(64), db.ForeignKey('trees.id'), nullable=False)
    invite_code = db.Column(db.String(128), unique=True, nullable=False, index=True)
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    expire_time = db.Column(db.DateTime, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'tree_id': self.tree_id,
            'invite_code': self.invite_code,
            'is_used': self.is_used,
            'expire_time': self.expire_time.isoformat() if self.expire_time else '',
        }


class TreeAnnouncement(db.Model):
    __tablename__ = 'tree_announcements'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tree_id = db.Column(db.String(64), db.ForeignKey('trees.id'), nullable=False, index=True)
    category = db.Column(db.String(32), default='notice', nullable=False)
    title = db.Column(db.String(128), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_pinned = db.Column(db.Boolean, default=False, nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def to_dict(self):
        comments = []
        if self.id:
            recent_comments = (
                AnnouncementComment.query
                .filter_by(announcement_id=self.id)
                .order_by(AnnouncementComment.create_time.desc())
                .limit(3)
                .all()
            )
            for comment in reversed(recent_comments):
                comment_item = comment.to_dict()
                user = User.query.get(comment.user_id)
                comment_item['user_name'] = user.nickname if user and user.nickname else '微信用户'
                comments.append(comment_item)
        return {
            'id': self.id,
            'tree_id': self.tree_id,
            'category': self.category or 'notice',
            'title': self.title,
            'content': self.content,
            'author_id': self.author_id,
            'is_pinned': self.is_pinned,
            'create_time': self.create_time.isoformat() if self.create_time else '',
            'like_count': AnnouncementLike.query.filter_by(announcement_id=self.id).count() if self.id else 0,
            'comment_count': AnnouncementComment.query.filter_by(announcement_id=self.id).count() if self.id else 0,
            'share_count': AnnouncementShare.query.filter_by(announcement_id=self.id).count() if self.id else 0,
            'comments': comments,
        }


class AnnouncementLike(db.Model):
    __tablename__ = 'announcement_likes'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey('tree_announcements.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    create_time = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'announcement_id': self.announcement_id,
            'user_id': self.user_id,
            'create_time': self.create_time.isoformat() if self.create_time else '',
        }


class AnnouncementComment(db.Model):
    __tablename__ = 'announcement_comments'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey('tree_announcements.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'announcement_id': self.announcement_id,
            'user_id': self.user_id,
            'content': self.content or '',
            'create_time': self.create_time.isoformat() if self.create_time else '',
        }


class AnnouncementShare(db.Model):
    __tablename__ = 'announcement_shares'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey('tree_announcements.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    create_time = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'announcement_id': self.announcement_id,
            'user_id': self.user_id,
            'create_time': self.create_time.isoformat() if self.create_time else '',
        }


class TreeVisit(db.Model):
    __tablename__ = 'tree_visits'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tree_id = db.Column(db.String(64), db.ForeignKey('trees.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    openid = db.Column(db.String(128), nullable=True)
    visitor_name = db.Column(db.String(128), default='访客', nullable=False)
    page = db.Column(db.String(64), default='tree_space', nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'tree_id': self.tree_id,
            'user_id': self.user_id,
            'openid': self.openid or '',
            'visitor_name': self.visitor_name or '访客',
            'page': self.page or '',
            'create_time': self.create_time.isoformat() if self.create_time else '',
        }


class OperationLog(db.Model):
    __tablename__ = 'operation_logs'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tree_id = db.Column(db.String(64), db.ForeignKey('trees.id'), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    category = db.Column(db.String(32), default='system', nullable=False)
    action = db.Column(db.String(64), nullable=False)
    detail = db.Column(db.String(512), default='', nullable=True)
    create_time = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'tree_id': self.tree_id or '',
            'user_id': self.user_id,
            'category': self.category or 'system',
            'action': self.action,
            'detail': self.detail or '',
            'create_time': self.create_time.isoformat() if self.create_time else '',
        }


class TreePrivacySetting(db.Model):
    __tablename__ = 'tree_privacy_settings'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tree_id = db.Column(db.String(64), db.ForeignKey('trees.id'), unique=True, nullable=False, index=True)
    visibility = db.Column(db.String(20), default='private', nullable=False)
    allow_qr_access = db.Column(db.Boolean, default=True, nullable=False)
    allow_password_access = db.Column(db.Boolean, default=False, nullable=False)
    access_password = db.Column(db.String(64), default='', nullable=True)
    allow_name_relation_access = db.Column(db.Boolean, default=True, nullable=False)
    auto_join_by_name_relation = db.Column(db.Boolean, default=True, nullable=False)
    allow_name_birth_access = db.Column(db.Boolean, default=True, nullable=False)
    auto_join_by_name_birth = db.Column(db.Boolean, default=True, nullable=False)
    allow_member_application = db.Column(db.Boolean, default=True, nullable=False)
    allow_branch_binding_application = db.Column(db.Boolean, default=True, nullable=False)
    show_in_public_list = db.Column(db.Boolean, default=True, nullable=False)
    tree_view_scope = db.Column(db.String(32), default='family', nullable=False)
    birth_date_scope = db.Column(db.String(32), default='public', nullable=False)
    death_date_scope = db.Column(db.String(32), default='public', nullable=False)
    contact_scope = db.Column(db.String(32), default='manager', nullable=False)
    bound_member_edit_scope = db.Column(db.String(32), default='none', nullable=False)
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'tree_id': self.tree_id,
            'visibility': self.visibility or 'private',
            'allow_qr_access': self.allow_qr_access,
            'allow_password_access': self.allow_password_access,
            'access_password': self.access_password or '',
            'allow_name_relation_access': self.allow_name_relation_access,
            'auto_join_by_name_relation': self.auto_join_by_name_relation,
            'allow_name_birth_access': self.allow_name_birth_access,
            'auto_join_by_name_birth': self.auto_join_by_name_birth,
            'allow_member_application': self.allow_member_application,
            'allow_branch_binding_application': self.allow_branch_binding_application,
            'show_in_public_list': self.show_in_public_list,
            'tree_view_scope': self.tree_view_scope or 'family',
            'birth_date_scope': self.birth_date_scope or 'public',
            'death_date_scope': self.death_date_scope or 'public',
            'contact_scope': self.contact_scope or 'manager',
            'bound_member_edit_scope': self.bound_member_edit_scope or 'none',
            'update_time': self.update_time.isoformat() if self.update_time else '',
        }


class GenealogyArticle(db.Model):
    __tablename__ = 'genealogy_articles'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tree_id = db.Column(db.String(64), db.ForeignKey('trees.id'), nullable=False, index=True)
    category = db.Column(db.String(32), default='preface', nullable=False, index=True)
    title = db.Column(db.String(128), nullable=False)
    content = db.Column(db.Text, default='', nullable=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    create_time = db.Column(db.DateTime, default=datetime.now, nullable=False)
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'tree_id': self.tree_id,
            'category': self.category or 'preface',
            'title': self.title,
            'content': self.content or '',
            'sort_order': self.sort_order or 0,
            'author_id': self.author_id,
            'create_time': self.create_time.isoformat() if self.create_time else '',
            'update_time': self.update_time.isoformat() if self.update_time else '',
        }


class VillageProfile(db.Model):
    __tablename__ = 'village_profiles'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tree_id = db.Column(db.String(64), db.ForeignKey('trees.id'), unique=True, nullable=False, index=True)
    village_name = db.Column(db.String(128), default='', nullable=True)
    alias_name = db.Column(db.String(128), default='', nullable=True)
    area_text = db.Column(db.String(128), default='', nullable=True)
    region = db.Column(db.String(255), default='', nullable=True)
    location = db.Column(db.String(255), default='', nullable=True)
    famous_people = db.Column(db.String(255), default='', nullable=True)
    intro = db.Column(db.Text, default='', nullable=True)
    cover_url = db.Column(db.String(512), default='', nullable=True)
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'tree_id': self.tree_id,
            'village_name': self.village_name or '',
            'alias_name': self.alias_name or '',
            'area_text': self.area_text or '',
            'region': self.region or '',
            'location': self.location or '',
            'famous_people': self.famous_people or '',
            'intro': self.intro or '',
            'cover_url': self.cover_url or '',
            'update_time': self.update_time.isoformat() if self.update_time else '',
        }


class FamilyAlbum(db.Model):
    __tablename__ = 'family_albums'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tree_id = db.Column(db.String(64), db.ForeignKey('trees.id'), nullable=False, index=True)
    title = db.Column(db.String(128), nullable=False)
    cover_url = db.Column(db.String(512), default='', nullable=True)
    create_time = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'tree_id': self.tree_id,
            'title': self.title,
            'cover_url': self.cover_url or '',
            'create_time': self.create_time.isoformat() if self.create_time else '',
        }


class FamilyPhoto(db.Model):
    __tablename__ = 'family_photos'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tree_id = db.Column(db.String(64), db.ForeignKey('trees.id'), nullable=False, index=True)
    album_id = db.Column(db.Integer, db.ForeignKey('family_albums.id'), nullable=True, index=True)
    image_url = db.Column(db.String(512), nullable=False)
    caption = db.Column(db.String(255), default='', nullable=True)
    location_text = db.Column(db.String(255), default='', nullable=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    create_time = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'tree_id': self.tree_id,
            'album_id': self.album_id,
            'image_url': self.image_url,
            'caption': self.caption or '',
            'location_text': self.location_text or '',
            'uploader_id': self.uploader_id,
            'create_time': self.create_time.isoformat() if self.create_time else '',
        }


class AlbumSetting(db.Model):
    __tablename__ = 'album_settings'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tree_id = db.Column(db.String(64), db.ForeignKey('trees.id'), unique=True, nullable=False, index=True)
    record_location = db.Column(db.Boolean, default=True, nullable=False)
    capacity_mb = db.Column(db.Integer, default=50, nullable=False)
    used_mb = db.Column(db.Integer, default=0, nullable=False)
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'tree_id': self.tree_id,
            'record_location': self.record_location,
            'capacity_mb': self.capacity_mb,
            'used_mb': self.used_mb,
            'remaining_mb': max(0, (self.capacity_mb or 0) - (self.used_mb or 0)),
            'update_time': self.update_time.isoformat() if self.update_time else '',
        }


class MemberBinding(db.Model):
    __tablename__ = 'member_bindings'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tree_id = db.Column(db.String(64), db.ForeignKey('trees.id'), nullable=False, index=True)
    member_id = db.Column(db.String(64), db.ForeignKey('members.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    relation_label = db.Column(db.String(64), default='', nullable=True)
    note = db.Column(db.Text, default='', nullable=True)
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)
    handler_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reject_reason = db.Column(db.String(255), default='', nullable=True)
    create_time = db.Column(db.DateTime, default=datetime.now, nullable=False)
    handle_time = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'tree_id': self.tree_id,
            'member_id': self.member_id,
            'user_id': self.user_id,
            'relation_label': self.relation_label or '',
            'note': self.note or '',
            'status': self.status,
            'handler_id': self.handler_id,
            'reject_reason': self.reject_reason or '',
            'create_time': self.create_time.isoformat() if self.create_time else '',
            'handle_time': self.handle_time.isoformat() if self.handle_time else '',
        }


class MemberReport(db.Model):
    __tablename__ = 'member_reports'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tree_id = db.Column(db.String(64), db.ForeignKey('trees.id'), nullable=False, index=True)
    parent_id = db.Column(db.String(64), db.ForeignKey('members.id'), nullable=True)
    spouse_id = db.Column(db.String(64), db.ForeignKey('members.id'), nullable=True)
    relation_type = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    is_alive = db.Column(db.Boolean, default=True, nullable=False)
    birth_date = db.Column(db.String(64), default='', nullable=True)
    desc = db.Column(db.Text, default='', nullable=True)
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)
    submitter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.now, nullable=False)
    handle_time = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'tree_id': self.tree_id,
            'parent_id': self.parent_id or '',
            'spouse_id': self.spouse_id or '',
            'relation_type': self.relation_type,
            'name': self.name,
            'gender': self.gender,
            'is_alive': self.is_alive,
            'birth_date': self.birth_date or '',
            'desc': self.desc or '',
            'status': self.status,
            'submitter_id': self.submitter_id,
            'create_time': self.create_time.isoformat() if self.create_time else '',
            'handle_time': self.handle_time.isoformat() if self.handle_time else '',
        }


class MemberCorrection(db.Model):
    __tablename__ = 'member_corrections'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tree_id = db.Column(db.String(64), db.ForeignKey('trees.id'), nullable=False, index=True)
    member_id = db.Column(db.String(64), db.ForeignKey('members.id'), nullable=False, index=True)
    proposed_name = db.Column(db.String(64), nullable=True)
    proposed_gender = db.Column(db.String(10), nullable=True)
    proposed_is_alive = db.Column(db.Boolean, nullable=True)
    proposed_birth_date = db.Column(db.String(64), nullable=True)
    proposed_desc = db.Column(db.Text, nullable=True)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False, index=True)
    submitter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    create_time = db.Column(db.DateTime, default=datetime.now, nullable=False)
    handle_time = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'tree_id': self.tree_id,
            'member_id': self.member_id,
            'proposed_name': self.proposed_name,
            'proposed_gender': self.proposed_gender,
            'proposed_is_alive': self.proposed_is_alive,
            'proposed_birth_date': self.proposed_birth_date,
            'proposed_desc': self.proposed_desc,
            'reason': self.reason,
            'status': self.status,
            'submitter_id': self.submitter_id,
            'create_time': self.create_time.isoformat() if self.create_time else '',
            'handle_time': self.handle_time.isoformat() if self.handle_time else '',
        }


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
    is_notable = db.Column(db.Boolean, default=False, nullable=False)
    notable_category = db.Column(db.String(32), default='elite', nullable=True)
    achievements = db.Column(db.String(512), default='', nullable=True)

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
            'adoption_type': self.adoption_type or '',
            'is_notable': self.is_notable,
            'notable_category': self.notable_category or 'elite',
            'achievements': self.achievements or ''
        }


class Counters(db.Model):
    __tablename__ = 'Counters'
    id = db.Column(db.Integer, primary_key=True)
    count = db.Column(db.Integer, default=1)
    created_at = db.Column(
        'createdAt',
        db.DateTime,
        nullable=False,
        default=datetime.now,
    )
    updated_at = db.Column(
        'updatedAt',
        db.DateTime,
        nullable=False,
        default=datetime.now,
        onupdate=datetime.now,
    )
