import os
import secrets
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError  # 【修改点】引入完整性错误异常

app = Flask(__name__)

# --- 配置 ---
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


class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    # 新增排序字段，默认0，越小越靠前
    sort_order = db.Column(db.Integer, default=0)

    # 关联查询时，让 commands 按 sort_order 排序
    commands = db.relationship('Command', backref='group', lazy=True,
                               order_by="[Command.sort_order, Command.id]",
                               cascade="all, delete-orphan")


class Command(db.Model):
    __tablename__ = 'commands'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    # 新增排序字段
    sort_order = db.Column(db.Integer, default=0)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# --- 初始化 (并发安全版) ---
def init_db():
    with app.app_context():
        db.create_all()

        # 1. 初始化管理员
        admin_user = os.environ.get('ADMIN_USER', 'admin')
        admin_pass = os.environ.get('ADMIN_PASSWORD', '123456')

        # 检查用户是否存在
        if not User.query.filter_by(username=admin_user).first():
            try:
                hashed_pw = generate_password_hash(admin_pass)
                db.session.add(User(username=admin_user, password_hash=hashed_pw))
                db.session.commit()
                print(f"[初始化] 管理员 {admin_user} 创建成功")

                # 2. 预置默认数据
                default_data = [
                    ("常用命令", 0, [
                        ("查看端口占用", "lsof -i :8080", 0),
                        ("解压 tar.gz", "tar -zxvf filename.tar.gz", 10),
                        ("查看磁盘空间", "df -h", 20),
                    ]),
                    ("Docker", 10, [
                        ("查看容器", "docker ps -a", 0),
                        ("查看日志", "docker logs -f --tail=100 <id>", 1),
                        ("进入容器", "docker exec -it <id> /bin/bash", 2),
                    ]),
                    ("Git", 20, [
                        ("简略日志", "git log --oneline -n 10", 0),
                        ("撤销修改", "git checkout .", 1),
                    ])
                ]

                for g_name, g_sort, cmds in default_data:
                    group = None
                    # 尝试查找分组
                    group = Group.query.filter_by(name=g_name).first()

                    # 如果分组不存在，尝试创建
                    if not group:
                        try:
                            group = Group(name=g_name, sort_order=g_sort)
                            db.session.add(group)
                            # flush 以获取 ID，如果此时有并发写入，这里会报错
                            db.session.flush()
                            db.session.commit()
                            print(f"[初始化] 分组 {g_name} 创建成功")
                        except IntegrityError:
                            db.session.rollback()
                            # 回滚后，说明被别的进程抢先创建了，重新查询获取该分组对象
                            group = Group.query.filter_by(name=g_name).first()
                            print(f"[初始化] 分组 {g_name} 并发跳过")

                    # 确保拿到了分组对象后，再处理下面的命令
                    if group:
                        for c_title, c_content, c_sort in cmds:
                            # 检查命令是否存在（避免重复添加）
                            if not Command.query.filter_by(title=c_title, group_id=group.id).first():
                                try:
                                    cmd = Command(title=c_title, content=c_content, sort_order=c_sort,
                                                  group_id=group.id)
                                    db.session.add(cmd)
                                    db.session.commit()
                                except IntegrityError:
                                    db.session.rollback()
                                    # 命令冲突忽略即可
                                    pass

            except IntegrityError:
                db.session.rollback()
                print(f"[初始化] 管理员 {admin_user} 已由其他进程创建，跳过")

        print("数据库初始化检查完成")


# --- 主页路由 ---

@app.route('/')
@login_required
def index():
    search_query = request.args.get('q', '').strip()

    if search_query:
        # 搜索逻辑
        commands = Command.query.filter(
            or_(Command.title.contains(search_query),
                Command.content.contains(search_query))
        ).order_by(Command.sort_order, Command.id).all()

        groups_data = {}
        for cmd in commands:
            if cmd.group not in groups_data:
                groups_data[cmd.group] = []
            groups_data[cmd.group].append(cmd)

        display_data = sorted(groups_data.items(), key=lambda x: (x[0].sort_order, x[0].id))
    else:
        # 正常展示
        all_groups = Group.query.order_by(Group.sort_order, Group.id).all()
        display_data = []
        for g in all_groups:
            if g.commands:
                display_data.append((g, g.commands))
            elif not search_query:
                display_data.append((g, []))

    all_groups_list = Group.query.order_by(Group.sort_order, Group.id).all()
    return render_template('index.html', display_data=display_data, all_groups=all_groups_list,
                           search_query=search_query)


@app.route('/command/add', methods=['POST'])
@login_required
def add_command():
    group_id = request.form.get('group_id')
    title = request.form.get('title')
    content = request.form.get('content')
    sort_order = request.form.get('sort_order', 0, type=int)

    if group_id and title and content:
        cmd = Command(group_id=group_id, title=title, content=content, sort_order=sort_order)
        db.session.add(cmd)
        db.session.commit()
        flash('命令添加成功', 'success')
    else:
        flash('请填写完整', 'warning')
    return redirect(url_for('index'))


@app.route('/command/edit/<int:id>', methods=['POST'])
@login_required
def edit_command(id):
    cmd = db.get_or_404(Command, id)
    cmd.title = request.form.get('title')
    cmd.content = request.form.get('content')
    cmd.group_id = request.form.get('group_id')
    cmd.sort_order = request.form.get('sort_order', 0, type=int)

    db.session.commit()
    flash('命令已更新', 'success')
    return redirect(url_for('index'))


@app.route('/command/delete/<int:id>')
@login_required
def delete_command(id):
    cmd = db.get_or_404(Command, id)
    db.session.delete(cmd)
    db.session.commit()
    flash('命令已删除', 'info')
    return redirect(url_for('index'))


# --- 分组管理路由 ---

@app.route('/groups')
@login_required
def manage_groups():
    groups = Group.query.order_by(Group.sort_order, Group.id).all()
    return render_template('groups.html', groups=groups)


@app.route('/groups/add', methods=['POST'])
@login_required
def add_group():
    name = request.form.get('name')
    sort_order = request.form.get('sort_order', 0, type=int)
    if name:
        if Group.query.filter_by(name=name).first():
            flash('该分组已存在', 'warning')
        else:
            db.session.add(Group(name=name, sort_order=sort_order))
            db.session.commit()
            flash('分组创建成功', 'success')
    return redirect(url_for('manage_groups'))


@app.route('/groups/edit/<int:id>', methods=['POST'])
@login_required
def edit_group(id):
    group = db.get_or_404(Group, id)
    new_name = request.form.get('name')
    sort_order = request.form.get('sort_order', 0, type=int)

    if new_name:
        group.name = new_name
        group.sort_order = sort_order
        db.session.commit()
        flash('分组更新成功', 'success')
    return redirect(url_for('manage_groups'))


@app.route('/groups/delete/<int:id>')
@login_required
def delete_group(id):
    group = db.get_or_404(Group, id)
    try:
        # 手动清理命令 (双重保险)
        for cmd in group.commands:
            db.session.delete(cmd)
        db.session.delete(group)
        db.session.commit()
        flash(f'分组 "{group.name}" 已删除', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败: {str(e)}', 'danger')
    return redirect(url_for('manage_groups'))


# --- 认证与API ---

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


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old = request.form.get('old_password')
        new = request.form.get('new_password')
        confirm = request.form.get('confirm_password')

        if not check_password_hash(current_user.password_hash, old):
            flash('旧密码错误', 'danger')
            return redirect(url_for('change_password'))
        if new != confirm or not new:
            flash('新密码不一致或为空', 'warning')
            return redirect(url_for('change_password'))

        current_user.password_hash = generate_password_hash(new)
        db.session.commit()
        flash('密码修改成功，请重新登录', 'success')
        logout_user()
        return redirect(url_for('login'))

    return render_template('change_password.html')


@app.route('/api/list')
@login_required
def api_list():
    groups = Group.query.order_by(Group.sort_order, Group.id).all()
    data = []
    for g in groups:
        if not g.commands: continue
        cmds = [{'title': c.title, 'content': c.content} for c in g.commands]
        data.append({'group': g.name, 'commands': cmds})
    return jsonify(data)


init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)