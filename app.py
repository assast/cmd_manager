import os
import secrets  # 用于生成安全随机密码
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_

app = Flask(__name__)

# --- 安全配置 ---
# SECRET_KEY 必须保持机密，建议通过环境变量设置
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))
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
    group_name = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- 关键修改：安全的初始化逻辑 ---
def init_db():
    with app.app_context():
        db.create_all()

        # 检查是否已存在管理员
        if not User.query.first():
            # 1. 尝试从环境变量获取用户名和密码
            admin_user = os.environ.get('ADMIN_USER', 'admin')
            admin_pass = os.environ.get('ADMIN_PASSWORD')

            # 2. 如果环境变量没设置密码，则生成随机密码
            is_random_pass = False
            if not admin_pass:
                admin_pass = secrets.token_urlsafe(12)  # 生成12位安全随机字符串
                is_random_pass = True

            # 3. 创建用户
            # 注意：不指定 method，使用默认最安全的 hash 算法
            hashed_pw = generate_password_hash(admin_pass)
            new_user = User(username=admin_user, password_hash=hashed_pw)
            db.session.add(new_user)
            db.session.commit()

            # 4. 打印登录信息到控制台/日志
            print("=" * 50)
            print(f" [系统初始化] 管理员账号已创建")
            print(f" 用户名: {admin_user}")
            if is_random_pass:
                print(f" 密码 (随机生成): {admin_pass}")
                print(f" ⚠️  请保存好此密码，或者在启动时通过环境变量 ADMIN_PASSWORD 指定。")
            else:
                print(f" 密码: (已通过环境变量设置)")
            print("=" * 50)
        else:
            # 如果数据库里已经有用户了，就不再重置，防止覆盖
            pass


# --- 路由保持不变 ---
@app.route('/')
@login_required
def index():
    search_query = request.args.get('q', '').strip()
    query = Command.query
    if search_query:
        query = query.filter(
            or_(Command.group_name.contains(search_query),
                Command.title.contains(search_query),
                Command.content.contains(search_query))
        )
    commands = query.order_by(Command.group_name, Command.title).all()
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
        db.session.add(Command(group_name=group.strip(), title=title.strip(), content=content.strip()))
        db.session.commit()
        flash('添加成功', 'success')
    else:
        flash('请填写完整', 'warning')
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
            flash('登录失败：用户名或密码错误', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# 初始化
init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)