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

    def to_dict(self):
        return {
            'id': self.id,
            'surname': self.surname,
            'title': self.title,
            'hall_name': self.hall_name or '',
            'region': self.region or '',
            'create_time': self.create_time,
            'update_time': self.update_time,
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
