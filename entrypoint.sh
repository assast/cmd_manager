#!/bin/bash

# 检查环境变量 CF_TOKEN 是否存在且长度不为 0
if [ -n "$CF_TOKEN" ]; then
    echo "🚀 检测到 CF_TOKEN，正在启动 Cloudflared Tunnel..."
    # 在后台运行 cloudflared，这样不会阻塞后续命令
    cloudflared tunnel run --token "$CF_TOKEN" &
else
    echo "⚠️  未检测到 CF_TOKEN 或值为空，跳过 Cloudflared 启动。"
fi

# 启动 Gunicorn
# 使用 exec 可以让 gunicorn 替换当前 shell 进程，接收系统信号（如关闭容器时的信号）
# 启动命令 (使用 Gunicorn 生产级服务器)
# -w 2: 开启 2 个工作进程 (适合大多数轻量应用)
# -b 0.0.0.0:5000: 监听所有 IP
# --access-logfile -: 将访问日志输出到 Docker logs
echo "🔥 正在启动 Gunicorn 服务..."
exec gunicorn -w 2 -b 0.0.0.0:5000 --access-logfile - app:app


