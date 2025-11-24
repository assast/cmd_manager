import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_

app = Flask(__name__)

# 配置：优先从环境变量读取，适合 Docker；本地开发使用默认值
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'secret_key_for_dev')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# --- 数据库模型 ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(200))


class Command(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_name = db.Column(db.String(100), nullable=False)  # 分组
    title = db.Column(db.String(100), nullable=False)  # 标题
    content = db.Column(db.Text, nullable=False)  # 命令内容


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- 初始化逻辑 ---
def init_db():
    with app.app_context():
        db.create_all()
        # 创建默认管理员账号 (已修复哈希报错)
        if not User.query.filter_by(username='admin').first():
            print("正在初始化管理员账号...")
            # 修正点：不再指定 method='sha256'，使用默认安全算法
            hashed_pw = generate_password_hash('123456')
            db.session.add(User(username='admin', password_hash=hashed_pw))
            db.session.commit()
            print("管理员账号创建成功: admin / 123456")


# --- 路由逻辑 ---
@app.route('/')
@login_required
def index():
    search_query = request.args.get('q', '').strip()

    query = Command.query

    # 搜索逻辑
    if search_query:
        query = query.filter(
            or_(
                Command.group_name.contains(search_query),
                Command.title.contains(search_query),
                Command.content.contains(search_query)
            )
        )

    # 排序逻辑：先按分组名排序，组内按标题排序 (A-Z)
    # 这样如果想调整顺序，只需在命名前加 "01.", "02." 即可
    commands = query.order_by(Command.group_name, Command.title).all()

    # 数据处理：转换为字典 { "Docker": [cmd1, cmd2], "Git": [cmd3] }
    grouped_commands = {}
    for cmd in commands:
        if cmd.group_name not in grouped_commands:
            grouped_commands[cmd.group_name] = []
        grouped_commands[cmd.group_name].append(cmd)

    return render_template('index.html', grouped_commands=grouped_commands, search_query=search_query)


@app.route('/add', methods=['POST'])
@login_required
def add_command():
    group = request.form.get('group')
    title = request.form.get('title')
    content = request.form.get('content')

    if group and title and content:
        # 简单的去空格
        db.session.add(Command(group_name=group.strip(), title=title.strip(), content=content.strip()))
        db.session.commit()
        flash('添加成功！', 'success')
    else:
        flash('内容不能为空', 'warning')

    return redirect(url_for('index'))


@app.route('/delete/<int:id>')
@login_required
def delete_command(id):
    cmd = Command.query.get_or_404(id)
    db.session.delete(cmd)
    db.session.commit()
    flash('已删除', 'info')
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('账号或密码错误', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# 应用启动时自动初始化
init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)