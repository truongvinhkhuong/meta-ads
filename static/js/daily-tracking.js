// JavaScript for Daily Tracking functionality

let dailyTrackingData = null;
let isPasswordUnlocked = false;

function initializeDailyTracking() {
    // Initialize password protection
    initializePasswordProtection();
    
    // Always start loading data in background so it's ready after unlock
    // UI remains covered by overlay until password is validated
    loadDailyTrackingData();
    
    // Event listeners
    document.getElementById('btn-refresh-daily').addEventListener('click', loadDailyTrackingData);
    document.getElementById('btn-export-daily').addEventListener('click', exportDailyData);
    document.getElementById('daily-date-preset').addEventListener('change', loadDailyTrackingData);
}

// Global filter integration
function updateDailyTrackingWithFilters(filterParams) {
    console.log('Updating daily tracking with filters:', filterParams);
    loadDailyTrackingData(filterParams);
}

async function refreshBudgetCache() {
    try {
        const button = event.target;
        const originalText = button.textContent;
        button.textContent = 'Đang cập nhật...';
        button.disabled = true;
        
        const response = await fetch('/api/refresh-budgets');
        const data = await response.json();
        
        if (data.success) {
            alert(`✅ Cập nhật thành công!\n- ${data.updated_count} campaigns được cập nhật\n- ${data.failed_count} campaigns thất bại\n\nCache sẽ được sử dụng trong 1 giờ tới.`);
            // Reload daily tracking data to show updated budget info
            loadDailyTrackingData();
        } else {
            alert(`❌ Lỗi: ${data.error}`);
        }
    } catch (error) {
        console.error('Error refreshing budget cache:', error);
        alert('❌ Lỗi kết nối khi cập nhật ngân sách');
    } finally {
        button.textContent = 'Cập nhật Ngân sách';
        button.disabled = false;
    }
}

async function loadDailyTrackingData(customParams = null) {
    try {
        // Allow data to load even when locked; UI is gated by overlay
        
        let preset = 'last_7d';
        let url = '/api/daily-tracking';
        
        if (customParams) {
            // Use global filter parameters
            const params = new URLSearchParams();
            if (customParams.date_preset) params.append('date_preset', customParams.date_preset);
            if (customParams.since) params.append('since', customParams.since);
            if (customParams.until) params.append('until', customParams.until);
            if (customParams.campaign_id) params.append('campaign_id', customParams.campaign_id);
            if (customParams.brand) params.append('brand', customParams.brand);
            
            url += '?' + params.toString();
            preset = customParams.date_preset || 'last_7d';
        } else {
            // Use local filter
            preset = document.getElementById('daily-date-preset').value || 'last_7d';
            url += `?date_preset=${encodeURIComponent(preset)}`;
        }
        
        const tbody = document.getElementById('daily-tracking-table');
        tbody.innerHTML = '<tr><td colspan="24" class="px-6 py-4 text-center text-gray-500">Đang tải dữ liệu...</td></tr>';
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.error) {
            console.error('Daily tracking error:', data.error);
            let errorMessage = data.error;
            if (typeof data.error === 'object' && data.error.message) {
                errorMessage = data.error.message;
            }
            
            // Check for token expiration
            if (errorMessage.includes('expired') || errorMessage.includes('Session has expired')) {
                errorMessage = 'Token Facebook đã hết hạn. Vui lòng cập nhật token mới trong file .env';
            }
            
            tbody.innerHTML = `<tr><td colspan="24" class="px-6 py-4 text-center text-red-500">Lỗi: ${errorMessage}</td></tr>`;
            return;
        }
        
        dailyTrackingData = data;
        updateDailyTrackingTable(data);
        updateDailySummaryCards(data);
        if (typeof updatePivotAdvanced === 'function') {
            try { updatePivotAdvanced(data); } catch (e) { console.error('updatePivotAdvanced error', e); }
        }
        
        // Show campaign status
        const statusEl = document.getElementById('campaign-status');
        if (data.total_campaigns > 0) {
            let statusText = `Đã tải ${data.successful_campaigns}/${data.processed_campaigns || data.total_campaigns} chiến dịch`;
            if (data.note) {
                statusText += ` (${data.note})`;
            }
            statusEl.textContent = statusText;
            statusEl.classList.remove('hidden');
            if (data.failed_campaigns > 0) {
                statusEl.classList.add('text-yellow-600');
                statusEl.classList.remove('text-blue-600');
            } else {
                statusEl.classList.add('text-green-600');
                statusEl.classList.remove('text-blue-600');
            }
        } else {
            statusEl.classList.add('hidden');
        }
    } catch (error) {
        console.error('Error loading daily tracking data:', error);
        const tbody = document.getElementById('daily-tracking-table');
        let errorMessage = 'Lỗi kết nối khi tải dữ liệu';
        
        if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
            errorMessage = 'Lỗi timeout - Dữ liệu quá lớn, vui lòng thử lại với date range nhỏ hơn';
        } else if (error.message.includes('timeout')) {
            errorMessage = 'Lỗi timeout - Vui lòng thử lại';
        }
        
        tbody.innerHTML = `<tr><td colspan="24" class="px-6 py-4 text-center text-red-500">${errorMessage}</td></tr>`;
    }
}

function updateDailyTrackingTable(data) {
    const tbody = document.getElementById('daily-tracking-table');
    tbody.innerHTML = '';
    
    if (!data.daily || data.daily.length === 0) {
        tbody.innerHTML = '<tr><td colspan="24" class="px-6 py-4 text-center text-gray-500">Không có dữ liệu</td></tr>';
        return;
    }
    
    data.daily.forEach(day => {
        const row = document.createElement('tr');
        row.className = 'hover:bg-gray-50';
        
        // Calculate metrics
        const spend = parseFloat(day.spend || 0);
        const reach = parseInt(day.reach || 0);
        const impressions = parseInt(day.impressions || 0);
        const clicks = parseInt(day.clicks || 0);
        const linkClicks = parseInt(day.inline_link_clicks || 0);
        const engagement = parseInt(day.post_engagement || 0);
        const messagingStarts = parseInt(day.messaging_contacts || day.messaging_starts || 0);
        const messagingNew = parseInt(day.messaging_new_contacts || 0);
        const purchases = parseInt(day.purchases || 0);
        const purchaseValue = parseFloat(day.purchase_value || 0);
        const frequency = parseFloat(day.frequency || 0);
        const videoViews = parseInt(day.video_views || 0);
        
        // Calculate derived metrics
        const ctr = impressions > 0 ? (clicks / impressions) * 100 : 0;
        const linkCtr = impressions > 0 ? (linkClicks / impressions) * 100 : 0;
        const cpc = clicks > 0 ? spend / clicks : 0;
        const linkCpc = linkClicks > 0 ? spend / linkClicks : 0;
        const cpm = impressions > 0 ? (spend / impressions) * 1000 : 0;
        const cpe = engagement > 0 ? spend / engagement : 0;
        const roas = spend > 0 ? purchaseValue / spend : 0;
        
        // Determine result based on objective (simplified)
        const result = linkClicks > 0 ? `${linkClicks} Link Clicks` : 
                      engagement > 0 ? `${engagement} Engagement` : 
                      `${clicks} Clicks`;
        
        const photoViews = parseInt(day.photo_view || 0);
        const video2sPlus = parseInt(day.video_2_sec_watched_actions || 0);
        const campaignCount = parseInt(day.campaign_count || 0);
        
        // Budget calculations
        const dailyBudget = parseFloat(day.daily_budget || 0);
        const lifetimeBudget = parseFloat(day.lifetime_budget || 0);
        const budgetRemaining = parseFloat(day.budget_remaining || 0);
        const totalBudget = dailyBudget + lifetimeBudget;
        const budgetUtilization = totalBudget > 0 ? (spend / totalBudget) * 100 : 0;
        
        row.innerHTML = `
            <td class="px-2 py-3 whitespace-nowrap text-sm font-medium text-gray-900 sticky left-0 bg-white">
                ${new Date(day.date_start || day.date).toLocaleDateString('vi-VN')}
            </td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-500">-</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900 font-medium">${VND_FMT.format(spend)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${totalBudget > 0 ? VND_FMT.format(totalBudget) : (budgetRemaining > 0 ? `Remaining: ${VND_FMT.format(budgetRemaining)}` : '-')}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${NUM_FMT.format(reach)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${NUM_FMT.format(impressions)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${frequency.toFixed(2)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${result}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${VND_FMT.format(cpc)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${NUM_FMT.format(messagingStarts)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${NUM_FMT.format(messagingNew)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${roas.toFixed(2)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${ctr.toFixed(2)}%</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${VND_FMT.format(cpm)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${NUM_FMT.format(engagement)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${NUM_FMT.format(linkClicks)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${linkCtr.toFixed(2)}%</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${VND_FMT.format(linkCpc)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${NUM_FMT.format(videoViews)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${NUM_FMT.format(photoViews)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${VND_FMT.format(cpe)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${NUM_FMT.format(video2sPlus)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${VND_FMT.format(purchaseValue)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${campaignCount}</td>
        `;
        
        tbody.appendChild(row);
    });
}

function updateDailySummaryCards(data) {
    if (!data.totals) return;
    
    const totals = data.totals;
    const spend = parseFloat(totals.spend || 0);
    const reach = parseInt(totals.reach || 0);
    const impressions = parseInt(totals.impressions || 0);
    const clicks = parseInt(totals.clicks || 0);
    const linkClicks = parseInt(totals.inline_link_clicks || 0);
    const engagement = parseInt(totals.post_engagement || 0);
    const messagingStarts = parseInt(totals.messaging_contacts || totals.messaging_starts || 0);
    const messagingNew = parseInt(totals.messaging_new_contacts || 0);
    const purchases = parseInt(totals.purchases || 0);
    const purchaseValue = parseFloat(totals.purchase_value || 0);
    
    // Calculate averages
    const avgCtr = impressions > 0 ? (clicks / impressions) * 100 : 0;
    const avgCpc = clicks > 0 ? spend / clicks : 0;
    const avgCpm = impressions > 0 ? (spend / impressions) * 1000 : 0;
    const avgRoas = spend > 0 ? purchaseValue / spend : 0;
    
    // Update summary cards
    document.getElementById('daily-total-spend').textContent = VND_FMT.format(spend);
    document.getElementById('daily-total-reach').textContent = NUM_FMT.format(reach);
    document.getElementById('daily-total-impressions').textContent = NUM_FMT.format(impressions);
    document.getElementById('daily-avg-ctr').textContent = avgCtr.toFixed(2) + '%';
    document.getElementById('daily-avg-cpc').textContent = VND_FMT.format(avgCpc);
    document.getElementById('daily-avg-cpm').textContent = VND_FMT.format(avgCpm);
    
    // Update summary section
    document.getElementById('summary-total-spend').textContent = VND_FMT.format(spend);
    document.getElementById('summary-total-reach').textContent = NUM_FMT.format(reach);
    document.getElementById('summary-total-impressions').textContent = NUM_FMT.format(impressions);
    document.getElementById('summary-avg-ctr').textContent = avgCtr.toFixed(2) + '%';
    document.getElementById('summary-avg-cpc').textContent = VND_FMT.format(avgCpc);
    document.getElementById('summary-avg-cpm').textContent = VND_FMT.format(avgCpm);
    document.getElementById('summary-total-messaging').textContent = NUM_FMT.format(messagingStarts);
    document.getElementById('summary-total-conversions').textContent = NUM_FMT.format(messagingNew);
    document.getElementById('summary-avg-roas').textContent = avgRoas.toFixed(2);
}

function exportDailyData() {
    if (!dailyTrackingData || !dailyTrackingData.daily) {
        alert('Không có dữ liệu để export');
        return;
    }
    
    const rows = dailyTrackingData.daily.map(day => {
        const spend = parseFloat(day.spend || 0);
        const reach = parseInt(day.reach || 0);
        const impressions = parseInt(day.impressions || 0);
        const clicks = parseInt(day.clicks || 0);
        const linkClicks = parseInt(day.inline_link_clicks || 0);
        const engagement = parseInt(day.post_engagement || 0);
        const messagingStarts = parseInt(day.messaging_contacts || day.messaging_starts || 0);
        const messagingNew = parseInt(day.messaging_new_contacts || 0);
        const purchases = parseInt(day.purchases || 0);
        const purchaseValue = parseFloat(day.purchase_value || 0);
        const frequency = parseFloat(day.frequency || 0);
        const videoViews = parseInt(day.video_views || 0);
        const photoViews = parseInt(day.photo_view || 0);
        const video2sPlus = parseInt(day.video_2_sec_watched_actions || 0);
        const campaignCount = parseInt(day.campaign_count || 0);
        
        const ctr = impressions > 0 ? (clicks / impressions) * 100 : 0;
        const linkCtr = impressions > 0 ? (linkClicks / impressions) * 100 : 0;
        const cpc = clicks > 0 ? spend / clicks : 0;
        const linkCpc = linkClicks > 0 ? spend / linkClicks : 0;
        const cpm = impressions > 0 ? (spend / impressions) * 1000 : 0;
        const cpe = engagement > 0 ? spend / engagement : 0;
        const roas = spend > 0 ? purchaseValue / spend : 0;
        
        return {
            'Ngày': new Date(day.date_start || day.date).toLocaleDateString('vi-VN'),
            'Phân phối': '-',
            'Tổng chi tiêu': spend,
            'Ngân sách': '-',
            'Reach': reach,
            'Impressions': impressions,
            'Tần suất': frequency,
            'Kết quả': linkClicks > 0 ? `${linkClicks} Link Clicks` : engagement > 0 ? `${engagement} Engagement` : `${clicks} Clicks`,
            'CPC': cpc,
            'Người liên hệ nhắn tin': messagingStarts,
            'Người liên hệ nhắn tin mới': messagingNew,
            'ROAS': roas,
            'CTR': ctr,
            'CPM': cpm,
            'Engagement': engagement,
            'Link Clicks': linkClicks,
            'Link CTR': linkCtr,
            'Link CPC': linkCpc,
            'Video Views': videoViews,
            'Photo Views': photoViews,
            'CPE': cpe,
            'Video 2s+': video2sPlus,
            'Purchase Value': purchaseValue,
            'Campaigns': campaignCount
        };
    });
    
    const csv = toCSV(rows);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `daily-tracking-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
}

// Initialize password protection
function initializePasswordProtection() {
    console.log('Initializing daily tracking password protection...');
    
    // Check if password is already stored in session
    const storedPassword = sessionStorage.getItem('daily-tracking-unlocked');
    if (storedPassword === 'true') {
        isPasswordUnlocked = true;
        hidePasswordOverlay();
        return;
    }
    
    // Set up password form event listener
    const passwordForm = document.getElementById('password-form');
    const passwordInput = document.getElementById('password-input');
    const passwordError = document.getElementById('password-error');
    
    if (passwordForm && passwordInput) {
        passwordForm.addEventListener('submit', function(e) {
            e.preventDefault();
            validatePassword();
        });
        
        // Clear error message when user starts typing
        passwordInput.addEventListener('input', function() {
            if (!passwordError.classList.contains('hidden')) {
                passwordError.classList.add('hidden');
            }
        });
        
        // Focus on password input when page loads
        passwordInput.focus();
    }
    
    // Set up lock/unlock button
    const lockUnlockBtn = document.getElementById('lock-unlock-btn');
    if (lockUnlockBtn) {
        lockUnlockBtn.addEventListener('click', function() {
            if (isPasswordUnlocked) {
                lockReport();
            } else {
                showPasswordOverlay();
            }
        });
        
        // Update button icon based on state
        updateLockButtonIcon();
    }
}

// Validate password
function validatePassword() {
    const passwordInput = document.getElementById('password-input');
    const passwordError = document.getElementById('password-error');
    const correctPassword = 'bbi1212';
    
    if (!passwordInput) return;
    
    const enteredPassword = passwordInput.value.trim();
    
    if (enteredPassword === correctPassword) {
        // Correct password
        isPasswordUnlocked = true;
        
        // Store in session storage
        sessionStorage.setItem('daily-tracking-unlocked', 'true');
        
        // Hide overlay
        hidePasswordOverlay();
        
        // If data already preloaded, just render-ready; otherwise fetch now
        if (!dailyTrackingData) {
            loadDailyTrackingData();
        }
        
        console.log('Daily tracking password validated successfully');
    } else {
        // Incorrect password
        passwordError.classList.remove('hidden');
        passwordInput.value = '';
        passwordInput.focus();
        
        // Shake animation for error feedback
        passwordInput.classList.add('animate-pulse');
        setTimeout(() => {
            passwordInput.classList.remove('animate-pulse');
        }, 500);
    }
}

// Hide password overlay
function hidePasswordOverlay() {
    const overlay = document.getElementById('password-protection-overlay');
    if (overlay) {
        overlay.style.opacity = '0';
        overlay.style.transform = 'scale(0.95)';
        
        setTimeout(() => {
            overlay.style.display = 'none';
        }, 300);
    }
    
    // Update lock button icon
    updateLockButtonIcon();
}

// Show password overlay
function showPasswordOverlay() {
    const overlay = document.getElementById('password-protection-overlay');
    if (overlay) {
        overlay.style.display = 'flex';
        overlay.style.opacity = '1';
        overlay.style.transform = 'scale(1)';
        
        // Clear password input and focus
        const passwordInput = document.getElementById('password-input');
        if (passwordInput) {
            passwordInput.value = '';
            passwordInput.focus();
        }
        
        // Hide error message
        const passwordError = document.getElementById('password-error');
        if (passwordError) {
            passwordError.classList.add('hidden');
        }
    }
}

// Lock the report
function lockReport() {
    isPasswordUnlocked = false;
    sessionStorage.removeItem('daily-tracking-unlocked');
    showPasswordOverlay();
    console.log('Daily tracking report locked');
}

// Update lock button icon
function updateLockButtonIcon() {
    const lockUnlockBtn = document.getElementById('lock-unlock-btn');
    if (!lockUnlockBtn) return;
    
    const icon = lockUnlockBtn.querySelector('svg path');
    if (!icon) return;
    
    if (isPasswordUnlocked) {
        // Show unlocked icon
        icon.setAttribute('d', 'M8 11V7a4 4 0 118 0m-4 8v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z');
        lockUnlockBtn.title = 'Khóa báo cáo';
        lockUnlockBtn.classList.remove('text-gray-500');
        lockUnlockBtn.classList.add('text-green-600');
    } else {
        // Show locked icon
        icon.setAttribute('d', 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z');
        lockUnlockBtn.title = 'Mở khóa báo cáo';
        lockUnlockBtn.classList.remove('text-green-600');
        lockUnlockBtn.classList.add('text-gray-500');
    }
}
