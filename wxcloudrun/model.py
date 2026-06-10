from datetime import datetime

from wxcloudrun import db


class Tree(db.Model):
    __tablename__ = 'trees'
    id = db.Column(db.String(64), primary_key=True)
    surname = db.Column(db.String(64), nullable=False)
    title = db.Column(db.String(128), nullable=False)
    hall_name = db.Column(db.String(128), nullable=True)
    region = db.Column(db.String(255), nullable=True)
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


class CollaboratorInvite(db.Model):
    __tablename__ = 'collaborator_invites'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tree_id = db.Column(db.String(64), db.ForeignKey('trees.id'), nullable=False)
    invite_code = db.Column(db.String(128), unique=True, nullable=False, index=True)
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    expire_time = db.Column(db.DateTime, nullable=False)


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
