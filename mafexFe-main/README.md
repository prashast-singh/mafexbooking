# Mafex frontend

Next.js 15 (App Router) UI for the Mafex room booking API.

## Setup

1. Copy environment:

   ```bash
   cp .env.local.example .env.local
   ```

2. Set `NEXT_PUBLIC_API_BASE_URL` to your API base (include `/api/v1`), e.g. `http://127.0.0.1:8000/api/v1`.

3. Install and run:

   ```bash
   npm install
   npm run dev
   ```

   App: [http://localhost:3000](http://localhost:3000)

## Stack

- TypeScript, Tailwind CSS, shadcn-style UI (Base UI primitives)
- Auth: OTP signup/login; JWT stored in `localStorage`
- Forms: React Hook Form + Zod where noted (auth steps, booking purpose, admin room create)
- `date-fns`, `lucide-react`, Sonner toasts

## Routes

| Path | Purpose |
|------|---------|
| `/` | Browse rooms (filters, pagination) |
| `/rooms/[roomId]` | Detail, availability grid, booking |
| `/login`, `/signup` | OTP flows; pending users redirect to `/awaiting-approval` |
| `/my-bookings` | List/cancel bookings (login required) |
| `/awaiting-approval` | Pending/rejected account messaging |
| `/admin/*` | Dashboard, approvals, users, rooms, amenities (admin role) |

## Production build

```bash
npm run build
npm start
```

Ensure `NEXT_PUBLIC_API_BASE_URL` is set at build time for server-side fetches on public pages.
