# edge-customize

Microsoft Edge 去臃肿配置，基于官方 Managed Policy 机制，覆盖 Windows / Linux / macOS。

不是改设置项，是写企业策略：入口直接从 UI 消失，后台服务直接不启动，改完是持久的、跟着文件走的、可版本回滚的。

## 文件

| 平台 | 文件 | 落点 |
|---|---|---|
| Windows | `windows/edge-debloat.reg` | `HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Edge` |
| Linux | `linux/managed.json` | `/etc/opt/edge/policies/managed/debloat.json` |
| macOS | `macos/com.microsoft.Edge.plist` | `com.microsoft.Edge` 偏好域 |

三个平台同一份策略集合：`linux/managed.json` 是唯一手改的源，macOS plist 直接由它生成，
Windows .reg 由它加上 `windows/extra.json`（22 条 Windows 专属策略）生成。
改完策略跑一次 `python3 tools/build.py` 重新生成，不要手改 .reg 和 .plist。

## 安装

### Windows

```powershell
# 双击 edge-debloat.reg → 是 → 重启 Edge
# 或者命令行:
reg import edge-debloat.reg
```

导入后打开 `edge://policy`，点右上角「重新加载政策」。

撤销：删除注册表键 `HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Edge` 与
`HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\EdgeUpdate`，重启 Edge。

> 公司域管 / Intune 环境里组策略会覆盖这里的 HKLM 值，`edge://policy` 的 source 会显示
> `Platform` 而不是 `Registry`，那就不会生效。

### Linux

```bash
sudo install -Dm644 linux/managed.json /etc/opt/edge/policies/managed/debloat.json
```

重启 Edge 后打开 `edge://policy`，点「重新加载政策」。

路径 `/etc/opt/edge/policies/managed/` 是 Linux 版 Edge 编译进去的固定位置，不用改。
文件必须是 `644`，目录 `755`。

撤销：`sudo rm /etc/opt/edge/policies/managed/debloat.json`，重启 Edge。

### macOS

用户级（推荐，不需要 root）：

```bash
defaults import com.microsoft.Edge macos/com.microsoft.Edge.plist
killall cfprefsd          # 让系统重新读偏好缓存
```

系统级（对所有用户生效，需要 sudo）：

```bash
sudo cp macos/com.microsoft.Edge.plist "/Library/Managed Preferences/com.microsoft.Edge.plist"
sudo chown root:wheel "/Library/Managed Preferences/com.microsoft.Edge.plist"
sudo chmod 644 "/Library/Managed Preferences/com.microsoft.Edge.plist"
killall cfprefsd
```

然后打开 `edge://policy` 点「重新加载政策」。

撤销：

```bash
defaults delete com.microsoft.Edge                              # 用户级
sudo rm "/Library/Managed Preferences/com.microsoft.Edge.plist" # 系统级
killall cfprefsd
```

## 关了哪些东西

| 分类 | 内容 |
|---|---|
| 遥测 | 个性化上报、第三方搜索遥测、资产下发、实验流量、Do Not Track、严格跟踪防护 |
| AI | Copilot 全部形态（含页面上下文、Entra、365 图标、历史 AI 搜索）、侧边栏 Copilot、Compose、本地 AI 模型下载、AI 主题、AI 自动填充 |
| 新标签页 | 新闻与内容流、Bing Chat、快捷链接、应用启动器、推荐与推广、Microsoft Rewards、游戏菜单 |
| 侧栏与集成 | 侧边栏、侧栏搜索、分屏、Drop、迷你菜单、Office 快链、分享、钱包、朗读 |
| 购物与广告 | 购物助手、优惠券、Acrobat 订阅按钮、PDF 推荐、推荐内容、Insider 推广 |
| 推销 | 首次运行引导、导入向导、关闭多标签确认 |
| 后台 | 网络预测预取、性能检测器、磁盘缓存限制 512MB |
| 密码 | 密码管理器（`PasswordManagerEnabled`）、银行卡与会员卡自动填充 |
| 企业噪音 | 管理后台、MAM、Web 转浏览器登录 |

**刻意保留**：Microsoft 账号登录与跨设备同步、地址自动填充、远程调试（`edge://inspect`）、
访客模式、拼写检查、通知、自动播放、常规浏览行为。

## 有代价的地方

用之前先看完这几条，都是有意为之、不是疏漏。

1. **设置页会显示「由你的组织管理」**，被策略覆盖的开关会变灰。这是 managed policy 的
   定义，不是 bug。想改回某一项，删掉文件里对应行再重新加载。
2. **默认搜索引擎被强制为 Google**（`DefaultSearchProvider*`）。要换 Bing 或
   DuckDuckGo，改 `DefaultSearchProviderName` 和 `DefaultSearchProviderSearchURL` 两行。
3. **下载弹窗和 Safe Browsing 不在这份配置里**。`SafeBrowsingProtectionLevel`、
   `SafeBrowsingDeepScanningEnabled`、`SafeBrowsingSurveysEnabled` 三条在 Edge 157
   已被移除，写进去只会让 `edge://policy` 报「错误」。要关掉「不常下载，可能有害」
   的提示，只能手动去 `edge://settings/privacy` → 「安全性」关闭
   **Microsoft Defender SmartScreen**，这是 UI 层唯一开关，没有替代策略。
4. **密码管理器关闭**，配套的是外部密码管理器（Bitwarden / KeePassXC 之类）。
   地址和银行卡自动填充仍然可用。
5. **未写 `HttpsOnlyMode`**：强制 HTTPS 会让内网 HTTP 站点每次手点继续。
   需要的话自己加 `"HttpsOnlyMode": "force_enabled"`。
6. **未写 `EdgeDefaultProfileEnabled`**：这一条在原项目里被作者标注为可能清空
   浏览器 profile，收益又极小，任何平台都不建议加。

## 已失效、不要再加的策略

Edge 157 已经移除下面这些。写进策略文件只会在 `edge://policy` 里报「错误」，
不会生效，也不会报错到影响其它策略。原项目里还留着它们，是因为那两份配置
最后维护到 2024 年。

| 策略 | 原本想做的事 |
|---|---|
| `DiagnosticData` | 关闭诊断数据上报 |
| `MetricsReportingEnabled` | 关闭使用统计上报 |
| `SafeBrowsingProtectionLevel` | 关闭 Safe Browsing 下载与站点拦截 |
| `SafeBrowsingDeepScanningEnabled` | 关闭下载文件深度扫描 |
| `SafeBrowsingSurveysEnabled` | 关闭 Safe Browsing 调查问卷 |
| `BackgroundModeEnabled` | 关闭后不再后台驻留 |
| `DefaultBrowserSettingEnabled` | 关闭默认浏览器提示 |
| `DefaultBrowserSettingsCampaignEnabled` | 关闭默认浏览器推广活动 |
| `NewTabPagePrerenderEnabled` | 关闭新标签页预渲染 |
| `PasswordGeneratorEnabled` | 关闭密码生成器 |
| `RoamingProfileSupportEnabled` | 关闭漫游配置 |
| `SpotlightExperiencesAndRecommendationsEnabled` | 关闭 Spotlight 推荐 |

判断一个策略还活着没有：`edge://policy` 列表里**带文档链接**的才是当前版本认识的；
只有裸名字、状态显示「错误」、点不开文档的，都是已废弃。

## 三条命令查状态

```text
edge://policy          所有策略及生效状态（OK / 被忽略 / 冲突）
edge://version         确认版本与 profile 路径
edge://settings        被策略锁定的项会显示「由你的组织管理」
```

`edge://policy` 里出现 `Error` 或 `Ignored` 是正常的——不同平台的 Edge 支持的策略
集合不完全一样，Windows 专属的策略写进 Linux/macOS 会被忽略，不影响其它条生效。

## 来源

策略集合整理自下面两个项目，剔除了不生效的条目、会删 profile 的条目、以及损害安全的条目：

- [marlock9/edge-debloat](https://github.com/marlock9/edge-debloat) —— 主来源，持续跟随 Edge relnote 更新
- [luciodaou/Edge-Debloater](https://github.com/luciodaou/Edge-Debloater) —— Copilot 相关条目的补充

策略语义以微软官方文档为准：
[Microsoft Edge Browser Policy Documentation](https://learn.microsoft.com/en-us/deployedge/microsoft-edge-policies)
