
-----

# 🚀 Cmd Manager - 极简命令管理系统

> **不仅是命令备忘录，更是你的终端效率神器。**

Cmd Manager 是一个轻量级的命令管理工具。你可以在漂亮的 Web 界面上录入、分组管理你的常用 Shell 命令，然后通过一行代码在任何服务器（小鸡）上唤出菜单，一键执行或复制命令。

## 体验站点
https://cmdmgr.lac.netlib.re
用户名：admin
密码：123456
```commandline
curl -fsSL https://raw.githubusercontent.com/assast/cmd_manager/refs/heads/main/install.sh -o cm_install.sh && chmod +x cm_install.sh && ./cm_install.sh admin 123456 https://cmdmgr.lac.netlib.re
```

## ✨ 功能亮点

  * **💻 Web 管理**：简洁的网页端，支持增删改查、分组管理。
  * **⚡️ 终端直连**：在 VPS 终端输入 `cm` 即可唤出命令菜单，选择即用。
  * **📋 自动复制**：支持将命令输出到控制台；如果有权限，还能自动写入剪贴板。
  * **📂 智能排序**：分组和命令支持按照权重排序
  * **🔒 数据安全**：支持 Docker 部署，数据本地持久化，账号密码加密存储。

-----

## 🛠 第一步：服务端部署 (Web 界面)

你需要在一台服务器（或本地电脑）上通过 Docker 运行管理后台。

### 1\. 快速启动 (小白推荐)

复制以下命令并在终端执行即可。

```bash
# 1. 创建一个文件夹用来保存数据（防止删容器后数据丢失）
mkdir -p cmd_data

# 2. 启动容器
docker run -d \
  --name my-cmd \
  --restart always \
  -p 5000:5000 \
  -v $(pwd)/cmd_data:/app/data \
  ghcr.io/assast/cmd_manager:latest
```

> **🔔 默认账号信息**
>
>   * 访问地址：`http://你的服务器IP:5000`
>   * 用户名：`admin`
>   * 密码：`123456`
>   * **注意：首次登录后，请务必在右上角修改密码！**

### 2\. 高级启动 (自定义配置)

如果你想在启动时直接设置好密码和密钥，可以使用以下命令：

```bash
docker run -d \
  --name my-cmd \
  --restart always \
  -p 5000:5000 \
  -v $(pwd)/cmd_data:/app/data \
  -e ADMIN_USER="admin" \
  -e ADMIN_PASSWORD="你的强密码" \
  -e SECRET_KEY="自己随便写一串乱码作为密钥" \
  ghcr.io/assast/cmd_manager:latest
```

**参数解释：**

  * `-v ...:/app/data`: **最重要的一步！** 将数据映射到宿主机，确保数据不丢失。
  * `-e ADMIN_PASSWORD`: 设置初始管理员密码。
  * `-e SECRET_KEY`: 用于加密 Session 的密钥，建议修改以提高安全性。

-----

## 💻 第二步：客户端安装 (小鸡一键脚本)

在任何你想要执行命令的服务器（小鸡）上安装这个脚本。安装后，只需输入 `cm` 即可使用。

### 1\. Root 用户安装 (推荐)

请将下方的 `用户名` `密码` `服务器地址` 替换为你自己的真实信息。

```bash
# 格式参考：
# ./cm_install.sh <用户名> <密码> <管理面板地址>

curl -fsSL https://raw.githubusercontent.com/assast/cmd_manager/refs/heads/main/install.sh -o cm_install.sh && chmod +x cm_install.sh && ./cm_install.sh admin 123456 http://1.2.3.4:5000
```

### 2\. 非 Root 用户安装 (sudo)

如果当前不是 root 用户，请加上 `sudo`：

```bash
curl -fsSL https://raw.githubusercontent.com/assast/cmd_manager/refs/heads/main/install.sh -o cm_install.sh && sudo chmod +x cm_install.sh && sudo ./cm_install.sh admin 123456 http://1.2.3.4:5000
```

*(安装后，使用 `sudo cm` 唤出面板)*

### ⚠️ 特殊字符注意事项

如果你的密码中包含特殊字符（如 `&`、`=`、`$`、`?` 等），**必须使用英文双引号包裹密码**，否则会报错！

**错误示例 ❌**：`... admin 123&456 ...`
**正确示例 ✅**：`... admin "123&456" ...`

-----

## 🚀 使用指南
### 1\. 唤出菜单

在安装了脚本的机器上，输入：

```bash
cm
```

即可看到交互式菜单，选择数字回车即可。

### 2\. 界面预览

**Web 管理界面：**
![](./static/WX20251125-090321@2x.png)

**终端交互菜单：**
![](./static/WX20251125-090411@2x.png)

-----

## ❓ 常见问题 (FAQ)

**Q: 部署后无法访问 Web 界面？**
A: 请检查服务器的防火墙（安全组）是否开放了 `5000` 端口。

**Q: 终端里显示“复制成功”，但我粘贴不出来？**
A: 这是因为 SSH 工具的剪贴板权限限制。脚本会自动将命令**输出显示在控制台**上，你可以手动选中复制，或者使用支持剪贴板透传的终端工具。

**Q: 我想修改 Web 面板的端口？**
A: 修改 Docker 命令中的 `-p` 参数，例如 `-p 8080:5000`，即可通过 8080 端口访问。