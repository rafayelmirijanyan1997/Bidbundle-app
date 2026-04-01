# BidBundle

`BidBundle` is a FastAPI + MySQL web app for bundled neighborhood home services. Homeowners and community managers post bulk service requests such as gardening, pool cleaning, or pressure washing, and vendors bid on the combined opportunity to win the work at the best price.

## Core Flow

1. Sign up as a `homeowner`, `vendor`, or `manager`
2. Homeowners/managers create a service bundle
3. Vendors submit one bid per bundle with price, timeline, and proposal
4. The bundle owner or a manager awards the winning bid

## Quick Start

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000](http://localhost:8000)

## Database

The app uses MySQL. You can let SQLAlchemy create tables automatically on startup or run [`sql/schema.sql`](sql/schema.sql) manually.

Default local connection:

```env
DATABASE_URL=mysql+asyncmy://chatuser:chatpass@localhost:3306/groupchat
JWT_SECRET=change_me
JWT_EXPIRE_MINUTES=43200
APP_HOST=0.0.0.0
APP_PORT=8000
```

## Lab Alignment

This project keeps the Lab 10 stack:

- FastAPI backend
- MySQL persistence
- Vanilla HTML/CSS/JS frontend
- Android TWA wrapper support in `twa_android_src`

To package the Android wrapper, point `twa_android_src/app/src/main/res/values/strings.xml` at your deployed BidBundle URL.
