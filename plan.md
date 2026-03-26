# Stablecoin Payments API — Development Plan

## 1. Project goal

Build a **Stripe-like Stablecoin Payments API** that lets a developer:

- create a customer
- create a wallet
- simulate a USD deposit
- credit the user with USDC
- send USDC to another wallet
- simulate merchant checkout
- track transaction lifecycle
- emit webhooks
- maintain a proper internal ledger

This project should feel like a miniature version of:

- Stripe
- Circle
- PayPal Crypto

---

## 2. Product vision

At a high level, the system should support this flow:

1. A user account is created.
2. A wallet is created for that user.
3. The user “deposits USD” into the platform.
4. The platform credits the user with USDC.
5. The user sends USDC to another wallet or pays a merchant.
6. The backend tracks every state transition.
7. Webhooks notify downstream systems of events.

This is not just a blockchain demo. It is a **payments infrastructure project**.

---

## 3. Architecture overview

Think in terms of four layers.

### Layer A: API Layer
This is the external interface for developers and merchants.

Example endpoints:

- `POST /v1/customers`
- `POST /v1/wallets`
- `POST /v1/deposits`
- `POST /v1/transfers`
- `POST /v1/payment_intents`
- `GET /v1/transactions/{id}`
- `POST /v1/webhooks/test`

### Layer B: Payments Orchestration Layer
This contains the core business logic:

- create wallets
- manage balances
- reserve funds
- build and submit transfers
- reconcile state
- emit webhooks
- confirm payments

### Layer C: Ledger Layer
This is the heart of the system.

The ledger should be the source of truth for balances, not the wallet provider.

Track:

- customer balances
- merchant balances
- available funds
- reserved funds
- platform fees
- treasury balances

### Layer D: Chain Integration Layer
This talks to external crypto infrastructure.

Suggested options:

- Coinbase Developer Platform managed wallets
- Base Sepolia testnet
- Ethereum Sepolia as optional expansion
- self-managed signing later if desired

---

## 4. Recommended tech stack

### Backend
- **Python + FastAPI**

### Database
- **PostgreSQL**

### ORM
- **SQLAlchemy**

### Queue / async jobs
- **Celery** or a lightweight worker

### Cache / broker
- **Redis**

### Chain integration
- Coinbase CDP SDK, or lower-level EVM tooling later

### Frontend (optional)
- simple React / Next.js checkout page
- admin dashboard for deposits, transfers, and webhook logs

### Local infra
- Docker Compose

Why this stack:

- FastAPI is fast to build with
- Python is strong for orchestration, risk logic, reconciliation, and jobs
- Postgres is ideal for ledgers and transactional systems
- Redis helps with workers, retries, and caching

---

## 5. Project phases

### Phase 1: Core entities
Build:

- customer creation
- wallet creation
- ledger account creation
- basic database schema
- auth scaffolding

### Phase 2: Internal ledger
Build:

- double-entry journal posting
- account balance computation
- support for available and reserved balances
- idempotent transaction posting

### Phase 3: Simulated USD deposit
Build:

- `POST /v1/deposits`
- pending → completed lifecycle
- internal USD/USDC crediting logic
- admin endpoint to confirm deposits

### Phase 4: On-chain USDC transfers
Build:

- `POST /v1/transfers`
- reserve funds before submission
- submit testnet USDC transaction
- persist tx hash
- background confirmation polling

### Phase 5: Merchant checkout simulation
Build:

- `POST /v1/payment_intents`
- hosted checkout page
- confirm payment
- merchant crediting
- optional platform fee deduction

### Phase 6: Webhooks
Build:

- event generation
- signed webhooks
- retry logic
- webhook event log table

### Phase 7: Reconciliation and observability
Build:

- balance verification jobs
- mismatch detection
- transaction dashboard
- replay tools for failed webhooks

---

## 6. Data model

## 6.1 Customers

### `customers`
- `id`
- `email`
- `external_ref`
- `created_at`

Purpose:
Represents the end user or merchant customer in your system.

---

## 6.2 Wallets

### `wallets`
- `id`
- `customer_id`
- `provider`
- `chain`
- `address`
- `wallet_provider_id`
- `created_at`

Purpose:
Stores the blockchain wallet associated with the customer.

Example provider values:

- `cdp`
- `local`

Example chain values:

- `base-sepolia`
- `ethereum-sepolia`

---

## 6.3 Ledger accounts

### `payment_accounts`
- `id`
- `customer_id` (nullable)
- `type`
- `currency`
- `created_at`

Examples of `type`:

- `customer_usdc_available`
- `customer_usdc_reserved`
- `customer_usd`
- `merchant_usdc`
- `platform_fee`
- `treasury_usdc`
- `bank_clearing_usd`

Purpose:
Each balance bucket should be modeled explicitly.

---

## 6.4 Ledger journals and entries

### `journals`
- `id`
- `reference_type`
- `reference_id`
- `description`
- `idempotency_key`
- `created_at`

### `ledger_entries`
- `id`
- `journal_id`
- `account_id`
- `direction`
- `amount`
- `currency`
- `created_at`

Purpose:
Implements double-entry accounting.

Important:
Every journal must balance.

---

## 6.5 Deposits

### `deposits`
- `id`
- `customer_id`
- `amount_usd`
- `status`
- `reference`
- `created_at`
- `completed_at`

Possible status values:

- `pending`
- `completed`
- `failed`

Purpose:
Represents a fiat deposit request into your system.

---

## 6.6 Transfers

### `transfers`
- `id`
- `sender_wallet_id`
- `recipient_address`
- `amount_usdc`
- `status`
- `chain`
- `tx_hash`
- `failure_reason`
- `created_at`
- `submitted_at`
- `confirmed_at`

Possible status values:

- `created`
- `submitted`
- `pending_confirmation`
- `confirmed`
- `failed`

Purpose:
Tracks outbound USDC transfers.

---

## 6.7 Payment intents

### `payment_intents`
- `id`
- `merchant_id`
- `customer_id`
- `amount`
- `currency`
- `status`
- `recipient_address`
- `metadata`
- `created_at`
- `confirmed_at`

Possible status values:

- `requires_payment_method`
- `processing`
- `succeeded`
- `failed`

Purpose:
Represents a Stripe-like merchant checkout object.

---

## 6.8 Webhook events

### `webhook_events`
- `id`
- `event_type`
- `payload`
- `delivery_status`
- `retry_count`
- `last_attempt_at`
- `created_at`

Purpose:
Tracks event delivery lifecycle for merchant integrations.

---

## 7. Ledger design

Do not skip the ledger.

A real payments system must track money movement with explicit debits and credits.

## 7.1 Rule
Every money movement should create a journal with balanced entries.

## 7.2 Example: simulated USD deposit
User deposits **100 USD** and receives **100 USDC** in your platform.

### Journal A: fiat deposit received
- Debit: `bank_clearing_usd` = 100
- Credit: `customer_usd` = 100

### Journal B: conversion to USDC
- Debit: `customer_usd` = 100
- Credit: `customer_usdc_available` = 100

For the demo, assume:
- `1 USD = 1 USDC`

## 7.3 Example: internal transfer
Alice sends Bob **25 USDC** internally.

- Debit: `alice_usdc_available` = 25
- Credit: `bob_usdc_available` = 25

## 7.4 Example: merchant checkout with fee
Customer pays merchant **100 USDC**, platform takes **2 USDC** fee.

- Debit: `customer_usdc_available` = 100
- Credit: `merchant_usdc` = 98
- Credit: `platform_fee` = 2

## 7.5 Example: reserve funds before transfer
Before chain submission, move user funds from available to reserved.

- Debit: `customer_usdc_available` = 25
- Credit: `customer_usdc_reserved` = 25

On success, consume reserved balance.
On failure, release it back.

---

## 8. Wallet strategy

You have two options.

## Option A: Managed wallets
Use Coinbase Developer Platform or similar wallet infrastructure.

Advantages:
- easier to ship
- avoids deep custody complexity early
- lets you focus on payments orchestration and API design

Recommended for V1.

## Option B: Self-managed wallets
Generate keys and sign transactions yourself.

Advantages:
- deeper technical understanding
- stronger custody architecture story

Disadvantages:
- more security and operational work

Recommended for V2, after the main system is working.

---

## 9. Network strategy

### Primary network for V1
- **Base Sepolia**

Why:
- EVM-compatible
- relevant to current stablecoin builders
- cheap and easy for testnet experiments

### Optional secondary network
- **Ethereum Sepolia**

Use this later to demonstrate chain abstraction.

---

## 10. API design

## 10.1 Create customer

### `POST /v1/customers`

Request:
```json
{
  "email": "alice@example.com"
}
```

Response:
```json
{
  "id": "cus_123",
  "email": "alice@example.com",
  "created_at": "2026-03-26T12:00:00Z"
}
```

---

## 10.2 Create wallet

### `POST /v1/wallets`

Request:
```json
{
  "customer_id": "cus_123",
  "chain": "base-sepolia"
}
```

Response:
```json
{
  "id": "wal_123",
  "address": "0xabc...",
  "chain": "base-sepolia"
}
```

---

## 10.3 Create deposit

### `POST /v1/deposits`

Request:
```json
{
  "customer_id": "cus_123",
  "amount_usd": "100.00"
}
```

Response:
```json
{
  "id": "dep_123",
  "status": "pending"
}
```

---

## 10.4 Confirm deposit

### `POST /v1/deposits/{id}/confirm`

Behavior:
- mark deposit as completed
- create ledger journals
- credit user internal USDC balance
- optionally trigger testnet USDC transfer to wallet

---

## 10.5 Create transfer

### `POST /v1/transfers`

Request:
```json
{
  "wallet_id": "wal_123",
  "recipient_address": "0xdef...",
  "amount_usdc": "25.00"
}
```

Response:
```json
{
  "id": "tr_123",
  "status": "submitted",
  "tx_hash": "0x..."
}
```

---

## 10.6 Create payment intent

### `POST /v1/payment_intents`

Request:
```json
{
  "merchant_id": "merch_123",
  "customer_id": "cus_123",
  "amount": "10.00",
  "currency": "USDC",
  "capture_method": "automatic"
}
```

---

## 10.7 Confirm payment intent

### `POST /v1/payment_intents/{id}/confirm`

Behavior:
- validate funding
- debit customer balance
- credit merchant balance
- optionally create on-chain transfer
- emit success webhook

---

## 10.8 Retrieve transaction

### `GET /v1/transactions/{id}`

Return:
- transaction status
- ledger references
- tx hash
- timestamps
- chain data
- webhook data if relevant

---

## 11. Deposit flow design

The deposit flow should evolve in steps.

## V1: fully simulated fiat
1. User requests a deposit.
2. Deposit is recorded as `pending`.
3. Admin or a worker confirms the deposit.
4. Ledger credits customer with USDC.

This gives you the operational lifecycle without requiring banking rails.

## V2: simulated mint to wallet
After deposit completion:
1. trigger a testnet USDC transfer from treasury wallet
2. store tx hash
3. confirm via polling worker

## V3: real provider-backed rails
Later, you can explore actual on/off-ramp providers.

For the portfolio version, V1 + V2 is enough.

---

## 12. Transfer flow design

This is the most important system flow.

### Request path
1. Client calls `POST /v1/transfers`
2. Validate wallet ownership
3. Validate available balance
4. Create transfer record
5. Reserve funds
6. Submit chain transaction
7. Store tx hash
8. Poll for confirmation
9. Finalize or reverse reservation

### Why reserve first
This protects against:
- retries
- duplicate requests
- partial failures
- race conditions

### Recommended balance model
Maintain separate balances:
- `available`
- `reserved`

---

## 13. Merchant checkout simulation

This is what makes the project feel product-grade.

## 13.1 Merchant creates checkout
Merchant calls:
- `POST /v1/payment_intents`

System returns:
- payment intent ID
- client secret
- checkout URL

## 13.2 Hosted checkout page
Build a simple page showing:
- merchant name
- amount
- token/currency
- destination
- fee breakdown
- “Pay now” button

## 13.3 Confirm payment
When user clicks pay:
- validate customer funding
- debit customer balance
- credit merchant balance
- emit `payment_intent.processing`
- then emit `payment_intent.succeeded`

Optional:
- also settle externally on-chain

---

## 14. Webhook system

Webhooks are mandatory for this project.

## 14.1 Events to emit
Suggested event types:

- `deposit.pending`
- `deposit.completed`
- `transfer.submitted`
- `transfer.confirmed`
- `transfer.failed`
- `payment_intent.created`
- `payment_intent.processing`
- `payment_intent.succeeded`

## 14.2 Webhook payload example
```json
{
  "id": "evt_123",
  "type": "payment_intent.succeeded",
  "created": "2026-03-26T14:00:00Z",
  "data": {
    "object": {
      "id": "pi_123",
      "amount": "10.00",
      "currency": "USDC",
      "status": "succeeded"
    }
  }
}
```

## 14.3 Best practices
Implement:
- HMAC signatures
- retries with backoff
- delivery logging
- manual replay
- timestamp verification

---

## 15. Blockchain transaction tracking

A background worker should monitor all non-terminal transactions.

## 15.1 Status lifecycle
Suggested normalized statuses:

- `created`
- `submitted`
- `pending_confirmation`
- `confirmed`
- `failed`

## 15.2 Polling worker behavior
For each transfer:
1. find transfers not in terminal state
2. fetch tx receipt
3. if successful, mark confirmed
4. if reverted, mark failed
5. update confirmations and metadata

## 15.3 Store metadata
Track:
- `tx_hash`
- `block_number`
- `confirmations`
- `gas_used`
- `effective_fee`
- `failure_reason`

---

## 16. Reconciliation

This is a major differentiator.

Build jobs that compare:
- internal expected balances
- on-chain actual balances

## Example reconciliation check
If treasury wallet should hold `10,000 USDC` internally but on-chain it only has `9,975`, surface that mismatch.

Possible causes:
- failed transfer handling
- missing journal
- manual wallet movement
- worker bug

Expose mismatches in an admin page or logs.

---

## 17. Security requirements

Even for a portfolio project, build this cleanly.

## 17.1 Auth
- JWT/session auth for end users
- API keys for merchants/admin integrations

## 17.2 Request safety
- idempotency keys on money-moving endpoints
- request validation with Pydantic
- server-side authorization checks

## 17.3 Secret management
- never hardcode secrets
- store private credentials in environment variables or a vault

## 17.4 Auditability
- store request IDs
- store actor identity
- log journal references for every money movement

## 17.5 Balance integrity
Never trust client-side balances.
Balance must come from:
- ledger computation, or
- a balance snapshot table derived from ledger entries

---

## 18. Suggested folder structure

```text
stablecoin-payments-api/
├── app/
│   ├── api/
│   │   ├── customers.py
│   │   ├── wallets.py
│   │   ├── deposits.py
│   │   ├── transfers.py
│   │   ├── payment_intents.py
│   │   └── webhooks.py
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── database.py
│   ├── models/
│   │   ├── customer.py
│   │   ├── wallet.py
│   │   ├── account.py
│   │   ├── journal.py
│   │   ├── deposit.py
│   │   ├── transfer.py
│   │   ├── payment_intent.py
│   │   └── webhook_event.py
│   ├── schemas/
│   │   ├── customer.py
│   │   ├── wallet.py
│   │   ├── deposit.py
│   │   ├── transfer.py
│   │   └── payment_intent.py
│   ├── services/
│   │   ├── ledger_service.py
│   │   ├── wallet_service.py
│   │   ├── deposit_service.py
│   │   ├── transfer_service.py
│   │   ├── payment_service.py
│   │   ├── webhook_service.py
│   │   └── reconciliation_service.py
│   ├── workers/
│   │   ├── transfer_status_worker.py
│   │   ├── webhook_retry_worker.py
│   │   └── reconciliation_worker.py
│   └── main.py
├── migrations/
├── scripts/
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 19. Endpoint-by-endpoint implementation order

Use this order.

### Step 1
- `POST /v1/customers`
- `POST /v1/wallets`

### Step 2
- create ledger accounts for each customer automatically

### Step 3
- `POST /v1/deposits`
- `POST /v1/deposits/{id}/confirm`

### Step 4
- `GET /v1/balances/{customer_id}`

### Step 5
- `POST /v1/transfers`

### Step 6
- background worker for transfer confirmation

### Step 7
- `POST /v1/payment_intents`
- `POST /v1/payment_intents/{id}/confirm`

### Step 8
- webhook event generation and delivery

### Step 9
- admin dashboard / simple UI

---

## 20. Two-week build roadmap

## Week 1

### Day 1
- initialize repo
- set up FastAPI, Postgres, SQLAlchemy
- configure Docker Compose
- create base models

### Day 2
- implement customer and wallet models
- build customer and wallet endpoints
- integrate wallet provider stub

### Day 3
- implement ledger schema
- build journal posting helpers
- add balance query logic

### Day 4
- implement deposit models and endpoints
- support pending → completed flow
- wire deposit confirmation into ledger

### Day 5
- build transfer models and endpoints
- add available/reserved balance logic
- create tx submission stub

### Day 6
- integrate real testnet transfer submission
- store tx hash
- build transfer polling worker

### Day 7
- clean up tests
- validate end-to-end flow:
  - create user
  - create wallet
  - deposit
  - transfer

## Week 2

### Day 8
- implement payment intents schema and endpoints

### Day 9
- build hosted checkout page

### Day 10
- connect payment confirmation to ledger posting

### Day 11
- implement webhook generation and signing

### Day 12
- implement webhook retry worker and logs

### Day 13
- add reconciliation checks and dashboard views

### Day 14
- demo polish
- write README
- record architecture notes
- prepare screenshots and sample API requests

---

## 21. Testing strategy

You should test this like a payments backend, not like a toy app.

## 21.1 Unit tests
Test:
- journal balancing
- balance computation
- idempotency behavior
- webhook signing
- transfer state transitions

## 21.2 Integration tests
Test:
- customer creation
- wallet creation
- deposit confirmation
- transfer flow
- payment intent confirmation
- webhook delivery

## 21.3 Failure cases
Test:
- insufficient balance
- duplicate transfer request
- failed blockchain transaction
- webhook endpoint timeout
- deposit confirmed twice
- race conditions around balance reservation

---

## 22. Demo flows to support

Your final project demo should support these.

## Demo 1: Create user and wallet
- create Alice
- create her Base Sepolia wallet

## Demo 2: Simulate deposit
- Alice deposits 100 USD
- admin confirms deposit
- Alice gets 100 USDC internally

## Demo 3: Send USDC
- Alice sends 20 USDC to another wallet
- tx hash is stored
- transfer eventually confirms

## Demo 4: Merchant checkout
- merchant creates a checkout for 15 USDC
- Alice pays
- merchant is credited
- webhook is emitted

## Demo 5: Inspect state
Show:
- ledger entries
- balances
- transfer history
- webhook delivery logs
- transaction metadata

---

## 23. Stretch goals

After V1 works, add:

- multi-chain routing
- refunds
- merchant fee configuration
- KYC/KYB status objects
- compliance/risk rules
- transfer allowlists
- frozen balances
- delayed capture / escrow
- API key dashboard
- webhook replay button
- support for off-chain internal transfers
- support for external merchant settlement

---

## 24. Resume / portfolio framing

This project is strong because it demonstrates:

- payments systems thinking
- ledger design
- wallet orchestration
- stablecoin movement
- asynchronous transaction handling
- webhook/event-driven architecture
- reconciliation mindset
- product API design

Possible portfolio description:

> Built a Stripe-like stablecoin payments backend supporting wallet creation, simulated fiat-to-USDC deposits, USDC transfers, merchant checkout flows, webhook delivery, and double-entry ledger reconciliation on Base Sepolia.

---

## 25. Final recommendation

Build V1 as:

- FastAPI
- Postgres
- Redis
- Coinbase-managed or stubbed wallets
- Base Sepolia
- simulated fiat deposits
- real testnet USDC transfers
- internal double-entry ledger
- Stripe-like payment intents
- webhook delivery system

That gives you the best mix of:
- realism
- reasonable scope
- infrastructure depth
- stablecoin relevance

---

## 26. Immediate next steps

Start with this exact order:

1. set up repo and database
2. define customer, wallet, account, journal, deposit, transfer tables
3. implement ledger posting helpers
4. build customer and wallet endpoints
5. build deposit lifecycle
6. build balance endpoint
7. build transfer lifecycle
8. integrate testnet USDC transfer
9. build payment intents
10. add webhooks and reconciliation

Once those are done, polish the project with:
- checkout UI
- admin dashboard
- docs
- architecture diagram
- test coverage
