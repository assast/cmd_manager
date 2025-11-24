# 使用官方轻量 Python 镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 复制依赖并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制所有项目文件
COPY . .

# 创建数据存放目录
RUN mkdir -p /app/data

# 设置环境变量
# 数据库文件将存放在 /app/data 目录下，方便挂载
ENV SQLALCHEMY_DATABASE_URI="sqlite:////app/data/database.db"
ENV SECRET_KEY="change_this_in_production"

# 暴露端口
EXPOSE 5000

# 启动命令 (使用 gunicorn 生产级服务器)
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]