import os
import sys

from flask import Flask
from flask_cors import CORS

from wxcloudrun import db

_this_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_this_dir)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

import config

app = Flask(__name__)
app.config.from_object(config)
CORS(app)
db.init_app(app)

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


with app.app_context():
    from wxcloudrun.model import Counters

    try:
        db.create_all()
        if not Counters.query.get(1):
            counter = Counters(id=1, count=0)
            db.session.add(counter)
            db.session.commit()
    except Exception as error:
        print('Warning: 初始化数据库失败，后续运行可能需要数据库连接。', error)

import wxcloudrun.views  # noqa: F401
