# Office room booking API (MVP)

FastAPI + SQLAlchemy 2 (async) + PostgreSQL + Alembic. Authentication is email OTP plus JWT. Bookings use explicit `unit_conflicts` for overlap rules between bookable units.

## Requirements

- Python 3.11+
- PostgreSQL (local instance on port `5432` is assumed; optional Docker Compose uses host port **5433** to avoid clashing with your existing server)

## Local setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set DATABASE_URL (with your real password), JWT_SECRET_KEY, and SMTP_* values.
```

Create the database if needed (name should match `DATABASE_URL`, e.g. `prashastsingh`).

## Migrations

```bash
export PYTHONPATH=.
alembic upgrade head
```

Generate new revisions after model changes:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## Bootstrap data

After migrations:

```bash
PYTHONPATH=. python -m app.scripts.seed_bootstrap
```

This inserts:

- Internal domain `uni-marburg.de`
- Amenities: Whiteboard, Monitor, LAN
- Default `booking_policy` (30-minute slots)

## Create the first admin

No OTP: this promotes or creates an admin user directly (bootstrap only).

```bash
PYTHONPATH=. python -m app.scripts.create_admin --email you@example.com --name "Your Name"
```

Use an internal-domain email if you want that user classified as internal in future signups; the script sets `user_type` to `internal` for new users.

## Run the server

```bash
PYTHONPATH=. uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- OpenAPI UI: http://localhost:8000/api/v1/docs  
- Health: http://localhost:8000/health  
- Static files (room images): http://localhost:8000/storage/room_images/…  

## Local storage (`STORAGE_ROOT`)

Uploaded room images are stored on disk under **`storage/room_images/`** (relative to the process working directory unless you override `STORAGE_ROOT` in `.env`). The directory is created on startup.

- **`STORAGE_ROOT`**: filesystem root for static hosting (default `storage`). URLs in the database look like `/storage/room_images/<uuid>.jpg`.
- The app mounts **`/storage`** to that folder so those URLs work without a separate web server.
- **`storage/`** is listed in `.gitignore`; files are not committed.
- **Resizing**: uploads are normalized to RGB JPEG. The **longest side is at most 1600px**; smaller images are **not** upscaled. Aspect ratio is preserved. This layout can later be swapped for S3 or another object store without changing the API shape (still return a `file_url` string).

## Room amenities (admin)

Link amenities to rooms via dedicated admin routes or by passing **`amenity_ids`** when creating or updating a room.

- **`GET /api/v1/admin/rooms/{room_id}/amenities`** — list linked amenities (full `AmenityOut` objects).
- **`POST /api/v1/admin/rooms/{room_id}/amenities`** — body `{"amenity_id": 1}`; returns updated list. Duplicate link → **409**.
- **`DELETE /api/v1/admin/rooms/{room_id}/amenities/{amenity_id}`** — remove link; returns updated list (idempotent if already detached).
- **`POST /api/v1/admin/rooms`** — optional **`amenity_ids`**: `[1, 2]` (duplicates in the array are deduplicated).
- **`PATCH /api/v1/admin/rooms/{room_id}`** — optional **`amenity_ids`**: if present, **replaces** all links for that room (use `[]` to clear).

Replace `TOKEN` with a JWT from login/OTP verification.

```bash
# List amenities on a room
curl -s -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/v1/admin/rooms/1/amenities

# Attach amenity 2 to room 1
curl -s -X POST -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" \
  -d '{"amenity_id":2}' \
  http://localhost:8000/api/v1/admin/rooms/1/amenities

# Detach amenity 2 from room 1
curl -s -X DELETE -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/api/v1/admin/rooms/1/amenities/2

# Create room with amenities
curl -s -X POST -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Seminar A","booking_mode":"hybrid","capacity":10,"amenity_ids":[1,3]}' \
  http://localhost:8000/api/v1/admin/rooms
```

## Room image upload (admin, multipart)

**`POST /api/v1/admin/rooms/{room_id}/images`** accepts **`multipart/form-data`**:

- **`file`**: required; allowed extensions **`.jpg`**, **`.jpeg`**, **`.png`**, **`.webp`**.
- **`sort_order`**: optional form field (integer, default `0`).

The server saves a **JPEG** under `storage/room_images/` and stores **`file_url`** like `/storage/room_images/<uuid>.jpg`.

```bash
curl -s -X POST -H "Authorization: Bearer TOKEN" \
  -F "file=@./photo.png" \
  -F "sort_order=0" \
  http://localhost:8000/api/v1/admin/rooms/1/images
```

Example JSON response:

```json
{
  "id": 5,
  "room_id": 1,
  "file_url": "/storage/room_images/a1b2c3d4e5f6....jpg",
  "sort_order": 0,
  "created_at": "2025-03-20T12:00:00+00:00"
}
```

**`DELETE /api/v1/admin/rooms/{room_id}/images/{image_id}`** removes the row and deletes the file on disk when `file_url` is under `/storage/room_images/`.

## Public room browse & availability (frontend)

User-facing room APIs return **structured JSON** (no extra stitching): amenities as `{ id, name, icon }`, images ordered by **`sort_order`** then **`id`**, and **`thumbnail_url`** = `file_url` of the first image in that order (or `null` if there are no images). Image URLs are served under **`/storage/...`** (see above).

### `GET /api/v1/rooms` (paginated)

Query parameters:

| Param | Description |
|--------|-------------|
| `page`, `limit` | Pagination (`page` ≥ 1, default `limit` 20) |
| `capacity` | Room or at least one **active** unit must meet this minimum capacity |
| `amenities` | Comma-separated ids; room must have **all** listed amenities |
| `unit_type` | `full_room`, `half_room`, `section`, `table` (alias: `room` → `full_room`) |
| `date`, `start_time`, `end_time` | Used with `available` (see below) |
| `available` | If `true` **and** `date` + `start_time` + `end_time` are set, only rooms where at least one unit can be booked for the **entire** start–end range (same overlap/conflict rules as booking). If the room has a `full_room` unit and none is free for that whole range, the room is excluded |

Example response:

```json
{
  "items": [
    {
      "id": 10,
      "name": "Conference Room A",
      "description": "Large meeting room",
      "location": "2nd Floor",
      "capacity": 10,
      "booking_mode": "hybrid",
      "is_active": true,
      "thumbnail_url": "/storage/room_images/abc.jpg",
      "amenities": [
        { "id": 1, "name": "Whiteboard", "icon": "whiteboard" }
      ],
      "images": [
        { "id": 100, "file_url": "/storage/room_images/abc.jpg", "sort_order": 0 }
      ]
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 20
}
```

### `GET /api/v1/rooms/{room_id}` (detail)

Same amenity/image/thumbnail conventions; **`bookable_units`** lists **all** units (including inactive) ordered by **`id`**, with `parent_unit_id`, `type`, `capacity`, `is_active`.

### `GET /api/v1/availability/rooms/{room_id}?date=YYYY-MM-DD`

Returns a **slot grid** for the room’s **availability window** (`availability_window_start`–`availability_window_end`, default **08:00–20:00** UTC; set per room in admin). Slots align to `booking_policy.slot_minutes` (usually 30). Each slot lists **active** units with `available` and optional `reason`: `booked` (overlap on that unit), `conflict` (peer unit in `unit_conflicts` has a blocking booking), or `inactive` (only if such a unit were included—normally only active units are listed).

Example (abbreviated):

```json
{
  "room_id": 10,
  "room_name": "Conference Room A",
  "date": "2026-03-25",
  "slot_minutes": 30,
  "slots": [
    {
      "start_time": "09:00",
      "end_time": "09:30",
      "units": [
        { "unit_id": 201, "unit_name": "Full Room", "unit_type": "full_room", "available": false, "reason": "conflict" },
        { "unit_id": 202, "unit_name": "Table 1", "unit_type": "table", "available": true, "reason": null }
      ]
    }
  ]
}
```

### `GET /api/v1/availability/search?date=YYYY-MM-DD`

Same slot structure **per matching room**, with optional filters: `capacity`, `amenities` (comma-separated), `unit_type`, and optional `start_time` / `end_time` to **restrict which slots** are returned (slots overlapping that range). Uses the same room filters as the browse list (capacity / amenities / unit type).

```json
{
  "date": "2026-03-25",
  "slot_minutes": 30,
  "rooms": [ { "room_id": 10, "room_name": "...", "date": "2026-03-25", "slot_minutes": 30, "slots": [ ... ] } ]
}
```

## SMTP environment variables

| Variable | Purpose |
|----------|---------|
| `SMTP_HOST` | SMTP server hostname |
| `SMTP_PORT` | Usually `587` (STARTTLS) or `465` (SSL) |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | Auth (leave empty if not required) |
| `SMTP_FROM_EMAIL` | `From` address for OTP emails |
| `SMTP_USE_TLS` | `true` for STARTTLS on port 587 (`false` if using plain/SSL-only setups) |

If SMTP is misconfigured, signup/login OTP routes will fail when sending mail.

## Tests

```bash
PYTHONPATH=. pytest
```

Uses in-memory SQLite with the same models (OTP hashing uses HMAC-SHA256 with `JWT_SECRET_KEY`). Tests use a temporary `STORAGE_ROOT` for uploads.

## Notes

- **OTP storage**: OTPs are stored as HMAC-SHA256 digests (keyed with `JWT_SECRET_KEY`), not plaintext.
- **Public rooms**: list and detail use **`thumbnail_url`** and rich **`amenities`** / **`images`**; see **Public room browse & availability** above.
- **Conflicts**: Add rows in `unit_conflicts` (admin API) so that booking one unit blocks overlapping bookings on paired units (e.g. full room vs tables).
- **Times**: Slot boundaries are validated against `booking_policy.slot_minutes`; `start_at` / `end_at` are built as **UTC** from `booking_date` + wall-clock `start_time` / `end_time`.

## Production deployment

See **[`../deploy/UBUNTU.md`](../deploy/UBUNTU.md)** for Ubuntu deployment (Nginx, systemd, HTTPS).

## What to do next (iteration ideas)

- Thumbnails and multiple sizes; CDN in front of `/storage`
- S3-compatible object storage instead of local `storage/` (keep the same `file_url` pattern or migrate to absolute URLs)
- Timezone-aware booking (e.g. `Europe/Berlin`) instead of UTC wall times
- Refresh tokens, rate limiting on OTP, audit logs
- Notification emails for approvals and booking reminders
