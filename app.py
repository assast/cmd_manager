import os
import secrets
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_

app = Flask(__name__)

# --- 配置 ---
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# --- 数据库模型 (升级版) ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password_hash = db.Column(db.String(200))


class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    # 关联关系：让 Group 可以直接访问包含的 commands，并按标题排序
    commands = db.relationship('Command', backref='group', lazy=True, order_by="Command.title")


class Command(db.Model):
    __tablename__ = 'commands'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    # 外键关联 Group 表
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- 初始化 ---
def init_db():
    with app.app_context():
        db.create_all()

        # 1. 初始化管理员
        if not User.query.first():
            admin_user = os.environ.get('ADMIN_USER', 'admin')
            admin_pass = os.environ.get('ADMIN_PASSWORD')
            if not admin_pass:
                admin_pass = secrets.token_urlsafe(10)
                print(f"\n[系统初始化] 随机密码生成: {admin_pass}\n")

            hashed_pw = generate_password_hash(admin_pass)
            db.session.add(User(username=admin_user, password_hash=hashed_pw))
            db.session.commit()

        # 2. 初始化默认分组 (防止下拉框为空)
        if not Group.query.first():
            db.session.add(Group(name="默认分组"))
            db.session.commit()


# --- 路由: 主页与命令管理 ---

@app.route('/')
@login_required
def index():
    search_query = request.args.get('q', '').strip()

    # 如果有搜索，我们需要过滤显示
    # 注意：为了保持分组视图，我们查询 Group，但只包含匹配的 Command
    # 这里为了简单，如果搜索存在，我们手动构建数据结构

    if search_query:
        # 查找匹配的命令
        commands = Command.query.filter(
            or_(Command.title.contains(search_query),
                Command.content.contains(search_query))
        ).all()

        # 临时按分组归类
        groups_data = {}
        for cmd in commands:
            if cmd.group not in groups_data:
                groups_data[cmd.group] = []
            groups_data[cmd.group].append(cmd)

        # 转换为列表元组方便前端遍历 [(group_obj, [cmd_list]), ...]
        display_data = groups_data.items()
    else:
        # 正常展示：查询所有分组 (按名称排序)
        all_groups = Group.query.order_by(Group.name).all()
        # 格式统一为: [(group_obj, group.commands), ...]
        display_data = []
        for g in all_groups:
            if g.commands:  # 只显示有命令的分组，或者你想显示空分组也可以
                display_data.append((g, g.commands))
            elif not search_query:  # 没搜索时，空分组也显示，方便知道有哪些组
                display_data.append((g, []))

    # 获取所有分组供“新增/编辑”模态框的下拉列表使用
    all_groups_list = Group.query.order_by(Group.name).all()

    return render_template('index.html', display_data=display_data, all_groups=all_groups_list,
                           search_query=search_query)


@app.route('/command/add', methods=['POST'])
@login_required
def add_command():
    group_id = request.form.get('group_id')
    title = request.form.get('title')
    content = request.form.get('content')

    if group_id and title and content:
        cmd = Command(group_id=group_id, title=title, content=content)
        db.session.add(cmd)
        db.session.commit()
        flash('命令添加成功', 'success')
    else:
        flash('请填写完整', 'warning')
    return redirect(url_for('index'))


@app.route('/command/edit/<int:id>', methods=['POST'])
@login_required
def edit_command(id):
    cmd = Command.query.get_or_404(id)
    cmd.title = request.form.get('title')
    cmd.content = request.form.get('content')
    cmd.group_id = request.form.get('group_id')

    db.session.commit()
    flash('命令已更新', 'success')
    return redirect(url_for('index'))


@app.route('/command/delete/<int:id>')
@login_required
def delete_command(id):
    cmd = Command.query.get_or_404(id)
    db.session.delete(cmd)
    db.session.commit()
    flash('命令已删除', 'info')
    return redirect(url_for('index'))


# --- 路由: 分组管理 ---

@app.route('/groups')
@login_required
def manage_groups():
    groups = Group.query.order_by(Group.name).all()
    return render_template('groups.html', groups=groups)


@app.route('/groups/add', methods=['POST'])
@login_required
def add_group():
    name = request.form.get('name')
    if name:
        if Group.query.filter_by(name=name).first():
            flash('该分组已存在', 'warning')
        else:
            db.session.add(Group(name=name))
            db.session.commit()
            flash('分组创建成功', 'success')
    return redirect(url_for('manage_groups'))


@app.route('/groups/edit/<int:id>', methods=['POST'])
@login_required
def edit_group(id):
    group = Group.query.get_or_404(id)
    new_name = request.form.get('name')
    if new_name:
        group.name = new_name
        db.session.commit()
        flash('分组重命名成功', 'success')
    return redirect(url_for('manage_groups'))


@app.route('/groups/delete/<int:id>')
@login_required
def delete_group(id):
    group = Group.query.get_or_404(id)
    # 安全检查：如果分组下有命令，禁止删除，防止误删数据
    if group.commands:
        flash(f'无法删除：分组 "{group.name}" 下还有 {len(group.commands)} 条命令。请先删除或移动命令。', 'danger')
    else:
        db.session.delete(group)
        db.session.commit()
        flash('分组已删除', 'success')
    return redirect(url_for('manage_groups'))


# --- 登录相关 ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password_hash, request.form.get('password')):
            login_user(user)
            return redirect(url_for('index'))
        flash('用户名或密码错误', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)