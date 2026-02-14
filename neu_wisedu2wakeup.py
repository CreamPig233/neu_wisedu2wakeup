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
import base64
from Crypto.Cipher import AES
import traceback

urllib3.disable_warnings()
colorama.init(autoreset=True)

session = requests.Session()
session.headers.update({"user-agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'})
using_webvpn = False

def check_network():
    print("正在检查网络连接，请稍等...")
    try:
        response = session.get("http://jwxt.neu.edu.cn", timeout=3)
        if response.status_code == 200:
            print(colorama.Fore.LIGHTBLACK_EX + "内网访问")
            return
        else:
            print(colorama.Fore.RED + "无法访问教务系统, 但这可能不是你的问题. 请稍等片刻后重新打开本程序.")
            print(colorama.Fore.LIGHTBLACK_EX + f"访问状态码: {response.status_code}" + colorama.Style.RESET_ALL)
            input("按回车键退出程序...")
            sys.exit(1)
    except requests.RequestException as e:
        print(colorama.Fore.LIGHTBLACK_EX + "WebVPN访问")
        try:
            response = session.get("https://webvpn.neu.edu.cn", timeout=3)
            if response.status_code == 200:
                global using_webvpn
                using_webvpn = True
                return
            else:
                print(colorama.Fore.RED + "无法访问WebVPN, 但这可能不是你的问题. 请稍等片刻后重新打开本程序.")
                print(colorama.Fore.LIGHTBLACK_EX + f"访问状态码: {response.status_code}" + colorama.Style.RESET_ALL)
                input("按回车键退出程序...")
                sys.exit(1)
        except requests.RequestException as e:
            print(colorama.Fore.RED + "无法访问WebVPN, 请检查你的网络链接后重试.")
            print(colorama.Fore.LIGHTBLACK_EX + f"错误信息：\n" + traceback.format_exc())
            input("按回车键退出程序...")
            sys.exit(1)
        except Exception as e:
            print(colorama.Fore.RED + "无法访问WebVPN, 发生未知错误, 请稍后重试.")
            print(colorama.Fore.LIGHTBLACK_EX + f"错误信息：\n" + traceback.format_exc())
            input("按回车键退出程序...")
            sys.exit(1)
    except Exception as e:
        print(colorama.Fore.RED + "无法访问教务系统, 发生未知错误, 请稍后重试.")
        print(colorama.Fore.LIGHTBLACK_EX + f"错误信息：\n" + traceback.format_exc())
        input("按回车键退出程序...")
        sys.exit(1)

def set_webvpn(url):
    if not using_webvpn:
        return url
    else:
        protocol, url = url.split("://")
        urlroot, urlpath = url.split("/", 1)
        
        if "qyQrLogin" in urlpath:
            urlpath = urlpath + "&service=https://webvpn.neu.edu.cn/login?cas_login=true"
            return protocol + "://" + urlroot + "/" + urlpath
        if "checkQRCodeScan" in urlpath:
            prepath, postpath = urlpath.split("?", 1)
            urlpath = prepath + "?vpn-12-o2-pass.neu.edu.cn&" + postpath
            url = "https://webvpn.neu.edu.cn/https/62304135386136393339346365373340a0e0b72cc4cb43c8bc1d6f66c806db"+ "/" + urlpath
            return url
        
        cipher = AES.new(
            b'b0A58a69394ce73@',
            AES.MODE_CFB,
            b'b0A58a69394ce73@',
            segment_size=128)
        cipher_text = cipher.encrypt(urlroot.ljust(len(urlroot)//16*16+16, '\0').encode())

        res = f'https://webvpn.neu.edu.cn/{protocol}/62304135386136393339346365373340' \
            + cipher_text[:len(urlroot)].hex() + "/" + urlpath
        return res

def neucas_qr_login():
    print(colorama.Fore.YELLOW + "\n请使用微信扫码登录")
    u_uuid = str(uuid.uuid4())
    u_qrurl = f"https://pass.neu.edu.cn/tpass/qyQrLogin?uuid={u_uuid}"
    u_checkurl = f"https://pass.neu.edu.cn/tpass/checkQRCodeScan?random={random.random():.16f}&uuid={u_uuid}"
    qr = qrcode.QRCode()
    qr.add_data(set_webvpn(u_qrurl))
    qr.make(fit=True)
    qr.print_ascii(invert=True)
    print(colorama.Fore.LIGHTBLACK_EX + "无法扫码？使用微信打开链接：" + set_webvpn(u_qrurl))
    input("在微信中点击“授权登录”后请按回车继续...")
    global session, using_webvpn
    if not using_webvpn:
        session.get(u_checkurl)
        session.get("https://pass.neu.edu.cn/tpass/login?service=https%3A%2F%2Fjwxt.neu.edu.cn%2Fjwapp%2Fsys%2Fhomeapp%2Findex.do", allow_redirects=False)
        session.get("https://pass.neu.edu.cn/tpass/login?service=https%3A%2F%2Fjwxt.neu.edu.cn%2Fjwapp%2Fsys%2Fhomeapp%2Findex.do%3FcontextPath%3D%2Fjwapp")
    else:
        session.get("https://webvpn.neu.edu.cn")
        session.headers.update({
            "referer": "https://webvpn.neu.edu.cn/https/62304135386136393339346365373340a0e0b72cc4cb43c8bc1d6f66c806db/tpass/login?service=https%3A%2F%2Fwebvpn.neu.edu.cn%2Flogin%3Fcas_login%3Dtrue",
        })
        session.get(set_webvpn(u_checkurl))
        session.get("https://webvpn.neu.edu.cn/http/62304135386136393339346365373340baf6bc2bc4cb43c8bc1d6f66c806db/jwapp/sys/homeapp/index.do")

def print_welcome():   
    global session
    response = session.get(set_webvpn("https://jwxt.neu.edu.cn/jwapp/sys/homeapp/api/home/currentUser.do"))
    response_json = response.json()
    username = response_json["datas"]["userName"]
    userid = response_json["datas"]["userId"]
    print(f"\n欢迎您，{username} ({userid})！")
    return username

def get_termcode():
    global session
    response = session.get(set_webvpn("https://jwxt.neu.edu.cn/jwapp/sys/homeapp/api/home/currentUser.do"))
    response_json = response.json()
    termcode = response_json["datas"]["welcomeInfo"]["xnxqdm"]
    termname = response_json["datas"]["welcomeInfo"]["xnxqmc"]
    print(f"当前学期为：{termname} ({termcode}) ")
    inputtermcode = input("如需更改学期请输入学期代码 (格式如2025-2026-1), 否则直接回车：")
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
    resp = session.get(set_webvpn(f"https://jwxt.neu.edu.cn/jwapp/sys/homeapp/api/home/student/getMyScheduledCampus.do?termCode={termcode}"))
    campuscode = resp.json()["datas"][0]["id"]
    return campuscode


def convert_arranged_by_WoDeKeBiao(term):

    headers = {
        "origin": "https://webvpn.neu.edu.cn" if using_webvpn else "https://jwxt.neu.edu.cn",
        "Referer": set_webvpn('https://jwxt.neu.edu.cn/jwapp/sys/homeapp/home/index.html?av=&contextPath=/jwapp'),
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
        set_webvpn('https://jwxt.neu.edu.cn/jwapp/sys/homeapp/api/home/student/getMyScheduleDetail.do'),
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
        set_webvpn('https://jwxt.neu.edu.cn/jwapp/sys/homeapp/api/home/student/getMyScheduleDetail.do'),
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
        "origin": "https://webvpn.neu.edu.cn" if using_webvpn else "https://jwxt.neu.edu.cn",
        "Referer": set_webvpn('https://jwxt.neu.edu.cn/jwapp/sys/homeapp/home/index.html?av=&contextPath=/jwapp'),
        "user-agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        "content-type": 'application/x-www-form-urlencoded;charset=UTF-8',
    }


    global session
    response = session.get(
        set_webvpn(f'https://jwxt.neu.edu.cn/jwapp/sys/homeapp/api/home/student/courses.do?termCode={term}'),
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
    resp = session.get(set_webvpn(f"https://jwxt.neu.edu.cn/jwapp/sys/homeapp/api/home/getTermWeeks.do?termCode={termcode}"))
    first_day = resp.json()["datas"][0]["startDate"]
    first_day = datetime.strptime(first_day, "%Y-%m-%d %H:%M:%S")
    first_day = int(first_day.timestamp())*1000
    return first_day

def export_to_aischedule(list_for_csv, termname, campuscode, first_day):
    print(colorama.Fore.YELLOW + "===========警告=============")
    print(colorama.Fore.YELLOW + "导出到小爱课程表属于实验性功能，可能存在导入失败等情况，请谨慎使用！")
    print(colorama.Fore.YELLOW + "当前支持MIUI/HyperOS系统中自带的小爱课程表 与 小爱课程表独立版app")
    print("请仔细阅读下述操作方法，")
    print("1. 打开小爱课程表，(独立版需要登录)，点击右下角头像按钮进入课程表设置")
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
    
    source_miui = False
    source_app = False
    
    try:
        info_userid = debug_info["userId"]
        if info_userid == 0:
            print(colorama.Fore.RED + "userId无效，失败，请检查是否登录。")
            input("按回车键退出程序...")
            sys.exit(-1)
        info_deviceId = debug_info["deviceId"]
        info_authorization = debug_info["authorization"]
        info_useragent = debug_info["userAgent"]
        urlroot = "https://i.xiaomixiaoai.com"
        source_miui = True
        sourceName = "course-app-miui"
        print(colorama.Fore.LIGHTBLACK_EX + "检测来源为系统自带小爱课程表")
    except KeyError:
        try:
            appId = debug_info["appId"]
            serviceToken = debug_info["serviceToken"]
            if serviceToken == "":
                print(colorama.Fore.RED + "serviceToken无效，失败，请检查是否登录。")
                input("按回车键退出程序...")
                sys.exit(-1)
            scope_data = base64.b64encode(json.dumps({"d": debug_info["deviceId"]}).encode("utf-8")).decode("ascii")

            info_authorization = f"AO-TOKEN-V1 dev_app_id:{appId},scope_data:{scope_data},access_token:{serviceToken}"
            urlroot = "https://i.ai.mi.com"
            source_app = True
            sourceName = "course-app-aiSchedule"
            print(colorama.Fore.LIGHTBLACK_EX + "检测来源为小爱课程表独立版app")
        except KeyError:
            print(colorama.Fore.RED + "数据缺失，失败。")
            input("按回车键退出程序...")
            sys.exit(-1)
    
    # 添加课表
    if source_miui:
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "access-control-allow-origin": "true",
            "user-agent": info_useragent,
            "authorization": info_authorization
        }
    if source_app:
        headers = {
            "content-type": "application/json",
            "access-control-allow-origin": "true",
            "authorization": info_authorization
        }
    response = requests.post(
        url=urlroot + "/course-multi-auth/table", 
        headers = headers,
        json={
            "name": termname,
            "current": 0,
            "sourceName": sourceName
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
    if source_miui:
        headers = {
            "content-type": "application/json",
            "user-agent": info_useragent,
            "authorization": info_authorization
        }
    if source_app:
        headers = {
            "content-type": "application/json",
            "access-control-allow-origin": "true",
            "authorization": info_authorization
        }
    response = requests.get(
        url=f"{urlroot}/course-multi-auth/table?ctId={ctId}&sourceName={sourceName}", 
        headers = headers)
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
    
    if source_miui:
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "origin": "https://i.xiaomixiaoai.com",
            "referer": "https://i.xiaomixiaoai.com/h5/precache/ai-schedule/",
            "user-agent": info_useragent,
            "authorization": info_authorization
        }
    if source_app:
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "access-control-allow-origin": "true",
            "authorization": info_authorization
        }
    
    response = requests.put(
        url=f"{urlroot}/course-multi-auth/table", 
        headers=headers, 
        json={
            "ctId": ctId,
            "deviceId": info_deviceId,
            "name":termname,
            "sourceName": sourceName,
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
    print("正在添加课程...")
    if source_miui:
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "origin": "https://i.xiaomixiaoai.com",
            "referer": "https://i.xiaomixiaoai.com/h5/precache/ai-schedule/",
            "user-agent": info_useragent,
            "authorization": info_authorization
        }
    if source_app:
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "access-control-allow-origin": "true",
            "authorization": info_authorization
        }
    url = f"{urlroot}/course-multi-auth/courseInfo?sourceName={sourceName}"
    
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
            "sourceName": sourceName
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
    print(colorama.Fore.YELLOW + "提示：导入后请与教务系统中的课程表进行比对。如存在区别，请以教务系统显示为准！" + colorama.Style.RESET_ALL)
    input("按回车键退出程序...")
        

    
if __name__ == "__main__":
    try:
        
        check_network()
        print("==========使用教程==========")
        print("1.打开程序，仔细阅读并理解本使用教程，而后按回车键继续")
        print("2.使用绑定了东北大学微信企业号的微信扫描程序显示的二维码 (或使用微信打开给出的链接)")
        print("3.扫描二维码，在微信点击授权登录后，在程序中按下回车键，等待运行结束")
        print("4.根据提示选择导出方式，导出课程表")
        print(colorama.Fore.YELLOW + "===========警告=============")
        print(colorama.Fore.YELLOW + "本工具仅提供辅助作用，如果生成的课程表与系统中显示的不一致，请时刻以教务系统中显示的为准！")
        print(colorama.Fore.YELLOW + "本项目已在 https://github.com/CreamPig233/neu_wisedu2wakeup 开源")
        print(colorama.Fore.YELLOW + "请尽量从上方网址处下载最新程序，以免出现问题。")
        print("===========================")
        input("请仔细阅读上述内容后，按回车键继续...")
        neucas_qr_login()
        username = print_welcome()
        termcode, termname = get_termcode()
        campuscode = get_campuscode(termcode)
        print(f"获取{termname} ({termcode}) 课程表中...")
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
            print("1. 导出至csv文件 (导出至WakeUP课程表)")
            print("2. 导出至小爱课程表"+colorama.Fore.YELLOW+" (!实验性功能!) "+colorama.Style.RESET_ALL)
            choice = input("请选择导出方式(输入数字1或2): ")
            if choice == "1":
                with open("schedule.csv", "w", newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(["课程名称", "星期", "开始节数", "结束节数", "老师", "地点", "周数"])
                    writer.writerows(list_for_csv)
                print(colorama.Fore.GREEN + "课程表已成功导出至程序同目录的schedule.csv，请使用WakeUP课程表导入该文件。")
                print("   如何导入? https://wakeup.fun/doc/import_from_csv.html")
                print(colorama.Fore.YELLOW + "提示：导入后请与教务系统中的课程表进行比对。如存在区别，请以教务系统显示为准！" + colorama.Style.RESET_ALL)
                input("按回车键退出程序...")
                sys.exit(0)
            elif choice == "2":
                first_day = get_first_day(termcode)
                export_to_aischedule(list_for_csv, termname, campuscode, first_day)
                sys.exit(0)
            else:
                print("无效的选择。")
                input("按回车键重试...")
                print("\033[2J\033[H", end="")

        
    except Exception as e:
        print(colorama.Fore.RED + "程序运行出现预料之外的异常，错误信息：\n" + traceback.format_exc())
        input("按回车键退出程序...")
        sys.exit(1)
