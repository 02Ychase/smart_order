# smart_order

## Backend setup

```bash
python -m pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python tools/seed_demo_data.py
python run.py
```

Demo login:

- username: `demo_user`
- password: `demo123456`

## Frontend setup

```bash
cd ui
npm install
npm run dev
```
