# Quick Start

## Backend
```bash
cd backend
npm run dev
```
Port: `http://localhost:8000`

Auto-start:
- MySQL (TiDB Cloud remote)
- MQTT (HiveMQ Cloud remote)
- Gemini AI service
- WebSocket server
- Scheduler (device automation)

## Frontend
```bash
cd frontend
npm install
npm run dev
```
Port: `http://localhost:3000`

Frontend auto-detect localhost, connect ke `http://localhost:8000/api/v1`

## First Time Setup

1. **Install Node.js** (untuk npm)

2. **Install Python 3.x**

3. **Backend deps** (otomatis via `npm run dev`, atau manual):
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Frontend deps**:
   ```bash
   cd frontend
   npm install
   ```

## Environment

Backend `.env` udah configured:
- TiDB Cloud MySQL (remote)
- HiveMQ MQTT broker (remote, TLS)
- Gemini API key
- JWT secrets
- CORS origins

Ga ada setup database/MQTT lokal. Semua cloud-based.

## Verification

Backend startup success kalo log tampil:
```
INFO app_startup_complete
```

Frontend buka browser: `http://localhost:3000`

## Troubleshooting

**uvicorn not found**: Python belum di PATH atau pip install belum jalan
**Port 8000 in use**: Kill process atau ganti PORT di backend/.env
**Frontend error connect**: Backend belum jalan atau port salah
