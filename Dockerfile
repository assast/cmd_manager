# 使用官方 Python 3.10 轻量版镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
# PYTHONDONTWRITEBYTECODE: 防止生成 .pyc 文件，减小体积
# PYTHONUNBUFFERED: 保证日志直接输出到 Docker 控制台，不缓存
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 1. 先只复制依赖文件 (利用 Docker 缓存机制加速构建)
COPY requirements.txt .

# 2. 安装依赖
# --no-cache-dir: 不缓存安装包，减小镜像体积
RUN pip install --no-cache-dir -r requirements.txt

# 3. 复制其余项目代码
COPY . .

# 4. 创建数据目录
# 我们将在运行容器时把宿主机的文件夹挂载到这里
RUN mkdir -p /app/data

# 设置应用内的环境变量默认值
# 指向 /app/data 目录，确保数据库文件持久化
ENV SQLALCHEMY_DATABASE_URI="sqlite:////app/data/database.db"
ENV SECRET_KEY=01KATX9WSFP1T9C4JK26C29AQB

# 暴露 5000 端口
EXPOSE 5000

# 启动命令 (使用 Gunicorn 生产级服务器)
# -w 2: 开启 2 个工作进程 (适合大多数轻量应用)
# -b 0.0.0.0:5000: 监听所有 IP
# --access-logfile -: 将访问日志输出到 Docker logs
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "--access-logfile", "-", "app:app"]
