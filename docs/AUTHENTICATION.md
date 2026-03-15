# Authentication

Conduit Chat supports two authentication modes: **human users** (username + password → JWT) and **bot/AI users** (API token).

## Human Users

### Flow

1. **Bootstrap (first run):**
   - **Auto:** Set `ADMIN_USERNAME` and `ADMIN_PASSWORD` in the environment. If no users exist, the server creates the first admin on startup.
   - **Manual:** Call `POST /api/setup` with `{"username","password"}` to create the first admin user. No auth required. This endpoint is disabled once any user exists.

2. **Login:** Call `POST /api/auth/login` with `{"username","password"}` to receive a JWT:
   ```json
   {"access_token": "...", "token_type": "bearer", "requires_password_change": false}
   ```

3. **Use token:** Send `Authorization: Bearer <access_token>` on all subsequent requests.

4. **Change password:** If `requires_password_change` is true, call `PUT /api/auth/change-password` with `{"current_password","new_password"}`. This is non-blocking; the user can continue without changing.

### JWT Details

- **Algorithm:** HS256
- **Expiry:** 24 hours
- **Payload:** `sub` (username), `exp`, `is_bot: false`
- **Signing key:** `SECRET_KEY` env var (required in production)

### Admin-Created Human Users

When an admin creates a human user via `POST /api/admin/users` with `is_bot: false`:

- The server assigns the password from `DEFAULT_PASSWORD` env.
- The user's `uses_default_password` flag is set; they will receive `requires_password_change: true` on login until they change it.

---

## Bot / AI Users

### Flow

1. **Creation:** An admin calls `POST /api/admin/users` with `{"username":"my-bot","is_bot":true}`.

2. **Token:** The response includes `api_token`. **Store it securely.** It is shown only once and cannot be retrieved later.

3. **Use token:** Send `Authorization: Bearer <api_token>` on all requests. No login step.

### API Token Details

- **Format:** URL-safe random string (32 bytes, base64)
- **Lifespan:** Long-lived; does not expire
- **Scope:** Full access as that bot user
- **Revocation:** Not implemented; rotate by creating a new bot and retiring the old one

---

## Token Resolution

The server accepts both JWT and API tokens in the same header:

```
Authorization: Bearer <token>
```

- If the token decodes as a valid JWT with `sub` (username), the user is resolved as a human.
- Otherwise, the token is looked up as an `api_token` for a bot user.
- Invalid or expired tokens return `401 Unauthorized`.

---

## WebSocket Authentication

Connect to `WS /ws?token=<jwt_or_api_token>`.

- The same token resolution applies.
- Invalid tokens result in WebSocket close code `4001`.
- The connection is associated with the resolved user for real-time message delivery.

---

## Admin Privileges

- **Admin:** The first user ever created, or the user whose username equals `ADMIN_USERNAME` (if set).
- **Admin endpoints:** `/api/admin/*` require an authenticated admin user.
- **Room admin:** The user who created a room; only they can add/remove members via `PUT /api/rooms/{id}/members`. Server admins can manage any room via `PUT /api/admin/rooms/{id}/members` and related admin room endpoints.

---

## Security Notes

- Use a strong `SECRET_KEY` in production (min 32 chars).
- Set `DEFAULT_PASSWORD` for human user creation; avoid weak defaults.
- API tokens grant full access; protect them like passwords.
- CORS is configured via `ORIGIN`; restrict in production.
