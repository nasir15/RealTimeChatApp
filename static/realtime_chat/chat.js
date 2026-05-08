(function () {
    const room = document.querySelector('.chat-room');
    const notificationTray = document.getElementById('notification-tray');
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const notificationsSocket = new WebSocket(`${scheme}://${window.location.host}/ws/notifications/`);

    notificationsSocket.onmessage = function (event) {
        const payload = JSON.parse(event.data);
        if (payload.type !== 'notification') {
            return;
        }
        renderNotification(payload);
    };

    if (!room) {
        return;
    }

    const roomType = room.dataset.roomType;
    const roomTarget = room.dataset.roomTarget;
    const isMember = room.dataset.isMember !== 'false';
    const messageList = document.getElementById('message-list');
    const typingIndicator = document.getElementById('typing-indicator');
    const form = document.getElementById('chat-form');
    const input = document.getElementById('chat-input');

    if (!form || !input || (roomType === 'group' && !isMember)) {
        return;
    }

    const socketPath = roomType === 'private'
        ? `/ws/chat/private/${roomTarget}/`
        : `/ws/chat/group/${roomTarget}/`;
    const chatSocket = new WebSocket(`${scheme}://${window.location.host}${socketPath}`);

    chatSocket.onmessage = function (event) {
        const payload = JSON.parse(event.data);
        if (payload.type === 'typing') {
            if (payload.sender !== window.chatConfig.username) {
                typingIndicator.textContent = `${payload.sender} is typing...`;
                window.clearTimeout(window.typingTimeout);
                window.typingTimeout = window.setTimeout(function () {
                    typingIndicator.textContent = '';
                }, 1200);
            }
            return;
        }

        if (payload.type === 'message') {
            appendMessage(payload);
            typingIndicator.textContent = '';
        }
    };

    form.addEventListener('submit', function (event) {
        event.preventDefault();
        const content = input.value.trim();
        if (!content) {
            return;
        }
        chatSocket.send(JSON.stringify({
            action: 'message',
            content: content,
        }));
        input.value = '';
    });

    input.addEventListener('input', function () {
        chatSocket.send(JSON.stringify({ action: 'typing' }));
    });

    function appendMessage(payload) {
        const isOwnMessage = payload.sender === window.chatConfig.username;
        const card = document.createElement('article');
        card.className = `message-bubble ${isOwnMessage ? 'own' : ''}`;
        card.innerHTML = `
            <header>${escapeHtml(payload.sender)}</header>
            <p>${escapeHtml(payload.content)}</p>
            <time>${new Date(payload.timestamp).toLocaleString()}</time>
        `;
        const empty = messageList.querySelector('.empty-state');
        if (empty) {
            empty.remove();
        }
        messageList.appendChild(card);
        messageList.scrollTop = messageList.scrollHeight;
    }

    function renderNotification(payload) {
        const card = document.createElement('div');
        card.className = 'notification';
        const heading = payload.scope === 'group'
            ? `${payload.sender} in ${payload.group}`
            : `${payload.sender} sent a message`;
        card.innerHTML = `
            <strong>${escapeHtml(heading)}</strong>
            <p>${escapeHtml(payload.content)}</p>
        `;
        notificationTray.appendChild(card);
        window.setTimeout(function () {
            card.remove();
        }, 3000);
    }

    function escapeHtml(value) {
        return value
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#39;');
    }
})();
