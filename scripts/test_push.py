# -*- coding: utf-8 -*-
"""Quick test: verify DingTalk work notification setup.

Usage (run from project root in a Windows CMD/PowerShell terminal):
  set DINGTALK_APP_KEY=ding5rniln1uxmwaytpl
  set DINGTALK_APP_SECRET=<your new secret>
  set DINGTALK_AGENT_ID=4595577348
  set DINGTALK_USER_IDS=<your userId>
  python scripts/test_push.py

Never paste secrets into chat or commit them.
"""

import os
import sys

# Fix Windows console encoding for emoji
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from notifier.dingtalk import _get_access_token, send_via_work_notice  # noqa: E402


def main():
    app_key = os.environ.get("DINGTALK_APP_KEY")
    app_secret = os.environ.get("DINGTALK_APP_SECRET")
    agent_id = os.environ.get("DINGTALK_AGENT_ID")
    user_ids = os.environ.get("DINGTALK_USER_IDS")

    print("=" * 50)
    print("Step 1: Check environment variables")

    for name, val in [
        ("DINGTALK_APP_KEY", app_key),
        ("DINGTALK_APP_SECRET", "***" if app_secret else None),
        ("DINGTALK_AGENT_ID", agent_id),
        ("DINGTALK_USER_IDS", user_ids),
    ]:
        ok = "[OK]" if val else "[MISSING]"
        display = val if name != "DINGTALK_APP_SECRET" else "***"
        print(f"  {ok}  {name} = {display}")

    if not all([app_key, app_secret, agent_id, user_ids]):
        print("\nPlease set all environment variables first.")
        print("Run these commands in CMD before re-running:")
        print("  set DINGTALK_APP_KEY=ding5rniln1uxmwaytpl")
        print("  set DINGTALK_APP_SECRET=<your new AppSecret>")
        print("  set DINGTALK_AGENT_ID=4595577348")
        print("  set DINGTALK_USER_IDS=<your userId>")
        sys.exit(1)

    # Step 2: test access token
    print("\nStep 2: Get access_token ...")
    try:
        token = _get_access_token(app_key, app_secret)
        print(f"  [OK] access_token acquired ({len(token)} chars)")
    except Exception as e:
        print(f"  [FAIL] {e}")
        sys.exit(1)

    # Step 3: send test message
    print("\nStep 3: Send test message ...")
    try:
        send_via_work_notice(
            title="TrendRadar Test",
            text=(
                "## Test OK\n\n"
                "If you see this, DingTalk work notice is configured correctly.\n\n"
                "---\n"
                "> From TrendRadar"
            ),
        )
        print("  [OK] Test message sent. Check DingTalk 'Work Notice' tab.")
    except Exception as e:
        print(f"  [FAIL] {e}")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("All checks passed. Ready to configure GitHub Secrets.")


if __name__ == "__main__":
    main()
