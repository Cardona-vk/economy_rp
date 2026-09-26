async function updateDashboard() {
    try {
        const response = await fetch('/api/dashboard');
        const data = await response.json();

        if (data.error) return;

        const saldoEl = document.getElementById('saldo-display');
        if (saldoEl) {
            saldoEl.innerText = `$ ${data.saldo.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        }

        const invListEl = document.getElementById('inventory-list');
        if (invListEl) {
            invListEl.innerHTML = '';
            data.inventario.forEach(function(item) {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${item.nombre}</td>
                    <td>$ ${item.precio}</td>
                    <td>${item.tiene_deuda ? '<span class="debt-badge">DEUDA</span>' : '<span style="color: var(--accent-neon)">OK</span>'}</td>
                `;
                invListEl.appendChild(row);
            });
        }
    } catch (e) {
        console.error("Error fetching dashboard:", e);
    }
}

async function sendTradeInvite() {
    const targetPlayerId = document.getElementById('target-player-id').value;
    const itemId = document.getElementById('my_item_id').value;
    const money = document.getElementById('my_money').value;

    if (!targetPlayerId) {
        alert("Por favor ingresa un ID de jugador válido.");
        return;
    }

    const currentUserId = document.body.dataset.userId ||
                          document.querySelector('[data-player-id]')?.dataset.playerId;

    if (targetPlayerId == currentUserId) {
        alert("No puedes iniciar una negociación contigo mismo.");
        return;
    }

    if (!itemId && !money) {
        alert("Debes ofrecer al menos un ítem o un monto de dinero");
        return;
    }

    try {
        const response = await fetch('/api/trades/open', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                destinatario: targetPlayerId,
                item_j1: itemId || null,
                monto_j1: money || 0
            })
        });
        const result = await response.json();
        if (result.success) {
            alert(result.message);
        } else {
            // Mostramos el mensaje exacto del servidor para debugging
            alert("Error: " + result.message);
        }
    } catch (e) {
        console.error("Error enviando invitación:", e);
        alert("Error crítico al enviar invitación: " + e.message);
    }
}

async function checkIncomingTrades() {
    const listEl = document.getElementById('trades-pending-list');
    if (!listEl) return;

    try {
        const response = await fetch('/api/trades/pending');
        const data = await response.json();

        if (!data.success) return;

        if (data.invitaciones.length === 0) {
            listEl.innerHTML = '<p style="color: var(--text-muted);">No hay invitaciones pendientes.</p>';
            return;
        }

        listEl.innerHTML = '';
        data.invitaciones.forEach(trade => {
            const card = document.createElement('div');
            card.className = 'stat-panel';
            card.style.cssText = 'background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; border-left: 4px solid var(--accent-blue); text-align: left;';
            card.innerHTML = `
                <div style="font-size: 0.9rem; margin-bottom: 5px;">
                    <strong>${trade.emisor}</strong> te invita a tradear
                </div>
                <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 10px;">
                    Oferta: ${trade.item_ofrecido || 'Sin Item'} / $${trade.monto_j1}
                </div>
                <button class="btn" style="width: 100%; padding: 5px; font-size: 0.8rem; background: var(--accent-blue);"
                        onclick="aceptarTrade(${trade.id_negociacion})">Aceptar</button>
            `;
            listEl.appendChild(card);
        });
    } catch (e) {
        console.error("Error checking trades:", e);
    }
}

async function aceptarTrade(idTrade) {
    try {
        const response = await fetch('/api/trades/accept', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ id_trade: idTrade })
        });
        const result = await response.json();
        if (result.success) {
            alert("Invitación aceptada. Entrando a la mesa de tradeo...");
            location.reload();
        } else {
            alert("Error: " + result.message);
        }
    } catch (e) {
        console.error("Error accepting trade:", e);
        alert("Error crítico al aceptar invitación");
    }
}

// --- LÓGICA DE LA MESA DE INTERCAMBIO EN TIEMPO REAL ---
let currentTradeId = null;
let pollingInterval = null;

async function syncTradeTable() {
    if (!currentTradeId) return;

    try {
        const response = await fetch(`/api/trades/${currentTradeId}/status`);
        const result = await response.json();

        if (!result.success) return;

        const trade = result.data;
        const myId = document.body.dataset.userId;
        const isPlayer1 = trade.id_jugador_1 == myId;

        const otherItem = isPlayer1 ? trade.id_item_j2 : trade.id_item_j1;
        const otherMoney = isPlayer1 ? trade.monto_j2 : trade.monto_j1;
        const otherConfirmed = isPlayer1 ? trade.confirmacion_j2 : trade.confirmacion_j1;

        document.getElementById('other-item-display').innerText = otherItem ? `Item ID: ${otherItem}` : 'Sin Item';
        document.getElementById('other-money-display').innerText = `$ ${otherMoney}`;
        document.getElementById('other-status-badge').innerText = otherConfirmed ? '✅ Listo' : '⏳ Esperando';
        document.getElementById('other-status-badge').style.color = otherConfirmed ? 'var(--accent-neon)' : 'var(--text-muted)';

        const myConfirmed = isPlayer1 ? trade.confirmacion_j1 : trade.confirmacion_j2;
        const myBadge = document.getElementById('my-status-badge');
        if (myBadge) {
            myBadge.innerText = myConfirmed ? '✅ Listo' : '⏳ Esperando';
            myBadge.style.color = myConfirmed ? 'var(--accent-neon)' : 'var(--text-muted)';
        }

        if (trade.estado === 'COMPLETADO') {
            clearInterval(pollingInterval);
            alert("¡Comercio completado con éxito!");
            window.location.href = '/dashboard';
        }
    } catch (e) {
        console.error("Error syncing trade table:", e);
    }
}

async function updateTradeOffer() {
    const itemId = document.getElementById('trade-item-select').value;
    const money = document.getElementById('trade-money-input').value || 0;

    if (!currentTradeId) return alert("No hay un tradeo activo.");

    try {
        const response = await fetch('/api/trades/update_offer', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                id_trade: currentTradeId,
                id_item: itemId || null,
                monto: money
            })
        });
        const result = await response.json();
        if (!result.success) alert("Error: " + result.message);
    } catch (e) {
        console.error("Error updating offer:", e);
    }
}

async function confirmTrade() {
    if (!currentTradeId) return alert("No hay un tradeo activo.");

    try {
        const response = await fetch('/api/trades/confirm', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ id_trade: currentTradeId })
        });
        const result = await response.json();
        if (!result.success) alert("Error: " + result.message);
    } catch (e) {
        console.error("Error confirming trade:", e);
    }
}

async function cancelCurrentTrade() {
    if (!currentTradeId) return alert("No hay un tradeo activo.");

    try {
        const response = await fetch('/api/trades/cancel', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ id_trade: currentTradeId })
        });
        const result = await response.json();
        if (result.success) {
            alert("Tradeo cancelado.");
            location.reload();
        }
    } catch (e) {
        console.error("Error cancelling trade:", e);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('saldo-display')) {
        updateDashboard();
        setInterval(updateDashboard, 5000);
    }

    if (document.getElementById('trades-pending-list')) {
        checkIncomingTrades();
        setInterval(checkIncomingTrades, 2000);
    }

    if (document.getElementById('active-trade-panel')) {
        const initTrade = async () => {
            try {
                const response = await fetch('/api/trades/active');
                const result = await response.json();
                if (result.success && result.data.id_negociacion) {
                    currentTradeId = result.data.id_negociacion;
                    document.getElementById('active-trade-panel').style.display = 'block';
                    document.getElementById('negotiation-panel').style.display = 'none';
                    pollingInterval = setInterval(syncTradeTable, 1500);
                    syncTradeTable();
                }
            } catch (e) {
                console.error("Error initializing active trade:", e);
            }
        };
        initTrade();
    }
});
