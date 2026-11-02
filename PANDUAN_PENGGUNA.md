# Panduan Pengguna Smart House IoT Dashboard

## Cara Kerja Sistem

Smart House adalah sistem kontrol rumah pintar berbasis web yang memungkinkan Anda mengendalikan perangkat elektronik rumah dari mana saja melalui internet.

### Komponen Sistem

```
[Perangkat IoT] ←→ [MQTT Broker] ←→ [Backend Server] ←→ [Web Dashboard]
     (ESP32)        (HiveMQ Cloud)      (FastAPI)         (Browser Anda)
```

### Alur Kerja

1. **Perangkat IoT** (lampu, AC, kipas, dll) terhubung ke WiFi rumah Anda
2. **MQTT Broker** meneruskan pesan antara perangkat dan server
3. **Backend Server** memproses perintah dan menyimpan data ke database
4. **Web Dashboard** menampilkan status dan menerima kontrol dari Anda

---

## Fitur Utama

### 1. Dashboard Beranda
- Lihat semua ruangan dan perangkat
- Status real-time: ON/OFF, suhu, kelembaban
- Cuaca dan lokasi rumah

### 2. Kontrol Perangkat

**Lampu:**
- Nyalakan/Matikan
- Atur brightness (kecerahan)

**AC:**
- Nyalakan/Matikan
- Atur suhu target (18°C - 30°C)
- Mode: Cool/Heat/Fan/Auto
- Kecepatan kipas: Low/Med/High/Auto

**Kipas:**
- Nyalakan/Matikan
- Atur kecepatan (1-5)

### 3. Ruangan (Rooms)
- Buat ruangan baru (Kamar Tidur, Ruang Tamu, dll)
- Kelompokkan perangkat per ruangan
- Edit/Hapus ruangan

### 4. Jadwal Otomatis (Schedule)
- Nyalakan lampu otomatis jam 18:00
- Matikan AC jam 06:00
- Atur hari aktif (Senin-Minggu)

### 5. AI Assistant (Gemini)
- Chat dengan AI untuk kontrol perangkat
- Contoh: "Nyalakan lampu kamar tidur"
- AI akan eksekusi perintah otomatis

### 6. Riwayat (History)
- Log perintah yang dikirim
- Telemetri sensor (suhu, kelembaban, daya)
- Export data CSV

---

## Cara Menggunakan

### Pertama Kali

1. **Registrasi Akun**
   - Buka web dashboard
   - Klik "Atur & Buat Akun Baru"
   - Isi: Nama Rumah, Email, Lokasi, Password (min 8 karakter)

2. **Login**
   - Email: yang Anda daftarkan
   - Password: yang Anda buat

3. **Buat Ruangan**
   - Klik "Tambah Ruangan"
   - Pilih ikon (bedroom, living room, kitchen, dll)
   - Beri nama (contoh: "Kamar Utama")

4. **Tambah Perangkat**
   - Klik ruangan → "Tambah Perangkat"
   - Device ID: sesuai hardware ESP32 (contoh: `LIGHT_001`)
   - Pilih tipe: Light/AC/Fan/TV/Door/Camera
   - Beri nama (contoh: "Lampu Meja")

### Kontrol Perangkat

**Manual:**
- Klik card perangkat
- Toggle switch ON/OFF
- Atur brightness/temperature dengan slider

**Voice Command (AI):**
- Klik ikon chat
- Ketik: "Nyalakan semua lampu di ruang tamu"
- AI akan eksekusi

**Jadwal:**
- Menu Jadwal → Tambah Jadwal
- Pilih perangkat, aksi (turn_on/turn_off)
- Set waktu mulai (contoh: 18:00)
- Pilih hari aktif (checklist Senin-Minggu)

### Monitoring

**Status Real-Time:**
- Indikator hijau = perangkat online
- Indikator merah = offline
- Suhu/Kelembaban update otomatis setiap 5 detik (via WebSocket)

**Riwayat:**
- Tab "Riwayat Perintah": semua aksi yang dilakukan
- Tab "Data Telemetri": grafik suhu, kelembaban, konsumsi daya

---

## Tips & Troubleshooting

### Perangkat Offline?
- Cek WiFi ESP32 terhubung
- Restart ESP32
- Cek MQTT credentials di hardware

### Kontrol Tidak Respon?
- Refresh halaman (F5)
- Cek backend server running
- Cek koneksi internet

### Jadwal Tidak Jalan?
- Pastikan jadwal "Active" (toggle hijau)
- Cek hari dipilih dengan benar
- Backend scheduler berjalan (auto-check setiap 60 detik)

### Password Lupa?
- Belum ada fitur reset (development version)
- Hubungi admin atau buat akun baru

---

## FAQ

**Q: Apakah bisa akses dari HP?**  
A: Ya, buka browser di HP dan akses URL yang sama. Responsive design.

**Q: Berapa perangkat maksimal?**  
A: Tidak terbatas. Tergantung database dan MQTT broker capacity.

**Q: Data aman?**  
A: Ya. Password di-hash dengan bcrypt. Komunikasi HTTPS (production). MQTT TLS encrypted.

**Q: Offline mode?**  
A: Tidak. Butuh koneksi internet untuk kontrol real-time.

**Q: Biaya?**  
A: Free tier: TiDB Cloud MySQL, HiveMQ MQTT, Gemini API (rate limited).

---

## Teknologi

- **Frontend:** HTML5, TailwindCSS, Vanilla JavaScript
- **Backend:** Python FastAPI, SQLAlchemy ORM
- **Database:** TiDB Cloud (MySQL-compatible)
- **MQTT Broker:** HiveMQ Cloud (port 8883 TLS)
- **AI:** Google Gemini 2.0 Flash (function calling)
- **Real-time:** WebSocket untuk status update

---

## Kontak Support

- GitHub Issues: [link repository]
- Email: [admin email]
- Dokumentasi Developer: `SETUP.md`

---

**Versi:** 3.0.0  
**Update Terakhir:** 31 Oktober 2026
