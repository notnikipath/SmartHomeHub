from __future__ import annotations

import json
import urllib.request

BASE = "http://localhost:8580"


def request(method: str, path: str, payload: dict | None = None) -> dict:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    challenge = request("POST", "/auth/challenge/start", {"user_id": "USR-OWNER-1", "password": "owner123"})
    token = request("POST", "/auth/challenge/verify", {"challenge_id": challenge["challenge_id"], "otp_code": "123456"})

    command = request(
        "POST",
        "/workflow/process-command",
        {
            "user_id": "USR-OWNER-1",
            "home_id": "HOME-DEMO",
            "source": "voice",
            "command_text": "turn off living room light",
            "actor_role": "owner",
        },
    )

    print(json.dumps({"token": token, "command": command}, ensure_ascii=False, indent=2))