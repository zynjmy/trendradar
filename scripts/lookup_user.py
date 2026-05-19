"""Fetch DingTalk user IDs by mobile number.

Usage (run from project root):
  set DINGTALK_APP_KEY=xxx
  set DINGTALK_APP_SECRET=xxx
  set DINGTALK_AGENT_ID=xxx
  python scripts/lookup_user.py 13812345678

This prints the userId string you need for DINGTALK_USER_IDS.
"""

import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from notifier.dingtalk import _get_access_token


def lookup_by_mobile(access_token: str, mobile: str) -> str:
    """Get DingTalk userId by mobile number."""
    resp = requests.post(
        "https://oapi.dingtalk.com/topapi/v2/user/getbymobile",
        params={"access_token": access_token},
        json={"mobile": mobile},
        timeout=15,
    )
    data = resp.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"查询失败: {data.get('errmsg', data)}")
    return data["result"]["userid"]


def main():
    if len(sys.argv) < 2:
        print("用法: python scripts/lookup_user.py <手机号>")
        sys.exit(1)

    mobile = sys.argv[1]
    app_key = os.environ["DINGTALK_APP_KEY"]
    app_secret = os.environ["DINGTALK_APP_SECRET"]

    token = _get_access_token(app_key, app_secret)
    userid = lookup_by_mobile(token, mobile)
    print(f"\n手机号: {mobile}")
    print(f"userId:  {userid}")
    print(f"\n在 GitHub Secrets 中设置: DINGTALK_USER_IDS = {userid}")


if __name__ == "__main__":
    main()
