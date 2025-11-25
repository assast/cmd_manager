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
trap cleanup EXIT

# 检查依赖
if ! command -v jq &> /dev/null; then
    echo -e "${RED}错误: 未安装 'jq'。${NC}Mac请运行: brew install jq; Linux(Debian/Ubuntu)请运行: sudo apt install jq" >&2
    exit 1
fi

# ------------------------------------------
# 1. 登录
# ------------------------------------------
echo -e "${YELLOW}>> 正在尝试登录: $SERVER_URL/login (用户: $USERNAME)${NC}" >&2

HTTP_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -c "$COOKIE_JAR" \
    --data-urlencode "username=$USERNAME" \
    --data-urlencode "password=$PASSWORD" \
    "$SERVER_URL/login")

if [ "$HTTP_RESPONSE" != "200" ] && [ "$HTTP_RESPONSE" != "302" ]; then
    echo -e "${RED}登录失败 ($HTTP_RESPONSE)。请检查密码或服务器状态。${NC}" >&2
    exit 1
fi

# ------------------------------------------
# 2. 获取数据
# ------------------------------------------
echo -e "${YELLOW}>> 正在尝试获取数据...${NC}" >&2

curl -s -L -b "$COOKIE_JAR" "$SERVER_URL/api/list" > "$DATA_FILE"

# 校验 JSON
if ! jq -e . "$DATA_FILE" >/dev/null 2>&1; then
    echo -e "${RED}数据获取失败。可能是登录后 Session 失效或密码依然不正确。${NC}" >&2
    echo -e "${CYAN}--- 服务器返回内容 ---${NC}" >&2
    cat "$DATA_FILE" >&2
    exit 1
fi

# ================= 交互逻辑 =================

GRP_LIST=()
while IFS= read -r line; do
    GRP_LIST+=("$line")
done < <(jq -r '.[].group' "$DATA_FILE")

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

if ! [[ "$group_idx" =~ ^[0-9]+$ ]] || [ "$group_idx" -lt 1 ] || [ "$group_idx" -gt "${#GRP_LIST[@]}" ]; then
    echo -e "${RED}无效选择${NC}" >&2
    exit 1
fi

SELECTED_GROUP="${GRP_LIST[$((group_idx-1))]}"

# === 步骤 2: 选择命令 ===
echo -e "\n${CYAN}=== 分组 [${SELECTED_GROUP}] ===${NC}" >&2

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
if command -v pbcopy &> /dev/null; then
    echo -n "$CMD_CONTENT" | pbcopy
    COPIED=1
elif command -v xclip &> /dev/null; then
    echo -n "$CMD_CONTENT" | xclip -selection clipboard
    COPIED=1
elif command -v clip.exe &> /dev/null; then
    echo -n "$CMD_CONTENT" | clip.exe
    COPIED=1
fi

if [ $COPIED -eq 1 ]; then
    echo -e "${GREEN}✔ 已复制到剪贴板${NC}" >&2
else
    if [ -t 1 ]; then
        echo -e "${YELLOW}ℹ 无法访问剪贴板，请手动复制：${NC}" >&2
    fi
fi

# --- 新增功能：在控制台醒目输出命令内容 ---
echo -e "${CYAN}------------------------------------------------${NC}" >&2
echo -e "${NC}$CMD_CONTENT${NC}" >&2
echo -e "${CYAN}------------------------------------------------${NC}" >&2

# 最终输出命令 (Stdout)，这行保留用于 eval 功能
echo "$CMD_CONTENT"