# Telegram CMS / Content Bot

A bilingual (Persian / English), fully database-driven Telegram bot with:

- A dynamic, unlimited-depth nested menu — **nothing is hard-coded**; every
  button and every piece of content is read from the database.
- The user-facing menu (all levels) is rendered as a **persistent reply
  keyboard** pinned at the bottom of the chat, not inline buttons —
  admins get an extra root-level "⚙️ Admin Panel" row that opens the
  admin panel (which itself still uses inline buttons/forms, since that
  part involves multi-step flows like renaming, pricing, and delete
  confirmations that work better as inline messages).
- Text / photo / video / document content per button (Telegram `file_id`
  is stored so files are never re-uploaded).
- Per-button pricing with **unlimited admin-created payment methods**
  (card transfer, crypto, gift card, etc. — each with its own editable
  instructions) assignable per product, plus a built-in automatic
  **Telegram Stars** method (native Bot API payments, currency `XTR`),
  with a locked-content screen shown until access is purchased or granted.
- Optional **mandatory channel membership** gate — require users to
  join a channel before using the bot, configured via environment
  variables (off by default).
- **Admin-to-user messaging**: send a message to one specific user, or
  broadcast to everyone who has started the bot.
- A multi-admin system with three roles (`OWNER`, `ADMIN`, `MODERATOR`)
  and a granular, per-admin permission table.
- Admin panel fully operable from inside Telegram — no external dashboard
  needed.

---

## 1. Requirements

- Python 3.12+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

## 2. Installation

```bash
git clone <this-repo>
cd telegram_bot

python -m venv venv
```

Activate the virtual environment:

- **Linux / macOS**
  ```bash
  source venv/bin/activate
  ```
- **Windows (PowerShell)**
  ```powershell
  venv\Scripts\Activate.ps1
  ```
- **Windows (cmd.exe)**
  ```cmd
  venv\Scripts\activate.bat
  ```

Install dependencies:

```bash
pip install -r requirements.txt
```

## 3. Configuration

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

```env
BOT_TOKEN=123456789:AAExampleTokenFromBotFather
OWNER_ID=123456789
DATABASE_URL=sqlite:///./bot.db
DEFAULT_CURRENCY=IRT
```

`.env` is git-ignored — never commit it.

### How to get `BOT_TOKEN`

1. Open a chat with [@BotFather](https://t.me/BotFather) on Telegram.
2. Send `/newbot` and follow the prompts (choose a name and a username
   ending in `bot`).
3. BotFather replies with an HTTP API token — paste it into `BOT_TOKEN`.

### How to find your `OWNER_ID`

1. Open a chat with [@userinfobot](https://t.me/userinfobot) (or any
   similar "get my ID" bot) and send it any message.
2. It replies with your numeric Telegram user ID — paste that into
   `OWNER_ID`. This account becomes the bot's Owner (super admin) the
   first time the bot starts.

## 4. Database

No manual setup needed. On first run the bot automatically creates
`bot.db` (SQLite) and all required tables, and registers `OWNER_ID` as
the Owner admin.

For production, you can point `DATABASE_URL` at Postgres/MySQL instead
(e.g. `postgresql+psycopg2://user:pass@host/dbname`) — the SQLAlchemy
models work unchanged. Schema changes going forward should be tracked
with Alembic:

```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

## 5. Mandatory channel membership (optional)

The bot can require users to join a channel before they can use it at
all. This is off by default — set these two variables in `.env` (or
your Railway Variables) to enable it:

```env
REQUIRED_CHANNEL=@mychannel
REQUIRED_CHANNEL_LINK=
```

- `REQUIRED_CHANNEL`: a public channel username (`@mychannel`) or, for
  a private channel, its numeric chat id (`-1001234567890`).
- `REQUIRED_CHANNEL_LINK`: the URL shown on the "Join" button. Leave
  empty for a public `@username` — the link is derived automatically
  (`https://t.me/mychannel`). For a private channel you must set this
  explicitly to an invite link (e.g. `https://t.me/+AbCdEfGh`),
  otherwise no clickable join link can be shown.

**Critical requirement:** the bot itself must be an **admin member**
of that channel, or Telegram's API will refuse every membership check
and every user will be told they haven't joined, even if they have.
Add the bot to the channel's admin list before turning this on.

Leave both variables empty to disable the feature entirely — nothing
else changes. Admins and the Owner are always exempt from this check,
so you can never accidentally lock yourself out of your own bot.

## 6. Creating your first admin / content

1. Start the bot (see below) and open it in Telegram as the account
   whose ID you put in `OWNER_ID`.
2. Send `/start`, pick a language.
3. Send `/admin` to open the admin panel.
4. Use **🔘 مدیریت دکمه‌ها / Manage Buttons → ➕ افزودن دکمه / Add Button**
   to create your first menu item, then **📦 مدیریت محتوا / Manage
   Content** on it to attach text/photos/videos/files.
5. Use **👑 مدیریت ادمین‌ها / Manage Admins** to add more admins (by their
   numeric Telegram ID) and assign them the `ADMIN` or `MODERATOR` role.
   Fine-grained permissions can then be toggled per admin.
6. Optionally, use **⚙️ تنظیمات / Settings** to set the display-only
   Stars recipient shown to buyers.

No BotFather "Payments" setup is required for Telegram Stars — unlike
Stripe or other providers, Stars need no provider token at all
(`provider_token=""` is intentional and correct in this codebase).
Just start selling: set a price on a button and it becomes payable
with Stars immediately.

## 7. Running the bot

```bash
python main.py
```

The bot runs with long polling. Logs are written to `logs/errors.log`,
`logs/admin.log`, and `logs/system.log`.

## 8. Running tests

```bash
pytest
```

Tests run against a temporary SQLite database created fresh for each
test session (see `tests/conftest.py`) and never touch your real `bot.db`.

## 9. Project structure

```
telegram_bot/
├── app/
│   ├── bot.py                  # Application factory - wires up all handlers
│   ├── config.py                # Reads .env / environment variables
│   ├── handlers/                 # Telegram update handlers
│   │   ├── start.py               # /start, language gate, main menu
│   │   ├── language.py            # language selection / switching
│   │   ├── user_menu.py           # dynamic menu navigation + content + paywall
│   │   ├── admin.py               # /admin entry point, permission helpers, stats/users
│   │   ├── admin_buttons.py       # button CRUD, pricing, move/reorder, delete
│   │   ├── admin_content.py       # content CRUD, captions, reorder
│   │   └── admin_admins.py        # admin CRUD, role + permission management
│   ├── keyboards/                # InlineKeyboardMarkup builders
│   ├── database/
│   │   ├── database.py            # SQLAlchemy engine/session
│   │   ├── models.py              # ORM models
│   │   └── repositories/          # DB access functions per entity
│   ├── services/                  # Business logic used by handlers
│   ├── locales/                   # fa.json / en.json translation strings
│   ├── utils/                     # permissions, translations, logging, helpers
│   └── states/                    # ConversationHandler state enums
├── migrations/                    # Alembic migration environment
├── tests/                         # pytest test suite
├── .env.example
├── .gitignore
├── requirements.txt
├── alembic.ini
└── main.py
```

## 10. Deployment

### Linux VPS

```bash
git clone <this-repo> && cd telegram_bot
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in values
python main.py
```

Run it under a process manager so it survives reboots/crashes, e.g.
`systemd`, `supervisor`, `pm2`, or `screen`/`tmux` for quick testing.

### Railway

This repo includes a `Procfile` and `railway.json` so Railway's Nixpacks
builder picks up the right start command automatically.

1. Push this repository to GitHub and create a new Railway project from
   it.
2. Set the environment variables `BOT_TOKEN`, `OWNER_ID`, `DATABASE_URL`
   (and optionally `DEFAULT_CURRENCY`) in the Railway dashboard.
3. **Replicas must stay at 1.** Telegram's long-polling API
   (`getUpdates`) only allows one active connection per bot token — a
   second replica will crash with a 409 Conflict error. `railway.json`
   already sets `numReplicas: 1`; don't raise it unless you switch the
   bot to webhook mode.
4. **Use Postgres, not SQLite, in production.** Railway's filesystem is
   ephemeral — a redeploy or restart wipes `bot.db` and you lose all
   buttons/content/admins. Add Railway's Postgres plugin, then set
   `DATABASE_URL` to the connection string it gives you (SQLAlchemy
   accepts it as `postgresql+psycopg2://...` — install `psycopg2-binary`
   if you go this route). The ORM models work unchanged either way.
5. Railway assigns a `PORT` automatically for HTTP services, but this
   bot runs on long polling and never binds a port — you can ignore
   `PORT` entirely, or leave it unset.

---

## What's ready for the next stage

- **Admin messaging**: from **⚙️ پنل مدیریت → 👥 کاربران → 📩 ارسال پیام**,
  an admin (with the `manage_users` permission) can send any content
  (text, photo, video, or file) either to one specific user by their
  numeric Telegram ID, or as a broadcast to everyone who has ever
  started the bot. Both use Telegram's `copy_message` under the hood,
  so whatever the admin sends is relayed as-is. Broadcasts ask for
  confirmation first (showing how many users will receive it), send
  with a small delay between each recipient to stay under Telegram's
  rate limits, skip users marked `is_blocked` in the database, and
  report a final success/failure count — a failure usually just means
  that particular user has blocked the bot. See
  `app/handlers/admin_messaging.py`.

- **Payments**: fully admin-configurable payment *methods*, not a fixed
  pair. From **⚙️ پنل مدیریت → 💳 روش‌های پرداخت**, an admin (with the
  `manage_payments` permission) can create any number of custom methods
  (card transfer, crypto, gift card, etc.), each with its own name and
  editable instructions/details shown to the buyer (e.g. a card number
  or wallet address). One special method, **⭐ Stars**, is seeded
  automatically at startup and can never be deleted, because it's the
  only method that's genuinely automatic:
  - **⭐ Stars** — a real, native Telegram invoice (currency `XTR`). No
    external gateway, no manual review. Telegram handles the charge;
    on success, access is granted automatically
    (`payment_service.record_successful_stars_payment`). See
    `_send_stars_invoice` / `precheckout` / `successful_payment` in
    `app/handlers/user_payment.py`.
    > **Important limitation:** Stars payments always credit the
    > *bot's own* balance — the Bot API has no way to route a payment
    > directly to a different Telegram account. The **⚙️ تنظیمات /
    > Settings** section in the admin panel lets you set a
    > display-only "Stars recipient" shown to buyers before they pay,
    > but actually transferring those Stars to that person has to be
    > done manually from the bot's own balance.
  - **Every other method** is a manual, receipt-based flow. The user
    reads that method's instructions, sends a photo of their receipt;
    it's forwarded to every admin holding the `manage_payments`
    permission (plus the Owner) with Approve/Reject buttons. Approving
    grants access immediately via `payment_service.approve_payment`;
    rejecting notifies the user so they can retry. A default "🎁 گیفت"
    method is seeded at startup alongside Stars so upgraded bots keep
    behaving the same as before this feature existed — rename, edit,
    or delete it freely, it's just data now. See `method_selected` /
    `receive_receipt` / `admin_review` in the same file.
    > Only the Owner gets `manage_payments` by default — grant it to
    > other admins from **👑 مدیریت ادمین‌ها → 🔐 مدیریت دسترسی** if you
    > want them to manage methods or review receipts too. An admin can
    > only receive a receipt photo if they've sent the bot `/start` at
    > least once.

  **Per-product method selection**: inside any button's management
  screen (📚 مدیریت دکمه), the new **💳 روش‌های پرداخت این محصول** row
  lets an admin pick exactly which methods apply to that specific
  product. If none are explicitly picked, every currently-enabled
  method is offered by default — so existing products need zero setup
  to keep working after this feature is added. See
  `button_payment_methods_view` / `button_payment_method_toggle` in
  `app/handlers/admin_buttons.py`, and `payment_method_repo.methods_for_button`
  for the exact fallback logic.

  All methods end at the same place — a `UserAccess` row — so
  `user_menu.py`'s access check unlocks the button immediately either
  way, and a user is never charged twice for the same button.
- **Currency**: Stars amounts (`XTR`) are the unit used everywhere
  prices are set or shown, including for manually-reviewed methods (the
  receipt just gets manually checked against that same number). The
  `Button.currency` column still exists for possible future uses but
  has no effect on the current flow.
- **Settings table**: a generic key/value `settings` table exists for
  future bot-wide configurable options (currently used only for the
  Stars recipient display string).

## What needs manual attention

- **Dependencies could not be verified by automated tests in the
  environment this project was generated in** (no network access to
  install `python-telegram-bot` / `SQLAlchemy` there). All files pass a
  Python syntax check and every callback-data string was manually traced
  against its regex handler, but please run `pip install -r
  requirements.txt && pytest` yourself before deploying to production.
- No real payment gateway is implemented (by design — see project scope).
- **Menu position is kept in memory** (`context.user_data["current_menu_id"]`),
  not in the database. If the bot process restarts, a user's "current
  position" resets — the next tap of an unrecognized reply-keyboard
  button simply re-shows the right level, so this degrades gracefully
  rather than breaking, but it's worth knowing about.
- For very high traffic, swap the synchronous SQLAlchemy session layer
  in `app/database/database.py` for an async engine (e.g.
  `sqlite+aiosqlite` or Postgres with `asyncpg`) — the service layer
  above the repositories is already isolated from this detail, so only
  `database.py` and the `repositories/` modules would need to change.
