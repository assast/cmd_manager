#!/bin/bash

# ================= 配置区 =================
SERVER_URL="http://127.0.0.1:5000" # 请修改为你的地址
USERNAME="${ADMIN_USER:-admin}"
PASSWORD="${ADMIN_PASSWORD:-123456}"
# ==========================================

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

COOKIE_JAR=$(mktemp)
DATA_FILE=$(mktemp)

cleanup() { rm -f "$COOKIE_JAR" "$DATA_FILE"; }
trap cleanup EXIT

# 检查依赖
if ! command -v jq &> /dev/null; then
    echo -e "${RED}错误: 未安装 'jq'。${NC}"
    exit 1
fi

# 1. 登录
# echo -e "${YELLOW}>> 登录中...${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -c "$COOKIE_JAR" \
    --data-urlencode "username=$USERNAME" \
    --data-urlencode "password=$PASSWORD" \
    "$SERVER_URL/login")

if [ "$HTTP_CODE" != "200" ] && [ "$HTTP_CODE" != "302" ]; then
    echo -e "${RED}登录失败 ($HTTP_CODE)。${NC}"
    exit 1
fi

# 2. 获取数据函数
fetch_data() {
    curl -s -L -b "$COOKIE_JAR" "$SERVER_URL/api/list" > "$DATA_FILE"
    if ! jq -e . "$DATA_FILE" >/dev/null 2>&1; then
        echo -e "${RED}获取数据失败。${NC}"
        exit 1
    fi
}

# 初次获取数据
fetch_data

# ================= 交互主循环 =================
while true; do
    clear
    echo -e "${CYAN}=== CMD Manager ===${NC}"

    # 获取分组列表
    GRP_LIST=()
    while IFS= read -r line; do GRP_LIST+=("$line"); done < <(jq -r '.[].group' "$DATA_FILE")

    if [ ${#GRP_LIST[@]} -eq 0 ]; then
        echo -e "${YELLOW}暂无数据。${NC}"
        exit 0
    fi

    # 显示分组
    i=1
    for g in "${GRP_LIST[@]}"; do
        echo -e "${GREEN}$i)${NC} $g"
        ((i++))
    done
    echo -e "${RED}0)${NC} 退出"

    echo -ne "\n${YELLOW}选择分组 [0-${#GRP_LIST[@]}]: ${NC}"
    read -r group_idx

    if [ "$group_idx" == "0" ]; then
        echo "Bye!"
        exit 0
    fi

    if ! [[ "$group_idx" =~ ^[0-9]+$ ]] || [ "$group_idx" -lt 1 ] || [ "$group_idx" -gt "${#GRP_LIST[@]}" ]; then
        echo -e "${RED}无效选择，回车重试...${NC}"
        read
        continue
    fi

    SELECTED_GROUP="${GRP_LIST[$((group_idx-1))]}"

    # === 子菜单：命令循环 ===
    while true; do
        clear
        echo -e "${CYAN}=== [${SELECTED_GROUP}] ===${NC}"

        # 获取该分组下的命令
        # 格式: "Title Name|true"
        CMD_LIST=()
        while IFS= read -r line; do CMD_LIST+=("$line"); done < <(jq -r --arg g "$SELECTED_GROUP" '.[] | select(.group == $g) | .commands[] | "\(.title)|\(.is_execute)"' "$DATA_FILE")

        j=1
        for item in "${CMD_LIST[@]}"; do
            title="${item%|*}"
            is_exec="${item#*|}"

            icon=""
            # 如果是直接执行，显示闪电图标提醒
            if [ "$is_exec" == "true" ]; then icon="${YELLOW}⚡${NC}"; fi

            echo -e "${GREEN}$j)${NC} $title $icon"
            ((j++))
        done
        echo -e "${BLUE}0)${NC} 返回上一级"

        echo -ne "\n${YELLOW}选择命令 [0-${#CMD_LIST[@]}]: ${NC}"
        read -r cmd_idx

        if [ "$cmd_idx" == "0" ]; then
            break # 跳出子循环，回到分组选择
        fi

        if ! [[ "$cmd_idx" =~ ^[0-9]+$ ]] || [ "$cmd_idx" -lt 1 ] || [ "$cmd_idx" -gt "${#CMD_LIST[@]}" ]; then
            echo -e "${RED}无效选择，回车重试...${NC}"
            read
            continue
        fi

        # 获取命令内容和执行状态
        RAW_JSON=$(jq -r --arg g "$SELECTED_GROUP" --argjson idx "$((cmd_idx-1))" \
            '.[] | select(.group == $g) | .commands[$idx]' "$DATA_FILE")

        CMD_CONTENT=$(echo "$RAW_JSON" | jq -r '.content')
        IS_EXEC=$(echo "$RAW_JSON" | jq -r '.is_execute')

        echo -e "\n${CYAN}------------------------------------------------${NC}"
        echo -e "${NC}$CMD_CONTENT${NC}"
        echo -e "${CYAN}------------------------------------------------${NC}"

        # === 核心修改逻辑 ===
        if [ "$IS_EXEC" == "true" ]; then
            # 直接执行，无需确认
            echo -e "${YELLOW}>>> ⚡ 正在直接执行...${NC}\n"
            eval "$CMD_CONTENT"
            echo -e "\n${GREEN}>>> 执行完毕。${NC}"
        else
            # 复制逻辑
            COPIED=0
            if command -v pbcopy &> /dev/null; then echo -n "$CMD_CONTENT" | pbcopy; COPIED=1;
            elif command -v xclip &> /dev/null; then echo -n "$CMD_CONTENT" | xclip -selection clipboard; COPIED=1;
            elif command -v clip.exe &> /dev/null; then echo -n "$CMD_CONTENT" | clip.exe; COPIED=1;
            fi

            if [ $COPIED -eq 1 ]; then
                echo -e "${GREEN}✔ 已复制到剪贴板${NC}"
            else
                echo -e "${YELLOW}ℹ 未检测到剪贴板，请手动复制上方命令。${NC}"
            fi
        fi

        echo -e "\n${BLUE}按回车键继续...${NC}"
        read
    done
done