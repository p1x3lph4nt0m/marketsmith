
/**
 * Helper to get Django CSRF Token from cookies
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Connects to the backend API to place an order
 */
async function executeTrade(action) {
    const priceInput = document.getElementById('price-input');
    const price = priceInput.value;

    if (!price || price <= 0) {
        alert("Enter valid price");
        return;
    }

    const orderData = new URLSearchParams({
        'type': action === 'Buy' ? 'BID' : 'ASK',
        'price': parseInt(price),
        'game_id': window.currentGameId
    });

    try {
        const response = await fetch('/api/order/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: orderData
        });

        const result = await response.json();

        if (result.status === 'queued') {
            addOrderToUI(action, price);
            priceInput.value = '';
        } else {
            alert(result.message);
        }

    } catch (error) {
        console.error('Error placing order:', error);
        alert("Connection lost.");
    }
}

/**
 * Internal UI helper to render the row
 */
function addOrderToUI(action, price) {
    const actionColor = action === 'Buy' ? '#38a169' : '#e53e3e';
    const ordersList = document.getElementById('working-orders-list');
    
    const orderRow = document.createElement('div');
    orderRow.className = 'data-row order-item';
    
    orderRow.innerHTML = `
        <span style="color: ${actionColor}; font-weight: bold;">${action}</span>
        <span>$${price}</span>
        <span style="cursor: pointer; color: #a0aec0;" onclick="this.parentElement.remove()">✕</span>
    `;

    ordersList.appendChild(orderRow);
}

document.addEventListener("DOMContentLoaded", () => {
    const tradeContainer = document.getElementById("trades-list");
    const tradeDataElement = document.getElementById("trade-data");

    if (!tradeContainer || !tradeDataElement) return;

    let allTrades = [];
    try {
        // This reads the trade_log already being sent by your views.py
        allTrades = JSON.parse(tradeDataElement.textContent);
    } catch (err) {
        allTrades = [];
    }

    tradeContainer.innerHTML = "";

    // 1. Filter trades where the current user's name appears as buyer or seller
    const myTrades = allTrades.filter(t => 
        t.buyer === window.currentUserName || t.seller === window.currentUserName
    );

    // 2. Handle Case: No trades found
    if (myTrades.length === 0) {
        tradeContainer.innerHTML = '<div class="data-row"><span>-</span><span>-</span><span>-</span></div>';
        return;
    }

    // 3. Handle Case: Trades found
    myTrades.forEach(trade => {
        const row = document.createElement("div");
        row.className = "data-row";

        // Logic: Compare strings to find the partner and the action
        const isBuyer = trade.buyer === window.currentUserName;
        const partner = isBuyer ? trade.seller : trade.buyer;
        const action = isBuyer ? "Buy" : "Sell";
        const color = isBuyer ? "#38a169" : "#e53e3e";

        row.innerHTML = `
            <span>${partner}</span>
            <span>${trade.price}</span>
            <span style="color: ${color}; font-weight: bold;">${action}</span>
        `;
        tradeContainer.appendChild(row);
    });
});