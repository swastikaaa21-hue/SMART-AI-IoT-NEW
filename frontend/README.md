# 📖 Frontend Documentation

## 📂 File Structure

```
frontend/
├── index.html              (4114 lines) - Main HTML file
├── CODE_STRUCTURE.md       (238 lines)  - Detailed code structure guide
├── css/
│   └── custom.css          (134 lines)  - Custom styles & animations
├── js/
│   ├── config.js           (70 lines)   - Configuration & i18n
│   ├── state.js            (14 lines)   - Global state management
│   ├── api.js              (39 lines)   - API helper functions
│   └── ui.js               (64 lines)   - UI helpers (toast, modals)
├── package.json
└── vercel.json
```

## 🎯 Quick Start

### Untuk Developer Baru:
1. **Baca `CODE_STRUCTURE.md`** - Peta lengkap lokasi setiap fitur
2. **Cari fitur yang ingin dimodifikasi** - Gunakan table di dokumentasi
3. **Edit langsung di `index.html`** - Semua code masih di satu file
4. **Test di browser** - Refresh dan test perubahan

### Untuk Debugging:
1. Lihat **Quick Navigation Guide** di `CODE_STRUCTURE.md`
2. Cek line number yang sesuai dengan error
3. Gunakan browser DevTools Console untuk error detail

## 🔍 Cara Mencari Code

### Method 1: Gunakan Line Numbers
Lihat `CODE_STRUCTURE.md` untuk line numbers:
- Login/Register: Line 2060-2171
- Device Control: Line 2552-2647
- Remote UI: Line 2797-3491
- Schedule: Line 3568-4092

### Method 2: Search by Comment
Semua section punya comment header:
```javascript
// ── Login (Backend Auth) ───────────────────────────
```

Cari dengan Ctrl+F di editor.

### Method 3: Search by Function Name
Gunakan DevTools atau editor search:
- `submitLogin()` - Login function
- `loadRooms()` - Load rooms & devices
- `sendRemoteCommand()` - Device control
- `submitCreateSchedule()` - Create schedule

## 🛠️ Common Tasks

### 1. Menambah Device Type Baru
**Location**: Line 2172-2228 (`getDeviceMeta`)
```javascript
function getDeviceMeta(type) {
    const meta = {
        // Tambah type baru di sini
        newtype: { icon: 'fa-icon-name', color: 'bg-color-500 text-white' }
    };
    return meta[type?.toLowerCase()] || { icon: 'fa-microchip', color: 'bg-gray-500 text-white' };
}
```

### 2. Modifikasi Remote Control
**Location**: Line 2797-3491
- AC Remote: `renderACRemote()` - Line 2797
- TV Remote: `renderTVRemote()` - Line 2914
- Light Remote: `renderLightRemote()` - Line 3031

### 3. Update API Endpoint
**Location**: Line 1456 (`config.js` sudah extracted)
```javascript
const API_BASE = isLocal ? LOCAL_BACKEND + '/api/v1' : RENDER_BACKEND_URL + '/api/v1';
```

### 4. Tambah Page Baru
**Steps**:
1. Tambah HTML di section Pages (Line 514-1072)
2. Tambah case di `navigate()` function (Line 2004-2059)
3. Tambah nav button jika perlu

## 🐛 Troubleshooting Guide

### Device tidak muncul di Home?
**Check**: `loadRooms()` at Line 2229
- Cek API response di Network tab
- Cek `state.allDevices` di Console

### Remote control tidak berfungsi?
**Check**: `sendRemoteCommand()` at Line 2715
- Cek payload yang dikirim
- Cek response dari backend

### Schedule tidak tersimpan?
**Check**: `submitCreateSchedule()` at Line 3639
- Cek form validation
- Cek selected devices

### Login gagal?
**Check**: `submitLogin()` at Line 2088
- Cek credentials
- Cek backend API status

### WebSocket disconnect terus?
**Check**: `connectWebSocket()` at Line 1856
- Cek backend WebSocket server
- Cek auth token masih valid

## 📦 File yang Sudah Di-extract (Opsional)

Beberapa file sudah di-extract untuk modularitas (tapi belum di-import ke index.html):

### `js/config.js`
- API configuration
- Auth tokens
- i18n translations

### `js/state.js`
- Global state object
- Current device reference

### `js/api.js`
- API helper function
- Auto-handle 401

### `js/ui.js`
- Toast notifications
- Modal functions
- Device metadata

### `css/custom.css`
- Custom animations
- Toggle switch styles
- Dark mode styles

**Note**: File-file ini bisa digunakan untuk refactoring di masa depan. Saat ini `index.html` masih self-contained.

## 🚀 Future Refactoring (Optional)

Jika ingin memecah `index.html` sepenuhnya:

1. **Phase 1**: Extract remaining JavaScript
   - `auth.js` - Authentication functions
   - `navigation.js` - Page routing
   - `home.js` - Home page logic
   
2. **Phase 2**: Extract device controls
   - `remote.js` - All remote render functions
   - `websocket.js` - WebSocket handling
   
3. **Phase 3**: Extract features
   - `schedule.js` - Schedule management
   - `chat.js` - AI assistant
   - `settings.js` - Settings page

4. **Phase 4**: Update index.html
   - Add script imports in order
   - Test each module
   - Fix dependencies

**Estimated effort**: 4-6 hours with thorough testing

## 📚 Additional Resources

- **Backend API Docs**: `/docs` endpoint when backend is running
- **Tailwind CSS**: https://tailwindcss.com/docs
- **Font Awesome Icons**: https://fontawesome.com/icons

## 🔐 Security Notes

- Auth tokens stored in localStorage
- WebSocket uses JWT authentication
- API automatically handles 401 (token expired)
- Passwords hashed with bcrypt on backend

## 💡 Best Practices

1. **Sebelum edit**: Backup `index.html`
2. **Test di localhost dulu** sebelum deploy
3. **Check browser console** untuk errors
4. **Gunakan DevTools Network tab** untuk debug API calls
5. **Read CODE_STRUCTURE.md** sebelum modify function besar

---

**Last Updated**: 2026-11-02  
**Maintainer**: Development Team  
**Questions**: Check CODE_STRUCTURE.md atau contact team
