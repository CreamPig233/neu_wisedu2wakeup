/**
 * 东北大学教务系统课表导出脚本
 * 
 * 使用方法:
 * 1. 登录 https://jwxt.neu.edu.cn/
 * 2. 按 F12 打开开发者工具 -> 控制台 (Console)
 * 3. 粘贴本脚本并回车
 * 4. 自动下载 CSV 文件，可直接导入 WakeUp 课程表
 */

(async function () {
    console.log("开始导出课表...");

    // 封装 fetch 请求
    async function fetchJSON(url, options = {}) {
        let resp = await fetch(url, options);
        if (!resp.ok) throw new Error(`HTTP 请求失败: ${url}`);
        return await resp.json();
    }

    try {
        // 1. 获取当前用户信息及学期代码
        console.log("获取当前学期信息...");
        let userUrl = "/jwapp/sys/homeapp/api/home/currentUser.do";
        let userData = await fetchJSON(userUrl);
        let termCode = userData.datas.welcomeInfo.xnxqdm;

        if (!termCode) {
            termCode = prompt("未能自动检测到学期代码，请输入(如 2024-2025-2):", "2024-2025-2");
        }
        console.log(`当前学期: ${termCode}`);

        // 2. 获取校区代码
        console.log("获取校区信息...");
        let campusUrl = `/jwapp/sys/homeapp/api/home/student/getMyScheduledCampus.do?termCode=${termCode}`;
        let campusData = await fetchJSON(campusUrl);
        // 默认取第一个校区ID
        let campusCode = campusData.datas[0].id;
        console.log(`校区代码: ${campusCode}`);

        // 3. 获取课表详情数据
        console.log("正在拉取课表数据...");
        let scheduleUrl = "/jwapp/sys/homeapp/api/home/student/getMyScheduleDetail.do";
        let formData = new URLSearchParams();
        formData.append('termCode', termCode);
        formData.append('campusCode', campusCode);
        formData.append('type', 'term');

        let scheduleData = await fetchJSON(scheduleUrl, {
            method: 'POST',
            body: formData,
            headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' }
        });

        // 4. 解析数据并生成 CSV 内容
        let arrangedList = scheduleData.datas.arrangedList;
        console.log(`共获取到 ${arrangedList.length} 门课程。`);

        let csvRows = [];
        // CSV 表头
        csvRows.push(["课程名称", "星期", "开始节数", "结束节数", "老师", "地点", "周数"]);

        arrangedList.forEach(item => {
            let courseName = item.courseName;
            let dayOfWeek = item.dayOfWeek;
            let beginSection = item.beginSection;
            let endSection = item.endSection;

            // "weeksAndTeachers"
            let weeksAndTeachers = item.weeksAndTeachers || "";
            let teacher = "";
            let parts = weeksAndTeachers.split('/');
            if (parts.length > 0) teacher = parts[parts.length - 1].replace(/\[主讲\]/g, "");

            // 遍历 titleDetail 解析具体的周数和地点
            let details = item.titleDetail;
            if (!details || details.length <= 1) {
                csvRows.push([courseName, dayOfWeek, beginSection, endSection, teacher, "", ""]);
            } else {
                // 跳过索引0 (汇总信息)，从1开始遍历
                for (let i = 1; i < details.length; i++) {
                    let dStr = details[i];
                    if (!/^\d/.test(dStr)) continue;

                    let dParts = dStr.split(" ");
                    let weeksRaw = dParts[0];
                    // 修复：如果 split 后只有一个元素，说明没有地点，location 应为空
                    let location = dParts.length > 1 ? dParts[dParts.length - 1] : "";

                    if (location && location.endsWith("校区")) {
                        location = "待定";
                    }

                    // 格式化周数
                    let weeks = weeksRaw.replace(/,/g, "、").replace(/[()]/g, "");

                    csvRows.push([
                        courseName,
                        dayOfWeek,
                        beginSection,
                        endSection,
                        teacher,
                        location,
                        weeks
                    ]);
                }
            }
        });

        // 5. 触发 CSV 下载
        let csvContent = "\uFEFF" + csvRows.map(e => e.map(f => `"${String(f).replace(/"/g, '""')}"`).join(",")).join("\n");

        let blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        let link = document.createElement("a");
        if (link.download !== undefined) {
            let url = URL.createObjectURL(blob);
            link.setAttribute("href", url);
            link.setAttribute("download", `schedule_${termCode}.csv`);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }

        console.log("导出成功！CSV 文件已下载。");

    } catch (err) {
        console.error("导出失败:", err);
        alert("导出出错，请查看控制台日志。\n" + err.message);
    }
})();
