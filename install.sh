#!/bin/bash

# ==========================================
# Cmd Manager 一键安装脚本 (修复版)
# ==========================================

# 1. 参数检查
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "❌ 错误: 缺少参数"
    echo "用法: ./install.sh <用户名> <密码> [服务器地址]"
    exit 1
fi

USER_ARG="$1"
PASS_ARG="$2"
URL_ARG="${3:-http://127.0.0.1:5000}"

# 下载源地址
DOWNLOAD_URL="https://raw.githubusercontent.com/assast/cmd_manager/refs/heads/main/cmd.sh"
TARGET_PATH="/usr/local/bin/cm"

# 定义 sudo
SUDO_CMD=""
if [ "$(id -u)" != "0" ] && command -v sudo &> /dev/null; then
    SUDO_CMD="sudo"
fi

# 依赖检查函数
check_and_install_dep() {
    local pkg="$1"
    if command -v "$pkg" &> /dev/null; then return 0; fi
    echo "⚠️  缺失依赖: $pkg，尝试安装..."

    if command -v apt-get &> /dev/null; then $SUDO_CMD apt-get update -y && $SUDO_CMD apt-get install -y "$pkg"
    elif command -v apk &> /dev/null; then $SUDO_CMD apk add "$pkg"
    elif command -v dnf &> /dev/null; then $SUDO_CMD dnf install -y "$pkg"
    elif command -v yum &> /dev/null; then $SUDO_CMD yum install -y "$pkg"
    elif command -v brew &> /dev/null; then brew install "$pkg"
    else echo "❌ 无法安装 '$pkg'，请手动安装。"; exit 1; fi
}

echo "🔍 检查依赖..."
check_and_install_dep "curl"
check_and_install_dep "jq"

echo "⬇️  正在下载脚本..."
TEMP_DOWNLOAD=$(mktemp)
# 使用 curl 下载，如果失败则退出
if ! curl -fsSL "$DOWNLOAD_URL" -o "$TEMP_DOWNLOAD"; then
    echo "❌ 下载失败，请检查网络。"
    rm -f "$TEMP_DOWNLOAD"
    exit 1
fi

echo "⚙️  配置用户信息..."
TEMP_CONFIG=$(mktemp)

# ========================================================
# 核心修复：增加 || [ -n "$line" ] 以防止漏掉最后一行
# ========================================================
while IFS= read -r line || [ -n "$line" ]; do
    if [[ "$line" =~ ^USERNAME= ]]; then
        echo "USERNAME=\"$USER_ARG\"" >> "$TEMP_CONFIG"
    elif [[ "$line" =~ ^PASSWORD= ]]; then
        echo "PASSWORD=\"$PASS_ARG\"" >> "$TEMP_CONFIG"
    elif [[ "$line" =~ ^SERVER_URL= ]]; then
        echo "SERVER_URL=\"$URL_ARG\"" >> "$TEMP_CONFIG"
    else
        echo "$line" >> "$TEMP_CONFIG"
    fi
done < "$TEMP_DOWNLOAD"

echo "📦 安装到 $TARGET_PATH ..."
$SUDO_CMD mv "$TEMP_CONFIG" "$TARGET_PATH"
$SUDO_CMD chmod 777 "$TARGET_PATH"
rm -f "$TEMP_DOWNLOAD"

if [ -x "$TARGET_PATH" ]; then
    echo "✅ 安装成功！输入 'cm' 即可使用。"
else
    echo "❌ 安装失败，请检查权限。"
    exit 1
fi