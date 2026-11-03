// ══════════════════════════════════════════════════════════
// Global State Management
// ══════════════════════════════════════════════════════════

const state = {
    activePage: 'splash',
    rooms: [],
    allDevices: [],
    currentRoomUUID: null,
    currentRoomDevices: [],
    schedules: [],
    deviceMeta: {}
};

// Current device for remote control
let currentDevice = null;
