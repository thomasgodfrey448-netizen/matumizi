/* =============================================
   MATUMIZI SYSTEM - Main JavaScript
   ============================================= */

document.addEventListener('DOMContentLoaded', function () {

  // ---- SIDEBAR TOGGLE ----
  const menuToggle = document.getElementById('menuToggle');
  const sidebar = document.getElementById('sidebar');
  const sidebarOverlay = document.getElementById('sidebarOverlay');

  if (menuToggle && sidebar) {
    menuToggle.addEventListener('click', function () {
      sidebar.classList.toggle('show');
      if (sidebarOverlay) sidebarOverlay.classList.toggle('show');
    });
  }

  if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', function () {
      sidebar.classList.remove('show');
      sidebarOverlay.classList.remove('show');
    });
  }

  // ---- AUTO-DISMISS ALERTS ----
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      alert.style.transition = 'opacity 0.5s ease';
      alert.style.opacity = '0';
      setTimeout(function () { alert.remove(); }, 500);
    }, 5000);
  });

  // ---- DYNAMIC ITEMS TABLE ----
  const addRowBtn = document.getElementById('addItemRow');
  const itemsBody = document.getElementById('itemsBody');
  const totalDisplay = document.getElementById('totalAmount');
  const totalInput = document.getElementById('totalAmountInput');

  function calculateTotal() {
    if (!itemsBody) return;
    let total = 0;
    const amountInputs = itemsBody.querySelectorAll('.item-amount');
    amountInputs.forEach(function (input) {
      const val = parseFloat(input.value) || 0;
      total += val;
    });
    if (totalDisplay) totalDisplay.textContent = formatNumber(total);
    if (totalInput) totalInput.value = total.toFixed(2);
  }

  function formatNumber(num) {
    return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function addItemRow() {
    if (!itemsBody) return;
    const rowCount = itemsBody.querySelectorAll('tr').length;
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${rowCount + 1}</td>
      <td><input type="text" name="item_description[]" class="form-control item-desc" placeholder="Description" required></td>
      <td><input type="number" name="item_amount[]" class="form-control item-amount" placeholder="0.00" step="0.01" min="0" required></td>
      <td><button type="button" class="btn-remove-row" onclick="removeRow(this)"><i class="fas fa-times"></i></button></td>
    `;
    itemsBody.appendChild(tr);
    tr.querySelector('.item-amount').addEventListener('input', calculateTotal);
    tr.querySelector('.item-desc').focus();
    updateRowNumbers();
  }

  window.removeRow = function (btn) {
    const tr = btn.closest('tr');
    if (itemsBody && itemsBody.querySelectorAll('tr').length > 1) {
      tr.remove();
      calculateTotal();
      updateRowNumbers();
    }
  };

  function updateRowNumbers() {
    if (!itemsBody) return;
    const rows = itemsBody.querySelectorAll('tr');
    rows.forEach(function (row, index) {
      const numCell = row.querySelector('td:first-child');
      if (numCell && !numCell.querySelector('input')) {
        numCell.textContent = index + 1;
      }
    });
  }

  if (addRowBtn) {
    addRowBtn.addEventListener('click', addItemRow);
  }

  // Attach listeners to existing rows
  if (itemsBody) {
    itemsBody.querySelectorAll('.item-amount').forEach(function (input) {
      input.addEventListener('input', calculateTotal);
    });
    calculateTotal();
  }

  // ---- DEPARTMENT -> APPROVER LOOKUP ----
  const deptSelect = document.getElementById('departmentSelect');
  const approverInfoBox = document.getElementById('approverInfoBox');

  if (deptSelect && approverInfoBox) {
    deptSelect.addEventListener('change', function () {
      const deptId = this.value;
      if (!deptId) {
        approverInfoBox.classList.remove('show');
        return;
      }
      fetch(`/expenses/api/approver/${deptId}/`)
        .then(function (res) { return res.json(); })
        .then(function (data) {
          if (data.success && data.approver_name) {
            let html = '<strong><i class="fas fa-user-check me-1"></i>First Approver:</strong><br>';
            html += `<span>${data.approver_name}`;
            if (data.approver_phone) html += ` &mdash; <i class="fas fa-phone"></i> ${data.approver_phone}`;
            html += '</span><br>';
            approverInfoBox.innerHTML = html;
            approverInfoBox.classList.add('show');
          } else {
            approverInfoBox.innerHTML = '<i class="fas fa-info-circle"></i> No first approver assigned for this department.';
            approverInfoBox.classList.add('show');
          }
        })
        .catch(function () {
          approverInfoBox.classList.remove('show');
        });
    });

    // Trigger on page load if dept already selected
    if (deptSelect.value) {
      deptSelect.dispatchEvent(new Event('change'));
    }
  }

  // ---- CONFIRM DELETE ----
  const deleteForms = document.querySelectorAll('.delete-form');
  deleteForms.forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (!confirm('Are you sure you want to delete this record? This action cannot be undone.')) {
        e.preventDefault();
      }
    });
  });

  // ---- MODAL HANDLING ----
  window.openModal = function (id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add('show');
  };

  window.closeModal = function (id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove('show');
  };

  document.querySelectorAll('.modal-overlay').forEach(function (overlay) {
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) overlay.classList.remove('show');
    });
  });

  // ---- FORM VALIDATION ----
  const expenseForm = document.getElementById('expenseForm');
  if (expenseForm) {
    expenseForm.addEventListener('submit', function (e) {
      const items = itemsBody ? itemsBody.querySelectorAll('tr') : [];
      let hasItem = false;
      items.forEach(function (row) {
        const desc = row.querySelector('.item-desc');
        const amt = row.querySelector('.item-amount');
        if (desc && desc.value.trim() && amt && parseFloat(amt.value) > 0) {
          hasItem = true;
        }
      });
      if (!hasItem) {
        e.preventDefault();
        showAlert('Please add at least one item with description and amount.', 'error');
      }
    });
  }

  // ---- INLINE ALERT ----
  window.showAlert = function (msg, type) {
    const container = document.getElementById('alertContainer');
    if (!container) return;
    const div = document.createElement('div');
    div.className = `alert alert-${type}`;
    div.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${msg}`;
    container.prepend(div);
    setTimeout(function () {
      div.style.opacity = '0';
      setTimeout(function () { div.remove(); }, 500);
    }, 5000);
  };

  // ---- TICKER PAUSE ON HOVER ----
  const ticker = document.querySelector('.ticker-text');
  if (ticker) {
    ticker.addEventListener('mouseenter', function () {
      ticker.style.animationPlayState = 'paused';
    });
    ticker.addEventListener('mouseleave', function () {
      ticker.style.animationPlayState = 'running';
    });
  }

  // ---- ACTIVE NAV ITEM ----
  const currentPath = window.location.pathname;
  document.querySelectorAll('.nav-item').forEach(function (link) {
    const href = link.getAttribute('href');
    if (href && currentPath.startsWith(href) && href !== '/') {
      link.classList.add('active');
    } else if (href === '/' && currentPath === '/') {
      link.classList.add('active');
    }
  });

});
