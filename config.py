import os

# 是否开启debug模式
DEBUG = True

# 数据库连接 URI 构建
if os.environ.get("MYSQL_ADDRESS") or os.environ.get("MYSQL_USERNAME"):
    # 使用 MySQL (支持微信云托管 MySQL)
    username = os.environ.get("MYSQL_USERNAME", 'root')
    password = os.environ.get("MYSQL_PASSWORD", 'XD7ZTPKg')
    db_address = os.environ.get("MYSQL_ADDRESS", '10.1.104.73:3306')
    database = os.environ.get("MYSQL_DATABASE", 'mapping_family')
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{username}:{password}@{db_address}/{database}?charset=utf8mb4"
elif os.environ.get("POSTGRES_ADDRESS"):
    # 使用 PostgreSQL
    username = os.environ.get("POSTGRES_USERNAME", 'postgres')
    password = os.environ.get("POSTGRES_PASSWORD", 'postgres')
    db_address = os.environ.get("POSTGRES_ADDRESS", '127.0.0.1:5432')
    database = os.environ.get("POSTGRES_DATABASE", 'genealogy')
    SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg2://{username}:{password}@{db_address}/{database}"
else:
    # 开发环境回退：使用 SQLite
    db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'wxcloudrun', 'data'))
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, 'genealogy.db')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"

SQLALCHEMY_TRACK_MODIFICATIONS = False
