"""DingTalk notification — work notices (IM) + group webhook fallback.

方案B (首选): 工作通知, 推送到个人 IM 窗口, 需要:
  DINGTALK_APP_KEY      企业应用 AppKey
  DINGTALK_APP_SECRET   企业应用 AppSecret
  DINGTALK_AGENT_ID     企业应用 AgentId
  DINGTALK_USER_IDS     推送目标, 逗号分隔的 DingTalk userId

方案A (回退): 群机器人 webhook, 需要:
  DINGTALK_WEBHOOK_URL  机器人 Webhook 地址
  DINGTALK_SECRET       机器人签名密钥 (可选)
"""

import base64
import hashlib
import hmac
import os
import time
import urllib.parse

import requests

# ── Classic DingTalk Open API ──────────────────────────────────────────────
TOKEN_URL = "https://oapi.dingtalk.com/gettoken"
WORK_NOTICE_URL = "https://oapi.dingtalk.com/topapi/message/corpconversation/asyncsend_v2"


def _get_access_token(app_key: str, app_secret: str) -> str:
    resp = requests.get(
        TOKEN_URL,
        params={"appkey": app_key, "appsecret": app_secret},
        timeout=15,
    )
    data = resp.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"获取 access_token 失败: {data.get('errmsg', data)}")
    return data["access_token"]


# ── 方案B: 工作通知 (推送到个人) ─────────────────────────────────────────

def send_via_work_notice(title: str, text: str) -> bool:
    """通过钉钉工作通知推送到指定用户的个人 IM。

    Env vars:
      DINGTALK_APP_KEY
      DINGTALK_APP_SECRET
      DINGTALK_AGENT_ID
      DINGTALK_USER_IDS
    """
    app_key = os.environ.get("DINGTALK_APP_KEY", "")
    app_secret = os.environ.get("DINGTALK_APP_SECRET", "")
    agent_id = os.environ.get("DINGTALK_AGENT_ID", "")
    user_ids_str = os.environ.get("DINGTALK_USER_IDS", "")

    missing = []
    if not app_key:     missing.append("DINGTALK_APP_KEY")
    if not app_secret:  missing.append("DINGTALK_APP_SECRET")
    if not agent_id:    missing.append("DINGTALK_AGENT_ID")
    if not user_ids_str: missing.append("DINGTALK_USER_IDS")
    if missing:
        raise RuntimeError(f"工作通知配置不完整, 缺少: {', '.join(missing)}")

    user_ids = [uid.strip() for uid in user_ids_str.split(",") if uid.strip()]
    if not user_ids:
        raise RuntimeError("DINGTALK_USER_IDS 为空")

    token = _get_access_token(app_key, app_secret)

    payload = {
        "agent_id": int(agent_id),
        "userid_list": ",".join(user_ids),
        "msg": {
            "msgtype": "markdown",
            "markdown": {"title": title, "text": text},
        },
    }

    resp = requests.post(
        WORK_NOTICE_URL,
        params={"access_token": token},
        json=payload,
        timeout=15,
    )
    data = resp.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"发送失败: {data.get('errmsg', data)}")
    print(f"  工作通知已发送 → {len(user_ids)} 位用户")
    return True


# ── 方案A: 群机器人 webhook (保留作为回退) ────────────────────────────────

def _sign_url(webhook_url: str, secret: str) -> str:
    ts = str(round(time.time() * 1000))
    sign = base64.b64encode(
        hmac.new(
            secret.encode("utf-8"),
            f"{ts}\n{secret}".encode("utf-8"),
            hashlib.sha256,
        ).digest()
    ).decode("utf-8")
    return f"{webhook_url}&timestamp={ts}&sign={urllib.parse.quote(sign)}"


def send_via_webhook(webhook_url: str, title: str, text: str) -> bool:
    """通过群机器人 webhook 推送到群聊。"""
    secret = os.environ.get("DINGTALK_SECRET", "")
    url = _sign_url(webhook_url, secret) if secret else webhook_url

    payload = {
        "msgtype": "markdown",
        "markdown": {"title": title, "text": text},
    }

    resp = requests.post(url, json=payload, timeout=15)
    data = resp.json()
    if data.get("errcode") != 0:
        raise RuntimeError(f"Webhook 发送失败: {data.get('errmsg', data)}")
    print("  Webhook 已发送到群聊")
    return True


# ── 统一入口 ──────────────────────────────────────────────────────────────

def send(title: str, text: str) -> bool:
    """自动选择推送方式: 工作通知 > 群机器人 webhook。

    Raises RuntimeError if nothing is configured.
    """
    if os.environ.get("DINGTALK_APP_KEY"):
        return send_via_work_notice(title, text)

    webhook = os.environ.get("DINGTALK_WEBHOOK_URL", "")
    if webhook:
        return send_via_webhook(webhook, title, text)

    raise RuntimeError(
        "未配置任何钉钉推送方式。请设置:\n"
        "  方案B (工作通知): DINGTALK_APP_KEY / APP_SECRET / AGENT_ID / USER_IDS\n"
        "  方案A (群机器人): DINGTALK_WEBHOOK_URL"
    )
