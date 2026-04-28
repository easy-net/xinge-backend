#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000/}"
# BASE_URL="${BASE_URL:-https://api.xgt.news/}"
LOGIN_CODE="${LOGIN_CODE:-replace-with-wx-login-code1}"
SYSTEM_VERSION="${SYSTEM_VERSION:-iOS 17.0}"
DEVICE_UUID="${DEVICE_UUID:-device-001}"
DEV_AUTH_BYPASS="${DEV_AUTH_BYPASS:-false}"

DISTRIBUTOR_ID="${DISTRIBUTOR_ID:-100}"
PHONE_CODE="${PHONE_CODE:-replace-with-phone-code1}"
SCHOOL_NAME="${SCHOOL_NAME:-北京大学}"
REPORT_ID="${REPORT_ID:-101}"
ORDER_ID="${ORDER_ID:-ORD1234567890}"
MESSAGE_ID="${MESSAGE_ID:-1001}"
NOTIFY_ID="${NOTIFY_ID:-notify-001}"

action="${1:-help}"

require_private_auth() {
  if [[ "${LOGIN_CODE}" == "replace-with-wx-login-code" ]]; then
    echo "LOGIN_CODE is required for private endpoints"
    exit 1
  fi
}

json_get() {
  local json_input="$1"
  local path="$2"
  JSON_INPUT="${json_input}" python3 - "$path" <<'PY'
import json
import os
import sys

path = sys.argv[1].split(".")
data = json.loads(os.environ["JSON_INPUT"])
cur = data
for key in path:
    if key.isdigit():
        cur = cur[int(key)]
    else:
        cur = cur[key]

if isinstance(cur, bool):
    print("true" if cur else "false")
elif cur is None:
    print("null")
else:
    print(cur)
PY
}

private_headers=(
  -H "Content-Type: application/json"
  -H "X-Login-Code: ${LOGIN_CODE}"
  -H "X-System-Version: ${SYSTEM_VERSION}"
  -H "X-Device-UUID: ${DEVICE_UUID}"
)

public_headers=(
  -H "Content-Type: application/json"
)

curl_public_json() {
  local path="$1"
  local body="$2"
  printf '%s' "${body}" | curl -sS -X POST "${BASE_URL}${path}" "${public_headers[@]}" --data-binary @-
}

curl_private_json() {
  local path="$1"
  local body="$2"
  require_private_auth
  printf '%s' "${body}" | curl -sS -X POST "${BASE_URL}${path}" "${private_headers[@]}" --data-binary @-
}

print_json() {
  local payload="$1"
  echo "${payload}"
  echo
}

show_help() {
  cat <<'EOF'
Usage:
  BASE_URL=https://your-domain LOGIN_CODE=xxx ./scripts/curl-demo.sh <action>

Core env vars:
  BASE_URL
  LOGIN_CODE
  SYSTEM_VERSION
  DEVICE_UUID
  DEV_AUTH_BYPASS

Optional env vars:
  DISTRIBUTOR_ID
  PHONE_CODE
  SCHOOL_NAME
  REPORT_ID
  ORDER_ID
  MESSAGE_ID
  NOTIFY_ID

Actions:
  healthz
  readyz
  product_config
  schools_list
  schools_detail
  login
  login_with_distributor
  bind_phone
  me
  update_me
  create_report
  reports_list
  report_detail
  report_status
  report_links
  create_order
  order_detail
  notify_wechat
  messages_list
  messages_unread
  messages_read
  public_smoke
  user_smoke
  report_smoke
  all_smoke
  full_flow
EOF
}

run_full_flow() {
  require_private_auth

  echo "== login =="
  local login_resp
  login_resp="$(curl_private_json "/api/v1/mp/auth/login" '{}')"
  print_json "${login_resp}"

  echo "== create report =="
  local create_report_resp
  create_report_resp="$(curl_private_json "/api/v1/mp/reports" "$(cat <<'JSON'
{
  "name": "张三",
  "school_name": "北京大学",
  "college_name": "信息科学技术学院",
  "major_name": "计算机科学与技术",
  "gender": "男",
  "gaokao_province": "广东",
  "gaokao_score": 620,
  "gaokao_rank": 5000,
  "enrollment_year": 2021,
  "chinese_score": 115,
  "math_score": 140,
  "english_score": 130,
  "physics_score": 85,
  "chemistry_score": 80,
  "biology_score": 75,
  "english_level": "CET-6",
  "hukou": "广东广州",
  "major_satisfaction": "一般满意",
  "employment_intention": ["名企大厂"],
  "study_intention": "一定要升",
  "study_path_priority": ["国内读研"],
  "target_major": ["软件工程"],
  "target_work_city": ["北京"],
  "notes": "对数据方向感兴趣"
}
JSON
)")"
  print_json "${create_report_resp}"

  local flow_report_id
  flow_report_id="$(json_get "${create_report_resp}" "data.report_id")"
  echo "report_id=${flow_report_id}"
  echo

  echo "== create order =="
  local create_order_resp
  create_order_resp="$(curl_private_json "/api/v1/mp/orders" "$(cat <<JSON
{
  "report_id": ${flow_report_id},
  "amount": 9900
}
JSON
)")"
  print_json "${create_order_resp}"

  local flow_order_id
  flow_order_id="$(json_get "${create_order_resp}" "data.order_id")"
  echo "order_id=${flow_order_id}"
  echo

  echo "== notify wechat =="
  local notify_resp
  notify_resp="$(curl_public_json "/api/v1/mp/orders/notify/wechat" "$(cat <<JSON
{
  "notify_id": "${NOTIFY_ID}",
  "order_id": "${flow_order_id}",
  "amount": 9900,
  "status": "success",
  "paid_at": "2026-04-25T10:00:00Z"
}
JSON
)")"
  print_json "${notify_resp}"

  echo "== order detail =="
  print_json "$(curl_private_json "/api/v1/mp/orders/detail" "$(cat <<JSON
{
  "order_id": "${flow_order_id}"
}
JSON
)")"

  echo "== report status =="
  print_json "$(curl_private_json "/api/v1/mp/reports/status" "$(cat <<JSON
{
  "report_id": ${flow_report_id}
}
JSON
)")"

  echo "== report links =="
  print_json "$(curl_private_json "/api/v1/mp/reports/links" "$(cat <<JSON
{
  "report_id": ${flow_report_id}
}
JSON
)")"
}

case "${action}" in
  help)
    show_help
    ;;

  healthz)
    curl -sS "${BASE_URL}/healthz"
    echo
    ;;

  readyz)
    curl -sS "${BASE_URL}/readyz"
    echo
    ;;

  product_config)
    print_json "$(curl_public_json "/api/v1/mp/config/product" '{}')"
    ;;

  schools_list)
    print_json "$(curl_public_json "/api/v1/mp/schools/list" '{
  "keyword": "北京",
  "city": "北京",
  "is_985": true,
  "page": 1,
  "page_size": 20
}')"
    ;;

  schools_detail)
    print_json "$(curl_public_json "/api/v1/mp/schools/detail" "$(cat <<JSON
{
  "school_name": "${SCHOOL_NAME}"
}
JSON
)")"
    ;;

  login)
    print_json "$(curl_private_json "/api/v1/mp/auth/login" '{}')"
    ;;

  login_with_distributor)
    print_json "$(curl_private_json "/api/v1/mp/auth/login" "$(cat <<JSON
{
  "distributor_id": ${DISTRIBUTOR_ID}
}
JSON
)")"
    ;;

  bind_phone)
    if [[ "${PHONE_CODE}" == "replace-with-phone-code" ]]; then
      echo "PHONE_CODE is required for bind_phone"
      exit 1
    fi
    print_json "$(curl_private_json "/api/v1/mp/auth/bind-phone" "$(cat <<JSON
{
  "phone_code": "${PHONE_CODE}"
}
JSON
)")"
    ;;

  me)
    print_json "$(curl_private_json "/api/v1/mp/users/me" '{}')"
    ;;

  update_me)
    print_json "$(curl_private_json "/api/v1/mp/users/me/update" '{
  "nickname": "张三",
  "avatar_url": "https://example.com/avatar.png"
}')"
    ;;

  create_report)
    print_json "$(curl_private_json "/api/v1/mp/reports" '{
  "name": "张三",
  "school_name": "北京大学",
  "college_name": "信息科学技术学院",
  "major_name": "计算机科学与技术",
  "gender": "男",
  "gaokao_province": "广东",
  "gaokao_score": 620,
  "gaokao_rank": 5000,
  "enrollment_year": 2021,
  "chinese_score": 115,
  "math_score": 140,
  "english_score": 130,
  "physics_score": 85,
  "chemistry_score": 80,
  "biology_score": 75,
  "english_level": "CET-6",
  "hukou": "广东广州",
  "major_satisfaction": "一般满意",
  "employment_intention": ["名企大厂"],
  "study_intention": "一定要升",
  "study_path_priority": ["国内读研"],
  "target_major": ["软件工程"],
  "target_work_city": ["北京"],
  "notes": "对数据方向感兴趣"
}')"
    ;;

  reports_list)
    print_json "$(curl_private_json "/api/v1/mp/reports/list" '{
  "page": 1,
  "page_size": 20
}')"
    ;;

  report_detail)
    print_json "$(curl_private_json "/api/v1/mp/reports/detail" "$(cat <<JSON
{
  "report_id": ${REPORT_ID}
}
JSON
)")"
    ;;

  report_status)
    print_json "$(curl_private_json "/api/v1/mp/reports/status" "$(cat <<JSON
{
  "report_id": ${REPORT_ID}
}
JSON
)")"
    ;;

  report_links)
    print_json "$(curl_private_json "/api/v1/mp/reports/links" "$(cat <<JSON
{
  "report_id": ${REPORT_ID}
}
JSON
)")"
    ;;

  create_order)
    print_json "$(curl_private_json "/api/v1/mp/orders" "$(cat <<JSON
{
  "report_id": ${REPORT_ID},
  "amount": 9900
}
JSON
)")"
    ;;

  order_detail)
    print_json "$(curl_private_json "/api/v1/mp/orders/detail" "$(cat <<JSON
{
  "order_id": "${ORDER_ID}"
}
JSON
)")"
    ;;

  notify_wechat)
    print_json "$(curl_public_json "/api/v1/mp/orders/notify/wechat" "$(cat <<JSON
{
  "notify_id": "${NOTIFY_ID}",
  "order_id": "${ORDER_ID}",
  "amount": 9900,
  "status": "success",
  "paid_at": "2026-04-25T10:00:00Z"
}
JSON
)")"
    ;;

  messages_list)
    print_json "$(curl_private_json "/api/v1/mp/messages/list" '{
  "page": 1,
  "page_size": 20
}')"
    ;;

  messages_unread)
    print_json "$(curl_private_json "/api/v1/mp/messages/list" '{
  "page": 1,
  "page_size": 20,
  "is_read": false
}')"
    ;;

  messages_read)
    print_json "$(curl_private_json "/api/v1/mp/messages/read" "$(cat <<JSON
{
  "message_id": ${MESSAGE_ID}
}
JSON
)")"
    ;;

  public_smoke)
    curl -sS "${BASE_URL}/healthz"
    echo
    curl -sS "${BASE_URL}/readyz"
    echo
    print_json "$(curl_public_json "/api/v1/mp/config/product" '{}')"
    print_json "$(curl_public_json "/api/v1/mp/schools/list" '{
  "keyword": "北京",
  "page": 1,
  "page_size": 20
}')"
    print_json "$(curl_public_json "/api/v1/mp/schools/detail" "$(cat <<JSON
{
  "school_name": "${SCHOOL_NAME}"
}
JSON
)")"
    ;;

  user_smoke)
    print_json "$(curl_private_json "/api/v1/mp/auth/login" '{}')"
    print_json "$(curl_private_json "/api/v1/mp/users/me" '{}')"
    print_json "$(curl_private_json "/api/v1/mp/users/me/update" '{
  "nickname": "张三",
  "avatar_url": "https://example.com/avatar.png"
}')"
    print_json "$(curl_private_json "/api/v1/mp/messages/list" '{
  "page": 1,
  "page_size": 20
}')"
    ;;

  report_smoke)
    print_json "$(curl_private_json "/api/v1/mp/reports/list" '{
  "page": 1,
  "page_size": 20
}')"
    print_json "$(curl_private_json "/api/v1/mp/reports/detail" "$(cat <<JSON
{
  "report_id": ${REPORT_ID}
}
JSON
)")"
    print_json "$(curl_private_json "/api/v1/mp/orders" "$(cat <<JSON
{
  "report_id": ${REPORT_ID},
  "amount": 9900
}
JSON
)")"
    print_json "$(curl_private_json "/api/v1/mp/orders/detail" "$(cat <<JSON
{
  "order_id": "${ORDER_ID}"
}
JSON
)")"
    print_json "$(curl_private_json "/api/v1/mp/reports/status" "$(cat <<JSON
{
  "report_id": ${REPORT_ID}
}
JSON
)")"
    print_json "$(curl_private_json "/api/v1/mp/reports/links" "$(cat <<JSON
{
  "report_id": ${REPORT_ID}
}
JSON
)")"
    ;;

  all_smoke)
    curl -sS "${BASE_URL}/healthz"
    echo
    curl -sS "${BASE_URL}/readyz"
    echo
    print_json "$(curl_public_json "/api/v1/mp/config/product" '{}')"
    print_json "$(curl_public_json "/api/v1/mp/schools/list" '{
  "keyword": "北京",
  "page": 1,
  "page_size": 20
}')"
    print_json "$(curl_public_json "/api/v1/mp/schools/detail" "$(cat <<JSON
{
  "school_name": "${SCHOOL_NAME}"
}
JSON
)")"
    print_json "$(curl_private_json "/api/v1/mp/auth/login" '{}')"
    print_json "$(curl_private_json "/api/v1/mp/users/me" '{}')"
    print_json "$(curl_private_json "/api/v1/mp/reports/list" '{
  "page": 1,
  "page_size": 20
}')"
    print_json "$(curl_private_json "/api/v1/mp/messages/list" '{
  "page": 1,
  "page_size": 20
}')"
    ;;

  full_flow)
    run_full_flow
    ;;

  *)
    echo "Unknown action: ${action}"
    echo
    show_help
    exit 1
    ;;
esac
