import csv
import uuid
import requests
from requests.packages import urllib3
import random
import qrcode
import re
import prettytable
import json
import colorama
import sys

urllib3.disable_warnings()
colorama.init(autoreset=True)

session = requests.Session()

def check_network():
    try:
        response = session.get("http://jwxt.neu.edu.cn", timeout=5)
        if response.status_code == 200:
            return
        else:
            print(colorama.Fore.RED + "无法访问教务系统，请连接校园网或OpenVPN后重试。")
            input("按回车键退出程序...")
            sys.exit(1)
    except requests.RequestException:
        print(colorama.Fore.RED + "无法访问教务系统，请连接校园网或OpenVPN后重试。")
        input("按回车键退出程序...")
        sys.exit(1)

def neucas_qr_login():
    print("请使用微信扫码登录")
    u_uuid = str(uuid.uuid4())
    u_qrurl = f"https://pass.neu.edu.cn/tpass/qyQrLogin?uuid={u_uuid}"
    u_checkurl = f"https://pass.neu.edu.cn/tpass/checkQRCodeScan?random={random.random():.16f}&uuid={u_uuid}"
    qr = qrcode.QRCode()
    qr.add_data(u_qrurl)
    qr.make(fit=True)
    qr.print_ascii(invert=True)
    print("或使用微信打开链接：", u_qrurl)
    input("在微信中点击“授权登录”后请按回车继续...")
    global session
    session.get(u_checkurl)
    session.get("https://pass.neu.edu.cn/tpass/login?service=https%3A%2F%2Fjwxt.neu.edu.cn%2Fjwapp%2Fsys%2Fhomeapp%2Findex.do", allow_redirects=False)
    session.get("https://pass.neu.edu.cn/tpass/login?service=https%3A%2F%2Fjwxt.neu.edu.cn%2Fjwapp%2Fsys%2Fhomeapp%2Findex.do%3FcontextPath%3D%2Fjwapp")

def print_welcome():   
    global session
    response = session.get("https://jwxt.neu.edu.cn/jwapp/sys/homeapp/api/home/currentUser.do")
    response_json = response.json()
    username = response_json["datas"]["userName"]
    userid = response_json["datas"]["userId"]
    print(f"欢迎您，{username} ({userid})！")
    return username

def get_termcode():
    global session
    response = session.get("https://jwxt.neu.edu.cn/jwapp/sys/homeapp/api/home/currentUser.do")
    response_json = response.json()
    termcode = response_json["datas"]["welcomeInfo"]["xnxqdm"]
    termname = response_json["datas"]["welcomeInfo"]["xnxqmc"]
    print("当前学期为：", termcode,"，", termname)
    inputtermcode = input("如需更改学期请输入学期代码（格式如2025-2026-1），否则直接回车：")
    if inputtermcode != "":
        codes = inputtermcode.split("-")
        if len(codes) != 3:
            print(colorama.Fore.RED + "学期代码格式错误，使用默认学期")
        elif codes[2] not in ["1", "2", "3"]:
            print(colorama.Fore.RED + "学期代码格式错误，使用默认学期")
        elif int(codes[0]) + 1 != int(codes[1]):
            print(colorama.Fore.RED + "学期代码格式错误，使用默认学期")
        else:
            termcode = inputtermcode
        
    return termcode, termname

def get_campuscode(termcode):
    global session
    resp = session.get(f"https://jwxt.neu.edu.cn/jwapp/sys/homeapp/api/home/student/getMyScheduledCampus.do?termCode={termcode}")
    campuscode = resp.json()["datas"][0]["id"]
    return campuscode


def convert_arranged_by_WoDeKeBiao(term):

    headers = {
        'Host': 'jwxt.neu.edu.cn',
        "Referer": 'https://jwxt.neu.edu.cn/jwapp/sys/homeapp/home/index.html?av=&contextPath=/jwapp',
        "user-agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        "content-type": 'application/x-www-form-urlencoded;charset=UTF-8',
    }
    
    # 获取南湖校区课表
    
    data = {
        'termCode': term,
        'campusCode': '00',
        'type': 'term',
    }

    global session
    response = session.post(
        'https://jwxt.neu.edu.cn/jwapp/sys/homeapp/api/home/student/getMyScheduleDetail.do',
        headers=headers,
        data=data,
        verify=False,
    )

    schedule_json = response.json()
    schedule_list = schedule_json["datas"]


    list_for_csv = []
    
    for each_class in schedule_list["arrangedList"]:
        courseName = each_class["courseName"]
        dayOfWeek = each_class["dayOfWeek"]
        beginSection = each_class["beginSection"]
        endSection = each_class["endSection"]
        titleDetail = each_class["titleDetail"]
        weeksAndTeachers = each_class["weeksAndTeachers"]
        teachers = weeksAndTeachers.split(r"/")[-1]
        for i in range(1,len(titleDetail)):
            i = titleDetail[i]
            if not i[0:1].isdigit():
                continue
            append_list = []
            week = i.split(" ")[0]
            placeName = i.split(" ")[-1].replace("*","")
            if placeName.endswith("校区"):
                placeName = "暂未安排教室"
            
            append_list.append(courseName)
            append_list.append(dayOfWeek)
            append_list.append(beginSection)
            append_list.append(endSection)
            append_list.append(re.sub(r'\[.*?\]', '', teachers))
            append_list.append(placeName)
            append_list.append(week.replace(",","、").replace("(","").replace(")",""))
            list_for_csv.append(append_list)
    
    # 获取浑南校区课表
    
    data = {
        'termCode': term,
        'campusCode': "01",
        'type': 'term',
    }

    response = session.post(
        'https://jwxt.neu.edu.cn/jwapp/sys/homeapp/api/home/student/getMyScheduleDetail.do',
        headers=headers,
        data=data,
        verify=False,
    )

    schedule_json = response.json()
    schedule_list = schedule_json["datas"]

    for each_class in schedule_list["arrangedList"]:
        courseName = each_class["courseName"]
        dayOfWeek = each_class["dayOfWeek"]
        beginSection = each_class["beginSection"]
        endSection = each_class["endSection"]
        titleDetail = each_class["titleDetail"]
        weeksAndTeachers = each_class["weeksAndTeachers"]
        teachers = weeksAndTeachers.split(r"/")[-1]
        for i in range(1,len(titleDetail)):
            i = titleDetail[i]
            if not i[0:1].isdigit():
                continue
            append_list = []
            week = i.split(" ")[0]
            placeName = i.split(" ")[-1].replace("*","")
            if placeName.endswith("校区"):
                placeName = "暂未安排教室"
            if placeName == "停课":
                continue

            append_list.append(courseName)
            append_list.append(dayOfWeek)
            append_list.append(beginSection)
            append_list.append(endSection)
            append_list.append(re.sub(r'\[.*?\]', '', teachers))
            append_list.append(placeName)
            append_list.append(week.replace(",","、").replace("(","").replace(")",""))
            list_for_csv.append(append_list)

        
    return list_for_csv
        

def convert_arranged_by_WoDeKeCheng(term):

    headers = {
        'Host': 'jwxt.neu.edu.cn',
        "Referer": 'https://jwxt.neu.edu.cn/jwapp/sys/homeapp/home/index.html?av=&contextPath=/jwapp',
        "user-agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        "content-type": 'application/x-www-form-urlencoded;charset=UTF-8',
    }


    global session
    response = session.get(
        f'https://jwxt.neu.edu.cn/jwapp/sys/homeapp/api/home/student/courses.do?termCode={term}',
        headers=headers,
        verify=False,
    )


    schedule_json = response.json()
    schedule_list = schedule_json["datas"]

    list_for_csv = []
    
    dayofweeklist = {'星期一':1,'星期二':2,'星期三':3,'星期四':4,'星期五':5,'星期六':6,'星期日':7,'星期天':7}
    sectionlist = {"第一节":1,"第二节":2,"第三节":3,"第四节":4,"第五节":5,"第六节":6,"第七节":7,"第八节":8,"第九节":9,"第十节":10,"第十一节":11,"第十二节":12}
    for each_class in schedule_list:
        courseName = each_class["courseName"]
        classDateAndPlace = each_class["classDateAndPlace"]
        if classDateAndPlace == None:
            continue
        classinfo = classDateAndPlace.split(r"，")
        for singleinfo in classinfo:
            singleinfo = singleinfo.split(r"/")
            weeks = re.sub(r'\[.*?\]', '', singleinfo[0]).replace(",","、")
            dayOfWeek = dayofweeklist[re.sub(r'\[.*?\]', '', singleinfo[1])]
            section = re.sub(r'\[.*?\]', '', singleinfo[2])
            beginSection = sectionlist[section.split("-")[0]]
            endSection = sectionlist[section.split("-")[1]]
            teachers = re.sub(r'\[.*?\]', '', singleinfo[3])
            try:
                placeName = singleinfo[4].replace("*","")
            except IndexError:
                placeName = "暂未安排教室"
            if placeName == "停课":
                continue
            weeks = weeks.replace(",","、").replace("(","").replace(")","")
            
            append_list = []
        
            
            append_list.append(courseName)
            append_list.append(dayOfWeek)
            append_list.append(beginSection)
            append_list.append(endSection)
            append_list.append(teachers)
            append_list.append(placeName)
            append_list.append(weeks)
            list_for_csv.append(append_list)
    
    return list_for_csv

def prettytable_print(list_for_csv):
    table = prettytable.PrettyTable()
    table.field_names = ["课程名称", "星期", "开始节数", "结束节数", "老师", "地点", "周数"]
    for row in list_for_csv:
        table.add_row(row)
    print(table)

def get_first_day(termcode):
    from datetime import datetime
    global session
    resp = session.get(f"https://jwxt.neu.edu.cn/jwapp/sys/homeapp/api/home/getTermWeeks.do?termCode={termcode}")
    first_day = resp.json()["datas"][0]["startDate"]
    first_day = datetime.strptime(first_day, "%Y-%m-%d %H:%M:%S")
    first_day = int(first_day.timestamp())*1000
    return first_day

def export_to_aischedule(list_for_csv, termname, campuscode, first_day):
    print(colorama.Fore.YELLOW + "===========警告=============")
    print(colorama.Fore.YELLOW + "导出到小爱课程表属于实验性功能，可能存在导入失败等情况，请谨慎使用！")
    print(colorama.Fore.YELLOW + "当前仅支持MIUI/HyperOS系统中自带的小爱课程表，独立版本及网页版暂不支持导入。")
    print("请仔细阅读下述操作方法，")
    print("1. 打开小爱课程表，点击右下角头像按钮进入课程表设置")
    print("2. 将页面滑到最下面，点击“开始新学期”下方空白处5次，进入Debug页面")
    print("3. 点击“点击获取UserInfo”，在弹窗中点击复制")
    print("4. 将复制得到的调试数据输入到下方")
    print("============================")
    debug_info = input("请输入调试数据：")
    try:
        debug_info = json.loads(debug_info)
    except json.JSONDecodeError:
        print(colorama.Fore.RED + "数据格式错误，失败。")
        input("按回车键退出程序...")
        sys.exit(-1)
    
    try:
        info_userid = debug_info["userId"]
        if info_userid == 0:
            print(colorama.Fore.RED + "userId无效，失败。")
            input("按回车键退出程序...")
            sys.exit(-1)
        info_deviceId = debug_info["deviceId"]
        info_authorization = debug_info["authorization"]
        info_useragent = debug_info["userAgent"]
    except KeyError:
        print(colorama.Fore.RED + "调试数据缺少必要字段，失败。")
        input("按回车键退出程序...")
        sys.exit(-1)
    
    # 添加课表
    response = requests.post(
        url="https://i.xiaomixiaoai.com/course-multi-auth/table", 
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "access-control-allow-origin": "true",
            "user-agent": info_useragent,
            "authorization": info_authorization
        },
        json={
            "name": termname,
            "current": 0,
            "sourceName": "course-app-miui"
        })
    responsecode = response.json()["code"]
    if responsecode != 0:
        print(colorama.Fore.RED + "课表创建失败")
        desc = response.json()["desc"]
        if desc == "course table name exist":
            print(colorama.Fore.RED + "已存在同名课表，请先删除已有课表后重试\n课表名称：" + termname)
        elif desc == "table num over max size":
            print(colorama.Fore.RED + "课表数量已达上限，请删除不需要的课表后重试")
        else:
            print(colorama.Fore.RED + "错误码：" + str(response.json()["code"]) + "，错误原因：" + desc)
        input("按回车键退出程序...")
        sys.exit(-1)
    ctId = response.json()["data"]
    if ctId == "0":
        print(colorama.Fore.RED +  "课表创建失败，错误原因：" + response.json()["desc"])
        input("按回车键退出程序...")
        sys.exit(-1)
    
    print("课表创建成功，课表名称：" + termname)
    #获取课表配置
    response = requests.get(
        url=f"https://i.xiaomixiaoai.com/course-multi-auth/table?ctId={ctId}&sourceName=course-app-miui", 
        headers =  {
            "content-type": "application/json",
            "user-agent": info_useragent,
            "authorization": info_authorization
        })
    responsecode = response.json()["code"]
    if responsecode != 0:
        print(colorama.Fore.RED + "获取课表配置失败")
        print(colorama.Fore.RED + "错误码：" + str(response.json()["code"]) + "，错误原因：" + response.json()["desc"])
        input("按回车键退出程序...")
        sys.exit(-1)
    settingId=response.json()["data"]["setting"]["id"]
    print("获取课表配置成功")
    
    #修改课表配置
    if campuscode == "00":
        #南湖校区时间表
        sections = r'[{"i":1,"s":"08:00","e":"08:45"},{"i":2,"s":"08:55","e":"09:40"},{"i":3,"s":"10:00","e":"10:45"},{"i":4,"s":"10:55","e":"11:40"},{"i":5,"s":"14:00","e":"14:45"},{"i":6,"s":"14:55","e":"15:40"},{"i":7,"s":"16:00","e":"16:45"},{"i":8,"s":"16:55","e":"17:40"},{"i":9,"s":"18:30","e":"19:15"},{"i":10,"s":"19:25","e":"20:10"},{"i":11,"s":"20:20","e":"21:05"},{"i":12,"s":"21:15","e":"22:00"}]'
    elif campuscode == "01":
        #浑南校区时间表
        sections = r'[{"i":1,"s":"08:30","e":"09:15"},{"i":2,"s":"09:25","e":"10:10"},{"i":3,"s":"10:30","e":"11:15"},{"i":4,"s":"11:25","e":"12:10"},{"i":5,"s":"14:00","e":"14:45"},{"i":6,"s":"14:55","e":"15:40"},{"i":7,"s":"16:10","e":"16:55"},{"i":8,"s":"17:05","e":"17:50"},{"i":9,"s":"18:30","e":"19:15"},{"i":10,"s":"19:25","e":"20:10"},{"i":11,"s":"20:20","e":"21:05"},{"i":12,"s":"21:15","e":"22:00"}]'
    
    response = requests.put(
        url="https://i.xiaomixiaoai.com/course-multi-auth/table", 
        headers={
            "accept": "application/json",
            "content-type": "application/json",
            "origin": "https://i.xiaomixiaoai.com",
            "referer": "https://i.xiaomixiaoai.com/h5/precache/ai-schedule/",
            "user-agent": info_useragent,
            "authorization": info_authorization
        }, 
        json={
            "ctId": ctId,
            "deviceId": info_deviceId,
            "name":termname,
            "sourceName": "course-app-miui",
            "userId": info_userid,
            "setting": {
                "afternoonNum":4,
                "extend":r'{"startSemester":"' + str(first_day) + r'","degree":"本科/专科","showNotInWeek":true,"bgSetting":{"name":"default","opacity":1}}',
                "id":settingId,
                "isWeekend":1,
                "morningNum":4,
                "nightNum":4,
                "presentWeek":1,
                "school":"{}",
                "sections":sections,
                "speak":1,
                "startSemester":str(first_day),
                "totalWeek":20,
                "weekStart":7
            }})
    responsecode = response.json()["code"]
    if responsecode != 0:
        print(colorama.Fore.RED + "修改课表配置失败")
        print(colorama.Fore.RED + "错误码：" + str(response.json()["code"]) + "，错误原因：" + response.json()["desc"])
        input("按回车键退出程序...")
        sys.exit(-1)
    print("课表配置修改成功")
    
    #添加课程
    url = "https://i.xiaomixiaoai.com/course-multi-auth/courseInfo"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "origin": "https://i.xiaomixiaoai.com",
        "referer": "https://i.xiaomixiaoai.com/h5/precache/ai-schedule/",
        "user-agent": info_useragent,
        "authorization": info_authorization
    }
    
    def explain_duplicate_lesson(duplicate_lesson):
        name = duplicate_lesson["name"]
        position = duplicate_lesson["position"]
        weeks = duplicate_lesson["weeks"]
        sections = duplicate_lesson["sections"]
        day = duplicate_lesson["day"]
        return f"课程名称：{name}，上课地点：{position}，上课周数：{weeks}，星期：{day}，上课节数：{sections}"
    
    lesson_color_style = [
        "{\"color\":\"#00A6F2\",\"background\":\"#E5F4FF\"}",
        "{\"color\":\"#FC6B50\",\"background\":\"#FDEBDE\"}",
        "{\"color\":\"#3CB3C8\",\"background\":\"#DEFBF8\"}",
        "{\"color\":\"#7D7AEA\",\"background\":\"#EDEDFF\"}",
        "{\"color\":\"#FF9900\",\"background\":\"#FCEBCD\"}",
        "{\"color\":\"#EF5B75\",\"background\":\"#FFEFF0\"}",
        "{\"color\":\"#5B8EFF\",\"background\":\"#EAF1FF\"}",
        "{\"color\":\"#F067BB\",\"background\":\"#FFEDF8\"}",
        "{\"color\":\"#29BBAA\",\"background\":\"#E2F8F3\"}",
        "{\"color\":\"#CBA713\",\"background\":\"#FFF8C8\"}",
        "{\"color\":\"#B967E3\",\"background\":\"#F9EDFF\"}",
        "{\"color\":\"#6E8ADA\",\"background\":\"#F3F2FD\"}"
    ]
    
    duplicate_lesson = []
    for row in list_for_csv:
        weeks = row[6].split("、")
        rawweek = ""
        for week in weeks:
            if week.endswith("周"):
                numbers = re.findall(r'\d+', week)
                if len(numbers) >= 2:
                    start = int(numbers[0])
                    end = int(numbers[1])
                    result = list(range(start, end + 1))
                    rawweek = rawweek + ',' + ','.join(str(i) for i in range(start, end + 1))
                elif len(numbers) == 1:
                    rawweek = rawweek + ',' + numbers[0]
            elif week.endswith("单"):
                numbers = re.findall(r'\d+', week)
                if len(numbers) >= 2:
                    start = int(numbers[0])
                    end = int(numbers[1])
                    result = [i for i in range(start, end + 1) if i % 2 != 0]
                    rawweek = rawweek + ',' + ','.join(str(i) for i in result)
                elif len(numbers) == 1:
                    rawweek = rawweek + ',' + numbers[0]
            elif week.endswith("双"):
                numbers = re.findall(r'\d+', week)
                if len(numbers) >= 2:
                    start = int(numbers[0])
                    end = int(numbers[1])
                    result = [i for i in range(start, end + 1) if i % 2 == 0]
                    rawweek = rawweek + ',' + ','.join(str(i) for i in result)
                elif len(numbers) == 1:
                    rawweek = rawweek + ',' + numbers[0]
        rawweek = rawweek.lstrip(',')
        data = {
            "ctId": ctId,
            "course": {
                "name": row[0],
                "position": row[5],
                "teacher": row[4],
                "extend": "",
                "weeks": rawweek,
                "day": [1,2,3,4,5,6,7][row[1]-1],
                "style": lesson_color_style[abs(hash(row[0]))%12],
                "sections": ','.join(str(i) for i in range(row[2], row[3] + 1))
            },
            "userId": info_userid,
            "deviceId": info_deviceId,
            "sourceName": "course-app-miui"
        }
        response = requests.post(url, headers=headers, json=data)
        
        #检查重复课程
        desc = response.json()["desc"]
        
        if desc == "course info has overlap":
            print(colorama.Fore.RED + "添加课程失败，存在重复课程")
            print(colorama.Fore.RED + "跳过该课程继续导入剩余课程")
            duplicate_lesson.append(data["course"])
            continue
        
        responsecode = response.json()["code"]
        if responsecode != 0:
            print(colorama.Fore.RED + "添加课程失败")
            desc = response.json()["desc"]
            print(colorama.Fore.RED + "错误码：" + str(response.json()["code"]) + "，错误原因：" +desc)
            print("导入课程信息时出错：" + str(data["course"]) )
            input("按回车键退出程序...")
            sys.exit(-1)
    
    if len(duplicate_lesson) > 0:
        print(colorama.Fore.YELLOW + "以下课程因与其他课程时间冲突，导入失败，请检查：")
        for lesson in duplicate_lesson:
            print(colorama.Fore.YELLOW + explain_duplicate_lesson(lesson))
    else:
        print(colorama.Fore.GREEN + "如果不出意外，课程表已成功导入")
    print(colorama.Fore.GREEN + "请退出小爱课程表并重新进入，点击右上角切换课表，即可看到新导入的课表")
    input("按回车键退出程序...")
        

    
if __name__ == "__main__":
    print("==========使用教程==========")
    print("1.打开程序，使用绑定了东北大学微信企业号的微信扫描程序显示的二维码")
    print("2.扫描二维码，在微信点击授权登录后，在程序中按下回车键，等待运行结束")
    print("3.根据提示选择导出方式，导出课程表")
    print(colorama.Fore.YELLOW + "===========警告=============")
    print(colorama.Fore.YELLOW + "本工具仅提供辅助作用，如果生成的课程表与系统中显示的不一致，请时刻以教务系统中显示的为准！")
    print("本项目已在 https://github.com/CreamPig233/neu_wisedu2wakeup 开源")
    print("===========================")
    try:
        check_network()
        input("请仔细阅读上述须知后，按回车键继续...")
        neucas_qr_login()
        username = print_welcome()
        termcode, termname = get_termcode()
        campuscode = get_campuscode(termcode)
        print(f"获取{termcode}课程表中...")
        try:
            list_for_csv = convert_arranged_by_WoDeKeCheng(termcode)
        except Exception as e:
            print(colorama.Fore.RED + "使用“我的课程”模块获取课程表失败")
            print(colorama.Fore.RED + "错误信息：" + str(e))
            print("尝试使用“我的课表”模块获取课程表...")

            try:
                list_for_csv = convert_arranged_by_WoDeKeBiao(termcode)
            except Exception as e2:
                print(colorama.Fore.RED + "使用“我的课表”模块获取课程表失败")
                print(colorama.Fore.RED + "错误信息：" + str(e2))
                input("课程表获取失败，按回车键退出程序...")
                sys.exit(1)
                
        while True:
            print("==========获取结束==========")
            print("以下是获取到的课程表预览：")
            
            prettytable_print(list_for_csv)

            print("导出方式：")
            print("1. 导出至csv文件（导出至WakeUP课程表）")
            print("2. 导出至小爱课程表"+colorama.Fore.YELLOW+"（！实验性功能！）"+colorama.Style.RESET_ALL)
            choice = input("请选择导出方式：（输入数字1或数字2）：")
            if choice == "1":
                with open("schedule.csv", "w", newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(["课程名称", "星期", "开始节数", "结束节数", "老师", "地点", "周数"])
                    writer.writerows(list_for_csv)
                print(colorama.Fore.GREEN + "课程表已成功导出至程序同目录的schedule.csv，请使用WakeUP课程表导入该文件。")
                print("   如何导入? https://wakeup.fun/doc/import_from_csv.html")
                input("按回车键退出程序...")
                sys.exit(0)
            elif choice == "2":
                first_day = get_first_day(termcode)
                #list_for_csv = [['井巷工程', 3, 1, 2, '赵兴东', '大成206', '1-8周'], ['井巷工程', 4, 9, 10, '赵兴东', '大成202', '1-8周'], ['井巷工程', 1, 1, 2, '赵兴东', '大成210', '1-8周'], ['金属矿床地下开采', 4, 7, 8, '李元辉,徐帅,姜海强,安龙,侯朋远,李坤蒙', '大成206', '1-9周、15-17周'], ['金属矿床地下开采', 1, 7, 8, '李元辉,徐帅,姜海强,安龙,侯朋远,李坤蒙', '大成102-智慧教室', '5-9周、11-17周'], ['金属矿床地下开采', 2, 7, 8, '李元辉,徐帅,姜海强,安龙,侯朋远,李坤蒙', '大成104-智慧教室', '5-9周、11-17周'], ['金属矿床地下开采', 3, 5, 8, '李元辉,徐帅,姜海强,安龙,侯朋远,李坤蒙', '实验楼601计算机实 验室（一）', '14周'], ['金属矿床地下开采', 6, 5, 8, '李元辉,徐帅,姜海强,安龙,侯朋远,李坤蒙', '实验楼601计算机实验室（一）', '14周'], ['金属矿床露天开采', 2, 3, 4, '王青,胥孝川,顾晓薇,张鹏海,潘济安', '采416', '1-16周'], ['金属矿床露天开采', 5, 3, 4, '王青,胥孝川,顾晓薇,张鹏海,潘济安', '大成102-智慧教室', '1-4周'], ['金属矿床露天开采', 1, 1, 2, '王青,胥孝川,顾晓薇,张鹏海,潘济安', '采416', '9-16周'], ['金属矿床露天开采', 1, 1, 2, '冲突测试', '实验楼601计算机实验室（一）', '13-14周'], ['非金属矿床开发', 1, 5, 6, '韩智勇', '大成408', '1-8周'], ['非金属矿床开发', 3, 3, 4, '韩智勇', '大成404', '5-8周'], ['井巷工程课程设计', 1, 9, 12, '赵兴东', '实验楼603计算机实验室（二）', '11-12周'], ['井巷工程课程设计', 3, 5, 8, '赵兴东', '实验楼605计算机实验室（三）', '15-16周'], ['人工智能基础', 1, 9, 12, '叶柠', '逸101', '1-4周、6-8周'], ['人工智能基础', 1, 9, 12, '叶柠', '机206', '5周'], ['形势与政策(3)', 5, 7, 8, '王宽,何彦彦', '大成205', '7-8周']]
                export_to_aischedule(list_for_csv, termname, campuscode, first_day)
                sys.exit(0)
            else:
                print("无效的选择。")
                input("按回车键重试...")
                print("\033[2J\033[H", end="")

        
    except Exception as e:
        print(colorama.Fore.RED + "程序运行出现预料之外的异常，错误信息：" + str(e))
        input("按回车键退出程序...")
        sys.exit(1)
