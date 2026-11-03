# 📁 Frontend Code Structure Guide

## File: `index.html` (4114 lines)

### 🎨 **CSS Section** (Lines 34-513)
- Custom scrollbar styling
- Page transitions & animations
- Toggle switch styles
- Connection status indicators
- Dark mode styles

---

## 📄 **HTML Structure** (Lines 514-1443)

### Pages:
1. **Splash** (Line 516-536) - Loading screen
2. **Login/Register** (Line 537-549) - Authentication
3. **Home** (Line 551-626) - Dashboard dengan rooms & devices
4. **Schedule** (Line 627-788) - Jadwal otomasi
5. **Create Schedule** (Line 790-870) - Form buat jadwal baru
6. **Settings** (Line 872-1010) - Pengaturan user
7. **Room Detail** (Line 1012-1053) - Detail ruangan
8. **Device Remote** (Line 1073-1102) - Remote kontrol device

### Modals:
- `modal-add-routine` (Line 1106-1195) - Buat rutinitas
- `modal-add-room` (Line 1197-1237) - Tambah ruangan
- `modal-add-device` (Line 1239-1283) - Tambah perangkat
- `modal-show-password` (Line 1285-1325) - Tampil password
- `modal-schedule-detail` (Line 1327-1349) - Detail jadwal
- `modal-confirm-delete` (Line 1351-1375) - Konfirmasi hapus

### Components:
- **Assistant Panel** (Line 1377-1443) - AI Chat sidebar

---

## 🔧 **JavaScript Section** (Lines 1456-4444)

### 📌 Core Functions

#### **1. Configuration** (Line 1456-1715)
```javascript
// API Configuration
API_BASE, authToken, refreshToken
initBackendUrlSetting(), saveBackendUrl()

// Internationalization
translations, setLanguage()
```

#### **2. State Management** (Line 1716-1728)
```javascript
state = {
    activePage, rooms, allDevices,
    currentRoomUUID, currentRoomDevices
}
currentDevice = null
```

#### **3. API Helper** (Line 1729-1775)
```javascript
api(method, endpoint, body)
// Auto-handle 401, token refresh
```

#### **4. UI Helpers** (Line 1776-1851)
```javascript
showToast(message, type)
openModal(modalId), closeModal(modalId)
getDeviceMeta(type)
```

---

### 🌐 **WebSocket** (Line 1852-1910)
```javascript
connectWebSocket()
handleWebSocketMessage(data)
// Real-time device status updates
```

---

### 🚀 **Initialization** (Line 1911-2003)
```javascript
DOMContentLoaded:
  - Check auth token
  - Navigate to splash/home/login
  - Initialize banner carousel
  - Connect WebSocket
  - Load rooms & schedules
```

---

### 🧭 **Navigation** (Line 2004-2059)
```javascript
navigate(pageId)
updateNavStyles(activePage)
// Page routing & sidebar management
```

---

### 🔐 **Authentication** (Line 2060-2171)
```javascript
// Login/Register Tab
switchLoginTab(tab)

// Login
submitLogin() -> API /auth/login
loadUserAndGo() -> Get user profile

// Register
submitRegister() -> API /auth/register

// Logout
logout() -> Clear tokens
```

---

### 🏠 **Home Page** (Line 2172-2551)
```javascript
// Room Functions
loadRooms() -> GET /rooms & /devices
renderDashboardDevices()
updateBadgeCounters()

// Room Detail
openRoom(roomId) -> GET /rooms/{id}
loadRoomDevices(roomId)
renderRoomDevices()

// Device Toggle
toggleDevice(deviceId, currentState) -> POST /commands/{id}

// Search
handleSearch() -> Filter rooms & devices
```

---

### 🎮 **Device Remote** (Line 2648-3491)
```javascript
// Remote Control
openDeviceRemote(identifier)
backToRoom()
deleteCurrentDevice() -> DELETE /devices/{id}
confirmDeleteDevice()

// Send Commands
sendRemoteCommand(deviceId, action, params)

// Render Remote UI
renderDeviceRemote(device)
  - renderACRemote() - AC controls
  - renderTVRemote() - TV D-pad navigation
  - renderLightRemote() - Light brightness
  - renderFanRemote() - Fan speed
  - renderPlugRemote() - Smart plug on/off
  - renderCameraRemote() - Camera controls
  - renderDoorRemote() - Door lock
  - renderCookerRemote() - Rice cooker
  - renderGenericRemote() - Default controls

// Device Actions
cycleACMode(), adjustACSpeed()
adjustTemp(), setACMode(), setFanSpeed()
openLearnMode() - IR learning mode
```

---

### 📅 **Schedule Page** (Line 3492-4092)
```javascript
// Modal Functions (Legacy)
openAddRoutineModal()
updateRoutineDevices(roomId)
submitAddRoutine()

// Schedule CRUD
loadSchedules() -> GET /schedules
renderSchedules(schedules)
toggleSchedule(id, active) -> PATCH /schedules/{id}
deleteSchedule(id) -> DELETE /schedules/{id}

// Create Schedule Page (New)
renderCreateScheduleDevices()
toggleCreateScheduleDate(type)
submitCreateSchedule() -> POST /schedules

// Calendar
renderCalendar()
changeCalendarMonth(delta)
selectDate(date)
```

---

### ➕ **Add Device/Room** (Line 4093-4129)
```javascript
submitAddDevice() -> POST /devices
submitAddRoom() -> POST /rooms
```

---

### 🤖 **AI Chat Assistant** (Line 4130-4251)
```javascript
toggleAssistant()
sendChatMessage() -> POST /chat
renderChatMessage(message, isUser)
startVoiceRecording() - Voice input
```

---

### ⚙️ **Settings Page** (Line 4252-4379)
```javascript
// Profile
toggleProfileDetails()
saveProfile() -> PATCH /auth/me

// Password
changePassword() -> PATCH /auth/me
togglePasswordVisibility()

// App Settings
toggleNotifications()
initBackendUrlSetting()
saveBackendUrl()
```

---

### 🌙 **Dark Mode** (Line 4380-4444)
```javascript
toggleTheme()
// Toggle between light/dark mode
```

---

## 🎯 Quick Navigation Guide

### To modify specific features:

| Feature | Location | Key Functions |
|---------|----------|---------------|
| **Login/Register** | Line 2060-2171 | `submitLogin()`, `submitRegister()` |
| **Device List** | Line 2229-2374 | `loadRooms()`, `renderDashboardDevices()` |
| **Device Control** | Line 2552-2647 | `toggleDevice()`, `sendRemoteCommand()` |
| **Remote UI** | Line 2797-3491 | `renderACRemote()`, `renderTVRemote()`, etc. |
| **Schedule** | Line 3568-4092 | `loadSchedules()`, `submitCreateSchedule()` |
| **AI Chat** | Line 4130-4251 | `sendChatMessage()`, `toggleAssistant()` |
| **Settings** | Line 4252-4379 | `saveProfile()`, `changePassword()` |

---

## 🔍 Tips untuk Problem Solving

1. **Device tidak muncul?** → Check `loadRooms()` line 2229
2. **Remote tidak berfungsi?** → Check `sendRemoteCommand()` line 2715
3. **Schedule error?** → Check `submitCreateSchedule()` line 3639
4. **Login gagal?** → Check `submitLogin()` line 2088
5. **WebSocket disconnect?** → Check `connectWebSocket()` line 1856

---

## 📦 Future Refactoring Plan

Jika ingin memecah file di masa depan:

### Suggested Structure:
```
frontend/
├── js/
│   ├── config.js       ✅ Created
│   ├── state.js        ✅ Created
│   ├── api.js          ✅ Created
│   ├── ui.js           ✅ Created
│   ├── auth.js         ⏳ TODO
│   ├── navigation.js   ⏳ TODO
│   ├── home.js         ⏳ TODO
│   ├── remote.js       ⏳ TODO
│   ├── schedule.js     ⏳ TODO
│   ├── chat.js         ⏳ TODO
│   ├── settings.js     ⏳ TODO
│   ├── websocket.js    ⏳ TODO
│   └── main.js         ⏳ TODO
├── css/
│   └── custom.css      ⏳ TODO
└── index.html          (Structure only)
```

**Note**: Refactoring harus dilakukan secara bertahap dengan testing setiap step untuk menghindari breaking changes.

---

Last Updated: 2026-11-02
