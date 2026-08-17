import os
from datetime import date

import jwt
import requests
from clickhouse_driver import Client as ClickHouseClient
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

app = FastAPI(title="BionicPRO Reports API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "http://localhost:3000")],
    allow_methods=["GET"],
    allow_headers=["Authorization"],
)

security = HTTPBearer()

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "reports-realm")
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "9000"))

_jwks_cache = None


def get_jwks():
    global _jwks_cache
    if _jwks_cache is None:
        url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
        _jwks_cache = requests.get(url, timeout=10).json()
    return _jwks_cache


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    token = credentials.credentials
    try:
        jwks = get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        key = None
        for k in jwks["keys"]:
            if k["kid"] == unverified_header["kid"]:
                key = jwt.algorithms.RSAAlgorithm.from_jwk(k)
                break
        if key is None:
            raise HTTPException(status_code=401, detail="Invalid token signing key")

        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={"verify_exp": True, "verify_aud": False},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_clickhouse():
    return ClickHouseClient(host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT)


@app.get("/reports")
def get_report(
    user: dict = Depends(get_current_user),
    report_date: date = Query(default=None),
):
    user_id = user.get("sub")
    username = user.get("preferred_username")
    email = user.get("email")

    ch = get_clickhouse()
    empty = {"user_id": user_id, "username": username, "report": []}

    try:
        last_processed = ch.execute(
            "SELECT max(report_date) FROM bionicpro.report_mart"
        )
    except Exception:
        return empty

    max_date = last_processed[0][0] if last_processed and last_processed[0][0] else None

    if report_date and max_date and report_date > max_date:
        raise HTTPException(
            status_code=404,
            detail=f"Данные за {report_date} ещё не обработаны Airflow. "
                   f"Последняя доступная дата: {max_date}",
        )

    query = """
        SELECT
            customer_id, first_name, last_name, email, device_id,
            total_sessions, total_movements,
            avg_response_time_ms, avg_signal_quality, avg_battery_level,
            last_activity, report_date
        FROM bionicpro.report_mart
        WHERE email = %(email)s
    """
    params = {"email": email}

    if report_date:
        query += " AND report_date = %(report_date)s"
        params["report_date"] = report_date

    query += " ORDER BY report_date DESC, device_id"

    rows = ch.execute(query, params)

    return {
        "user_id": user_id,
        "username": username,
        "report": [
            {
                "device_id": r[4],
                "total_sessions": r[5],
                "total_movements": r[6],
                "avg_response_time_ms": round(r[7], 2),
                "avg_signal_quality": round(r[8], 2),
                "avg_battery_level": round(r[9], 2),
                "last_activity": str(r[10]),
                "report_date": str(r[11]),
            }
            for r in rows
        ],
    }
