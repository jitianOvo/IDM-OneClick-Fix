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
- 自动更新被关闭，不会再收到更新提醒

## 命令行（可选）

```
IDMFix.exe            # 安装
IDMFix.exe status     # 查看当前状态
IDMFix.exe --help
```

## 出问题怎么办

程序会在同目录生成 `C:\IDM-Fix` 工作目录，其中保留原始文件备份：

- `IDMan.exe.bak-original`：原始文件
- 把它复制回 `C:\Program Files (x86)\Internet Download Manager\IDMan.exe` 即可恢复原状

如果写入失败，重启电脑后再运行一次。

## 支持的版本

IDM 6.43 Build 15（`IDMan.exe` 版本号 6.43.15.2）。其他版本会明确提示 `signature mismatch` 并拒绝修改，不会写坏文件。

## 许可

MIT