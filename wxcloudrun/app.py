import os
import logging
import sys
from logging.handlers import TimedRotatingFileHandler

from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from sqlalchemy import inspect, text
from dotenv import load_dotenv

from wxcloudrun import db

_this_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_this_dir)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import config
if config.DEBUG:
    load_dotenv(os.path.join(_this_dir, '.env'))

app = Flask(__name__)
app.config.from_object(config)
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'bjyp_secret_key_2026')
CORS(app)
db.init_app(app)

migrate = Migrate(app,db)


def setup_logger(flask_app):
    log_dir = os.path.join(_backend_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, 'app.log')
    file_handler = TimedRotatingFileHandler(
        log_file,
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    file_handler.suffix = "%Y-%m-%d"

    console_handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s (Line %(lineno)d): %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    file_handler.setLevel(logging.INFO)
    console_handler.setLevel(logging.INFO)

    flask_app.logger.handlers.clear()
    flask_app.logger.addHandler(file_handler)
    flask_app.logger.addHandler(console_handler)
    flask_app.logger.setLevel(logging.INFO)
    flask_app.logger.propagate = False
    logging.getLogger('werkzeug').setLevel(logging.INFO)


setup_logger(app)

UPLOAD_ROOT = os.path.join(_this_dir, 'uploads')
AVATAR_UPLOAD_DIR = os.path.join(UPLOAD_ROOT, 'avatars')
ALLOWED_AVATAR_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
MAX_AVATAR_SIZE = 2 * 1024 * 1024
os.makedirs(AVATAR_UPLOAD_DIR, exist_ok=True)


def generate_id(prefix):
    import os
    import time

    suffix = os.urandom(4).hex()
    return f'{prefix}_{int(time.time() * 1000)}_{suffix}'


def get_file_size(file_storage):
    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    return size


def ensure_permission_schema():
    inspector = inspect(db.engine)
    table_names = inspector.get_table_names()
    if 'trees' not in table_names:
        return

    tree_columns = {column['name'] for column in inspector.get_columns('trees')}
    if 'creator_id' not in tree_columns:
        db.session.execute(text('ALTER TABLE trees ADD COLUMN creator_id INTEGER'))
        db.session.commit()


with app.app_context():
    from wxcloudrun.model import Counters, User, Tree, Member, TreeCollaborator, CollaboratorInvite, MemberReport, MemberCorrection

    try:
        db.create_all()
        ensure_permission_schema()
        if not Counters.query.get(1):
            counter = Counters(id=1, count=0)
            db.session.add(counter)
            db.session.commit()
    except Exception as error:
        app.logger.warning('初始化数据库失败，后续运行可能需要数据库连接。%s', error)

import wxcloudrun.views  # noqa: F401
