这份 README 经过了全面的润色和完善。

**主要的优化点如下：**

1.  **结构优化**：将“演示体验”置顶，方便用户第一时间尝试。
2.  **特性补充**：补充了我们刚刚开发的“直接执行”、“自动依赖安装”和“简洁模式”等新特性说明。
3.  **排版美化**：优化了排版细节，增加了提示块，使文档更具可读性和专业感。
4.  **维护指南**：增加了“更新容器”的说明（对应自动数据库迁移功能）。

你可以直接复制以下内容到 `README.md`。

-----

# 🚀 Cmd Manager - 极简命令管理系统

> **不仅是命令备忘录，更是你的终端效率神器。**

Cmd Manager 是一个轻量级、私有化的命令管理工具。你可以在现代化的 Web 界面上录入、分组、排序你的常用 Shell 命令，然后通过一行代码在任何服务器（小鸡）上唤出交互式菜单，实现命令的一键复制或**直接执行**。

  

-----

## 🎮 立即体验 (Demo)

想先试试效果？无需部署，直接在你的终端运行以下命令即可体验客户端交互：

```bash
curl -fsSL https://raw.githubusercontent.com/assast/cmd_manager/refs/heads/main/install.sh -o cm_install.sh && chmod +x cm_install.sh && ./cm_install.sh admin 123456 https://cmdmgr.lac.netlib.re
```

*(注：上述命令连接的是演示站点，仅供体验交互逻辑)*

**Web 端演示：**

  * **地址**：`https://cmdmgr.lac.netlib.re`
  * **账号**：`admin` / `123456`
  * *(演示站点数据公开，请勿修改密码或存入敏感信息)*

-----

## ✨ 核心特性

  * **💻 现代化 Web 管理**
      * 支持命令的**增删改查**与**分组管理**。
      * **双视图模式**：支持“完整版”与“简洁版”切换，单行/多行命令智能展示。
      * **智能排序**：支持通过数字权重自定义分组和命令的排序（权重越小越靠前）。
  * **⚡️ 终端直连 (Cm Client)**
      * **交互式菜单**：输入 `cm` 唤出菜单，支持键盘操作，体验丝滑。
      * **自动依赖处理**：安装脚本自动检测并安装 `jq`、`curl` 等依赖。
      * **直接执行**：配置为“直接执行”的命令，在终端选择后无需复制，确认即可运行（支持 `eval`）。
  * **📋 智能剪贴板**
      * 自动检测系统环境（MacOS/Linux/Windows WSL），将命令写入剪贴板。
      * 若无剪贴板权限（如纯 SSH 环境），会自动将命令高亮输出到控制台方便复制。
  * **🔒 安全与持久化**
      * 基于 Docker 部署，数据本地持久化。
      * 账号密码哈希加密存储。

-----

## 🛠 第一步：服务端部署 (Docker)

你需要在一台服务器（或本地电脑）上通过 Docker 运行管理后台。

### 1\. 快速启动 (推荐)

```bash
# 1. 创建数据目录（防止删除容器后数据丢失）
mkdir -p cmd_data

# 2. 启动容器
docker run -d \
  --name my-cmd \
  --restart always \
  -p 5000:5000 \
  -v $(pwd)/cmd_data:/app/data \
  ghcr.io/assast/cmd_manager:latest
```

> **🔔 默认账号**
>
>   * 访问：`http://IP:5000`
>   * 账号：`admin`
>   * 密码：`123456`
>   * **安全提示：首次登录后，请务必在右上角修改密码！**

### 2\. 高级启动 (自定义配置)

适合生产环境，自定义密码和密钥。

```bash
docker run -d \
  --name my-cmd \
  --restart always \
  -p 5000:5000 \
  -v $(pwd)/cmd_data:/app/data \
  -e ADMIN_USER="admin" \
  -e ADMIN_PASSWORD="你的强密码" \
  -e SECRET_KEY="随机生成的复杂字符串" \
  ghcr.io/assast/cmd_manager:latest
```

**环境变量说明：**

  * `ADMIN_USER` / `ADMIN_PASSWORD`: 初始化管理员账号（仅在首次运行时生效）。
  * `SECRET_KEY`: Flask Session 加密密钥，建议修改以提高安全性。

-----

## 💻 第二步：客户端安装 (一键脚本)

在任何需要使用命令的服务器（小鸡）上执行此脚本。脚本会自动检测系统依赖（如 `jq`）并完成安装。

### 1\. Root 用户安装

请替换 `<用户名>`、`<密码>` 和 `<面板地址>`：

```bash
# 语法：./install.sh <User> <Pass> <Url>
curl -fsSL https://raw.githubusercontent.com/assast/cmd_manager/refs/heads/main/install.sh -o cm_install.sh && chmod +x cm_install.sh && \
./cm_install.sh admin 123456 http://1.2.3.4:5000
```

### 2\. 非 Root 用户安装 (sudo)

脚本会自动识别非 root 用户并尝试使用 sudo 提权安装到 `/usr/local/bin`。

```bash
curl -fsSL https://raw.githubusercontent.com/assast/cmd_manager/refs/heads/main/install.sh -o cm_install.sh && sudo chmod +x cm_install.sh && \
sudo ./cm_install.sh admin 123456 http://1.2.3.4:5000
```

> **⚠️ 特殊字符提示**
> 如果密码包含 `&`、`=`、`$` 等特殊字符，**必须用双引号**包裹密码，例如 `"P@ssw&rd"`。

-----

## 🚀 使用指南

### 1\. Web 端管理

  * **排序**：在新增或编辑时，填写“排序权重”。数字 **0** 排最前，数字越大越靠后。
  * **直接执行**：编辑命令时，勾选 **“在脚本中直接执行”**。
      * 未勾选：终端选中后仅复制/输出命令。
      * 已勾选：终端选中后会直接运行该命令（适合 `df -h`, `docker ps` 等查看类命令）。

### 2\. 终端调用

在安装了脚本的机器上输入：

```bash
cm
```

  * **选择**：输入数字选择分组或命令。
  * **返回**：输入 `0` 返回上一级或退出。
  * **执行**：带有 `⚡` 图标的命令会被直接执行。

### 3\. 界面预览

**Web 管理界面 (支持简洁/完整模式切换)：**

**终端交互菜单：**

-----

## 🔄 更新指南

本项目支持**数据库自动迁移**。当拉取新镜像更新时，程序会自动检测并升级数据库结构（如新增 `is_execute` 字段），无需担心数据丢失。

```bash
# 1. 拉取最新镜像
docker pull ghcr.io/assast/cmd_manager:latest

# 2. 删除旧容器（数据在挂载卷里，不会丢）
docker stop my-cmd && docker rm my-cmd

# 3. 重新运行（使用相同的启动命令）
docker run -d ... (参考上文启动命令)
```

-----

## ❓ 常见问题 (FAQ)

**Q: 部署后无法访问 Web 界面？**
A: 请检查服务器防火墙（安全组）是否放行了 `5000` 端口。

**Q: 终端显示“已复制”，但粘贴板为空？**
A: 这是因为 SSH 工具（如 Putty, Xshell）的剪贴板权限限制。脚本会自动将命令**高亮输出到控制台**，方便手动复制。

**Q: 脚本报错 `jq: command not found`？**
A: 最新的安装脚本会自动尝试安装 `jq`。如果自动安装失败，请手动执行 `apt install jq` 或 `yum install jq`。

**Q: 如何修改 Web 面板端口？**
A: 修改 Docker 命令的 `-p` 参数，例如 `-p 8080:5000` 即可通过 8080 端口访问。