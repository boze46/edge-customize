# edge-customize

Microsoft Edge 去臃肿配置，基于官方 Managed Policy 机制，覆盖 Windows / Linux / macOS。

不是改设置项，是写企业策略：入口直接从 UI 消失，后台服务直接不启动，改完是持久的、跟着文件走的、可版本回滚的。

## 文件

| 平台 | 文件 | 落点 |
|---|---|---|
| Windows | `windows/edge-debloat.reg` | `HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Edge` |
| Linux | `linux/managed.json` | `/etc/opt/edge/policies/managed/debloat.json` |
| macOS | `macos/com.microsoft.Edge.plist` | `com.microsoft.Edge` 偏好域 |

三个平台共用一套策略：`linux/managed.json` 是唯一手改的源，另外两个平台各有一份补充
（`windows/extra.json` 33 条、`macos/extra.json` 4 条，都是 Linux 不认但该平台官方支持的）。
改完策略跑一次 `python3 tools/build.py` 重新生成 `.reg` 和 `.plist`，不要手改这两份。

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
| 安全 | SmartScreen 关闭（`SmartScreenEnabled`）、SmartScreen DNS 请求、PUA 拦截 |
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
3. **SmartScreen 完全关闭**（`SmartScreenEnabled: false`）。下载文件的信誉检查、钓鱼网站
   拦截都不再生效，Edge 不会再拦任何东西。这是关掉「不常下载，可能有害」弹窗的唯一策略
   （旧名 `SafeBrowsingProtectionLevel` 已废弃）。想少弹窗又保住外网防护的话，删掉这一行，
   改用 `SmartScreenForTrustedDownloadsEnabled: false`——只跳过内网和本地来源的检查，
   Windows 版已经包含它。
4. **密码管理器关闭**，配套的是外部密码管理器（Bitwarden / KeePassXC 之类）。
   地址和银行卡自动填充仍然可用。
5. **未写 `HttpsOnlyMode`**：强制 HTTPS 会让内网 HTTP 站点每次手点继续。
   需要的话自己加 `"HttpsOnlyMode": "force_enabled"`。
6. **未写 `EdgeDefaultProfileEnabled`**：这一条在原项目里被作者标注为可能清空
   浏览器 profile，收益又极小，任何平台都不建议加。

## 平台差异与策略改名

微软的策略文档只列 Windows / macOS / Android / iOS 四栏，**Linux 从来不在里面**，
所以 Linux 的集合只能靠 `edge://policy` 实测确认。实测下来有 12 条在 Linux 上报「错误」，
原因分三类：

**一、Edge 把 SafeBrowsing 系列整体改名为 SmartScreen**

| 旧名（已废弃） | 新名（本文档使用） |
|---|---|
| `SafeBrowsingProtectionLevel` | `SmartScreenEnabled` |
| `SafeBrowsingAllowlistDomains` | `SmartScreenAllowListDomains` |
| `SafeBrowsingForTrustedSourcesEnabled` | `SmartScreenForTrustedDownloadsEnabled` |
| `SafeBrowsingDeepScanningEnabled` | 无对应，功能已并入 SmartScreen |
| `SafeBrowsingSurveysEnabled` | 无对应，已移除 |

**二、官方标注 OBSOLETE，全平台失效**

- `MetricsReportingEnabled` —— Windows/macOS 77-88，Edge 88 之后不再生效。

**三、Linux 不支持，但 Windows / macOS 依然有效**

这 8 条放在各自的 `extra.json` 里，Linux 版本不含：

| 策略 | Windows | macOS | 作用 |
|---|---|---|---|
| `DiagnosticData` | ≥122 | ≥86 | 关闭诊断数据上报 |
| `BackgroundModeEnabled` | ≥77 | — | 关闭后不再后台驻留 |
| `DefaultBrowserSettingEnabled` | ≥77 | ≥77 | 关闭默认浏览器提示 |
| `DefaultBrowserSettingsCampaignEnabled` | ≥113 | — | 关闭默认浏览器推广活动 |
| `NewTabPagePrerenderEnabled` | ≥85 | ≥85 | 关闭新标签页预渲染 |
| `PasswordGeneratorEnabled` | ≥93 | ≥93 | 关闭密码生成器 |
| `RoamingProfileSupportEnabled` | ≥85 | — | 关闭漫游配置 |
| `SpotlightExperiencesAndRecommendationsEnabled` | ≥86 | — | 关闭 Spotlight 推荐 |
| `SmartScreenForTrustedDownloadsEnabled` | ≥78 | — | 内网/本地来源的下载跳过信誉检查 |

此外 `EdgeAdminCenterEnabled` 在 Linux 上实测生效，但官方文档页 404，查不到另外两个平台
的支持情况，所以只在 Linux 版里保留。

判断一个策略在某平台活不活：`edge://policy` 列表里**带文档链接**的才是当前版本认识的；
只有裸名字、状态「错误」、点不开文档的，就是该平台不支持。

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
