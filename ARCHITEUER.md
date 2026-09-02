# neu_wisedu2wakeup 项目实现架构

> 本文基于当前仓库中的全部项目文件（`neu_wisedu2wakeup.py`、`extract_schedule.js`、`requirements.txt`、`README.md` 和 `.gitignore`）整理。文件名沿用用户要求的 `ARCHITEUER.md`。

## 1. 项目定位

本项目是一个面向东北大学本科教务管理系统的课程表导出工具，核心目标是把金智教育（Wisedu）教务系统中的课程数据转换为：

- WakeUP 课程表可导入的 CSV 文件；
- 小爱课程表（系统内置 MIUI/HyperOS 版本或独立 App）可直接写入的课程表。

仓库提供两条实现路径：

1. **Python 命令行程序**：负责网络探测、东北大学统一认证扫码登录、课表拉取、解析、预览以及 CSV/小爱课程表导出。
2. **浏览器控制台 JavaScript 脚本**：复用浏览器中已经完成的教务系统登录态，直接请求课表接口并下载 CSV；它不处理登录和小爱课程表写入。

项目是脚本型、单体式实现，没有后端服务、数据库、前端工程或模块化包结构。

## 2. 文件与职责

| 文件/目录 | 职责 |
|---|---|
| `neu_wisedu2wakeup.py` | 主程序和全部 Python 业务逻辑；采用全局 `requests.Session` 串联登录、查询和导出流程 |
| `extract_schedule.js` | 浏览器 Console 中执行的轻量 CSV 导出脚本 |
| `requirements.txt` | Python 依赖：`requests`、`qrcode`、`prettytable`、`pycryptodome` |
| `README.md` | 使用教程、支持范围、网络与登录说明、第三方导入说明 |
| `.gitignore` | 忽略构建产物、虚拟环境、生成的 `schedule.csv` 等 |
| `.dsh/AGENT.md` | 面向后续代码代理/维护者的项目工作约定和架构摘要 |
| `.dsh/logs/` | DSH 工作日志目录，当前为空目录 |

## 3. Python 程序分层与调用链

虽然代码集中在一个文件中，但可以按职责划分为以下逻辑层：

### 3.1 运行环境与会话层

- 导入 CSV、HTTP、二维码、正则、JSON、AES、终端表格等依赖。
- 创建全局 `requests.Session`，统一设置浏览器 User-Agent，并复用 Cookie。
- 通过 `urllib3.disable_warnings()` 隐藏 HTTPS 证书警告；课表请求显式使用 `verify=False`，这意味着证书校验被关闭，应视为安全风险。
- `using_webvpn` 全局变量标识是否需要通过东北大学 WebVPN 访问。

### 3.2 网络与统一认证层

`check_network()` 先访问 `https://jwxt.neu.edu.cn`：

- HTTP 200：认为可以直接访问校内教务系统；
- 请求异常：改为探测 `https://webvpn.neu.edu.cn`，成功后启用 WebVPN URL 重写；
- 两者都不可用时退出。

`set_webvpn(url)` 在 WebVPN 模式下把原始教务系统 URL 改写成 WebVPN 代理 URL。对 CAS 二维码登录 URL 和二维码轮询 URL 有专门分支，普通主机名则使用固定 AES-CFB 参数生成 WebVPN 所需的主机编码。

`neucas_qr_login()`：

1. 生成 UUID；
2. 构造东北大学统一认证二维码地址和扫码状态检查地址；
3. 在终端打印二维码，同时显示可用微信打开的链接；
4. 用户在微信企业号中扫码并授权后，使用同一 Session 请求扫码检查和 CAS 登录地址；
5. WebVPN 模式下先进入 WebVPN，再设置 Referer，并通过代理地址完成后续认证。

认证结果不由程序自行解析账号密码，而是依赖 CAS/微信扫码流程将登录 Cookie/重定向状态写入 `requests.Session`。

### 3.3 学期、用户和校区查询层

- `print_welcome()`：查询当前用户，打印 `userName` 和 `userId`。
- `get_termcode()`：从当前用户欢迎信息取得默认 `xnxqdm`/`xnxqmc`，允许用户输入自定义学期代码；输入后通过学期索引接口校验。
- `check_xnxq_index(termcode)`：遍历返回的学期列表，按 `itemCode` 找到学期名称。
- `get_campuscode(termcode)`：查询该学期的可排课校区，并取返回数组第一项的 `id`。这个值主要用于小爱课程表的时间表配置；实际“我的课表”抓取函数还固定请求南湖 `00` 和浑南 `01` 两个校区。
- `get_first_day(termcode)`：查询学期周次信息，取第一项 `startDate`，转换为毫秒时间戳，供小爱课程表设置使用。

### 3.4 课表获取与规范化层

主流程当前调用 `convert_arranged_by_WoDeKeBiao(termcode)`，名称意为“我的课表”/WoDeKeBiao 数据路径：

- 对南湖校区 `campusCode=00` 发起一次 POST；
- 对浑南校区 `campusCode=01` 再发起一次 POST；
- 两次结果都读取 `datas.arrangedList` 并合并；
- 根据 `courseCode` 是否包含 `-` 区分普通课程和实验类课程。

`process_normal_course()`：

- 从 `courseName`、`dayOfWeek`、`beginSection`、`endSection` 读取基本排课信息；
- 从 `weeksAndTeachers` 的最后一段提取教师；
- 遍历 `titleDetail`（跳过汇总项），提取周次和地点；
- 去掉教师的方括号标注，清理周次中的逗号/括号；若地点以“校区”结尾则标记为暂未安排教室；
- 每个详情项返回一行七列数据。

`process_lab_course()`：

- 针对实验类返回结构提取教师、地点、周次；
- 从 `placeName` 和 `weeksAndTeachers` 解析排课信息；
- 同样输出统一的七列课程行。

统一中间格式为：

```text
[课程名称, 星期(1-7), 开始节数, 结束节数, 老师, 地点, 周数]
```

代码中还保留了 `convert_arranged_by_WoDeCheng(term)` 备用/兼容路径：它请求 `courses.do`，解析 `classDateAndPlace` 中按逗号、斜杠分隔的日期、节次、教师和地点，并跳过“停课”记录。但主流程中对该 fallback 的调用已被注释，当前课表详情请求失败时直接退出。

### 3.5 展示与输出层

- `prettytable_print()`：用表格在终端预览统一课程数据。
- CSV 导出：写入 UTF-8 BOM 的 `schedule.csv`，表头为“课程名称、星期、开始节数、结束节数、老师、地点、周数”，适配 WakeUP 的 CSV 导入。
- 小爱课程表导出：`export_to_aischedule()` 先让用户粘贴 App Debug 信息，识别两种来源，然后创建课表、读取设置、更新学期/节次配置，逐课写入课程信息。

小爱导出时会把中文周次表达转换为数字周列表：普通范围展开为全部周，单周/双周分别筛选奇数/偶数周；依据课程名称计算 12 种颜色之一；遇到服务端报告的时间重叠课程会记录并继续导入其余课程。

### 3.6 主入口

`if __name__ == "__main__"` 的实际调用顺序：

```text
check_network
  -> 用户阅读提示
  -> neucas_qr_login
  -> print_welcome
  -> get_termcode
  -> get_campuscode
  -> convert_arranged_by_WoDeKeBiao
  -> prettytable_print
  -> 选择 CSV 或小爱课程表
       -> CSV: 写 schedule.csv
       -> 小爱: get_first_day -> export_to_aischedule
```

所有异常最终由最外层捕获，打印 traceback 后等待回车退出。程序没有单元测试、结构化日志、配置文件或重试机制。

## 4. 复用的东北大学教务系统接口

以下接口均由 Python 程序直接调用，或由 `extract_schedule.js` 在已登录的教务系统页面中以相对路径调用。基础站点为 `https://jwxt.neu.edu.cn`；在校外环境下会经过 `https://webvpn.neu.edu.cn` 代理改写。

### 4.1 教务系统业务 API

| 方法 | 接口路径 | 参数/请求体 | 用途与关键响应字段 |
|---|---|---|---|
| GET | `/jwapp/sys/homeapp/api/home/currentUser.do` | 无 | 获取当前登录用户；使用 `datas.userName`、`datas.userId`，以及 `datas.welcomeInfo.xnxqdm`、`xnxqmc` 获取当前学期 |
| GET | `/jwapp/sys/homeapp/api/home/kb/xnxq.do` | 无 | 获取学期索引；按 `datas[*].itemCode` 匹配学期代码，读取 `itemName` |
| GET | `/jwapp/sys/homeapp/api/home/student/getMyScheduledCampus.do?termCode={termCode}` | 查询参数 `termCode` | 获取该学期可排课校区；读取 `datas[0].id` |
| POST | `/jwapp/sys/homeapp/api/home/student/getMyScheduleDetail.do` | 表单：`termCode`、`campusCode`、`type=term` | 获取“我的课表”详情；读取 `datas.arrangedList`，包含课程名、星期、节次、课程代码、教师/周次详情、地点等字段。Python 对 `00` 和 `01` 各请求一次；JS 默认只请求返回的第一个校区 |
| GET | `/jwapp/sys/homeapp/api/home/student/courses.do?termCode={termCode}` | 查询参数 `termCode` | 兼容/备用“我的课程”数据源；读取课程的 `classDateAndPlace`。Python 中解析函数存在，但主流程 fallback 已注释 |
| GET | `/jwapp/sys/homeapp/api/home/getTermWeeks.do?termCode={termCode}` | 查询参数 `termCode` | 获取学期周次起始日期；读取 `datas[0].startDate`，转换为 Unix 毫秒时间戳 |

### 4.2 东北大学认证与网络入口

这些不是课表业务 API，但也是项目复用东北大学系统所必需的接口：

| 方法 | 接口 | 用途 |
|---|---|---|
| GET | `https://pass.neu.edu.cn/tpass/qyQrLogin?uuid={uuid}` | 生成微信企业号扫码登录二维码 |
| GET | `https://pass.neu.edu.cn/tpass/checkQRCodeScan?random={random}&uuid={uuid}` | 用户扫码授权后的状态检查 |
| GET | `https://pass.neu.edu.cn/tpass/login?service=...` | 将统一认证结果导向教务系统首页，建立教务系统登录态 |
| GET | `https://jwxt.neu.edu.cn` | 内网教务系统连通性探测 |
| GET | `https://webvpn.neu.edu.cn` | 校外 WebVPN 连通性探测及代理入口 |

认证依赖 Session Cookie 和重定向链路，不向用户索取教务系统密码。二维码 UUID 使用 Python `uuid.uuid4()` 生成，轮询 URL 的 `random` 使用随机浮点数。

## 5. 非东北大学接口：小爱课程表写入端

为了区分“来源接口”和“目标接口”，以下是项目访问的小米服务，不属于东北大学教务系统：

- `POST https://i.xiaomixiaoai.com/course-multi-auth/table`：创建课程表；
- `GET https://i.xiaomixiaoai.com/course-multi-auth/table?ctId=...&sourceName=...`：读取课程表配置；
- `PUT https://i.xiaomixiaoai.com/course-multi-auth/table`：更新课程表学期、节次和校区时间配置；
- `POST https://i.xiaomixiaoai.com/course-multi-auth/courseInfo?sourceName=...`：逐条添加课程；
- 独立 App 使用 `https://i.ai.mi.com`，路径相同。

认证信息来自用户粘贴的小爱课程表 Debug JSON：系统版本使用 `userId/deviceId/authorization/userAgent`，独立 App 使用 `appId/serviceToken/deviceId` 组合 AO-TOKEN-V1 授权头。该信息属于敏感凭据，不应写入日志、提交到 Git 或分享。

## 6. JavaScript 路径与 Python 路径的差异

| 方面 | Python | 浏览器 JavaScript |
|---|---|---|
| 登录 | 自己探测内网/WebVPN并执行微信二维码/CAS流程 | 复用浏览器当前登录态 |
| 学期 | 自动获取并可手动修改、校验 | 自动获取，缺失时 prompt |
| 校区 | 固定抓取 `00`、`01` 两个校区 | 仅取 `datas[0].id` |
| 课表接口 | `getMyScheduleDetail.do`；另有未启用的 `courses.do` 兼容解析 | `getMyScheduleDetail.do` |
| 目标 | CSV 或小爱课程表 | 仅下载 CSV |
| 解析 | 普通课程/实验课程分支 | 主要按 `titleDetail` 解析，未显式区分实验课程 |

## 7. 数据流概览

```text
东北大学微信企业号
        │ 扫码授权
        ▼
pass.neu.edu.cn / CAS ── Cookie/重定向 ──► requests.Session 或浏览器登录态
                                                   │
                                                   ▼
                                    currentUser / xnxq / campus
                                                   │
                                                   ▼
                              getMyScheduleDetail.do（课表原始 JSON）
                                                   │
                                                   ▼
                           课程解析与统一七列中间格式
                              │                    │
                              ▼                    ▼
                 UTF-8-BOM schedule.csv       小米课程表 API
                              │                    │
                              ▼                    ▼
                       WakeUP 导入             小爱课程表
```

## 8. 已知限制与维护注意事项

1. 教务系统接口是未公开、面向网页端的内部接口，字段结构和 URL 可能随系统升级变化；文档中的字段是当前代码实际依赖字段，不代表官方稳定契约。
2. Python 使用硬编码的东北大学域名、WebVPN 编码规则、AES 密钥/初始向量和校区代码；WebVPN 或教务系统升级时可能失效。
3. `verify=False` 会关闭证书校验；若要长期维护，应改为正常证书验证并完善错误处理。
4. `getMyScheduleDetail.do` 的南湖/浑南校区代码被硬编码为 `00`/`01`，且 JS 版本只取第一个校区，可能遗漏其他校区。
5. 课表周次、教师和地点依赖中文字符串格式与分隔符（`/`、空格、`，` 等），上游格式变化会导致解析异常或静默缺失。
6. `convert_arranged_by_WoDeCheng()` 的备用路径目前未接入主流程；若重新启用，应补充异常处理并与详情路径做结果比对。
7. 小爱导出使用用户提供的授权信息直接请求第三方服务，属于实验性功能；不要记录 Debug JSON、Authorization、ServiceToken 等敏感数据。
8. 当前没有自动化测试和模拟响应样例。改动解析器时建议先保存脱敏后的接口响应，补充针对普通课、实验课、单双周、无教室和停课数据的测试。
9. `schedule.csv` 是运行时生成物，已在 `.gitignore` 中忽略；二进制构建产物和虚拟环境同样不应提交。
