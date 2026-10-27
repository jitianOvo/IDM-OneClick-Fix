# IDM One-Click Fix

一键把 Internet Download Manager 变成完整版，并关掉自动更新与反复弹窗。

## 适用环境

- Windows 10 / 11
- 已安装 IDM 6.43（Build 15 已验证）
- 需要管理员权限

## 使用

1. 下载 `IDMFix.exe`
2. 右键 → 以管理员身份运行（或直接双击，程序会自己提权）
3. 等待出现 `[+] install complete`
4. 完成后 IDM 会自动启动

再次运行是安全的，会跳过已完成的步骤。

## 效果

- 版本显示为 Full，不再出现试用提示
- 注册 / 购买弹窗不再出现
- `IDM is corrupt` 弹窗不再出现
- 该提示后的修复网页不会自动打开，也不会重新安排一小时提醒
- 下载时的“主程序文件已损坏 / 继续下载”倒计时提示不再出现
- 修复旧补丁引起的冷启动后右键图片“使用 IDM 下载”无响应
- 自动更新被关闭，不会再收到更新提醒

## 命令行（可选）

```powershell
IDMFix.exe            # 安装
IDMFix.exe status     # 查看当前状态
IDMFix.exe --help
```

## 更新记录

### v1.1.2

- 修复右键图片下载无响应的根因：旧补丁把比较和跳转改成 NOP，却保留了操作数的 PE 重定位；Windows 冷加载时会把这些 NOP 改成错误指令
- 保留原比较、跳转及重定位，只处理专用下载提示调用，继续沿用正常下载窗口与下载流程
- 支持修复旧版本已写入的 9 字节 NOP，以及只完成部分提示修复的文件
- 增加四个加载地址的 ASLR 回归、重定位校验和未知版本拒绝测试
- 本机完成 IDM 完全退出后重新启动、无诊断工具的窗口测试，并由实际浏览器右键图片下载验收通过

### v1.1.1
- 同步实际定位并验证的专用提示线程修复，取消消息框及其后续打开修复页、重新设置一小时提醒的完整路径
- 修复“提示消失，但仍无故打开 `download2.html?lng=chn2`”的问题
- 修改前核对 PE 布局、显示调用和清理分支，发现不匹配时拒绝生成安装文件
- 重新计算 PE CheckSum，支持重复应用和仅取消了提示显示的中间状态
- 增加合成 PE 回归测试，不在仓库包含 IDM 程序、注册表或个人下载记录

### v1.1.0
- 修复 `IDM is corrupt` 反复弹出的问题
- 之前版本会误改损坏标志的写入点，导致该标志保持旧值并持续弹窗

## 出问题怎么办

程序会在同目录生成 `C:\IDM-Fix` 工作目录，其中保留原始文件备份：

- `IDMan.exe.bak-original`：原始文件
- 把它复制回 `C:\Program Files (x86)\Internet Download Manager\IDMan.exe` 即可恢复原状

如果写入失败，重启电脑后再运行一次。

## 支持的版本

IDM 6.43 Build 15（`IDMan.exe` 版本号 6.43.15.2）。其他版本会明确提示 `signature mismatch` 并拒绝修改，不会写坏文件。

## 源码验证

Windows Python 3.11 环境：

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python run.py status
```

仅运行测试和 `status` 不会修改已安装的 IDM。`install` 会执行原有完整安装流程。

提示及修复网页的后续路径已单独验证；浏览器自动接管下载通过文件校验，右键图片下载已实际成功。最新验收包含 IDM 完全退出后重新启动；未把进程重启描述为 Windows 整机重启。重新安装或升级主程序后需要重新核对版本。

## 许可

MIT
