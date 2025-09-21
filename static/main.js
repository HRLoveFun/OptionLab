// Extracted JavaScript from index.html
// Handles options section, form persistence, ticker validation, and submission.

let currentPrice = null;

function toggleOptionsSection() {
    const content = document.getElementById('options-content');
    const icon = document.getElementById('options-toggle-icon');
    if (content.style.display === 'none' || content.style.display === '') {
        content.style.display = 'block';
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-up');
    } else {
        content.style.display = 'none';
        icon.classList.remove('fa-chevron-up');
        icon.classList.add('fa-chevron-down');
    }
}

function initializeOptionsTable() {
    const tbody = document.getElementById('options-tbody');
    tbody.innerHTML = '';
    addOptionRow();
}

function createOptionRow() {
    const row = document.createElement('tr');
    row.innerHTML = `
        <td>
            <select name="option_type" class="option-select">
                <option value="">Select Type</option>
                <option value="SC">Short Call</option>
                <option value="SP">Short Put</option>
                <option value="LC">Long Call</option>
                <option value="LP">Long Put</option>
            </select>
        </td>
        <td>
            <input type="number" name="strike" step="0.01" placeholder="${currentPrice || 'Strike'}" value="" class="strike-input">
        </td>
        <td>
            <input type="number" name="quantity" placeholder="Quantity" value="" class="quantity-input">
        </td>
        <td>
            <input type="number" name="premium" step="0.01" placeholder="Premium" value="" class="premium-input">
        </td>
        <td>
            <button type="button" class="btn-delete" onclick="deleteOptionRow(this)">
                <i class="fas fa-trash"></i>
            </button>
        </td>`;
    return row;
}

function addOptionRow() {
    const tbody = document.getElementById('options-tbody');
    const row = createOptionRow();
    tbody.appendChild(row);
    FormManager.saveState();
}

function deleteOptionRow(button) {
    const tbody = document.getElementById('options-tbody');
    const row = button.closest('tr');
    row.remove();
    if (tbody.children.length === 0) {
        addOptionRow();
    }
    FormManager.saveState();
}

const FormManager = {
    saveState() {
        const formData = {
            ticker: document.getElementById('ticker').value,
            start_time: this.normalizeMonth(document.getElementById('start_time').value),
            end_time: document.getElementById('end_time') ? this.normalizeMonth(document.getElementById('end_time').value) : '',
            frequency: document.getElementById('frequency').value,
            risk_threshold: document.getElementById('risk_threshold').value,
            side_bias: document.getElementById('side_bias').value,
            options: this.getOptionsData()
        };
        localStorage.setItem('marketAnalysisForm', JSON.stringify(formData));
    },
    loadState() {
        const saved = localStorage.getItem('marketAnalysisForm');
        if (!saved) return;
        try {
            const formData = JSON.parse(saved);
            if (formData.ticker) document.getElementById('ticker').value = formData.ticker;
            if (formData.start_time) document.getElementById('start_time').value = this.toMonthInput(formData.start_time);
            if (formData.end_time && document.getElementById('end_time')) document.getElementById('end_time').value = this.toMonthInput(formData.end_time);
            if (formData.frequency) document.getElementById('frequency').value = formData.frequency;
            if (formData.risk_threshold) document.getElementById('risk_threshold').value = formData.risk_threshold;
            if (formData.side_bias) document.getElementById('side_bias').value = formData.side_bias;
            // No periods checkboxes anymore
            if (formData.options && formData.options.length > 0) {
                this.restoreOptionsTable(formData.options);
            }
        } catch (e) {
            console.error('Error loading saved form state:', e);
        }
    },
    normalizeMonth(val) {
        // Accept 'YYYY-MM' (from month input) or 'YYYYMM'; return 'YYYYMM'
        if (!val) return '';
        const m = val.match(/^(\d{4})[-]?(\d{2})$/);
        return m ? `${m[1]}${m[2]}` : val;
    },
    toMonthInput(val) {
        // Convert 'YYYYMM' to 'YYYY-MM' for month input
        const m = val.match(/^(\d{4})(\d{2})$/);
        return m ? `${m[1]}-${m[2]}` : val;
    },
    validateHorizon() {
        const startVal = this.normalizeMonth(document.getElementById('start_time').value);
        const endVal = this.normalizeMonth(document.getElementById('end_time').value);
        const warning = document.getElementById('horizon-warning');
        warning.style.display = 'none';
        warning.textContent = '';
        if (startVal && endVal && endVal < startVal) {
            warning.textContent = 'End month must be the same or after Start month.';
            warning.style.display = 'block';
            return false;
        }
        return true;
    },
    getOptionsData() {
        const rows = document.querySelectorAll('#options-table tbody tr');
        const optionsData = [];
        rows.forEach(row => {
            const option_type = row.querySelector('select[name="option_type"]').value;
            const strike = row.querySelector('input[name="strike"]').value;
            const quantity = row.querySelector('input[name="quantity"]').value;
            const premium = row.querySelector('input[name="premium"]').value;
            if (option_type && strike && quantity && premium && parseFloat(strike) > 0 && parseInt(quantity) !== 0 && parseFloat(premium) > 0) {
                optionsData.push({ option_type, strike, quantity, premium });
            }
        });
        return optionsData;
    },
    restoreOptionsTable(optionsData) {
        const tbody = document.getElementById('options-tbody');
        tbody.innerHTML = '';
        const rowCount = Math.max(1, optionsData.length);
        for (let i = 0; i < rowCount; i++) {
            const row = createOptionRow();
            if (i < optionsData.length) {
                const option = optionsData[i];
                row.querySelector('select[name="option_type"]').value = option.option_type;
                row.querySelector('input[name="strike"]').value = option.strike;
                row.querySelector('input[name="quantity"]').value = option.quantity;
                row.querySelector('input[name="premium"]').value = option.premium;
            }
            tbody.appendChild(row);
        }
    }
};

let validationTimeout;
function validateTicker() {
    const ticker = document.getElementById('ticker').value.trim().toUpperCase();
    const validationDiv = document.getElementById('ticker-validation');
    if (!ticker) {
        validationDiv.innerHTML = '';
        currentPrice = null;
        updateStrikePlaceholders();
        return;
    }
    clearTimeout(validationTimeout);
    validationTimeout = setTimeout(() => {
        validationDiv.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Validating...';
        fetch('/api/validate_ticker', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker })
        })
        .then(response => response.json())
        .then(data => {
            if (data.valid) {
                validationDiv.innerHTML = '<i class="fas fa-check-circle"></i> Valid';
                validationDiv.className = 'ticker-validation valid';
                currentPrice = data.price || null;
            } else {
                validationDiv.innerHTML = '<i class="fas fa-exclamation-circle"></i> Invalid';
                validationDiv.className = 'ticker-validation invalid';
                currentPrice = null;
            }
            updateStrikePlaceholders();
        })
        .catch(() => {
            validationDiv.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
            validationDiv.className = 'ticker-validation warning';
            currentPrice = null;
            updateStrikePlaceholders();
        });
    }, 500);
}

function updateStrikePlaceholders() {
    document.querySelectorAll('.strike-input').forEach(input => {
        input.placeholder = currentPrice ? currentPrice.toString() : 'Strike';
    });
}

document.getElementById('analysis-form')?.addEventListener('submit', function(e) {
    e.preventDefault();
    if (!FormManager.validateHorizon()) {
        return; // Block submit on invalid horizon
    }
    FormManager.saveState();
    const optionsData = FormManager.getOptionsData();
    document.getElementById('option_position').value = JSON.stringify(optionsData);
    const submitBtn = this.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';
    submitBtn.disabled = true;
    this.submit();
    setTimeout(() => {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }, 30000);
});

document.addEventListener('DOMContentLoaded', function() {
    FormManager.loadState();
    // Validate horizon on load and on change
    FormManager.validateHorizon();
    ['start_time','end_time'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', () => {
                FormManager.validateHorizon();
                FormManager.saveState();
            });
        }
    });
    const tbody = document.getElementById('options-tbody');
    if (tbody && tbody.children.length === 0) {
        initializeOptionsTable();
    }
    const content = document.getElementById('options-content');
    if (content) content.style.display = 'none';
    const tickerInput = document.getElementById('ticker');
    if (tickerInput) tickerInput.addEventListener('input', validateTicker);
    document.querySelectorAll('input, select').forEach(el => {
        el.addEventListener('change', FormManager.saveState.bind(FormManager));
    });
    if (document.querySelector('.results-section')) {
        setTimeout(() => {
            document.querySelector('.results-section').scrollIntoView({ behavior: 'smooth' });
        }, 500);
    }
});
