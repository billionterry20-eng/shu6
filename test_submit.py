#!/usr/bin/env python3
"""
步数提交测试脚本
"""

import requests

API_URL = "http://8.140.250.130/king/api/step"

# 使用用户提供的有效 token
AUTH_TOKEN = "5aa77abb20f11a5e7f2440747a655a55"
TIME_TOKEN = "1772274234275"

# 账号信息
PHONE = "Tbh2356@163.com"
PASSWORD = "112233qq"
STEPS = 89888


def submit_steps():
    """提交步数"""
    headers = {
        "Host": "8.140.250.130",
        "Accept": "*/*",
        "Authorization": AUTH_TOKEN,
        "X-Requested-With": "XMLHttpRequest",
        "time": TIME_TOKEN,
        "Accept-Language": "zh-TW,zh-Hant;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "http://8.140.250.130",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1",
        "Referer": "http://8.140.250.130/bushu/",
        "Connection": "keep-alive"
    }
    
    data = {
        "phone": PHONE,
        "pwd": PASSWORD,
        "num": str(STEPS)
    }
    
    try:
        print(f"正在提交: 账号={PHONE}, 步数={STEPS}")
        print(f"使用 Token: {AUTH_TOKEN[:20]}...")
        
        response = requests.post(API_URL, headers=headers, data=data, timeout=30)
        result = response.json()
        
        print(f"\n响应: {result}")
        
        if result.get('code') == 200 and result.get('msg') == 'success':
            print("\n✅ 提交成功！")
            return True
        else:
            print(f"\n❌ 提交失败: {result.get('data', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"\n❌ 请求错误: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("步数提交测试")
    print("=" * 60)
    print()
    
    submit_steps()
