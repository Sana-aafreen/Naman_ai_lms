from __future__ import annotations

import argparse

from agents.auth import authenticate_and_issue_token


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test MongoDB authentication against employees collection.")
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--user-name", default="")
    parser.add_argument("--password", required=True)
    parser.add_argument("--department", default="")
    args = parser.parse_args()

    result = authenticate_and_issue_token(
        user_id=args.user_id,
        user_name=args.user_name,
        password=args.password,
        department=args.department,
    )

    user = result.get("user", {})
    token = result.get("token", "")
    print("Authenticated:", {k: user.get(k) for k in ("id", "gsheet_uid", "name", "department", "role", "email")})
    print("Token (first 32):", token[:32] + ("..." if len(token) > 32 else ""))


if __name__ == "__main__":
    main()

