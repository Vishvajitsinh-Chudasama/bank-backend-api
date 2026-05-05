# Payment Gateway API

Django REST API for user registration, JWT authentication, bank accounts (up to three per user), top-ups, transfers between accounts, and transaction history. A simple HTML dashboard lives at the site root (`/`).

## Production deployment (Render)

This app is deployed on [Render](https://render.com/):

| | URL |
|--|-----|
| **Web dashboard** | [https://bank-backend-api.onrender.com/](https://bank-backend-api.onrender.com/) |
| **API base** | [https://bank-backend-api.onrender.com/api/](https://bank-backend-api.onrender.com/api/) |

The bundled [`home/templates/home/home.html`](home/templates/home/home.html) sets `API_BASE` to `https://bank-backend-api.onrender.com/api`, so the hosted page calls the API on the same host. For local runs, change `API_BASE` to `http://127.0.0.1:8000/api`.

## Stack

- Django 6, Django REST Framework, Simple JWT
- PostgreSQL via `DATABASE_URL` (see [dj-database-url](https://github.com/jacobian/dj-database-url))

## Prerequisites

- Python 3.11+ (matching your deployment target)
- PostgreSQL or another database URL compatible with `dj-database-url`

## Environment variables

| Variable | Purpose |
|----------|---------|
| `DJANGO_SECRET_KEY` | Django secret key (required in production) |
| `DATABASE_URL` | Database connection string |
| `DEBUG` | Set to `True` for local debug (default treated as `False`) |

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root with at least:

```
DJANGO_SECRET_KEY=your-secret-key
DATABASE_URL=postgres://user:pass@localhost:5432/dbname
DEBUG=True
```

Run migrations and start the server:

```bash
python manage.py migrate
python manage.py runserver
```

- **Web UI:** http://127.0.0.1:8000/
- **Admin:** http://127.0.0.1:8000/admin/
- **API base:** http://127.0.0.1:8000/api/

All JSON APIs expect `Content-Type: application/json` unless noted.

---

## Authentication

Protected endpoints require a JWT **access** token in the header:

```http
Authorization: Bearer <access_token>
```

Obtain tokens via **Login** (below). Access tokens expire after **5 minutes**; use **Refresh** with a valid refresh token to obtain a new access token. Refresh tokens last **1 day** (see `SIMPLE_JWT` in `payment_gateway_api/settings.py`).

---

## API quick reference

Paths below are from the site root. Use `Content-Type: application/json` for bodies. Where it says **None (Requires Token)**, send header `Authorization: Bearer <access>`.

| Category | Endpoint | Method | Purpose | Data sent by user |
|----------|----------|--------|---------|-------------------|
| Identity | `/api/users/register/` | POST | Sign up a new user. | Username, Password, Email |
| Identity | `/api/users/` | GET | See a list of all users. | None (Requires Token) |
| Identity | `/api/users/<id>/` | GET | View specific user profile. | ID in URL |
| Identity | `/api/users/<id>/` | PUT | Update user details (Name, etc). | Updated Profile JSON |
| Identity | `/api/users/<id>/` | DELETE | Remove user account. | ID in URL |
| Security | `/api/auth/login/` | POST | Get Access/Refresh tokens. | Username, Password |
| Security | `/api/auth/refresh/` | POST | Get new access token. | Refresh Token |
| Banking | `/api/accounts/` | GET | View your bank accounts. | None (Requires Token) |
| Banking | `/api/accounts/` | POST | Create a new account (Max 3). | None (Auto-generated) |
| Banking | `/api/accounts/<id>/` | DELETE | Close a specific account. | ID in URL |
| Banking | `/api/accounts/<id>/topup/` | POST | Add money to the balance. | Amount |
| Money | `/api/payments/transfer/` | POST | Move money between accounts. | Sender ID, Receiver ID, Amount |
| Money | `/api/payments/transactions/` | GET | View your transfer history. | None (Requires Token) |

**Implementation notes:** Registration may include optional `first_name` and `last_name` in addition to username, password, and email. Account delete is rejected if balance &gt; 0. Login/refresh bodies use JSON keys `username`/`password` and `refresh` respectively; transfer uses `sender_account_id`, `receiver_account_id`, `amount`.

For request/response examples, status codes, and business rules, see the detailed sections below.

---

## API reference

Base path: **`/api/`** (all routes below are relative to this prefix).

### Users

#### Register user

Creates a Django user. Public; no JWT required.

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/users/register/` |

**Request body (JSON):**

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `username` | string | Yes | Unique username |
| `password` | string | Yes | Stored hashed |
| `email` | string | No | |
| `first_name` | string | No | |
| `last_name` | string | No | |

**Success:** `201 Created` — body matches `UserSerializer`: `id`, `username`, `email`, `first_name`, `last_name` (password is write-only, never returned).

**Errors:** `400` validation errors from DRF.

---

#### List users

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/users/` |
| **Auth** | JWT required |

Returns all users in the system (`id`, `username`, `email`, `first_name`, `last_name`). Admin-style listing; consider restricting in production.

---

#### View specific user profile

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/users/<pk>/` |
| **Auth** | JWT required |
| **Purpose** | View that user’s profile. |
| **Data sent by user** | User id in the URL (`<pk>`). |

Returns `id`, `username`, `email`, `first_name`, `last_name` (no password).

---

#### Update user details

| | |
|---|---|
| **Method** | `PUT` |
| **URL** | `/users/<pk>/` |
| **Auth** | JWT required |
| **Purpose** | Update user details (name, email, etc.). |
| **Data sent by user** | Full updated profile JSON (same fields as the user resource; include `password` only if changing it). |

---

#### Remove user account

| | |
|---|---|
| **Method** | `DELETE` |
| **URL** | `/users/<pk>/` |
| **Auth** | JWT required |
| **Purpose** | Delete that user record. |
| **Data sent by user** | User id in the URL (`<pk>`). |

---

### Auth (JWT)

#### Login (obtain token pair)

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/auth/login/` |

**Request body:**

```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**Success:** `200 OK`

```json
{
  "refresh": "<refresh_token>",
  "access": "<access_token>"
}
```

**Errors:** `401` if credentials are invalid.

---

#### Refresh access token

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/auth/refresh/` |

**Request body:**

```json
{
  "refresh": "<refresh_token>"
}
```

**Success:** `200 OK` — returns a new `access` token (and optionally rotated refresh, depending on Simple JWT defaults).

**Errors:** `401` if refresh token is invalid or expired.

---

### Bank accounts

All account endpoints scope data to the **authenticated user**.

#### List accounts & create account

| | |
|---|---|
| **Methods** | `GET`, `POST` |
| **URL** | `/accounts/` |
| **Auth** | JWT required |

**GET** — Returns the caller’s bank accounts. Each object includes:

| Field | Meaning |
|-------|---------|
| `id` | Account primary key (used in transfers and URLs) |
| `user` | Owning user id |
| `account_number` | Auto-generated 10-digit string (read-only on create) |
| `balance` | Decimal balance (read-only via API on create) |
| `created_at` | Creation timestamp |

**POST** — Opens a new account for the current user. Body can be empty `{}`; `user`, `account_number`, and `balance` are set server-side.

**Business rule:** A user may have **at most 3** accounts. Exceeding returns `400` with `{"error": "Maximum of 3 bank accounts allowed."}`.

---

#### Delete account

| | |
|---|---|
| **Method** | `DELETE` |
| **URL** | `/accounts/<pk>/` |
| **Auth** | JWT required |

`<pk>` must belong to the authenticated user.

**Business rule:** Deletion is **rejected** if `balance > 0`. Response `400`:

```json
{"error": "Cannot delete account with an active balance. Please transfer funds first."}
```

**Success:** `204 No Content` if balance is zero.

---

#### Top up account

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/accounts/<pk>/topup/` |
| **Auth** | JWT required |

**Request body:**

```json
{
  "amount": "100.50"
}
```

`amount` must be **greater than zero**. Increments `balance` atomically (single account update).

**Success:** `200 OK`

```json
{
  "message": "Top-up successful",
  "new_balance": "<decimal as string>"
}
```

**Errors:**

| Status | Condition |
|--------|-----------|
| `400` | Missing/zero/negative amount (`{"error": "Invalid amount"}`) |
| `404` | Account id not found or not owned by user (`{"error": "Account not found."}`) |

---

### Payments

#### Transfer (payment between accounts)

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/payments/transfer/` |
| **Auth** | JWT required |

Moves funds from one bank account to another inside one database transaction (`select_for_update` on both rows).

**Request body:**

```json
{
  "sender_account_id": 1,
  "receiver_account_id": 2,
  "amount": "50.00"
}
```

**Rules:**

- `amount` must be **> 0** (`400` — `"Invalid amount"`).
- Sender and receiver **must differ** (`400` — `"Sender and receiver accounts must be different."`).
- **Sender** must belong to the **authenticated user** (lookup uses `sender_id` + `user=request.user`).
- **Receiver** can be **any** existing account (including another user’s), enabling cross-user payments.
- If sender **balance < amount**, balances are **not** changed; a **FAILED** `Transaction` row is created (`400` — `"Insufficient balance"`).
- On success, balances update and a **SUCCESS** `Transaction` is recorded.

**Success:** `200 OK`

```json
{"message": "Internal transfer successful"}
```

or, when receiver belongs to a different user:

```json
{"message": "Payment successful"}
```

**Errors:**

| Status | Meaning |
|--------|---------|
| `404` | One or both account IDs invalid (`{"error": "One or both accounts not found."}`) |

---

#### List transactions

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/payments/transactions/` |
| **Auth** | JWT required |

Returns transactions where the current user’s accounts appear as **either** sender **or** receiver, newest first.

Serializer exposes model fields (including `id`, `sender_account`, `receiver_account`, `amount`, `status`, `created_at`). `status` is `SUCCESS` or `FAILED`.

---

## Example flow (cURL)

```bash
BASE=http://127.0.0.1:8000/api

# Register
curl -s -X POST "$BASE/users/register/" \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"secret","email":"a@example.com"}'

# Login
TOKENS=$(curl -s -X POST "$BASE/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"secret"}')
ACCESS=$(python -c "import sys,json; print(json.load(sys.stdin)['access'])" <<< "$TOKENS")

# Create account & top up
curl -s -X POST "$BASE/accounts/" -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" -d '{}'
curl -s -X POST "$BASE/accounts/1/topup/" -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" -d '{"amount":"100"}'

# Transfer (adjust IDs)
curl -s -X POST "$BASE/payments/transfer/" -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -d '{"sender_account_id":1,"receiver_account_id":2,"amount":"25"}'

# History
curl -s "$BASE/payments/transactions/" -H "Authorization: Bearer $ACCESS"
```

---

## Frontend (`home.html`)

The template `home/templates/home/home.html` is a single-page demo that calls these endpoints. In production it uses `API_BASE = "https://bank-backend-api.onrender.com/api"`; for local development switch that to `http://127.0.0.1:8000/api` (same path prefix).

## License

Add your license here if applicable.
