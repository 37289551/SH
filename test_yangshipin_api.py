#!/usr/bin/env python3
"""
测试央视频EPG API接口
"""

import requests
import json
from datetime import datetime, timezone, timedelta

# 测试频道: CCTV-1
pid = '600001859'
date_str = '20260311'

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Referer': f'https://yangshipin.cn/tv/home?pid={pid}',
    'Origin': 'https://yangshipin.cn'
}

api_list = [
    # 基于app.js分析的真实API
    ('https://capi.yangshipin.cn/api/yspepg/program/list', {'cid': pid, 'date': date_str}, 'capi yspepg list (GET)'),
    ('https://capi.yangshipin.cn/api/yspepg/program/get', {'cid': pid, 'date': date_str}, 'capi yspepg get (GET)'),
    ('https://appdevteamtest.yangshipin.cn/api/yspepg/program/list', {'cid': pid, 'date': date_str}, '测试环境 yspepg list'),
    ('https://precapi.yangshipin.cn/api/yspepg/program/list', {'cid': pid, 'date': date_str}, '预发布环境 yspepg list'),
    # 备用推测接口
    ('https://api.yangshipin.cn/content/api/channel/getEpgInfo', {'pid': pid, 'date': date_str}, 'getEpgInfo'),
    ('https://api.yangshipin.cn/content/channel/programList', {'pid': pid, 'date': date_str}, 'programList'),
    ('https://api.cctv.com/api/epg/epginfo', {'serviceId': 'tvcctv', 'c': pid, 'd': date_str, 't': 'json'}, 'cctv epginfo'),
]

print("=" * 80)
print("央视频 EPG API 测试")
print(f"频道: CCTV-1 (pid={pid})")
print(f"日期: {date_str}")
print("=" * 80)

for url, params, name in api_list:
    print(f"\n[{name}]")
    print(f"URL: {url}")
    print(f"参数: {params}")

    try:
        # 测试GET请求
        response = requests.get(url, params=params, headers=headers, timeout=10)
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            try:
                data = response.json()
                print(f"响应结构: {json.dumps(list(data.keys()), ensure_ascii=False)}")

                # 查找节目数据
                if 'data' in data:
                    print(f"  data 类型: {type(data['data'])}")
                    if isinstance(data['data'], dict):
                        print(f"  data keys: {list(data['data'].keys())}")
                        if 'programList' in data['data']:
                            print(f"  ✓ 找到 programList，共 {len(data['data']['programList'])} 个节目")
                            if data['data']['programList']:
                                print(f"  第一个节目: {json.dumps(data['data']['programList'][0], ensure_ascii=False)}")
                    elif isinstance(data['data'], list):
                        print(f"  ✓ data是列表，共 {len(data['data'])} 项")
                        if data['data']:
                            print(f"  第一个节目: {json.dumps(data['data'][0], ensure_ascii=False)}")

                elif 'programList' in data:
                    print(f"  ✓ 找到 programList，共 {len(data['programList'])} 个节目")
                    if data['programList']:
                        print(f"  第一个节目: {json.dumps(data['programList'][0], ensure_ascii=False)}")

                elif isinstance(data, list):
                    print(f"  ✓ 响应是列表，共 {len(data)} 项")
                    if data:
                        print(f"  第一个节目: {json.dumps(data[0], ensure_ascii=False)}")

                elif 'list' in data:
                    print(f"  ✓ 找到 list，共 {len(data['list'])} 个节目")
                    if data['list']:
                        print(f"  第一个节目: {json.dumps(data['list'][0], ensure_ascii=False)}")

                else:
                    print(f"  响应: {json.dumps(data, ensure_ascii=False)[:500]}")

            except json.JSONDecodeError as e:
                print(f"JSON解析失败: {e}")
                print(f"响应内容: {response.text[:500]}")
        else:
            print(f"响应: {response.text[:200]}")

    except Exception as e:
        print(f"错误: {e}")

# POST测试
print("\n" + "=" * 80)
print("POST 接口测试")
print("=" * 80)

post_apis = [
    ('https://capi.yangshipin.cn/api/yspepg/program/list', {'cid': pid, 'date': date_str}, 'capi yspepg list (POST)'),
]

for url, data, name in post_apis:
    print(f"\n[{name}]")
    print(f"URL: {url}")
    print(f"数据: {data}")

    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            try:
                result = response.json()
                print(f"响应结构: {json.dumps(list(result.keys()), ensure_ascii=False)}")

                # 查找节目数据
                if 'data' in result:
                    print(f"  data 类型: {type(result['data'])}")
                    if isinstance(result['data'], dict):
                        print(f"  data keys: {list(result['data'].keys())}")
                        if 'dataList' in result['data']:
                            print(f"  ✓ 找到 dataList，共 {len(result['data']['dataList'])} 个节目")
                            if result['data']['dataList']:
                                print(f"  第一个节目: {json.dumps(result['data']['dataList'][0], ensure_ascii=False)}")

                print(f"完整响应: {json.dumps(result, ensure_ascii=False)[:500]}")
            except json.JSONDecodeError as e:
                print(f"JSON解析失败: {e}")
                print(f"响应内容: {response.text[:500]}")
        else:
            print(f"响应: {response.text[:200]}")
    except Exception as e:
        print(f"错误: {e}")

print("\n" + "=" * 80)
