# 使用官方 Python 3.10 轻量版镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
# PYTHONDONTWRITEBYTECODE: 防止生成 .pyc 文件，减小体积
# PYTHONUNBUFFERED: 保证日志直接输出到 Docker 控制台，不缓存
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# 设置时区
ENV TZ=Asia/Shanghai

# --- 新增部分开始: 安装系统依赖和 Cloudflared ---

# 1. 安装下载工具 curl 和证书 ca-certificates (Debian系必须)
# 2. 清理 apt 缓存以减小镜像体积
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 3. 下载并安装 cloudflared
# 注意: 这里使用的是 amd64 架构，如果你是在 ARM (如 M1/M2 Mac 或 树莓派) 上构建，
# 请将链接中的 'amd64' 替换为 'arm64'
RUN curl -L --output cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 && \
    mv cloudflared /usr/local/bin/cloudflared && \
    chmod +x /usr/local/bin/cloudflared && \
    cloudflared --version

# --- 新增部分结束 ---

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

# 1. 复制启动脚本到工作目录
COPY entrypoint.sh .

# 2. 赋予脚本执行权限
RUN chmod +x entrypoint.sh

# 3. 将 CMD 修改为执行这个脚本
CMD ["./entrypoint.sh"]