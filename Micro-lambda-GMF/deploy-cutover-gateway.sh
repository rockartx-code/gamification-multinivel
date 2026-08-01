#!/usr/bin/env bash
# Cutover final a microlambdas: crea los recursos faltantes en API Gateway ge2omdgk33,
# fija el webhook de Mercado Pago en la config y verifica. Idempotente-ish: si un
# recurso ya existe, el create falla y se reutiliza el id existente.
set -uo pipefail

API=ge2omdgk33
REGION=us-east-1
ACCT=049945345964
ROOT_ID=o4f5pjxkpl
BASE="https://ge2omdgk33.execute-api.us-east-1.amazonaws.com/Prod"

lambda_uri() {
  echo "arn:aws:apigateway:${REGION}:lambda:path/2015-03-31/functions/arn:aws:lambda:${REGION}:${ACCT}:function:$1/invocations"
}

get_res_id() { # $1 = path
  aws apigateway get-resources --rest-api-id $API --region $REGION \
    --query "items[?path=='$1'].id" --output text
}

ensure_resource() { # $1 parent_id, $2 path_part, $3 full_path -> echo id
  local id
  id=$(get_res_id "$3")
  if [ -z "$id" ] || [ "$id" = "None" ]; then
    id=$(aws apigateway create-resource --rest-api-id $API --parent-id "$1" \
      --path-part "$2" --region $REGION --query "id" --output text)
  fi
  echo "$id"
}

wire() { # $1 resource_id, $2 lambda_name
  aws apigateway put-method --rest-api-id $API --resource-id "$1" \
    --http-method ANY --authorization-type NONE --region $REGION >/dev/null 2>&1
  aws apigateway put-integration --rest-api-id $API --resource-id "$1" \
    --http-method ANY --type AWS_PROXY --integration-http-method POST \
    --uri "$(lambda_uri "$2")" --region $REGION >/dev/null
}

echo "== 1. /coupons -> Multinivel-order =="
CUP_ID=$(ensure_resource $ROOT_ID coupons "/coupons")
CUP_PROXY_ID=$(ensure_resource "$CUP_ID" '{proxy+}' '/coupons/{proxy+}')
wire "$CUP_ID" Multinivel-order
wire "$CUP_PROXY_ID" Multinivel-order
aws lambda add-permission --function-name Multinivel-order \
  --statement-id apigw-coupons --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${REGION}:${ACCT}:${API}/*/*/coupons*" \
  --region $REGION 2>/dev/null || echo "(permiso apigw-coupons ya existia)"

echo "== 2. /user-dashboard -> Multinivel-Dashboard =="
UD_ID=$(ensure_resource $ROOT_ID user-dashboard "/user-dashboard")
wire "$UD_ID" Multinivel-Dashboard
aws lambda add-permission --function-name Multinivel-Dashboard \
  --statement-id apigw-user-dashboard --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${REGION}:${ACCT}:${API}/*/*/user-dashboard*" \
  --region $REGION 2>/dev/null || echo "(permiso apigw-user-dashboard ya existia)"

echo "== 3. Desplegar stage Prod =="
aws apigateway create-deployment --rest-api-id $API --stage-name Prod \
  --description "coupons + user-dashboard (cutover microlambdas 2026-08-01)" \
  --region $REGION --query "id" --output text

echo "== 4. Webhook de Mercado Pago en config =="
curl -s -X PUT "$BASE/commissions/config/app" \
  -H "Content-Type: application/json" \
  -H "x-user-id: admin-001" -H "x-user-name: Admin" -H "x-user-role: admin" \
  -d "{\"payments\":{\"mercadoLibre\":{\"notificationUrl\":\"$BASE/webhooks/mercadolibre\"}}}" \
  -o /dev/null -w "PUT config: %{http_code}\n"

echo "== 5. Verificacion =="
sleep 3
curl -s -o /dev/null -w "GET /user-dashboard: %{http_code} (esperado 200/4xx de negocio, NO 403)\n" "$BASE/user-dashboard?userId=1"
curl -s -o /dev/null -w "GET /coupons: %{http_code} (esperado 200/4xx de negocio, NO 403)\n" \
  -H "x-user-id: admin-001" -H "x-user-name: Admin" -H "x-user-role: admin" "$BASE/coupons"
curl -s "$BASE/commissions/config/app" -H "x-user-id: admin-001" -H "x-user-name: Admin" -H "x-user-role: admin" \
  | grep -oE '"notificationUrl": "[^"]*"' | head -1
echo "== Listo =="
