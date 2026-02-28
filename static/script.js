// static/script.js

function switchTab(evt, tabId) {
    const panes = document.querySelectorAll('.tab-pane');
    const tabs = document.querySelectorAll('.tab-link');
    panes.forEach(p => p.classList.remove('active'));
    tabs.forEach(t => t.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    evt.currentTarget.classList.add('active');
}

function initLobby() {
    // 1. The Django template already renders the real leaderboard on the homepage.
    // We removed the bots array and renderTable() so it stops overwriting the real data.

    // 2. Check if we are actually in the waiting room before starting WebSockets.
    // If we are just on the main lobby page, we stop executing here.
    const path = window.location.pathname;
    if (!path.includes('/waiting/')) {
        return; 
    }

    // --- WAITING ROOM WEBSOCKET LOGIC ---
    const pathParts = path.split('/');
    const gameIdFromUrl = pathParts[pathParts.length - 2]; 
    const statusText = document.getElementById("lobby-status");

    // Establish the connection
    const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const socket = new WebSocket(wsProtocol + window.location.host + `/ws/waiting/${gameIdFromUrl}/`);

    // Listen for the backend signal
    socket.onmessage = function(e) {
        const data = JSON.parse(e.data);
        
        // When the 6th player joins, the backend sends 'game_started'
        if (data.type === 'game_started') {
            if (statusText) {
                statusText.innerText = `LOBBY FULL! REDIRECTING...`;
            }
            
            // Redirect to the actual Django URL
            setTimeout(() => {
                window.location.href = `/game/${gameIdFromUrl}/`;
            }, 1000);
        }

        // Real-time count update
        if (data.type === 'player_joined') {
            if (statusText) {
                statusText.innerText = `LOBBY STATUS: ${data.player_count}/6 PARTICIPANTS`;
            }
        }
    };
}
