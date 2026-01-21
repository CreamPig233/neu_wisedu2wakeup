import csv
import uuid
import requests
from requests.packages import urllib3
import random
import qrcode
import re

urllib3.disable_warnings()

session = requests.Session()

def check_network():
    try:
        response = session.get("http://jwxt.neu.edu.cn", timeout=5)
        if response.status_code == 200:
            return
        else:
            print("无法访问教务系统，请连接校园网或OpenVPN后重试。")
            input("按回车键退出程序...")
            exit(1)
    except requests.RequestException:
        print("无法访问教务系统，请连接校园网或OpenVPN后重试。")
        input("按回车键退出程序...")
        exit(1)

def neucas_qr_login():
    print("请使用微信扫码登录")
    u_uuid = str(uuid.uuid4())
    u_qrurl = f"https://pass.neu.edu.cn/tpass/qyQrLogin?uuid={u_uuid}"
    u_checkurl = f"https://pass.neu.edu.cn/tpass/checkQRCodeScan?random={random.random():.16f}&uuid={u_uuid}"
    qr = qrcode.QRCode()
    qr.add_data(u_qrurl)
    qr.make(fit=True)
    qr.print_ascii(invert=True)
    input("手机端确认登录后请按回车继续...")
    global session
    session.get(u_checkurl)
    session.get("https://pass.neu.edu.cn/tpass/login?service=https%3A%2F%2Fjwxt.neu.edu.cn%2Fjwapp%2Fsys%2Fhomeapp%2Findex.do", allow_redirects=False)
    session.get("https://pass.neu.edu.cn/tpass/login?service=https%3A%2F%2Fjwxt.neu.edu.cn%2Fjwapp%2Fsys%2Fhomeapp%2Findex.do%3FcontextPath%3D%2Fjwapp")




def convert_arranged_by_WoDeKeBiao(campuscode, term):

    headers = {
        'Host': 'jwxt.neu.edu.cn',
        "Referer": 'https://jwxt.neu.edu.cn/jwapp/sys/homeapp/home/index.html?av=&contextPath=/jwapp',
        "user-agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
        "content-type": 'application/x-www-form-urlencoded;charset=UTF-8',
    }

    data = {
        'termCode': term,
        'campusCode': campuscode,
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


    with open("schedule.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(["课程名称", "星期", "开始节数", "结束节数", "老师", "地点", "周数"])
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
    
    with open("schedule.csv", "a") as f:
        writer = csv.writer(f)
        writer.writerows(list_for_csv)
        
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
    # print(response.text)
    # print(response.content.decode('utf-8'))

    schedule_json = response.json()
    schedule_list = schedule_json["datas"]


    with open("schedule.csv", "w") as f:
        writer = csv.writer(f)
        writer.writerow(["课程名称", "星期", "开始节数", "结束节数", "老师", "地点", "周数"])
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
    
    with open("schedule.csv", "a") as f:
        writer = csv.writer(f)
        writer.writerows(list_for_csv)
        
    return list_for_csv


def get_termcode():
    global session
    response = session.get("https://jwxt.neu.edu.cn/jwapp/sys/homeapp/api/home/currentUser.do")
    response_json = response.json()
    termcode = response_json["datas"]["welcomeInfo"]["xnxqdm"]
    print("当前学期为：", termcode)
    inputtermcode = input("如需更改学期请输入学期代码（格式如2025-2026-1），否则直接回车：")
    if inputtermcode != "":
        codes = inputtermcode.split("-")
        if len(codes) != 3:
            print("学期代码格式错误，使用默认学期")
        elif codes[2] not in ["1", "2", "3"]:
            print("学期代码格式错误，使用默认学期")
        elif int(codes[0]) + 1 != int(codes[1]):
            print("学期代码格式错误，使用默认学期")
        else:
            termcode = inputtermcode
        
    return termcode

def get_campuscode(termcode):
    global session
    resp = session.get(f"https://jwxt.neu.edu.cn/jwapp/sys/homeapp/api/home/student/getMyScheduledCampus.do?termCode={termcode}")
    campuscode = resp.json()["datas"][0]["id"]
    return campuscode
    
def print_welcome():   
    global session
    response = session.get("https://jwxt.neu.edu.cn/jwapp/sys/homeapp/api/home/currentUser.do")
    response_json = response.json()
    username = response_json["datas"]["userName"]
    userid = response_json["datas"]["userId"]
    print(f"欢迎您，{username} ({userid})！")
    
if __name__ == "__main__":
    print("==========使用教程==========")
    print("1.打开程序，使用绑定了东北大学微信企业号的微信扫描程序显示的二维码")
    print("2.扫描二维码，在微信点击授权登录后，在程序中按下回车键，等待运行结束")
    print("3.在程序同目录找到schedule.csv，使用WakeUP课程表导入该文件。")
    print("   如何导入? https://wakeup.fun/doc/import_from_csv.html")
    print("===========警告=============")
    print("本工具仅提供辅助作用，如果生成的课程表与系统中显示的不一致，请时刻以教务系统中显示的为准！")
    print("本项目已在 https://github.com/CreamPig233/neu_wisedu2wakeup 开源")
    print("===========================")
    try:
        check_network()
        neucas_qr_login()
        print_welcome()
        termcode = get_termcode()
        campuscode = get_campuscode(termcode)
        print(f"获取{termcode}课程表中...")
        try:
            list_for_csv = convert_arranged_by_WoDeKeBiao(campuscode, termcode)
        except Exception as e:
            print("使用“我的课表”模块获取课程表失败")
            print("错误信息：", str(e))
            print("尝试使用“我的课程”模块获取课程表...")

            try:
                list_for_csv = convert_arranged_by_WoDeKeCheng(termcode)
            except Exception as e2:
                print("使用“我的课程”模块获取课程表失败")
                print("错误信息：", str(e2))
                input("课程表获取失败，按回车键退出程序...")
                exit(1)
        print(list_for_csv)
        input("课程表已保存至schedule.csv，按回车键退出程序...")
    except Exception as e:
        print("程序运行出现预料之外的异常，错误信息：", str(e))
        input("按回车键退出程序...")
        exit(1)
