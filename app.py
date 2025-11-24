import os
import secrets
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_
from flask import jsonify

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

        # 1. 初始化管理员 (保持原逻辑)
        if not User.query.first():
            admin_user = os.environ.get('ADMIN_USER', 'admin')
            admin_pass = os.environ.get('ADMIN_PASSWORD', '123456')

            hashed_pw = generate_password_hash(admin_pass)
            db.session.add(User(username=admin_user, password_hash=hashed_pw))
            db.session.commit()

        # ==========================================
        # 2. 预置默认命令数据 (在这里修改你的内置命令)
        # ==========================================
        default_data = {
            "常用命令": [
                ("查看端口占用", "lsof -i :8080"),
                ("解压 tar.gz", "tar -zxvf filename.tar.gz"),
                ("查看磁盘空间", "df -h"),
            ],
            "Docker": [
                ("查看所有容器", "docker ps -a"),
                ("进入容器终端", "docker exec -it <container_id> /bin/bash"),
                ("查看实时日志", "docker logs -f --tail=100 <container_id>"),
                ("清理无用镜像", "docker system prune -a"),
            ],
            "Git": [
                ("简略提交日志", "git log --oneline -n 10"),
                ("撤销工作区修改", "git checkout ."),
                ("强制拉取覆盖本地", "git fetch --all\ngit reset --hard origin/master"),
            ],
            "Kubernetes": [
                ("查看所有 Pod", "kubectl get pods -A"),
                ("查看 Pod 描述", "kubectl describe pod <pod_name>"),
            ]
        }

        # 3. 循环写入数据库
        for group_name, commands in default_data.items():
            # A. 检查或创建分组
            group = Group.query.filter_by(name=group_name).first()
            if not group:
                group = Group(name=group_name)
                db.session.add(group)
                db.session.commit()  # 提交以获取 group.id
                print(f"[初始化] 创建分组: {group_name}")

            # B. 检查或创建命令
            for title, content in commands:
                # 检查该分组下是否已存在同名标题的命令，避免重复添加
                exists = Command.query.filter_by(title=title, group_id=group.id).first()
                if not exists:
                    cmd = Command(title=title, content=content, group_id=group.id)
                    db.session.add(cmd)
                    print(f"   └─ 添加命令: {title}")

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


# --- 新增：修改密码路由 ---
@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # 1. 验证旧密码是否正确
        if not check_password_hash(current_user.password_hash, old_password):
            flash('旧密码错误，请重试。', 'danger')
            return redirect(url_for('change_password'))

        # 2. 验证两次新密码是否一致
        if new_password != confirm_password:
            flash('两次输入的新密码不一致。', 'warning')
            return redirect(url_for('change_password'))

        # 3. 验证新密码不能为空
        if not new_password or len(new_password.strip()) == 0:
            flash('新密码不能为空。', 'warning')
            return redirect(url_for('change_password'))

        # 4. 更新数据库
        # 注意：这里使用默认的安全哈希算法
        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()

        flash('密码修改成功！请重新登录。', 'success')
        logout_user()  # 修改成功后强制登出
        return redirect(url_for('login'))

    return render_template('change_password.html')

# --- 新增：API 接口供 Shell 脚本调用 ---
@app.route('/api/list')
@login_required
def api_list():
    # 查询所有分组及其命令
    groups = Group.query.order_by(Group.name).all()
    data = []
    for g in groups:
        if not g.commands: continue

        cmds = []
        for c in g.commands:
            cmds.append({
                'title': c.title,
                'content': c.content
            })

        data.append({
            'group': g.name,
            'commands': cmds
        })
    return jsonify(data)

init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)