#!/usr/bin/env python3
"""
PushPlus WeChat Push Script
=============================
将智能情报通过 PushPlus 推送到微信

用法:
  python pushplus_wechat.py --token YOUR_TOKEN --title "标题" --content "内容"

支持渠道: wechat(微信), dingtalk, feishu, mail, bark, sms
支持模板: html, json, markdown, text
"""
import argparse
import json
import sys
import urllib.parse
import urllib.request

PUSHPLUS_URL = "https://www.pushplus.plus/send"

def push(token: str, title: str, content: str,
         channel: str = "wechat",
         template: str = "markdown") -> dict:
    """推送消息到 PushPlus"""
    data = {
        "token": token,
        "title": title,
        "content": content,
        "channel": channel,
        "template": template
    }

    json_data = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        PUSHPLUS_URL,
        data=json_data,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result
    except Exception as e:
        return {"code": -1, "msg": str(e)}

def main():
    p = argparse.ArgumentParser(description="PushPlus WeChat Push")
    p.add_argument("--token", "-t", required=True, help="PushPlus Token")
    p.add_argument("--title", required=True, help="消息标题")
    p.add_argument("--content", "-c", required=True, help="消息内容")
    p.add_argument("--channel", default="wechat",
                   choices=["wechat","dingtalk","feishu","mail","bark","sms"],
                   help="推送渠道 (默认: wechat)")
    p.add_argument("--template", default="markdown",
                   choices=["html","json","markdown","text"],
                   help="消息模板 (默认: markdown)")

    args = p.parse_args()

    result = push(args.token, args.title, args.content, args.channel, args.template)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result.get("code") == 200:
        print("PushPlus: SUCCESS")
        sys.exit(0)
    else:
        print(f"PushPlus: FAILED - {result.get('msg')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
