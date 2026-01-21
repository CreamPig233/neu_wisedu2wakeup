# neu_wisedu2wakeup
针对金智教育教务系统的课程表导出至WakeUP课程表中间件
（以东北大学本科教务管理系统(2026更新)为例）

关键词：东北大学, NEU, 金智教育, _WEU, 教务系统, 课程表, WakeUP

> [!CAUTION]
> 截至目前(2026-1-21)，新教务系统仍在持续更新，本工具仅提供辅助作用，如果课程表有改动，请**时刻**以教务系统中显示的为准！

> [!WARNING]
> (2026-1-21 更新)
> 
> 目前，新教务系统的课表功能**全面**下线，因此本脚本暂时失效，待课表功能恢复后进行测试

安装依赖`pip install -r requirements.txt`

## 如何使用

### Python 脚本

(右侧 Release 可以下载预编译版本)

1. 打开程序，使用绑定了东北大学微信企业号的微信扫描程序显示的二维码
2. 扫描二维码，在微信点击授权登录后，在程序中按下回车键，等待运行结束
3. 在程序同目录找到schedule.csv，使用WakeUP课程表导入该文件。[如何导入？](https://wakeup.fun/doc/import_from_csv.html)

### JS 脚本

1. 复制 [extract_schedule.js](extract_schedule.js) 的全部代码
2. 浏览器登录 [东北大学本科教学网](https://jwxt.neu.edu.cn/)
3. 按 F12 打开开发者工具，点击控制台 (Console) 标签页
4. 粘贴代码并按回车运行
5. 脚本会自动下载 `schedule_*-*-*.csv` 文件
6. 使用 WakeUP 课程表导入该文件。[如何导入？](https://wakeup.fun/doc/import_from_csv.html)
