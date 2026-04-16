# Naman LMS Fullstack

This repo contains both the frontend and backend for the LMS project in one normal Git repository.

## Structure

- `Frontend` - Vite + React frontend
- `Backend` - Express backend

## Getting started

### Frontend

```bash
cd Frontend
npm install
npm run dev
```

### Backend

```bash
cd Backend
npm install
copy .env.example .env
npm start
```

### Python agents (Course Generator, etc.)

The Python code under `Backend/` uses a virtual environment at `Backend/venv` and dependencies from `Backend/requirements.txt`.

```bash
cd Backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Environment setup

- Frontend variables live in `Frontend/.env`
- Backend variables live in `Backend/.env`
- Example files are included as `Frontend/.env.example` and `Backend/.env.example`
