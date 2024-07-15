import json
import requests
import re
import urllib3
import ssl
import sys
import random
from requests import ConnectionError,ReadTimeout
from bs4 import BeautifulSoup

# Ignore warning
urllib3.disable_warnings()
# Ignore ssl warning info.
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    # Legacy Python that doesn't verify HTTPS certificates by default
    pass
else:
    # Handle target environment that doesn't support HTTPS verification
    ssl._create_default_https_context = _create_unverified_https_context

def get_logo(app_num,finger_num):
    print("""

██╗    ██╗ █████╗ ██╗   ██╗
██║    ██║██╔══██╗╚██╗ ██╔╝
██║ █╗ ██║███████║ ╚████╔╝ 
██║███╗██║██╔══██║  ╚██╔╝  
╚███╔███╔╝██║  ██║   ██║   
 ╚══╝╚══╝ ╚═╝  ╚═╝   ╚═╝   W(ho) a(re) y(ou)? 
  _ Powered by Leonardo.
  _ Version_1.0.0               

 |  支持产品  |  %s   |
 |  指纹数量  |  %s  |
""" % (app_num,finger_num)
)

def random_str(num):
    return ''.join(random.sample(['z','y','x','w','v','u','t','s','r','q','p','o','n','m','l','k','j','i','h','g','f','e','d','c','b','a','1','2','3','4','5','6','7','8','9','0'], num))

def get_title(htmlcode):
    """
    获取网站title  

    use:
    get_title(html_source)  

    return:  
    title  
    """
    soup = BeautifulSoup(htmlcode, 'html.parser')

    end = str(soup.title).find("</title>")
    title = str(soup.title)[7:end] + "<title>"

    return title

def get_finger_rules():
    with open("data/FingerRule.json") as f:
        finger_rules = f.read()
    return json.loads(finger_rules)

def update_finger_rules(new_finger):
    """
    考虑到脚本中已经多次出现对指纹库的更新和保存操作了，每次都重写一遍也挺麻烦的，因此决定把这个操作函数化
    接收一个参数：new_finger 新指纹库
    """
    with open("data/FingerRule.json", "w+", encoding='utf-8') as f:
        json.dump(new_finger,   # 待写入数据
                f, # File对象
                indent=2,  # 空格缩进符，写入多行
                sort_keys=True,  # 键的排序
                ensure_ascii=False)  # 显示中文

def get_app_info():
    with open("data/AppInfo.json") as f:
        app_info = f.read()
    return json.loads(app_info)

def simple_http_req(url):
    try:
        req = requests.get(url=url,verify=False,timeout=20)

        headers = req.headers
        title = get_title(req.text)
        body = req.text

        return headers,title,body
    except (ConnectionError,ReadTimeout):
        return False


rtitle = re.compile(r'title="(.*)"')
rheader = re.compile(r'header="(.*)"')
rbody = re.compile(r'body="(.*)"')
result = []
todo_url = [] # 计划将来扫描过程中遇到的没有命中任何指纹的url就存放在这里，等扫描完了我就专门去处理这些url，拿到平台去做对比测试，写新的规则

def rule_verify(rule,title,header,body,type):
    header = header # {'Connection': 'close', 'Content-Type': 'text/html; charset=utf-8', 'Date': 'Fri, 30 Dec 2022 02:00:30 GMT', 'Server': 'nginx'}
    if type == "str":
        if "title=\"" in rule:
            if re.findall(rtitle,rule)[0].lower() in title.lower():
                return True
        elif "body=\"" in rule:
            if re.findall(rbody,rule)[0] in body: 
                return True
        elif "header=\"" in rule:
            rule = re.findall(rheader,rule)[0]
            if ": " in rule:
                key,value = rule.split(": ")
                keys = [key.lower() for key in header.keys()]
                if key.lower() in keys and value.lower() in header[key].lower():
                    return True
            else:
                for head in header:
                    if rule.lower() in header[head].lower():
                        return True
    else:
        if "title=\"" in rule:
            reg = re.findall(rtitle,rule)[0]
            if re.search(r'' + reg,title,re.I):
                return True
        elif "body=\"" in rule:
            reg = re.findall(rbody,rule)[0]
            if re.search(r'' + reg,body,re.I):
                return True
        elif "header=\"" in rule:
            reg = re.findall(rheader,rule)[0]
            if ": " in reg:
                key,value = reg.split(": ")
                keys = [key.lower() for key in header.keys()]
                if key.lower() in keys:
                    new_header = {}
                    for k in header:
                        new_header.update({k.lower(): header[k]})
                    if re.search(r'' + value,new_header[key.lower()],re.I):
                        return True
            else:
                for head in header:
                    if re.search(r'' + reg,header[head],re.I):
                        return True
    return False

def handle_once(finger_rules,headers,title,body):
    hit = False
    for i in range(len(finger_rules)):
        rule = finger_rules[i]["rule"]
        if "&&" in rule:
            num = 0
            rules = rule.split(" && ")
            for subrule in rules:
                if rule_verify(subrule,title=title,header=headers,body=body,type=finger_rules[i]["type"]) == True:
                    num += 1

            if num == len(rules):
                hit = True
                print("[*] 命中 %s 规则，Token：%s" % (finger_rules[i]["name"],finger_rules[i]["token"]))
                result.append(
                    {
                        "url":url,
                        "name":finger_rules[i]["name"],
                        "rule":rule
                    }
                )
                finger_rules[i]["hit"] += 1
                # break
        else:
            if rule_verify(rule=rule,title=title,header=headers,body=body,type=finger_rules[i]["type"]):
                hit = True
                print("[*] 命中 %s 规则，Token：%s" % (finger_rules[i]["name"],finger_rules[i]["token"]))
                result.append(
                    {
                        "url":url,
                        "name":finger_rules[i]["name"],
                        "rule":rule
                    }
                )
                finger_rules[i]["hit"] += 1
                # break
    if hit == False:
        print("[!] 未命中任何指纹")
    return finger_rules,hit

if len(sys.argv) == 1:
    app_info = get_app_info()
    finger_rule = get_finger_rules()
    get_logo(str(len(app_info)),str(len(finger_rule)))
else:
    if sys.argv[1] in ["-u","-f"]:
        if sys.argv[1] == "-u":
            urls = [sys.argv[2]]
        else:
            with open(sys.argv[2].strip()) as f:
                urls = [i.strip() for i in f.readlines()]

        url_num = 0
        finger_rules = get_finger_rules()
        app_infos = get_app_info()

        for url in urls:
            url_num += 1
            print("[%d/%d]  |  current task: %s" % (url_num,len(urls),url))
            try:
                headers,title,body = simple_http_req(url)
            except:
                print("[!] %s 不可达" % url)
                continue
            finger_rules,hit = handle_once(finger_rules=finger_rules,headers=headers,title=title,body=body)
            todo_url.append(url) if hit == False else ""

        update_finger_rules(finger_rules)

        if len(urls) > 1:
            with open("report.txt","w+") as f:
                for i in result:
                    f.write("目标：%s  |  命中：%s  |  规则：%s\n" % (i["url"],i["name"],i["rule"]))
            with open("todo_url.txt","w+") as f:
                for i in todo_url:
                    f.write(i + "\n")
    if sys.argv[1] == "--debug":
        rule = "header=\"x-Powered-By: asp\\.NET\""
        type = "reg"
        url = "http://shx.huel.edu.cn"

        try:
            headers,title,body = simple_http_req(url)
            # body = "jquery-1.2.min.js"
            # headers = "server: ngx_openresty"
        except:
            print("[!] %s 不可达" % url)
            sys.exit()

        rules = []
        if " && " in rule:
            for i in rule.split(" && "):
                rules.append(i)
        else:
            rules = [rule]

        flag = 0

        for i in rules:
            if rule_verify(i,title=title,header=headers,body=body,type=type):
                print("[*] 规则  %s  匹配成功" % i)
                flag += 1
            else:
                print("[*] 规则  %s  匹配失败" % i)
        if flag == len(rules):
            print("[*] 恭喜，规则完全匹配！")
        else:
            print("[*] 很抱歉，规则不完全匹配！")
            if input("是否需要输出目标相应页面（是：y/Y，否：会车）：").lower() == "y":
                print("[*] Body部分：\n%s\n" % body)

                print("[*] Header部分：\n")
                for i in headers:
                    print("%s: %s" % (i,headers[i]))

                print("[*] Title部分：\n%s\n" % title)

    if sys.argv[1] == "--addrule":
        name = input("请输入产品名称：")
        rule = input("请输入指纹规则(不要转义！)：")
        type = "reg" if input("请输入指纹类型(str/reg)：") == "reg" else "str"  # 默认是str，即关键字匹配的形式
        finger_rules = get_finger_rules()
        for i in range(len(finger_rules)):
            if finger_rules[i]["name"] == name and finger_rules[i]["rule"] == rule:
                print("[*] 规则重复，请确认后再添加")
                sys.exit()
        token = random_str(9)
        new_rule = {
            "name": name,
            "rule": rule,
            "type": type,
            "hit": 0,
            "example": "",
            "token": token
        }
        finger_rules.append(new_rule)
        update_finger_rules(finger_rules)
        print("[*] 规则添加成功，token：" + token)