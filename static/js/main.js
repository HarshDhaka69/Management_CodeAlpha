/**
 * ProjectManager — Main JavaScript
 * Handles:
 *   - Sidebar toggle (mobile)
 *   - WebSocket connection for real-time notifications
 *   - Bell badge updates
 *   - Toast notifications
 *   - Task status quick-change (AJAX)
 *   - Auto-dismiss alerts
 */

'use strict';

/* ══════════════════════════════════════════════════════
   1. SIDEBAR TOGGLE (mobile)
══════════════════════════════════════════════════════ */
(function initSidebar() {
  const sidebar      = document.getElementById('sidebar');
  const toggle       = document.getElementById('sidebarToggle');
  const closeBtn     = document.getElementById('sidebarClose');
  const backdrop     = document.getElementById('sidebarBackdrop');

  if (!sidebar) return;

  function openSidebar() {
    sidebar.classList.add('open');
    if (backdrop) {
      backdrop.classList.add('show');
    }
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    if (backdrop) {
      backdrop.classList.remove('show');
    }
    document.body.style.overflow = '';
  }

  if (toggle)   toggle.addEventListener('click', openSidebar);
  if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
  if (backdrop) backdrop.addEventListener('click', closeSidebar);

  // Close sidebar on ESC key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeSidebar();
  });
})();


/* ══════════════════════════════════════════════════════
   2. TOAST NOTIFICATIONS
══════════════════════════════════════════════════════ */
function showToast(message, type = 'success', duration = 4000) {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const icons = {
    success: 'bi-check-circle-fill',
    danger:  'bi-exclamation-circle-fill',
    warning: 'bi-exclamation-triangle-fill',
    info:    'bi-info-circle-fill',
  };

  const toastEl = document.createElement('div');
  toastEl.className = `toast toast-pf align-items-center border-0 text-bg-${type} show`;
  toastEl.setAttribute('role', 'alert');
  toastEl.setAttribute('aria-live', 'assertive');
  toastEl.innerHTML = `
    <div class="d-flex">
      <div class="toast-body d-flex align-items-center gap-2">
        <i class="bi ${icons[type] || icons.info}"></i>
        <span>${message}</span>
      </div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto"
              data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;

  container.appendChild(toastEl);

  // Auto-remove after duration
  setTimeout(() => {
    toastEl.classList.remove('show');
    setTimeout(() => toastEl.remove(), 300);
  }, duration);

  // Manual close button
  toastEl.querySelector('.btn-close').addEventListener('click', () => {
    toastEl.classList.remove('show');
    setTimeout(() => toastEl.remove(), 300);
  });
}

// Convert Django messages (alerts) into toasts
(function convertDjangoMessages() {
  document.querySelectorAll('.alert[class*="alert-"]').forEach((alert) => {
    const type = Array.from(alert.classList)
      .find(c => c.startsWith('alert-') && c !== 'alert-dismissible')
      ?.replace('alert-', '') || 'info';
    const message = alert.textContent.trim().replace(/×/g, '').trim();
    if (message) showToast(message, type);
    // Hide the original alert silently
    alert.style.display = 'none';
  });
})();


/* ══════════════════════════════════════════════════════
   3. NOTIFICATION BELL (WebSocket)
══════════════════════════════════════════════════════ */
(function initNotificationWebSocket() {
  if (typeof USER_AUTHENTICATED === 'undefined' || !USER_AUTHENTICATED) return;

  const badge      = document.getElementById('notif-badge');
  const sidebarBadge = document.getElementById('sidebar-notif-badge');

  // Update both badges with a count
  function updateBadges(count) {
    [badge, sidebarBadge].forEach(el => {
      if (!el) return;
      if (count > 0) {
        el.textContent = count > 99 ? '99+' : count;
        el.style.display = '';
      } else {
        el.style.display = 'none';
      }
    });
  }

  // Determine WebSocket protocol (ws/wss)
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl    = `${protocol}//${window.location.host}/ws/notifications/`;

  let socket;
  let reconnectDelay = 2000;

  function connect() {
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      reconnectDelay = 2000; // reset backoff
    };

    socket.onmessage = (event) => {
      let data;
      try {
        data = JSON.parse(event.data);
      } catch {
        return;
      }

      if (data.type === 'unread_count') {
        updateBadges(data.count);
      }

      if (data.type === 'new_notification') {
        // Show a toast for the new notification
        const icon = data.notif_type === 'task_assigned'
          ? '📋'
          : '💬';
        showToast(`${icon} ${data.message}`, 'info', 6000);
        // The unread_count message follows immediately, so badge updates automatically
      }
    };

    socket.onclose = (event) => {
      if (!event.wasClean) {
        // Reconnect with exponential backoff (max 30s)
        setTimeout(connect, Math.min(reconnectDelay, 30000));
        reconnectDelay = Math.min(reconnectDelay * 1.5, 30000);
      }
    };

    socket.onerror = () => {
      socket.close();
    };
  }

  connect();

  // Expose socket globally so notification page can use it
  window.notifSocket = {
    markRead(notifId) {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'mark_read', notification_id: notifId }));
      }
    },
    markAllRead() {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'mark_all_read' }));
      }
    },
  };
})();


/* ══════════════════════════════════════════════════════
   4. TASK STATUS QUICK-CHANGE (AJAX)
   Handles dropdown "Move to" buttons on Kanban cards
══════════════════════════════════════════════════════ */
(function initStatusChange() {
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('.status-change-btn');
    if (!btn) return;

    const taskId   = btn.dataset.taskId;
    const newStatus = btn.dataset.status;
    if (!taskId || !newStatus) return;

    e.preventDefault();
    e.stopPropagation();

    try {
      const response = await fetch(`/tasks/${taskId}/status/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRFToken': typeof CSRF_TOKEN !== 'undefined' ? CSRF_TOKEN : getCookie('csrftoken'),
        },
        body: `status=${encodeURIComponent(newStatus)}`,
      });

      const data = await response.json();

      if (data.success) {
        showToast('Task moved successfully!', 'success');
        // Reload the page to reflect Kanban changes
        // In a production app you'd do a smooth DOM update
        setTimeout(() => window.location.reload(), 600);
      } else {
        showToast('Failed to update task status.', 'danger');
      }
    } catch (err) {
      showToast('Network error. Please try again.', 'danger');
    }
  });
})();


/* ══════════════════════════════════════════════════════
   5. AUTO-DISMISS FLASH ALERTS (fallback)
   In case any alert wasn't converted to toast
══════════════════════════════════════════════════════ */
(function autoDismissAlerts() {
  document.querySelectorAll('.alert-dismissible.fade.show').forEach((alert) => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      bsAlert.close();
    }, 5000);
  });
})();


/* ══════════════════════════════════════════════════════
   6. CONFIRM BEFORE DELETE (data-confirm attribute)
══════════════════════════════════════════════════════ */
document.addEventListener('submit', (e) => {
  const form = e.target;
  const confirmMsg = form.dataset.confirm;
  if (confirmMsg && !window.confirm(confirmMsg)) {
    e.preventDefault();
  }
});


/* ══════════════════════════════════════════════════════
   7. UTILITY: Get CSRF cookie (fallback)
══════════════════════════════════════════════════════ */
function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^|;\\s*)${name}=([^;]*)`));
  return match ? decodeURIComponent(match[2]) : null;
}


/* ══════════════════════════════════════════════════════
   8. TOOLTIP INIT
══════════════════════════════════════════════════════ */
(function initTooltips() {
  document.querySelectorAll('[title]').forEach(el => {
    // Only initialize Bootstrap tooltips on elements that have a title
    // and are not form elements or links (those use native title)
    if (el.tagName !== 'A' && el.tagName !== 'INPUT') {
      new bootstrap.Tooltip(el, { trigger: 'hover', placement: 'top' });
    }
  });
})();
