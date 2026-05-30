from datetime import datetime

from wxcloudrun import db
from wxcloudrun.model import Counters, Member, Tree


def query_counterbyid(counter_id):
    return Counters.query.get(counter_id)


def delete_counterbyid(counter_id):
    counter = query_counterbyid(counter_id)
    if not counter:
        return False
    db.session.delete(counter)
    db.session.commit()
    return True


def insert_counter():
    counter = Counters(count=1)
    db.session.add(counter)
    db.session.commit()
    return counter


def update_counterbyid(counter_id, count):
    counter = query_counterbyid(counter_id)
    if not counter:
        return None
    counter.count = count
    counter.updated_at = datetime.now()
    db.session.commit()
    return counter


def get_tree_by_id(tree_id):
    return Tree.query.get(tree_id)


def get_member_by_id(member_id):
    return Member.query.get(member_id)


def get_members(tree_id):
    return Member.query.filter_by(tree_id=tree_id).all()


def delete_tree_with_members(tree_id):
    tree = get_tree_by_id(tree_id)
    if not tree:
        return False
    Member.query.filter_by(tree_id=tree_id).delete()
    db.session.delete(tree)
    db.session.commit()
    return True


def has_parent_cycle(child_id, new_parent_id):
    if not new_parent_id or child_id == new_parent_id:
        return False

    visited = set()
    current_id = new_parent_id
    while current_id:
        if current_id == child_id:
            return True
        if current_id in visited:
            return True
        visited.add(current_id)
        parent = get_member_by_id(current_id)
        if not parent:
            break
        current_id = parent.parent_id
    return False


def clear_spouse_links(member):
    if member.spouse_id:
        spouse = get_member_by_id(member.spouse_id)
        if spouse:
            spouse.spouse_id = ''
            spouse.is_spouse = False
            db.session.add(spouse)
    member.spouse_id = ''
    member.is_spouse = False


def sync_spouse_link(member, spouse):
    if not spouse:
        return
    member.spouse_id = spouse.id
    member.is_spouse = True
    spouse.spouse_id = member.id
    spouse.is_spouse = True
    db.session.add(spouse)


def validate_member_relation(tree_id, parent_id, spouse_id, current_member_id=None):
    if parent_id and parent_id != '':
        parent = get_member_by_id(parent_id)
        if not parent or parent.tree_id != tree_id:
            return False, '父节点不存在或不属于当前家谱。'
        if current_member_id and has_parent_cycle(current_member_id, parent_id):
            return False, '父节点关系会导致循环。'

    if spouse_id and spouse_id != '':
        spouse = get_member_by_id(spouse_id)
        if not spouse or spouse.tree_id != tree_id:
            return False, '配偶不存在或不属于当前家谱。'
        if spouse_id == current_member_id:
            return False, '配偶不能是自身。'
        if spouse.spouse_id and spouse.spouse_id != current_member_id:
            return False, '指定配偶已关联其他族员。'

    return True, ''


def delete_member_safe(member_id):
    member = get_member_by_id(member_id)
    if not member:
        return None, '未找到该族员。'
    children_exist = Member.query.filter_by(parent_id=member.id).first()
    if children_exist:
        return None, '当前族员存在子代，请先删除或解除子代关系。'
    if member.spouse_id:
        spouse = get_member_by_id(member.spouse_id)
        if spouse:
            spouse.spouse_id = ''
            spouse.is_spouse = False
            db.session.add(spouse)
    db.session.delete(member)
    db.session.commit()
    return member, ''
