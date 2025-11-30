#!/bin/bash

# ==========================================
# Cmd Manager 一键安装脚本
# 功能: 自动检测安装依赖 (jq, curl) 并部署 cm 命令
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

# 下载源地址
DOWNLOAD_URL="https://raw.githubusercontent.com/assast/cmd_manager/refs/heads/main/cmd.sh"
# 安装目标路径
TARGET_PATH="/usr/local/bin/cm"

# 定义 sudo 前缀 (如果非 root 用户)
SUDO_CMD=""
if [ "$(id -u)" != "0" ]; then
    if command -v sudo &> /dev/null; then
        SUDO_CMD="sudo"
    else
        echo "⚠️  当前非 root 用户且未检测到 sudo，安装可能会失败。"
    fi
fi

# ==========================================
# 函数: 检查并自动安装依赖
# ==========================================
check_and_install_dep() {
    local pkg="$1"

    # 检查命令是否存在
    if command -v "$pkg" &> /dev/null; then
        return 0
    fi

    echo "⚠️  检测到缺失依赖: $pkg，正在尝试自动安装..."

    if command -v apt-get &> /dev/null; then
        # Debian / Ubuntu
        $SUDO_CMD apt-get update -y > /dev/null 2>&1
        $SUDO_CMD apt-get install -y "$pkg"
    elif command -v apk &> /dev/null; then
        # Alpine Linux
        $SUDO_CMD apk add "$pkg"
    elif command -v dnf &> /dev/null; then
        # Fedora / RHEL 8+
        $SUDO_CMD dnf install -y "$pkg"
    elif command -v yum &> /dev/null; then
        # CentOS / RHEL 7
        $SUDO_CMD yum install -y "$pkg"
    elif command -v pacman &> /dev/null; then
        # Arch Linux
        $SUDO_CMD pacman -S --noconfirm "$pkg"
    elif command -v brew &> /dev/null; then
        # macOS
        brew install "$pkg"
    else
        echo "❌ 无法自动安装 '$pkg'，请手动安装后重试。"
        exit 1
    fi

    # 再次检查是否安装成功
    if ! command -v "$pkg" &> /dev/null; then
        echo "❌ '$pkg' 安装失败，请检查网络或源配置。"
        exit 1
    fi
    echo "✅ '$pkg' 安装成功。"
}

# ==========================================
# 主逻辑
# ==========================================

# 2. 检查必要的依赖 (curl 和 jq)
echo "🔍 正在检查系统依赖..."
check_and_install_dep "curl"
check_and_install_dep "jq"

echo "⬇️  正在从 $DOWNLOAD_URL 下载脚本..."

# 3. 下载脚本到临时位置 (避免权限问题)
TEMP_DOWNLOAD=$(mktemp)
if ! curl -sL "$DOWNLOAD_URL" -o "$TEMP_DOWNLOAD"; then
    echo "❌ 下载失败，请检查网络或 URL 地址。"
    rm -f "$TEMP_DOWNLOAD"
    exit 1
fi

echo "⚙️  正在配置用户信息..."

# 4. 使用 sed 修改文件内容 (注入账号密码)
TEMP_CONFIG=$(mktemp)

# 逐行读取并替换配置项
while IFS= read -r line; do
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

# 5. 安装到系统路径
# 因为目标是 /usr/local/bin，非 root 用户需要 sudo
echo "📦 正在安装到 $TARGET_PATH ..."

$SUDO_CMD mv "$TEMP_CONFIG" "$TARGET_PATH"
$SUDO_CMD chmod +x "$TARGET_PATH"

# 清理临时下载文件
rm -f "$TEMP_DOWNLOAD"

# 验证安装
if [ -x "$TARGET_PATH" ]; then
    echo "✅ 安装成功！"
    echo "------------------------------------------------"
    echo "依赖检测: curl (OK), jq (OK)"
    echo "调用命令: cm"
    echo "服务器地址: $URL_ARG"
    echo "登录用户:   $USER_ARG"
    echo "------------------------------------------------"
else
    echo "❌ 安装失败：无法移动文件到 $TARGET_PATH，请检查权限。"
    exit 1
fi