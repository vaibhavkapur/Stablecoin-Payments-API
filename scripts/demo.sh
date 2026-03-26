#!/usr/bin/env bash
# Demo script: walks through the full payment lifecycle
# Requires: curl, jq, and the API running on localhost:8000

set -euo pipefail
BASE="http://localhost:8000"

echo "=== Stablecoin Payments API Demo ==="
echo ""

# 1. Create API key
echo "1. Creating API key..."
API_KEY=$(curl -s -X POST "$BASE/v1/admin/api_keys" | jq -r '.api_key')
echo "   API Key: $API_KEY"
echo ""

H="X-API-Key: $API_KEY"

# 2. Create Alice (customer)
echo "2. Creating customer (Alice)..."
ALICE=$(curl -s -X POST "$BASE/v1/customers" \
  -H "$H" -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com"}')
ALICE_ID=$(echo "$ALICE" | jq -r '.id')
echo "   Customer ID: $ALICE_ID"
echo ""

# 3. Create merchant
echo "3. Creating merchant..."
MERCHANT=$(curl -s -X POST "$BASE/v1/customers" \
  -H "$H" -H "Content-Type: application/json" \
  -d '{"email": "merchant@shop.com"}')
MERCHANT_ID=$(echo "$MERCHANT" | jq -r '.id')
echo "   Merchant ID: $MERCHANT_ID"
echo ""

# 4. Create wallet for Alice
echo "4. Creating wallet for Alice..."
WALLET=$(curl -s -X POST "$BASE/v1/wallets" \
  -H "$H" -H "Content-Type: application/json" \
  -d "{\"customer_id\": \"$ALICE_ID\", \"chain\": \"base-sepolia\"}")
WALLET_ID=$(echo "$WALLET" | jq -r '.id')
WALLET_ADDR=$(echo "$WALLET" | jq -r '.address')
echo "   Wallet ID: $WALLET_ID"
echo "   Address: $WALLET_ADDR"
echo ""

# 5. Create wallet for merchant
echo "5. Creating wallet for merchant..."
MWALLET=$(curl -s -X POST "$BASE/v1/wallets" \
  -H "$H" -H "Content-Type: application/json" \
  -d "{\"customer_id\": \"$MERCHANT_ID\", \"chain\": \"base-sepolia\"}")
echo "   Merchant wallet: $(echo "$MWALLET" | jq -r '.id')"
echo ""

# 6. Deposit 100 USD for Alice
echo "6. Creating deposit (100 USD)..."
DEPOSIT=$(curl -s -X POST "$BASE/v1/deposits" \
  -H "$H" -H "Content-Type: application/json" \
  -d "{\"customer_id\": \"$ALICE_ID\", \"amount_usd\": \"100.00\"}")
DEP_ID=$(echo "$DEPOSIT" | jq -r '.id')
echo "   Deposit ID: $DEP_ID (status: $(echo "$DEPOSIT" | jq -r '.status'))"
echo ""

# 7. Confirm deposit
echo "7. Confirming deposit..."
CONFIRMED=$(curl -s -X POST "$BASE/v1/deposits/$DEP_ID/confirm" -H "$H")
echo "   Status: $(echo "$CONFIRMED" | jq -r '.status')"
echo ""

# 8. Check balance
echo "8. Checking Alice's balance..."
BALANCE=$(curl -s "$BASE/v1/balances/$ALICE_ID" -H "$H")
echo "   $BALANCE" | jq '.balances'
echo ""

# 9. Transfer 20 USDC
echo "9. Transferring 20 USDC to external address..."
TRANSFER=$(curl -s -X POST "$BASE/v1/transfers" \
  -H "$H" -H "Content-Type: application/json" \
  -d "{\"wallet_id\": \"$WALLET_ID\", \"recipient_address\": \"0xdeadbeef1234567890abcdef1234567890abcdef\", \"amount_usdc\": \"20.00\"}")
TR_ID=$(echo "$TRANSFER" | jq -r '.id')
echo "   Transfer ID: $TR_ID"
echo "   Status: $(echo "$TRANSFER" | jq -r '.status')"
echo "   Tx Hash: $(echo "$TRANSFER" | jq -r '.tx_hash')"
echo ""

# 10. Confirm transfer
echo "10. Confirming transfer on-chain..."
TR_CONF=$(curl -s -X POST "$BASE/v1/transfers/$TR_ID/confirm" -H "$H")
echo "   Status: $(echo "$TR_CONF" | jq -r '.status')"
echo ""

# 11. Merchant checkout
echo "11. Creating payment intent (15 USDC)..."
PI=$(curl -s -X POST "$BASE/v1/payment_intents" \
  -H "$H" -H "Content-Type: application/json" \
  -d "{\"merchant_id\": \"$MERCHANT_ID\", \"amount\": \"15.00\", \"currency\": \"USDC\"}")
PI_ID=$(echo "$PI" | jq -r '.id')
echo "   Payment Intent ID: $PI_ID"
echo "   Client Secret: $(echo "$PI" | jq -r '.client_secret')"
echo ""

# 12. Confirm payment
echo "12. Confirming payment..."
PI_CONF=$(curl -s -X POST "$BASE/v1/payment_intents/$PI_ID/confirm" \
  -H "$H" -H "Content-Type: application/json" \
  -d "{\"customer_id\": \"$ALICE_ID\"}")
echo "   Status: $(echo "$PI_CONF" | jq -r '.status')"
echo ""

# 13. Final balances
echo "13. Final balances..."
echo "   Alice:"
curl -s "$BASE/v1/balances/$ALICE_ID" -H "$H" | jq '.balances'
echo "   Merchant:"
curl -s "$BASE/v1/balances/$MERCHANT_ID" -H "$H" | jq '.balances'
echo ""

# 14. Webhook events
echo "14. Recent webhook events:"
curl -s "$BASE/v1/webhooks/events" -H "$H" | jq '.[].event_type'
echo ""

# 15. Reconciliation
echo "15. Running reconciliation..."
curl -s "$BASE/v1/admin/reconciliation" -H "$H" | jq '.'
echo ""

# 16. Ledger summary
echo "16. Ledger summary:"
curl -s "$BASE/v1/admin/ledger_summary" -H "$H" | jq '.accounts'
echo ""

echo "=== Demo complete ==="
