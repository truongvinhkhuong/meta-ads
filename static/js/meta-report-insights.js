// Meta Report Insights Functions
let metaReportData = null;

// Format numbers for Vietnamese locale (check if already declared)
if (typeof VND_FMT === 'undefined') {
    window.VND_FMT = new Intl.NumberFormat('vi-VN',{ style:'currency', currency:'VND', maximumFractionDigits:0 });
}
if (typeof NUM_FMT === 'undefined') {
    window.NUM_FMT = new Intl.NumberFormat('vi-VN');
}

function initializeMetaReportInsights() {
    console.log('Initializing Meta Report Insights...');
    
    // Remove old local filters (we now use a single unified filter)
    try {
        const oldApply = document.getElementById('apply-filters-btn');
        if (oldApply) {
            oldApply.onclick = null;
        }
    } catch(_){}
    // Initialize Meta Report date controls (since/until)
    try {
        const mrPreset = document.getElementById('meta-report-date-preset');
        const mrCustom = document.getElementById('meta-report-custom-dates');
        const mrSince = document.getElementById('meta-report-since');
        const mrUntil = document.getElementById('meta-report-until');
        const mrApply = document.getElementById('meta-report-apply');
        if (mrPreset) {
            mrPreset.addEventListener('change', () => {
                if (mrPreset.value === 'custom') {
                    mrCustom && mrCustom.classList.remove('hidden');
                } else {
                    mrCustom && mrCustom.classList.add('hidden');
                }
            });
        }
        if (mrApply) {
            mrApply.addEventListener('click', () => {
                const params = {};
                const preset = mrPreset?.value || 'last_30d';
                if (preset === 'custom' && mrSince?.value && mrUntil?.value) {
                    params.date_preset = 'custom';
                    params.since = mrSince.value;
                    params.until = mrUntil.value;
                } else {
                    params.date_preset = preset;
                }
                loadMetaReportData(params);
            });
        }
    } catch (e) { console.warn('Meta Report date controls init error', e); }
    
    // Initialize the daily interaction chart
    initializeDailyInteractionChart();
    
    // Load initial data
    loadPageInsightsData();
    
    // Load agency report data
    loadAgencyReport();
    
    // Initialize agency report filters
    initializeAgencyReportFilters();
    
    // Initialize KPI Performance tracking
    initializeKPIPerformanceTracking();
    
    // Agency report will load real data automatically
    
    console.log('Meta Report Insights initialized successfully');
    
    // Test API connection
    testAPIConnection();
}

// Test API connection
async function testAPIConnection() {
    try {
        const response = await fetch('/api/test');
        const data = await response.json();
        console.log('API Test Result:', data);
    } catch (error) {
        console.error('API Test Failed:', error);
    }
}

// Initialize filter functionality
function initializeFilters() {
    const datePresetFilter = document.getElementById('date-preset-filter');
    const customDateInputs = document.getElementById('custom-date-inputs');
    const applyFiltersBtn = document.getElementById('apply-filters-btn');
    
    if (datePresetFilter) {
        datePresetFilter.addEventListener('change', function() {
            if (this.value === 'custom') {
                customDateInputs.classList.remove('hidden');
            } else {
                customDateInputs.classList.add('hidden');
            }
        });
    }
    
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', function() {
            loadPageInsightsData();
        });
    }
    
    // Demo data checkbox
    const useDemoDataCheckbox = document.getElementById('use-demo-data');
    if (useDemoDataCheckbox) {
        useDemoDataCheckbox.addEventListener('change', function() {
            loadPageInsightsData();
        });
    }
    
    // Set default date range
    const sinceDate = document.getElementById('since-date');
    const untilDate = document.getElementById('until-date');
    
    if (sinceDate && untilDate) {
        const endDate = new Date();
        const startDate = new Date();
        startDate.setDate(startDate.getDate() - 30);
        
        sinceDate.value = startDate.toISOString().split('T')[0];
        untilDate.value = endDate.toISOString().split('T')[0];
    }
}

// Initialize Daily Interaction Chart
function initializeDailyInteractionChart() {
    const ctx = document.getElementById('daily-interaction-chart');
    if (!ctx) return;
    
    // Sample data for the chart (matching the image)
    const dates = ['01/06', '05/06', '10/06', '15/06', '20/06', '25/06', '01/07', '05/07', '10/07', '15/07', '20/07', '25/07', '01/08', '05/08', '10/08', '15/08', '18/08', '19/08', '20/08', '25/08', '31/08', '03/09', '05/09', '10/09', '15/09', '20/09', '25/09', '29/09'];
    
    // Sample data for the chart
    const newLikes = [5, 8, 12, 15, 18, 22, 25, 28, 32, 35, 38, 42, 45, 48, 52, 55, 58, 61, 64, 67, 70, 73, 76, 79, 82, 85, 88, 91];
    const pageImpressions = [8000, 12000, 15000, 18000, 20000, 22000, 25000, 28000, 30000, 32000, 35000, 38000, 40000, 42000, 45000, 48000, 14135, 12958, 50000, 52000, 13097, 14813, 55000, 58000, 60000, 62000, 65000, 68000];
    const pagePostEngagements = [200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 488, 282, 1800, 1900, 332, 434, 2000, 2100, 2200, 2300, 2400, 2500];
    const postClicks = [100, 150, 200, 250, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800, 850, 0, 0, 900, 950, 1, 1182, 1000, 1050, 1100, 1150, 1200, 1250];
    
    // Destroy existing chart if it exists
    if (window.dailyInteractionChart) {
        window.dailyInteractionChart.destroy();
    }
    
    window.dailyInteractionChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'New likes',
                    data: newLikes,
                    borderColor: '#3b82f6',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.3,
                    pointRadius: 0,
                    pointHoverRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    display: true,
                    grid: {
                        display: false
                    },
                    ticks: {
                        maxTicksLimit: 10
                    }
                },
                y: {
                    display: true,
                    beginAtZero: true,
                    grid: {
                        color: '#e5e7eb'
                    },
                    ticks: {
                        callback: function(value) {
                            if (value >= 1000) {
                                return (value / 1000) + 'N';
                            }
                            return value;
                        }
                    }
                }
            },
            elements: {
                point: {
                    hoverRadius: 6
                }
            }
        }
    });
    
    // Add bar chart overlays for other metrics
    addBarOverlays(ctx, dates, pageImpressions, pagePostEngagements, postClicks);
}

// Add bar chart overlays to the existing chart
function addBarOverlays(ctx, dates, impressions, engagements, clicks) {
    const chart = window.dailyInteractionChart;
    if (!chart) return;
    
    // Add datasets for bar charts
    chart.data.datasets.push(
        {
            label: 'Page Impressions',
            data: impressions,
            type: 'bar',
            backgroundColor: 'rgba(156, 163, 175, 0.6)',
            borderColor: 'rgba(156, 163, 175, 1)',
            borderWidth: 1,
            yAxisID: 'y1'
        },
        {
            label: 'Page Post Engagements',
            data: engagements,
            type: 'bar',
            backgroundColor: 'rgba(244, 114, 182, 0.6)',
            borderColor: 'rgba(244, 114, 182, 1)',
            borderWidth: 1,
            yAxisID: 'y1'
        },
        {
            label: 'Post Clicks',
            data: clicks,
            type: 'bar',
            backgroundColor: 'rgba(251, 146, 60, 0.6)',
            borderColor: 'rgba(251, 146, 60, 1)',
            borderWidth: 1,
            yAxisID: 'y1'
        }
    );
    
    // Add secondary y-axis for bar charts
    chart.options.scales.y1 = {
        type: 'linear',
        display: true,
        position: 'right',
        grid: {
            drawOnChartArea: false,
        },
        ticks: {
            callback: function(value) {
                if (value >= 1000) {
                    return (value / 1000) + 'N';
                }
                return value;
            }
        }
    };
    
    chart.update();
}

// Load real data from API
async function loadPageInsightsData() {
    try {
        console.log('Loading page insights data...');
        
        // Get filter values
        const postType = document.getElementById('post-type-filter')?.value || 'all';
        const datePreset = document.getElementById('date-preset-filter')?.value || 'last_30d';
        const sinceDate = document.getElementById('since-date')?.value;
        const untilDate = document.getElementById('until-date')?.value;
        
        // Build API URL - sử dụng demo API nếu checkbox được chọn
        const useDemoData = document.getElementById('use-demo-data')?.checked || false;
        let apiUrl = useDemoData ? '/api/page-insights-demo?' : '/api/page-insights?';
        const params = new URLSearchParams();
        
        if (postType !== 'all') {
            params.append('post_type', postType);
        }
        
        if (datePreset === 'custom' && sinceDate && untilDate) {
            params.append('since', sinceDate);
            params.append('until', untilDate);
        } else {
            // Use preset dates
            const endDate = new Date();
            let startDate = new Date();
            
            switch (datePreset) {
                case 'last_90d':
                    startDate.setDate(startDate.getDate() - 90);
                    break;
                case 'last_180d':
                    startDate.setDate(startDate.getDate() - 180);
                    break;
                default: // last_30d
                    startDate.setDate(startDate.getDate() - 30);
                    break;
            }
            
            params.append('since', startDate.toISOString().split('T')[0]);
            params.append('until', endDate.toISOString().split('T')[0]);
        }
        
        apiUrl += params.toString();
        
        // Show loading state
        showLoadingState();
        
        // Fetch data
        const response = await fetch(apiUrl);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            throw new Error('Response is not JSON. Server may be returning an HTML error page.');
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        // Update UI with real data
        updatePageInsightsUI(data);
        updateDailyInteractionChartWithRealData(data);
        updateTopContentWithRealData(data);
        
        // Update date range display
        updateDateRangeDisplay(data.date_range);
        
        // Show demo data notice if using demo
        showDataSourceNotice(useDemoData);
        
        console.log('Page insights data loaded successfully');
        
    } catch (error) {
        console.error('Error loading page insights:', error);
        showErrorState(error.message);
    }
}

// Show loading state
function showLoadingState() {
    const loadingElements = [
        document.getElementById('total-likes'),
        document.getElementById('new-likes'),
        document.getElementById('page-impressions'),
        document.getElementById('page-video-views'),
        document.getElementById('post-engagement'),
        document.getElementById('post-clicks'),
        document.getElementById('post-comment'),
        document.getElementById('post-like-total')
    ];
    
    loadingElements.forEach(el => {
        if (el) el.textContent = '...';
    });
    
    // Update fanpage name display to loading state
    const nameDisplay = document.getElementById('fanpage-name-display');
    if (nameDisplay) {
        nameDisplay.textContent = 'Đang tải tên fanpage...';
        nameDisplay.className = 'px-2 py-1 bg-blue-50 border border-blue-200 rounded text-sm w-full text-blue-600';
    }
}

// Show error state
function showErrorState(message) {
    const errorElements = [
        document.getElementById('total-likes'),
        document.getElementById('new-likes'),
        document.getElementById('page-impressions'),
        document.getElementById('page-video-views'),
        document.getElementById('post-engagement'),
        document.getElementById('post-clicks'),
        document.getElementById('post-comment'),
        document.getElementById('post-like-total')
    ];
    
    errorElements.forEach(el => {
        if (el) el.textContent = 'Error';
    });
    
    // Update fanpage name display to error state
    const nameDisplay = document.getElementById('fanpage-name-display');
    if (nameDisplay) {
        nameDisplay.textContent = 'Lỗi tải dữ liệu';
        nameDisplay.className = 'px-2 py-1 bg-red-50 border border-red-200 rounded text-sm w-full text-red-600';
    }
    
    console.error('Error state:', message);
}

// Update page insights UI with real data
function updatePageInsightsUI(data) {
    const pageInfo = data.page_info || {};
    const summaryMetrics = data.summary_metrics || {};
    
    // Update fanpage name display
    const nameDisplay = document.getElementById('fanpage-name-display');
    if (nameDisplay) {
        if (pageInfo.name) {
            nameDisplay.textContent = pageInfo.name;
            nameDisplay.className = 'px-2 py-1 bg-green-50 border border-green-200 rounded text-sm w-full text-green-900 font-medium';
        } else {
            nameDisplay.textContent = 'Không có thông tin fanpage';
            nameDisplay.className = 'px-2 py-1 bg-gray-50 border border-gray-200 rounded text-sm w-full text-gray-500';
        }
    }
    
    // Update metric cards với dữ liệu thực tế
    updateElement('total-likes', formatNumber(pageInfo.fan_count || 0));
    updateElement('new-likes', formatNumber(pageInfo.new_like_count || 0));
    
    // Sử dụng post impressions nếu có, fallback về page impressions
    const displayImpressions = summaryMetrics.total_post_impressions || summaryMetrics.total_impressions || 0;
    updateElement('page-impressions', formatNumber(displayImpressions));
    
    updateElement('page-video-views', formatNumber(summaryMetrics.total_video_views || 0));
    
    // Sử dụng post engagements nếu có, fallback về page engagements
    const displayEngagements = summaryMetrics.total_post_engagements || summaryMetrics.total_engagements || 0;
    updateElement('post-engagement', formatNumber(displayEngagements));
    
    // Sử dụng dữ liệu thực tế từ posts
    updateElement('post-clicks', formatNumber(summaryMetrics.total_post_clicks || 0));
    updateElement('post-comment', formatNumber(Math.round(summaryMetrics.comments || 0))); // Sử dụng dữ liệu comment thực tế
    updateElement('post-like-total', formatNumber(summaryMetrics.total_post_reactions || 0));
}

// Update daily interaction chart with real data
function updateDailyInteractionChartWithRealData(data) {
    const dailyData = data.daily_data || [];
    
    if (dailyData.length === 0) return;
    
    // Sort by date
    dailyData.sort((a, b) => new Date(a.date) - new Date(b.date));
    
    const dates = dailyData.map(d => {
        const date = new Date(d.date);
        return `${date.getDate()}/${date.getMonth() + 1}`;
    });
    
    const newLikes = dailyData.map(d => d.page_impressions_unique || 0);
    const pageImpressions = dailyData.map(d => d.page_impressions || 0);
    const pagePostEngagements = dailyData.map(d => d.page_post_engagements || 0);
    const pageVideoViews = dailyData.map(d => d.page_video_views || 0);
    
    // Update existing chart
    if (window.dailyInteractionChart) {
        window.dailyInteractionChart.destroy();
    }
    
    const ctx = document.getElementById('daily-interaction-chart');
    if (!ctx) return;
    
    window.dailyInteractionChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'New likes',
                    data: newLikes,
                    borderColor: '#3b82f6',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.3,
                    pointRadius: 0,
                    pointHoverRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    display: true,
                    grid: {
                        display: false
                    },
                    ticks: {
                        maxTicksLimit: 10
                    }
                },
                y: {
                    display: true,
                    beginAtZero: true,
                    grid: {
                        color: '#e5e7eb'
                    },
                    ticks: {
                        callback: function(value) {
                            if (value >= 1000) {
                                return (value / 1000) + 'N';
                            }
                            return value;
                        }
                    }
                }
            }
        }
    });
    
    // Add bar overlays
    addBarOverlays(ctx, dates, pageImpressions, pagePostEngagements, pageVideoViews);
}

// Update top content with real data
function updateTopContentWithRealData(data) {
    const topPosts = data.top_posts || [];
    const contentTypes = data.content_types || {};
    
    // Debug: Log data for verification
    console.log('🔍 Loading TOP 5 CONTENT with real Facebook data:', {
        topPostsCount: topPosts.length,
        contentTypes: contentTypes
    });
    
    // Update content types table
    updateContentTypesTable(contentTypes);
    
    // Update top 5 content sections
    updateTopContentSection('impressions', topPosts, 'impressions');
    updateTopContentSection('likes', topPosts, 'engagement');
    updateTopContentSection('clicks', topPosts, 'clicks');
}

// Update content types table
function updateContentTypesTable(contentTypes) {
    const tbody = document.querySelector('.content-overview table tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    let total = 0;
    Object.entries(contentTypes).forEach(([type, count]) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900">${type}</td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900">${count}</td>
        `;
        tbody.appendChild(row);
        total += count;
    });
    
    // Add total row
    const totalRow = document.createElement('tr');
    totalRow.className = 'bg-gray-50 font-semibold';
    totalRow.innerHTML = `
        <td class="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">Total</td>
        <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-900">${total}</td>
    `;
    tbody.appendChild(totalRow);
}

// Update top content section
function updateTopContentSection(sectionType, posts, metric) {
    const section = document.querySelector(`[data-section="${sectionType}"]`);
    if (!section) {
        console.warn(`❌ Section with data-section="${sectionType}" not found`);
        return;
    }
    
    const top5 = posts.slice(0, 5);
    const container = section.querySelector('.space-y-2');
    if (!container) {
        console.warn(`❌ Container with class "space-y-2" not found in section ${sectionType}`);
        return;
    }
    
    // Debug: Log section update
    console.log(`✅ Updating ${sectionType} section with ${top5.length} posts using metric: ${metric}`);
    
    container.innerHTML = '';
    
    top5.forEach((post, index) => {
        const item = document.createElement('div');
        item.className = 'content-item cursor-pointer hover:bg-gray-50 transition-colors rounded-lg p-2';
        
        // Tạo link clickable
        const postLink = post.permalink_url || `https://facebook.com/${post.id}`;
        
        // Tạo icon cho từng loại post
        const getPostIcon = (type) => {
            switch(type) {
                case 'photo': return '📷';
                case 'video': return '🎥';
                case 'link': return '🔗';
                case 'status': return '💬';
                default: return '📄';
            }
        };
        
        // Tạo thumbnail từ hình ảnh thật hoặc icon
        const thumbnailHtml = post.thumbnail_url ? 
            `<img src="${post.thumbnail_url}" alt="Post thumbnail" class="w-8 h-8 rounded-full object-cover">` :
            `<div class="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                <span class="text-blue-600 text-xs">${getPostIcon(post.type)}</span>
            </div>`;

        item.innerHTML = `
            <div class="content-rank">${index + 1}</div>
            <div class="content-thumbnail">
                ${thumbnailHtml}
            </div>
            <div class="flex-1 min-w-0">
                <div class="text-sm font-medium text-gray-900 truncate">${post.type || 'Unknown'}</div>
                <div class="text-xs text-gray-600 line-clamp-2">${post.message || 'No message'}</div>
                <div class="text-xs text-gray-500 mt-1 flex gap-2 flex-wrap">
                    <span class="inline-block bg-gray-100 px-2 py-1 rounded-full">
                        ${formatNumber(post.impressions || 0)} impressions
                    </span>
                    <span class="inline-block bg-blue-100 px-2 py-1 rounded-full text-blue-700">
                        ${formatDate(post.created_time)}
                    </span>
                    ${post.likes_count ? `<span class="inline-block bg-red-100 px-2 py-1 rounded-full text-red-700">❤️ ${post.likes_count}</span>` : ''}
                    ${post.comments_count ? `<span class="inline-block bg-green-100 px-2 py-1 rounded-full text-green-700">💬 ${post.comments_count}</span>` : ''}
                </div>
            </div>
            <div class="text-right">
                <div class="text-sm font-semibold text-blue-600">${formatNumber(post[metric] || 0)}</div>
                <div class="text-xs text-gray-500">${metric}</div>
            </div>
        `;
        
        // Thêm event listener để mở link
        item.addEventListener('click', function() {
            window.open(postLink, '_blank');
        });
        
        // Thêm title để hiển thị full message khi hover
        item.title = `${post.message || 'No message'} - Click to view on Facebook`;
        
        container.appendChild(item);
    });
    
    // Add total
    const total = top5.reduce((sum, post) => sum + (post[metric] || 0), 0);
    const totalDiv = document.createElement('div');
    totalDiv.className = 'bg-gray-50 p-2 rounded text-sm font-semibold';
    totalDiv.textContent = `Total: ${formatNumber(total)}`;
    container.appendChild(totalDiv);
}

// Update date range display
function updateDateRangeDisplay(dateRange) {
    const display = document.getElementById('date-range-display');
    if (display && dateRange) {
        const since = new Date(dateRange.since);
        const until = new Date(dateRange.until);
        
        const formatDate = (date) => {
            return `${date.getDate()} thg ${date.getMonth() + 1}, ${date.getFullYear()}`;
        };
        
        display.textContent = `${formatDate(since)} - ${formatDate(until)}`;
    }
}

// Helper functions
function updateElement(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

// Format date for display
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    
    try {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        
        if (diffDays === 0) {
            return 'Hôm nay';
        } else if (diffDays === 1) {
            return 'Hôm qua';
        } else if (diffDays < 7) {
            return `${diffDays} ngày trước`;
        } else {
            return date.toLocaleDateString('vi-VN', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric'
            });
        }
    } catch (error) {
        return 'N/A';
    }
}

// Show data source notice
function showDataSourceNotice(isDemo) {
    // Remove existing notice
    const existingNotice = document.getElementById('data-source-notice');
    if (existingNotice) {
        existingNotice.remove();
    }
    
    if (isDemo) {
        const notice = document.createElement('div');
        notice.id = 'data-source-notice';
        notice.className = 'fixed top-4 right-4 bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-2 rounded shadow-lg z-50';
        notice.innerHTML = `
            <div class="flex items-center gap-2">
                <span>⚠️</span>
                <span class="text-sm font-medium">Demo Data Mode</span>
                <button onclick="this.parentElement.parentElement.remove()" class="text-yellow-600 hover:text-yellow-800">×</button>
            </div>
        `;
        document.body.appendChild(notice);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notice.parentElement) {
                notice.remove();
            }
        }, 5000);
    }
}

// Global filter integration
function updateMetaReportWithFilters(filterParams) {
    console.log('Updating Meta Report with filters:', filterParams);
    loadMetaReportData(filterParams);
}

async function loadMetaReportData(customParams = null) {
    try {
        console.log('Loading Meta Report data...');
        let preset = 'last_30d';
        let url = '/api/meta-report-insights';
        
        if (customParams) {
            // Use global filter parameters
            const params = new URLSearchParams();
            if (customParams.date_preset) params.append('date_preset', customParams.date_preset);
            if (customParams.since) params.append('since', customParams.since);
            if (customParams.until) params.append('until', customParams.until);
            if (customParams.campaign_id) params.append('campaign_id', customParams.campaign_id);
            if (customParams.brand) params.append('brand', customParams.brand);
            
            url += '?' + params.toString();
            preset = customParams.date_preset || 'last_30d';
        } else {
            // Use local Meta Report date filter
            const localPreset = document.getElementById('meta-report-date-preset')?.value || 'last_30d';
            const since = document.getElementById('meta-report-since')?.value;
            const until = document.getElementById('meta-report-until')?.value;
            const params = new URLSearchParams();
            if (localPreset === 'custom' && since && until) {
                params.append('date_preset', 'custom');
                params.append('since', since);
                params.append('until', until);
            } else {
                params.append('date_preset', localPreset);
            }
            preset = localPreset;
            url += `?${params.toString()}`;
        }
        
        const tbody = document.getElementById('meta-report-table');
        
        console.log('Preset:', preset, 'Table body found:', !!tbody);
        
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="14" class="px-6 py-4 text-center text-gray-500">Đang tải dữ liệu...</td></tr>';
        }
        
        const response = await fetch(url);
        console.log('API response status:', response.status);
        
        const data = await response.json();
        console.log('API response data:', data);
        
        if (data.error) {
            console.error('Meta Report Insights error:', data.error);
            let errorMessage = data.error;
            if (typeof data.error === 'object' && data.error.message) {
                errorMessage = data.error.message;
            }
            
            if (tbody) {
                tbody.innerHTML = `<tr><td colspan="14" class="px-6 py-4 text-center text-red-500">Lỗi: ${errorMessage}</td></tr>`;
            }
            return;
        }
        
        metaReportData = data;
        updateMetaReportTable(data);
        updateMetaReportSummaryCards(data);
        updateBrandAnalysis(data);
        updateContentAnalysis(data);
        createMetaReportCharts(data);
        
    } catch (error) {
        console.error('Error loading meta report data:', error);
        const tbody = document.getElementById('meta-report-table');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="14" class="px-6 py-4 text-center text-red-500">Lỗi kết nối khi tải dữ liệu</td></tr>';
        }
    }
}

async function loadMetaContentInsights(){
    try{
        const target = document.getElementById('meta-ai-content');
        const s = document.getElementById('meta-ai-since')?.value?.trim();
        const u = document.getElementById('meta-ai-until')?.value?.trim();
        if(target) target.textContent = 'Đang lấy bài viết và phân tích AI...';
        const qs = new URLSearchParams({ limit: '50' });
        if(s) qs.set('since', s);
        if(u) qs.set('until', u);
        const res = await fetch(`/api/meta-report-content-insights?${qs.toString()}`);
        const data = await res.json();
        if(data.error){
            target.textContent = `Lỗi: ${typeof data.error==='object'?JSON.stringify(data.error):data.error}`;
            return;
        }
        const raw = data.ai?.insights || 'Không có kết quả AI';
        const cleaned = sanitizeAIText(raw);
        target.innerHTML = renderAITextAsHtml(cleaned);
        renderMetaPostsCards(data.posts||[]);
    }catch(err){
        const target = document.getElementById('meta-ai-content');
        if(target) target.textContent = `Lỗi kết nối: ${err}`;
    }
}

function sanitizeAIText(text){
    if(!text) return '';
    // Remove markdown artifacts like repeated # and leading * spaces
    let t = text.replace(/[\t\r]+/g,'\n');
    // Normalize bullets: lines starting with * or - (remove asterisks)
    t = t.replace(/^\s*\*+\s+/gm, '• ');
    t = t.replace(/^\s*\-+\s+/gm, '• ');
    // Remove excessive ### while keeping heading markers for rendering
    t = t.replace(/\n{3,}/g, '\n\n');
    return t.trim();
}

// Agency report rendering
async function loadAgencyReport() {
    try {
        console.log('Loading agency report...');
        const wrap = document.getElementById('agency-funnel');
        if (!wrap) {
            console.error('agency-funnel element not found');
            return;
        }
        wrap.textContent = 'Đang tải phễu...';
        
        // Get month filter value
        const selectedMonth = document.getElementById('agency-month-select')?.value || '2025-09';
        
        // Build API URL with month filter
        let apiUrl = '/api/agency-report?';
        const params = new URLSearchParams();
        params.append('month', selectedMonth);
        
        apiUrl += params.toString();
        
        console.log('Fetching agency report with filters:', apiUrl);
        const res = await fetch(apiUrl);
        console.log('API response status:', res.status);
        const data = await res.json();
        console.log('API response data:', data);
        if (!res.ok || data.error) {
            console.error('API error:', data.error);
            console.log('Loading demo data instead...');
            loadAgencyReportDemo();
            return;
        }
        
        // Check if data is empty
        if (!data.groups || Object.keys(data.groups).length === 0) {
            console.log('No data available, loading demo data...');
            loadAgencyReportDemo();
            return;
        }
        // Process the data using the shared function
        processAgencyReportData(data);
        
        // Update month display
        updateAgencyMonthDisplay(selectedMonth);
    } catch (e) {
        console.error('loadAgencyReport error', e);
        // Fallback to demo data on any error
        console.log('Falling back to demo data due to error...');
        loadAgencyReportDemo();
    }
}

// Agency report is now loaded in initializeMetaReportInsights()

// Initialize agency report filters
function initializeAgencyReportFilters() {
    const monthSelect = document.getElementById('agency-month-select');
    const applyFiltersBtn = document.getElementById('agency-apply-filters-btn');
    
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', function() {
            loadAgencyReport();
        });
    }
    
    // Initialize PDF export button
    const exportPdfBtn = document.getElementById('agency-export-pdf-btn');
    if (exportPdfBtn) {
        exportPdfBtn.addEventListener('click', function() {
            exportAgencyReportToPDF();
        });
    }
    
    // Set default month display
    updateAgencyMonthDisplay('2025-09');
}

// Update agency month display
function updateAgencyMonthDisplay(selectedMonth) {
    const display = document.getElementById('agency-month-display');
    if (!display) return;
    
    // Format month display (e.g., "2025-08" -> "Tháng 08/2025")
    const [year, month] = selectedMonth.split('-');
    const monthNames = {
        '01': '01', '02': '02', '03': '03', '04': '04', '05': '05', '06': '06',
        '07': '07', '08': '08', '09': '09', '10': '10', '11': '11', '12': '12'
    };
    
    display.textContent = `Tháng ${monthNames[month]}/${year}`;
}

// Export agency report to PDF
async function exportAgencyReportToPDF() {
    try {
        console.log('Starting PDF export...');
        
        // Get the agency report section
        const agencyReportSection = document.querySelector('#agency-report-section');
        if (!agencyReportSection) {
            console.error('Agency report section not found');
            alert('Không tìm thấy phần báo cáo để xuất PDF');
            return;
        }
        
        // Show loading state
        const exportBtn = document.getElementById('agency-export-pdf-btn');
        const originalText = exportBtn.innerHTML;
        exportBtn.innerHTML = '<svg class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg> Đang xuất...';
        exportBtn.disabled = true;
        
        // Get current month for filename
        const selectedMonth = document.getElementById('agency-month-select')?.value || '2025-09';
        const [year, month] = selectedMonth.split('-');
        const monthNames = {
            '01': '01', '02': '02', '03': '03', '04': '04', '05': '05', '06': '06',
            '07': '07', '08': '08', '09': '09', '10': '10', '11': '11', '12': '12'
        };
        const monthDisplay = `Thang_${monthNames[month]}_${year}`;
        
        // Create a temporary container for better PDF layout
        const tempContainer = document.createElement('div');
        tempContainer.style.position = 'absolute';
        tempContainer.style.left = '-9999px';
        tempContainer.style.top = '0';
        tempContainer.style.width = '800px';
        tempContainer.style.backgroundColor = 'white';
        tempContainer.style.padding = '20px';
        tempContainer.style.fontFamily = 'Arial, sans-serif';
        
        // Clone the agency report section
        const clonedSection = agencyReportSection.cloneNode(true);
        
        // Remove the filter controls from the cloned version
        const filterControls = clonedSection.querySelector('.flex.items-center.gap-4');
        if (filterControls) {
            filterControls.remove();
        }
        
        // Add title and date
        const titleDiv = document.createElement('div');
        titleDiv.style.marginBottom = '20px';
        titleDiv.style.textAlign = 'center';
        titleDiv.innerHTML = `
            <h1 style="font-size: 24px; font-weight: bold; color: #1f2937; margin-bottom: 5px;">REPORT ĐẠI LÝ</h1>
            <p style="font-size: 14px; color: #6b7280;">Báo cáo hiệu suất phễu chuyển đổi - ${monthDisplay.replace('_', ' ')}</p>
            <p style="font-size: 12px; color: #9ca3af;">Xuất ngày: ${new Date().toLocaleDateString('vi-VN')}</p>
        `;
        
        tempContainer.appendChild(titleDiv);
        tempContainer.appendChild(clonedSection);
        document.body.appendChild(tempContainer);
        
        // Convert to canvas
        const canvas = await html2canvas(tempContainer, {
            scale: 2,
            useCORS: true,
            allowTaint: true,
            backgroundColor: '#ffffff',
            width: 800,
            height: tempContainer.scrollHeight
        });
        
        // Remove temporary container
        document.body.removeChild(tempContainer);
        
        // Create PDF
        const { jsPDF } = window.jspdf;
        const pdf = new jsPDF('p', 'mm', 'a4');
        const imgWidth = 210;
        const pageHeight = 295;
        const imgHeight = (canvas.height * imgWidth) / canvas.width;
        let heightLeft = imgHeight;
        
        let position = 0;
        
        // Add image to PDF
        pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, position, imgWidth, imgHeight);
        heightLeft -= pageHeight;
        
        // Add new pages if needed
        while (heightLeft >= 0) {
            position = heightLeft - imgHeight;
            pdf.addPage();
            pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, position, imgWidth, imgHeight);
            heightLeft -= pageHeight;
        }
        
        // Save PDF
        const fileName = `Report_Dai_Ly_${monthDisplay}.pdf`;
        pdf.save(fileName);
        
        console.log('PDF exported successfully:', fileName);
        
        // Reset button state
        exportBtn.innerHTML = originalText;
        exportBtn.disabled = false;
        
        // Show success message
        alert(`Đã xuất PDF thành công: ${fileName}`);
        
    } catch (error) {
        console.error('PDF export error:', error);
        alert('Có lỗi khi xuất PDF. Vui lòng thử lại.');
        
        // Reset button state
        const exportBtn = document.getElementById('agency-export-pdf-btn');
        if (exportBtn) {
            exportBtn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg> Xuất PDF';
            exportBtn.disabled = false;
        }
    }
}

// Demo data for agency report when API is not available
function loadAgencyReportDemo() {
    console.log('Loading agency report demo data...');
    const wrap = document.getElementById('agency-funnel');
    if (!wrap) {
        console.error('agency-funnel element not found for demo data');
        return;
    }
    console.log('agency-funnel element found, proceeding with demo data...');
    
    // Demo data
    const demoData = {
        funnel: [
            {'key': 'impressions', 'title': 'Lượt hiển thị', 'label': 'Hiển thị', 'total': 125000, 'delta_pct': 15.2},
            {'key': 'reach', 'title': 'Lượt tiếp cận', 'label': 'Tiếp cận', 'total': 85000, 'delta_pct': 8.5},
            {'key': 'engagement', 'title': 'Lượt tương tác', 'label': 'Tương tác', 'total': 12000, 'delta_pct': 22.1},
            {'key': 'link_clicks', 'title': 'Lượt click vào liên kết', 'label': 'Clicks', 'total': 3500, 'delta_pct': 18.3},
            {'key': 'messaging_starts', 'title': 'Bắt đầu trò chuyện', 'label': 'Quan tâm', 'total': 450, 'delta_pct': 12.7},
            {'key': 'purchases', 'title': 'Lượt mua trên Meta', 'label': 'Chuyển đổi', 'total': 85, 'delta_pct': 25.4}
        ],
        groups: {
            'display': [
                {'key': 'impressions', 'title': 'Lượt hiển thị', 'total': 125000, 'delta_pct': 15.2},
                {'key': 'reach', 'title': 'Lượt tiếp cận', 'total': 85000, 'delta_pct': 8.5},
                {'key': 'ctr', 'title': '%CTR (tất cả)', 'total': 2.8, 'delta_pct': 0.3}
            ],
            'engagement': [
                {'key': 'engagement', 'title': 'Lượt tương tác', 'total': 12000, 'delta_pct': 22.1},
                {'key': 'link_clicks', 'title': 'Lượt click vào liên kết', 'total': 3500, 'delta_pct': 18.3}
            ],
            'conversion': [
                {'key': 'messaging_starts', 'title': 'Bắt đầu trò chuyện qua tin nhắn', 'total': 450, 'delta_pct': 12.7},
                {'key': 'purchases', 'title': 'Lượt mua trên meta', 'total': 85, 'delta_pct': 25.4},
                {'key': 'purchase_value', 'title': 'Giá trị chuyển đổi từ lượt mua', 'total': 4250000, 'delta_pct': 28.9}
            ]
        },
        spend: 2500000,
        purchase_value: 4250000
    };
    
    // Process demo data the same way as real data
    console.log('Processing demo data...');
    processAgencyReportData(demoData);
    console.log('Demo data processing completed');
}

function processAgencyReportData(data) {
    const wrap = document.getElementById('agency-funnel');
    if (!wrap) return;
    
    // Ensure format functions are available
    if (typeof window.VND_FMT === 'undefined') {
        window.VND_FMT = new Intl.NumberFormat('vi-VN',{ style:'currency', currency:'VND', maximumFractionDigits:0 });
    }
    if (typeof window.NUM_FMT === 'undefined') {
        window.NUM_FMT = new Intl.NumberFormat('vi-VN');
    }
    
    // cache spend and revenue for annotations
    window.metaAgencyCacheSpend = Number(data.spend || 0);
    window.metaAgencyPurchaseValue = Number(data.purchase_value || 0);
    
    // Render SVG funnel chart with gradients, shadows and side annotations
    const funnel = (data.funnel || []).slice(0, 6);
    const max = Math.max(1, ...funnel.map(f => f.total || 0));
    const colors = ['#0ea5e9','#0bb49f','#f59e0b','#f97316','#ef4444','#8b5cf6'];
    const rect = wrap.getBoundingClientRect();
    const available = (rect.width || 680);
    // Use almost full width for the SVG; annotations live inside SVG now
    const W = Math.max(520, Math.floor(available - 40));
    const H = Math.max(280, 90 * funnel.length + 20);
    const topWidth = Math.floor(W * 0.86);
    const minWidth = Math.floor(W * 0.42);
    const stageHeight = Math.floor((H - 40) / funnel.length) - 6;
    const topX = (W - topWidth) / 2;

    // desired widths proportional to totals; enforce decreasing shape
    const target = funnel.map(s => Math.max(minWidth, (s.total / max) * topWidth));
    const widths = [];
    for (let i = 0; i < target.length; i++) {
        const prev = i === 0 ? topWidth : widths[i-1] - 10;
        widths.push(Math.max(minWidth, Math.min(prev, target[i])));
    }

    // defs: gradients and soft shadow
    const defs = () => {
        let g = '<defs>';
        g += `
        <filter id="funnelShadow" x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000000" flood-opacity="0.15"/>
        </filter>`;
        for (let i = 0; i < funnel.length; i++) {
            const c = colors[i%colors.length];
            g += `
                <linearGradient id="grad${i}" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="${c}" stop-opacity="0.95"/>
                    <stop offset="100%" stop-color="${c}" stop-opacity="0.75"/>
                </linearGradient>`;
        }
        g += '</defs>';
        return g;
    };

    let y = 20;
    let svg = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">`;
    svg += defs();
    // background subtle grid
    svg += `<rect x="0" y="0" width="${W}" height="${H}" fill="#ffffff"/>`;
    for (let i = 0; i < funnel.length; i++) {
        const wTop = i === 0 ? topWidth : widths[i-1];
        const wBot = widths[i];
        const xTop = (W - wTop) / 2;
        const xBot = (W - wBot) / 2;
        const h = stageHeight;
        const path = `M ${xTop} ${y} L ${xTop + wTop} ${y} L ${xBot + wBot} ${y + h} L ${xBot} ${y + h} Z`;
        svg += `<path d="${path}" fill="url(#grad${i})" stroke="#ffffff" stroke-width="2" filter="url(#funnelShadow)"/>`;
        // labels
        const label = funnel[i].title || '';
        const value = (funnel[i].total || 0).toLocaleString('vi-VN');
        svg += `<text x="${W/2}" y="${y + h/2 - 4}" text-anchor="middle" fill="#ffffff" font-size="13" font-weight="600">${label}</text>`;
        svg += `<text x="${W/2}" y="${y + h/2 + 14}" text-anchor="middle" fill="#ffffff" font-size="16" font-weight="700">${value}</text>`;
        // right side annotation with cost ratios (skip for first stage - impressions)
        if (i > 0) {
            const leftVal = funnel[i-1]?.total || funnel[i].total || 0;
            const rightVal = funnel[i].total || 0;
            const ratio = leftVal > 0 ? leftVal / rightVal : 0; // proxy if spend not available per stage
            // mapping labels for remaining stages from top to bottom
            const rightLabels = ['Tương tác','Quan tâm','Tiếp cận', 'Chuyển đổi','Doanh thu'];
            const labelRight = rightLabels[Math.min(i-1, rightLabels.length-1)] || '';
            const displayVal = (()=>{
                if(i===funnel.length-1){
                    // Last stage: revenue value
                    return (window.metaAgencyPurchaseValue||0).toLocaleString('vi-VN');
                }
                return ratio>0? ratio.toFixed(2): '0.00';
            })();
            const annX = Math.min(W - 20 - 240, xTop + wTop + 24);
            const annY = y + h/2 - 14;
            const boxW = 240;
            svg += `<line x1="${xTop + wTop - 4}" y1="${y + h/2}" x2="${annX - 8}" y2="${annY + 14}" stroke="#cbd5e1" stroke-width="1.5"/>`;
            svg += `<rect x="${annX}" y="${annY}" rx="8" ry="8" width="${boxW}" height="28" fill="#ffffff" stroke="#e2e8f0"/>`;
            svg += `<text x="${annX + 10}" y="${annY + 19}" fill="#334155" font-size="12">${labelRight}</text>`;
            svg += `<text x="${annX + boxW - 10}" y="${annY + 19}" text-anchor="end" fill="#0f172a" font-size="12" font-weight="700">${displayVal}</text>`;
        }
        y += h + 12;
    }
    svg += '</svg>';
    wrap.innerHTML = svg;

    // Fill metric groups
    const groups = data.groups || {};
    console.log('Processing groups:', groups);
    const g = (key, id, fmtPct=false) => {
        const group = groups[key] || [];
        const item = group.find(x=>x.key===id);
        console.log(`Looking for ${key}.${id}:`, item);
        return item || { total: 0, delta_pct: 0 };
    };
    const setVal = (el, val, isPct=false, isCurrency=false) => {
        const e = document.getElementById(el);
        if (!e) {
            console.warn(`Element ${el} not found`);
            return;
        }
        try {
            let displayValue = '';
            if (isPct) {
                displayValue = `${Number(val||0).toFixed(2)}%`;
            } else if (isCurrency) {
                if (window.VND_FMT && typeof window.VND_FMT.format === 'function') {
                    displayValue = window.VND_FMT.format(Number(val||0));
                } else {
                    displayValue = `${Number(val||0).toLocaleString('vi-VN')} VNĐ`;
                }
            } else {
                if (window.NUM_FMT && typeof window.NUM_FMT.format === 'function') {
                    displayValue = typeof val==='number'? window.NUM_FMT.format(val) : val;
                } else {
                    displayValue = typeof val==='number'? Number(val).toLocaleString('vi-VN') : val;
                }
            }
            e.textContent = displayValue;
            console.log(`Set ${el} to: ${displayValue} (original: ${val})`);
        } catch (error) {
            console.error(`Error setting value for ${el}:`, error);
            e.textContent = val || '0';
        }
    };
    const setDelta = (el, val) => {
        const e = document.getElementById(el);
        if (!e) return;
        // Remove percentage display for agency report as requested
        e.textContent = '';
        e.style.display = 'none';
    };

    const dImp = g('display','impressions');
    setVal('agency-display-impressions', dImp.total);
    setDelta('agency-display-impressions-delta', dImp.delta_pct);

    const dReach = g('display','reach');
    setVal('agency-display-reach', dReach.total);
    setDelta('agency-display-reach-delta', dReach.delta_pct);

    const dCtr = g('display','ctr');
    setVal('agency-display-ctr', dCtr.total, true);
    setDelta('agency-display-ctr-delta', dCtr.delta_pct);

    const eTotal = g('engagement','engagement');
    setVal('agency-engagement-total', eTotal.total);
    setDelta('agency-engagement-total-delta', eTotal.delta_pct);

    const eClicks = g('engagement','link_clicks');
    setVal('agency-engagement-clicks', eClicks.total);
    setDelta('agency-engagement-clicks-delta', eClicks.delta_pct);

    const cMsg = g('conversion','messaging_starts');
    setVal('agency-conv-messages', cMsg.total);
    setDelta('agency-conv-messages-delta', cMsg.delta_pct);

    const cPur = g('conversion','purchases');
    setVal('agency-conv-purchase', cPur.total);
    setDelta('agency-conv-purchase-delta', cPur.delta_pct);

    const cVal = g('conversion','purchase_value');
    setVal('agency-conv-value', cVal.total, false, true);
    setDelta('agency-conv-value-delta', cVal.delta_pct);
}

function renderAITextAsHtml(text){
    // Simple renderer: convert headings and bullets, and inline bold/italic
    const lines = text.split(/\n/);
    const html = [];
    for(const line of lines){
        if(/^\s*#{1,6}\s+/.test(line)){
            const lvl = (line.match(/^\s*(#{1,6})\s+/) || [,'#'])[1].length;
            const content = line.replace(/^\s*#{1,6}\s+/, '');
            html.push(`<div class="font-semibold mt-2 mb-1" style="font-size:${Math.max(16,22-(lvl*1))}px">${formatInline(content)}</div>`);
        } else if(/^\s*•\s+/.test(line)){
            html.push(`<div class="pl-3">• ${formatInline(line.replace(/^\s*•\s+/,''))}</div>`);
        } else if(line.trim().length===0){
            html.push('<div class="h-2"></div>');
        } else {
            html.push(`<div>${formatInline(line)}</div>`);
        }
    }
    return html.join('');
}

function escapeHtml(s){
    return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c]));
}

function formatInline(s){
    if(!s) return '';
    // Convert simple markdown bold/italic while keeping HTML safe
    let t = String(s);
    // Mark tokens to avoid escaping them
    t = t.replace(/\*\*(.+?)\*\*/g, '<<b>>$1<</b>>');
    t = t.replace(/\*(.+?)\*/g, '<<i>>$1<</i>>');
    // Escape HTML
    t = escapeHtml(t);
    // Restore tokens
    t = t.replace(/&lt;&lt;b&gt;&gt;/g, '<b>').replace(/&lt;&lt;\/b&gt;&gt;/g, '</b>');
    t = t.replace(/&lt;&lt;i&gt;&gt;/g, '<i>').replace(/&lt;&lt;\/i&gt;&gt;/g, '</i>');
    return t;
}

function renderMetaPostsCards(posts){
    const wrap = document.getElementById('meta-ai-posts');
    if(!wrap) return;
    wrap.innerHTML = '';
    const top = posts.slice(0,9).sort((a,b)=>{
        const as=(a.reactions_count||0)+(a.comments_count||0)+(a.shares_count||0);
        const bs=(b.reactions_count||0)+(b.comments_count||0)+(b.shares_count||0);
        return bs-as;
    });
    for(const p of top){
        const total = (p.reactions_count||0)+(p.comments_count||0)+(p.shares_count||0);
        const msg = (p.message||'').slice(0,160);
        const created = (p.created_time||'').replace('T',' ').split('+')[0];
        const link = p.permalink_url ? p.permalink_url : `https://facebook.com/${encodeURIComponent(p.id||'')}`;
        const card = document.createElement('a');
        card.href = link;
        card.target = '_blank';
        card.rel = 'noopener noreferrer';
        card.className = 'block meta-report-card hover:shadow-md border cursor-pointer';
        card.innerHTML = `
            <div class="text-sm text-gray-600 mb-1">${escapeHtml(created)}</div>
            <div class="font-medium text-gray-900 mb-2">${escapeHtml(msg)}</div>
            <div class="flex gap-4 text-sm">
                <div>👍 ${window.NUM_FMT.format(p.reactions_count||0)}</div>
                <div>💬 ${window.NUM_FMT.format(p.comments_count||0)}</div>
                <div>↗️ ${window.NUM_FMT.format(p.shares_count||0)}</div>
                <div class="ml-auto font-semibold">Tổng: ${window.NUM_FMT.format(total)}</div>
            </div>
        `;
        wrap.appendChild(card);
    }
}

function updateMetaReportTable(data) {
    const tbody = document.getElementById('meta-report-table');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (!data.monthly_data || data.monthly_data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="14" class="px-6 py-4 text-center text-gray-500">Không có dữ liệu</td></tr>';
        return;
    }
    
    data.monthly_data.forEach(month => {
        const row = document.createElement('tr');
        row.className = 'hover:bg-gray-50';
        
        // Calculate metrics
        const spend = parseFloat(month.spend || 0);
        const reach = parseInt(month.reach || 0);
        const impressions = parseInt(month.impressions || 0);
        const clicks = parseInt(month.clicks || 0);
        const engagement = parseInt(month.engagement || 0);
        const videoViews = parseInt(month.video_views || 0);
        const linkClicks = parseInt(month.link_clicks || 0);
        
        // Calculate derived metrics
        const ctr = impressions > 0 ? (clicks / impressions) * 100 : 0;
        const cpc = clicks > 0 ? spend / clicks : 0;
        const engagementRate = impressions > 0 ? (engagement / impressions) * 100 : 0;
        
        // Format brands and content formats
        const brandsText = month.brands ? month.brands.join(', ') : 'Unknown';
        const contentFormatsText = month.content_formats ? month.content_formats.join(', ') : 'Unknown';
        
        row.innerHTML = `
            <td class="px-2 py-3 whitespace-nowrap text-sm font-medium text-gray-900 sticky left-0 bg-white">
                ${month.month}
            </td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-500">${brandsText}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-500">${contentFormatsText}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${month.campaign_count}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900 font-medium">${window.VND_FMT.format(spend)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${window.NUM_FMT.format(reach)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${window.NUM_FMT.format(impressions)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${window.NUM_FMT.format(clicks)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${ctr.toFixed(2)}%</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${window.VND_FMT.format(cpc)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${window.NUM_FMT.format(engagement)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${engagementRate.toFixed(2)}%</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${window.NUM_FMT.format(videoViews)}</td>
            <td class="px-2 py-3 whitespace-nowrap text-sm text-gray-900">${window.NUM_FMT.format(linkClicks)}</td>
        `;
        
        tbody.appendChild(row);
    });
}

function updateMetaReportSummaryCards(data) {
    if (!data.monthly_data || data.monthly_data.length === 0) return;
    
    // Calculate totals
    let totalBrands = 0;
    let totalContentFormats = 0;
    let totalSpend = 0;
    let totalReach = 0;
    let totalEngagement = 0;
    let totalClicks = 0;
    let totalImpressions = 0;
    
    const allBrands = new Set();
    const allContentFormats = new Set();
    
    data.monthly_data.forEach(month => {
        totalSpend += parseFloat(month.spend || 0);
        totalReach += parseInt(month.reach || 0);
        totalEngagement += parseInt(month.engagement || 0);
        totalClicks += parseInt(month.clicks || 0);
        totalImpressions += parseInt(month.impressions || 0);
        
        if (month.brands) {
            month.brands.forEach(brand => allBrands.add(brand));
        }
        if (month.content_formats) {
            month.content_formats.forEach(format => allContentFormats.add(format));
        }
    });
    
    totalBrands = allBrands.size;
    totalContentFormats = allContentFormats.size;
    
    const avgCtr = totalImpressions > 0 ? (totalClicks / totalImpressions) * 100 : 0;
    
    // Update summary cards
    const elements = {
        'meta-total-brands': totalBrands,
        'meta-total-content-formats': totalContentFormats,
        'meta-total-spend': window.VND_FMT.format(totalSpend),
        'meta-total-reach': window.NUM_FMT.format(totalReach),
        'meta-total-engagement': window.NUM_FMT.format(totalEngagement),
        'meta-avg-ctr': avgCtr.toFixed(2) + '%'
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    });
}

function updateBrandAnalysis(data) {
    const brandList = document.getElementById('brand-analysis-list');
    if (!brandList || !data.brand_analysis) return;
    
    brandList.innerHTML = '';
    
    Object.entries(data.brand_analysis).forEach(([brand, analysis]) => {
        const div = document.createElement('div');
        div.className = 'meta-report-analysis-item';
        
        const spend = parseFloat(analysis.total_spend || 0);
        const impressions = parseInt(analysis.total_impressions || 0);
        const clicks = parseInt(analysis.total_clicks || 0);
        const engagement = parseInt(analysis.total_engagement || 0);
        
        const ctr = impressions > 0 ? (clicks / impressions) * 100 : 0;
        const engagementRate = impressions > 0 ? (engagement / impressions) * 100 : 0;
        
        div.innerHTML = `
            <div class="flex justify-between items-start">
                <div>
                    <div class="font-medium text-gray-900">${brand}</div>
                    <div class="text-xs text-gray-500">${analysis.campaign_count} campaigns</div>
                </div>
                <div class="text-right">
                    <div class="text-sm font-medium text-gray-900">${window.VND_FMT.format(spend)}</div>
                    <div class="text-xs text-gray-500">CTR: ${ctr.toFixed(2)}%</div>
                </div>
            </div>
            <div class="mt-2 text-xs text-gray-600">
                Reach: ${window.NUM_FMT.format(impressions)} | Engagement: ${window.NUM_FMT.format(engagement)} (${engagementRate.toFixed(2)}%)
            </div>
        `;
        
        brandList.appendChild(div);
    });
}

function updateContentAnalysis(data) {
    const contentList = document.getElementById('content-analysis-list');
    if (!contentList || !data.content_analysis) return;
    
    contentList.innerHTML = '';
    
    Object.entries(data.content_analysis).forEach(([format, analysis]) => {
        const div = document.createElement('div');
        div.className = 'meta-report-analysis-item';
        
        const spend = parseFloat(analysis.total_spend || 0);
        const impressions = parseInt(analysis.total_impressions || 0);
        const clicks = parseInt(analysis.total_clicks || 0);
        const engagement = parseInt(analysis.total_engagement || 0);
        const performanceScore = parseFloat(analysis.performance_score || 0);
        
        const ctr = impressions > 0 ? (clicks / impressions) * 100 : 0;
        const engagementRate = impressions > 0 ? (engagement / impressions) * 100 : 0;
        
        div.innerHTML = `
            <div class="flex justify-between items-start">
                <div>
                    <div class="font-medium text-gray-900">${format}</div>
                    <div class="text-xs text-gray-500">${analysis.campaign_count} campaigns</div>
                </div>
                <div class="text-right">
                    <div class="text-sm font-medium text-gray-900">Score: ${performanceScore.toFixed(2)}</div>
                    <div class="text-xs text-gray-500">CTR: ${ctr.toFixed(2)}%</div>
                </div>
            </div>
            <div class="mt-2 text-xs text-gray-600">
                Spend: ${window.VND_FMT.format(spend)} | Engagement: ${window.NUM_FMT.format(engagement)} (${engagementRate.toFixed(2)}%)
            </div>
        `;
        
        contentList.appendChild(div);
    });
}

function createMetaReportCharts(data) {
    // Brand Chart
    if (data.brand_analysis) {
        const brandCtx = document.getElementById('brand-chart');
        if (brandCtx) {
            const ctx = brandCtx.getContext('2d');
            if (window.charts && window.charts.brand) {
                window.charts.brand.destroy();
            }
            
            const brandEntries = Object.entries(data.brand_analysis).slice(0, 10);
            const brandLabels = brandEntries.map(([brand]) => brand);
            const brandSpend = brandEntries.map(([, analysis]) => parseFloat(analysis.total_spend || 0));
            
            window.charts = window.charts || {};
            window.charts.brand = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: brandLabels,
                    datasets: [{
                        label: 'Chi tiêu',
                        data: brandSpend,
                        backgroundColor: '#247ba0'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        }
    }
    
    // Content Format Chart
    if (data.content_analysis) {
        const contentCtx = document.getElementById('content-format-chart');
        if (contentCtx) {
            const ctx = contentCtx.getContext('2d');
            if (window.charts && window.charts.contentFormat) {
                window.charts.contentFormat.destroy();
            }
            
            const contentEntries = Object.entries(data.content_analysis).slice(0, 10);
            const contentLabels = contentEntries.map(([format]) => format);
            const contentScores = contentEntries.map(([, analysis]) => parseFloat(analysis.performance_score || 0));
            
            window.charts = window.charts || {};
            window.charts.contentFormat = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: contentLabels,
                    datasets: [{
                        data: contentScores,
                        backgroundColor: ['#247ba0', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#84cc16', '#f97316']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });
        }
    }
    
    // Monthly Trends Chart
    if (data.monthly_data && data.monthly_data.length > 0) {
        const trendsCtx = document.getElementById('monthly-trends-chart');
        if (trendsCtx) {
            const ctx = trendsCtx.getContext('2d');
            if (window.charts && window.charts.monthlyTrends) {
                window.charts.monthlyTrends.destroy();
            }
            
            const months = data.monthly_data.map(month => month.month);
            const spendData = data.monthly_data.map(month => parseFloat(month.spend || 0));
            const reachData = data.monthly_data.map(month => parseInt(month.reach || 0));
            const engagementData = data.monthly_data.map(month => parseInt(month.engagement || 0));
            
            window.charts = window.charts || {};
            window.charts.monthlyTrends = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: months,
                    datasets: [
                        {
                            label: 'Chi tiêu',
                            data: spendData,
                            borderColor: '#247ba0',
                            backgroundColor: 'rgba(36,123,160,0.1)',
                            tension: 0.3,
                            yAxisID: 'y'
                        },
                        {
                            label: 'Reach',
                            data: reachData,
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16,185,129,0.1)',
                            tension: 0.3,
                            yAxisID: 'y1'
                        },
                        {
                            label: 'Engagement',
                            data: engagementData,
                            borderColor: '#f59e0b',
                            backgroundColor: 'rgba(245,158,11,0.1)',
                            tension: 0.3,
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { type: 'linear', display: true, position: 'left' },
                        y1: { type: 'linear', display: true, position: 'right', grid: { drawOnChartArea: false } }
                    }
                }
            });
        }
    }
}

function exportMetaReportData() {
    if (!metaReportData || !metaReportData.monthly_data) {
        alert('Không có dữ liệu để export');
        return;
    }
    
    const rows = metaReportData.monthly_data.map(month => {
        const spend = parseFloat(month.spend || 0);
        const reach = parseInt(month.reach || 0);
        const impressions = parseInt(month.impressions || 0);
        const clicks = parseInt(month.clicks || 0);
        const engagement = parseInt(month.engagement || 0);
        const videoViews = parseInt(month.video_views || 0);
        const linkClicks = parseInt(month.link_clicks || 0);
        
        const ctr = impressions > 0 ? (clicks / impressions) * 100 : 0;
        const cpc = clicks > 0 ? spend / clicks : 0;
        const engagementRate = impressions > 0 ? (engagement / impressions) * 100 : 0;
        
        return {
            'Tháng': month.month,
            'Thương hiệu': month.brands ? month.brands.join(', ') : 'Unknown',
            'Định dạng nội dung': month.content_formats ? month.content_formats.join(', ') : 'Unknown',
            'Chiến dịch': month.campaign_count,
            'Chi tiêu': spend,
            'Reach': reach,
            'Impressions': impressions,
            'Clicks': clicks,
            'CTR': ctr,
            'CPC': cpc,
            'Engagement': engagement,
            'Engagement Rate': engagementRate,
            'Video Views': videoViews,
            'Link Clicks': linkClicks
        };
    });
    
    const csv = toCSV(rows);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `meta-report-insights-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
}

// KPI Performance Tracking Functions
function initializeKPIPerformanceTracking() {
    console.log('Initializing KPI Performance Tracking...');
    
    // Initialize KPI month filter
    const kpiMonthSelect = document.getElementById('kpi-month-select');
    const kpiApplyBtn = document.getElementById('kpi-apply-filters-btn');
    
    if (kpiApplyBtn) {
        kpiApplyBtn.addEventListener('click', function() {
            loadKPIPerformanceData();
        });
    }
    
    // Initialize KPI input listeners
    const kpiInputs = document.querySelectorAll('.kpi-target-input');
    kpiInputs.forEach(input => {
        input.addEventListener('input', function() {
            calculateKPIEffectiveness(this.dataset.metric);
        });
    });
    
    // Load initial KPI data
    loadKPIPerformanceData();
    
    console.log('KPI Performance Tracking initialized successfully');
}

// Load KPI Performance data
async function loadKPIPerformanceData() {
    try {
        console.log('Loading KPI Performance data...');
        
        // Get selected month
        const selectedMonth = document.getElementById('kpi-month-select')?.value || '2024-09';
        
        // Build API URL
        let apiUrl = '/api/kpi-performance?';
        const params = new URLSearchParams();
        params.append('month', selectedMonth);
        
        apiUrl += params.toString();
        
        console.log('Fetching KPI performance data:', apiUrl);
        const response = await fetch(apiUrl);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('KPI Performance API response:', data);
        
        if (data.error) {
            console.error('KPI Performance API error:', data.error);
            loadKPIPerformanceDemoData();
            return;
        }
        
        // Check if data is empty
        if (!data.metrics || Object.keys(data.metrics).length === 0) {
            console.log('No KPI data available, loading demo data...');
            loadKPIPerformanceDemoData();
            return;
        }
        
        // Update KPI table with real data
        updateKPITable(data.metrics);
        
        // Update month display
        updateKPIMonthDisplay(selectedMonth);
        
    } catch (error) {
        console.error('Error loading KPI performance data:', error);
        console.log('Falling back to demo data...');
        loadKPIPerformanceDemoData();
    }
}

// Load demo data for KPI Performance when API is not available
function loadKPIPerformanceDemoData() {
    console.log('Loading KPI Performance demo data...');
    
    // Demo data - these would come from your actual API in real implementation
    const demoMetrics = {
        reach: 85000,
        impressions: 125000,
        frequency: 1.47,
        video_plays: 45000,
        ctr: 2.8,
        interactions: 12000,
        message_conversations: 450,
        video_plays_2s: 38000,
        conversion_rate: 12.5,
        roas: 1.7
    };
    
    updateKPITable(demoMetrics);
    
    // Update month display
    const selectedMonth = document.getElementById('kpi-month-select')?.value || '2024-09';
    updateKPIMonthDisplay(selectedMonth);
}

// Update KPI table with actual data
function updateKPITable(metrics) {
    console.log('Updating KPI table with metrics:', metrics);
    
    // Update actual achieved values (first column)
    Object.entries(metrics).forEach(([metric, value]) => {
        const row = document.querySelector(`tr[data-metric="${metric}"]`) || 
                   document.querySelector(`tr .kpi-result[data-metric="${metric}"]`)?.closest('tr');
        
        if (row) {
            // Update the first column with actual value
            const firstCell = row.querySelector('td:first-child');
            if (firstCell) {
                const metricName = firstCell.textContent.trim();
                firstCell.innerHTML = `
                    <div class="text-sm font-medium text-gray-900">${metricName}</div>
                    <div class="text-lg font-bold text-blue-600">${formatKPINumber(metric, value)}</div>
                `;
            }
            
            // Store the actual value for calculation
            row.dataset.actualValue = value;
            
            // Calculate effectiveness if KPI target is set
            const kpiInput = row.querySelector('.kpi-target-input');
            if (kpiInput && kpiInput.value) {
                calculateKPIEffectiveness(metric);
            }
        }
    });
}

// Calculate KPI effectiveness
function calculateKPIEffectiveness(metric) {
    const row = document.querySelector(`tr .kpi-result[data-metric="${metric}"]`)?.closest('tr') ||
                document.querySelector(`tr[data-metric="${metric}"]`);
    
    if (!row) return;
    
    const actualValue = parseFloat(row.dataset.actualValue || 0);
    const kpiInput = row.querySelector('.kpi-target-input');
    const kpiTarget = parseFloat(kpiInput?.value || 0);
    
    if (kpiTarget <= 0) {
        // Reset result if no target set
        const resultDiv = row.querySelector('.kpi-result');
        if (resultDiv) {
            resultDiv.innerHTML = `
                <span class="kpi-value font-semibold">-</span>
                <span class="kpi-percentage">%</span>
            `;
            resultDiv.className = 'kpi-result';
        }
        return;
    }
    
    // Calculate effectiveness percentage
    const effectiveness = (actualValue / kpiTarget) * 100;
    
    // Update result display
    const resultDiv = row.querySelector('.kpi-result');
    if (resultDiv) {
        const valueSpan = resultDiv.querySelector('.kpi-value');
        const percentageSpan = resultDiv.querySelector('.kpi-percentage');
        
        if (valueSpan && percentageSpan) {
            valueSpan.textContent = effectiveness.toFixed(1);
            
            // Apply color coding based on effectiveness
            if (effectiveness >= 100) {
                // Achieved KPI - Green
                resultDiv.className = 'kpi-result bg-green-100 text-green-800 px-2 py-1 rounded font-semibold';
            } else {
                // Not achieved KPI - Red
                resultDiv.className = 'kpi-result bg-red-100 text-red-800 px-2 py-1 rounded font-semibold';
            }
        }
    }
}

// Format KPI numbers based on metric type
function formatKPINumber(metric, value) {
    const numValue = parseFloat(value);
    
    switch (metric) {
        case 'ctr':
        case 'conversion_rate':
            return `${numValue.toFixed(2)}%`;
        case 'frequency':
        case 'roas':
            return numValue.toFixed(2);
        case 'reach':
        case 'impressions':
        case 'video_plays':
        case 'interactions':
        case 'message_conversations':
        case 'video_plays_2s':
            if (numValue >= 1000000) {
                return `${(numValue / 1000000).toFixed(1)}M`;
            } else if (numValue >= 1000) {
                return `${(numValue / 1000).toFixed(1)}K`;
            }
            return numValue.toLocaleString('vi-VN');
        default:
            return numValue.toLocaleString('vi-VN');
    }
}

// Update KPI month display
function updateKPIMonthDisplay(selectedMonth) {
    const display = document.getElementById('kpi-month-display');
    if (!display) return;
    
    // Format month display (e.g., "2024-09" -> "Tháng 09/2024")
    const [year, month] = selectedMonth.split('-');
    const monthNames = {
        '01': '01', '02': '02', '03': '03', '04': '04', '05': '05', '06': '06',
        '07': '07', '08': '08', '09': '09', '10': '10', '11': '11', '12': '12'
    };
    
    display.textContent = `Tháng ${monthNames[month]}/${year}`;
}

// Save KPI targets to backend (for persistence)
async function saveKPITargets() {
    try {
        const targets = {};
        const kpiInputs = document.querySelectorAll('.kpi-target-input');
        
        kpiInputs.forEach(input => {
            if (input.value) {
                targets[input.dataset.metric] = parseFloat(input.value);
            }
        });
        
        const selectedMonth = document.getElementById('kpi-month-select')?.value || '2024-09';
        
        const response = await fetch('/api/kpi-targets', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                month: selectedMonth,
                targets: targets
            })
        });
        
        if (response.ok) {
            console.log('KPI targets saved successfully');
        } else {
            console.error('Failed to save KPI targets');
        }
        
    } catch (error) {
        console.error('Error saving KPI targets:', error);
    }
}

// Load saved KPI targets from backend
async function loadKPITargets() {
    try {
        const selectedMonth = document.getElementById('kpi-month-select')?.value || '2024-09';
        
        const response = await fetch(`/api/kpi-targets?month=${selectedMonth}`);
        
        if (response.ok) {
            const data = await response.json();
            
            if (data.targets) {
                Object.entries(data.targets).forEach(([metric, value]) => {
                    const input = document.querySelector(`.kpi-target-input[data-metric="${metric}"]`);
                    if (input) {
                        input.value = value;
                        calculateKPIEffectiveness(metric);
                    }
                });
            }
        }
        
    } catch (error) {
        console.error('Error loading KPI targets:', error);
    }
}
