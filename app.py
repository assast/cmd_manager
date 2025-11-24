import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_

app = Flask(__name__)

# 配置：优先读取环境变量，方便 Docker 部署时动态修改
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_default_secret')
# 默认使用本地文件，Docker 中会通过环境变量覆盖此路径
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# --- 模型 ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(200))


class Command(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_name = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- 初始化 ---
def init_db():
    """应用启动时检查并创建数据库和默认用户"""
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            print("初始化管理员账号: admin / 123456")
            hashed_pw = generate_password_hash('123456', method='sha256')
            db.session.add(User(username='admin', password_hash=hashed_pw))
            db.session.commit()


# --- 路由 ---
@app.route('/')
@login_required
def index():
    search_query = request.args.get('q', '').strip()

    query = Command.query

    # 搜索逻辑：匹配分组、标题或内容
    if search_query:
        query = query.filter(
            or_(
                Command.group_name.contains(search_query),
                Command.title.contains(search_query),
                Command.content.contains(search_query)
            )
        )

    # 排序逻辑：先按分组名称 A-Z 排序，再按标题 A-Z 排序
    commands = query.order_by(Command.group_name, Command.title).all()

    # 分组逻辑：将扁平的列表转换为字典 { "分组名": [命令对象, ...] }
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
        db.session.add(Command(group_name=group, title=title, content=content))
        db.session.commit()
        flash('命令添加成功', 'success')
    else:
        flash('请填写所有字段', 'danger')

    return redirect(url_for('index'))


@app.route('/delete/<int:id>')
@login_required
def delete_command(id):
    cmd = Command.query.get_or_404(id)
    db.session.delete(cmd)
    db.session.commit()
    flash('命令已删除', 'info')
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
            flash('用户名或密码错误', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# 启动时初始化数据库
init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)