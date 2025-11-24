#!/bin/bash

# ================= 配置区 =================
SERVER_URL="http://127.0.0.1:5000" # 改成你自己的域名
USERNAME="${ADMIN_USER:-admin}"
# 如果使用环境变量，请保留 $ADMIN_PASSWORD，否则直接填入密码字符串
PASSWORD="${ADMIN_PASSWORD:-123456}"
# ==========================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 临时文件
COOKIE_JAR=$(mktemp)
DATA_FILE=$(mktemp)

cleanup() {
    rm -f "$COOKIE_JAR" "$DATA_FILE"
}
# 确保在脚本退出时清理临时文件
trap cleanup EXIT

# 检查依赖
if ! command -v jq &> /dev/null; then
    echo -e "${RED}错误: 未安装 'jq'。${NC}Mac请运行: brew install jq; Linux(Debian/Ubuntu)请运行: sudo apt install jq" >&2
    exit 1
fi

# ------------------------------------------
# URL 编码函数 (修复密码中 & # 等特殊字符问题)
# ------------------------------------------
url_encode() {
    local data="$1"
    # 使用 awk 来实现编码
    # 替换所有非字母数字和非 '-' '.' '_' 的字符为 %XX 格式
    echo "$data" | awk '
        BEGIN {
            ORS = ""
            # 构建编码查找表
            for (i = 0; i <= 255; i++) {
                char = sprintf("%c", i)
                # 保留字符: a-z A-Z 0-9 - . _
                if (char ~ /[a-zA-Z0-9\-\._]/) {
                    encoded[char] = char
                } else {
                    encoded[char] = sprintf("%%%02X", i)
                }
            }
        }
        {
            # 遍历输入字符串的每一个字符并输出编码
            for (i = 1; i <= length($0); i++) {
                char = substr($0, i, 1)
                printf "%s", encoded[char]
            }
            print ""
        }
    '
}

# ------------------------------------------
# 编码处理和登录数据构造
# ------------------------------------------
ENCODED_PASSWORD=$(url_encode "$PASSWORD")
LOGIN_DATA="username=$USERNAME&password=$ENCODED_PASSWORD"


# 1. 登录
echo -e "${YELLOW}>> 正在尝试登录: $SERVER_URL/login (用户: $USERNAME)${NC}" >&2
# 打印 POST 数据供调试
# echo -e "${CYAN}POST Data: $LOGIN_DATA${NC}" >&2

# 使用 --data-raw 确保发送已编码的字符串，-s 静默模式，-w 获取 HTTP 状态码
# 增加 -v 选项来输出详细的 curl 响应头到 stderr，帮助调试
HTTP_RESPONSE=$(curl -s -v -o /dev/null -w "%{http_code}" -c "$COOKIE_JAR" \
    --data-raw "$LOGIN_DATA" \
    "$SERVER_URL/login" 2>&1)
HTTP_CODE=$(echo "$HTTP_RESPONSE" | tail -n 1) # 获取最后的 HTTP 状态码

if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "302" ]; then
    echo -e "${RED}登录失败 ($HTTP_CODE)。请检查服务器状态，以及配置是否正确。${NC}" >&2
    exit 1
fi

# 2. 获取数据
echo -e "${YELLOW}>> 正在尝试获取数据: $SERVER_URL/api/list${NC}" >&2
# 使用 -b 携带登录成功的 Cookie
curl -s -b "$COOKIE_JAR" "$SERVER_URL/api/list" > "$DATA_FILE"

# 校验 JSON
if ! jq -e . "$DATA_FILE" >/dev/null 2>&1; then
    echo -e "${RED}数据获取失败,请检查用户名、密码、地址是否报错。${NC}" >&2

    # 如果获取数据失败，打印服务器返回的原始内容
    echo -e "${CYAN}--- 服务器返回原始内容 (可能为登录页或错误信息) ---${NC}" >&2
    cat "$DATA_FILE" >&2
    echo -e "${CYAN}------------------------------------------------${NC}" >&2

    exit 1
fi

# ================= 交互逻辑 (兼容 Bash 3.2+) =================

# 读取分组名称到数组 (替代 mapfile)
GRP_LIST=()
while IFS= read -r line; do
    GRP_LIST+=("$line")
done < <(jq -r '.[].group' "$DATA_FILE")

# 判空
if [ ${#GRP_LIST[@]} -eq 0 ]; then
    echo -e "${YELLOW}没有查询到分组数据。${NC}" >&2
    exit 0
fi

# === 步骤 1: 选择分组 ===
echo -e "${CYAN}=== 请选择分组 ===${NC}" >&2
i=1
for g in "${GRP_LIST[@]}"; do
    echo -e "${GREEN}$i)${NC} $g" >&2
    ((i++))
done

echo -ne "${YELLOW}输入序号: ${NC}" >&2
read -r group_idx

# 验证输入
if ! [[ "$group_idx" =~ ^[0-9]+$ ]] || [ "$group_idx" -lt 1 ] || [ "$group_idx" -gt "${#GRP_LIST[@]}" ]; then
    echo -e "${RED}无效选择${NC}" >&2
    exit 1
fi

# 获取选中的分组名
SELECTED_GROUP="${GRP_LIST[$((group_idx-1))]}"

# === 步骤 2: 选择命令 ===
echo -e "\n${CYAN}=== 分组 [${SELECTED_GROUP}] ===${NC}" >&2

# 读取命令标题到数组
TITLE_LIST=()
while IFS= read -r line; do
    TITLE_LIST+=("$line")
done < <(jq -r --arg g "$SELECTED_GROUP" '.[] | select(.group == $g) | .commands[].title' "$DATA_FILE")

j=1
for t in "${TITLE_LIST[@]}"; do
    echo -e "${GREEN}$j)${NC} $t" >&2
    ((j++))
done

echo -ne "${YELLOW}输入序号: ${NC}" >&2
read -r cmd_idx

if ! [[ "$cmd_idx" =~ ^[0-9]+$ ]] || [ "$cmd_idx" -lt 1 ] || [ "$cmd_idx" -gt "${#TITLE_LIST[@]}" ]; then
    echo -e "${RED}无效选择${NC}" >&2
    exit 1
fi

# === 步骤 3: 获取并输出 ===
CMD_CONTENT=$(jq -r --arg g "$SELECTED_GROUP" --argjson idx "$((cmd_idx-1))" \
    '.[] | select(.group == $g) | .commands[$idx].content' "$DATA_FILE")

echo -e "\n${BLUE}>>> 准备就绪:${NC}" >&2

# 剪贴板支持
COPIED=0
# 检查是否在 macOS (pbcopy)
if command -v pbcopy &> /dev/null; then
    echo -n "$CMD_CONTENT" | pbcopy
    COPIED=1
# 检查是否在 Linux/WSL (xclip)
elif command -v xclip &> /dev/null; then
    echo -n "$CMD_CONTENT" | xclip -selection clipboard
    COPIED=1
# 检查是否在 Windows Git Bash/WSL (clip.exe)
elif command -v clip.exe &> /dev/null; then
    echo -n "$CMD_CONTENT" | clip.exe
    COPIED=1
fi

if [ $COPIED -eq 1 ]; then
    echo -e "${GREEN}✔ 已复制到剪贴板${NC}" >&2
fi

# 最终输出命令 (Stdout)
echo "$CMD_CONTENT"