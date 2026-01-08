import csv
import uuid
import requests
from requests.packages import urllib3
import random
import qrcode

urllib3.disable_warnings()

session = requests.Session()

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




def get_schedule(campuscode, term):

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
    # print(response.text)
    # print(response.content.decode('utf-8'))

    schedule_json = response.json()
    schedule_list = schedule_json["datas"]
    return schedule_list


def convert_arranged(schedule_list):
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
            placeName = i.split(" ")[-1]
            if placeName.endswith("校区"):
                placeName = "暂未安排教室"
            
            append_list.append(courseName)
            append_list.append(dayOfWeek)
            append_list.append(beginSection)
            append_list.append(endSection)
            append_list.append(teachers)
            append_list.append(placeName)
            append_list.append(week.replace(",","、").replace("(","").replace(")",""))
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
    neucas_qr_login()
    print_welcome()
    termcode = get_termcode()
    campuscode = get_campuscode(termcode)
    print(f"获取{termcode}课程表中...")
    schedule_list = get_schedule(campuscode, termcode)
    list_for_csv = convert_arranged(schedule_list)
    print(list_for_csv)
    input("课程表已保存至schedule.csv，按回车键退出程序。")
