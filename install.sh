#!/bin/bash

# ==========================================
# Cmd Manager 一键安装脚本
# 用法: ./install.sh <用户名> <密码> [服务器地址]
# ==========================================

# 1. 参数检查
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "❌ 错误: 缺少参数"
    echo "用法: bash install.sh <用户名> <密码> [服务器地址]"
    echo "示例: bash install.sh admin 123456 http://192.168.1.100:5000"
    exit 1
fi

USER_ARG="$1"
PASS_ARG="$2"
# 如果没有提供第3个参数，默认使用 localhost
URL_ARG="${3:-http://127.0.0.1:5000}"

# 下载源地址 (请修改为你存放 cmd.sh 的真实地址)
DOWNLOAD_URL="https://raw.githubusercontent.com/assast/cmd_manager/refs/heads/main/cmd.sh"

# 安装目标路径 (在 PATH 里的路径，方便直接敲 cm 运行)
TARGET_PATH="/usr/local/bin/cm"

echo "⬇️  正在从 $DOWNLOAD_URL 下载脚本..."

# 2. 下载脚本到目标位置
# 使用 curl -L 跟随重定向，-o 指定输出文件
if ! curl -sL "$DOWNLOAD_URL" -o "$TARGET_PATH"; then
    echo "❌ 下载失败，请检查网络或 URL 地址。"
    exit 1
fi

echo "⚙️  正在配置用户信息..."

# 3. 使用 sed 修改文件内容 (注入账号密码)
# 注意：为了兼容 macOS 和 Linux 的 sed 差异，我们采用 "生成临时文件 -> 覆盖" 的策略
TEMP_FILE=$(mktemp)

# 逐行读取并替换配置项
while IFS= read -r line; do
    if [[ "$line" =~ ^USERNAME= ]]; then
        echo "USERNAME=\"$USER_ARG\"" >> "$TEMP_FILE"
    elif [[ "$line" =~ ^PASSWORD= ]]; then
        # 兼容脚本里可能存在的 ADMIN_PASSWORD 写法
        echo "PASSWORD=\"$PASS_ARG\"" >> "$TEMP_FILE"
    elif [[ "$line" =~ ^SERVER_URL= ]]; then
        echo "SERVER_URL=\"$URL_ARG\"" >> "$TEMP_FILE"
    else
        echo "$line" >> "$TEMP_FILE"
    fi
done < "$TARGET_PATH"

# 覆盖原文件
mv "$TEMP_FILE" "$TARGET_PATH"

# 4. 赋予执行权限
chmod +x "$TARGET_PATH"

echo "✅ 安装成功！"
echo "------------------------------------------------"
echo "现在你可以在终端任何位置输入 'cm' 来调用命令了。"
echo "服务器地址: $URL_ARG"
echo "登录用户:   $USER_ARG"
echo "------------------------------------------------"