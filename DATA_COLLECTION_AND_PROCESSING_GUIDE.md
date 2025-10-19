## Kiến Trúc Thu Thập Dữ Liệu

### 1. Backend Data Collection 

#### Facebook Ads Extractor (`facebook_ads_extractor.py`)
- **Mục đích**: Lớp chính để thu thập dữ liệu từ Facebook API
- **Token Management**: Sử dụng User Token cho ad accounts và Page Token cho insights
- **API Configuration**: 
  - Base URL: `https://graph.facebook.com/v21.0`
  - Timeout: Có thể cấu hình thông qua `heroku_config.py`
  - Retry Strategy: Sử dụng HTTPAdapter với retry cho các lỗi 429, 500, 502, 503, 504

#### Quy Trình Thu Thập Dữ Liệu

**Bước 1: Kết Nối Và Xác Thực**
```python
def test_connection(self) -> bool:
    url = f"{self.base_url}/me/adaccounts"
    params = {
        'access_token': self.access_token,
        'fields': 'id,name'
    }
```

**Bước 2: Thu Thập Campaigns**
```python
def get_campaigns(self, account_id: str) -> List[Dict[str, Any]]:
    fields = 'id,name,status,objective,created_time,start_time,stop_time'
    limit = 100
```

**Bước 3: Thu Thập Insights**
```python
def get_campaign_insights(self, account_id: str, campaign_id: str) -> Dict[str, Any]:
    fields = 'campaign_name,impressions,clicks,spend,ctr,cpc,cpm,reach,frequency'
    date_preset = 'maximum'
    time_increment = 1
```

### 2. Data Structure

#### Campaign Data Structure
```json
{
  "extraction_date": "2024-01-01T00:00:00",
  "start_date": "2023-01-01",
  "campaigns": [
    {
      "account_id": "act_123456789",
      "campaign_id": "123456789",
      "campaign_name": "Campaign Name",
      "status": "ACTIVE",
      "objective": "CONVERSIONS",
      "created_time": "2023-01-15T00:00:00+0000",
      "start_time": "2023-01-15T00:00:00+0000",
      "stop_time": null,
      "page_id": "page_123",
      "page_name": "Page Name",
      "insights": {
        "campaign_name": "Campaign Name",
        "impressions": "150000",
        "clicks": "2500",
        "spend": "5000.00",
        "ctr": "1.67",
        "cpc": "2.00",
        "cpm": "33.33",
        "reach": "120000",
        "frequency": "1.25"
      }
    }
  ]
}
```

## Xử Lý Dữ Liệu Theo Từng Section

### 1. Dashboard Overview Section

#### Metric Cards
**Dữ liệu đầu vào**: `data.campaigns` từ API `/api/ads-data`

**Cách tính toán**:
```javascript
function updateDashboard(data) {
    const total = data.campaigns.length;
    const active = data.campaigns.filter(c => c.status === 'ACTIVE').length;
    const paused = total - active;
    
    document.getElementById('total-campaigns').textContent = total.toLocaleString();
    document.getElementById('active-campaigns').textContent = active.toLocaleString();
    document.getElementById('paused-campaigns').textContent = paused.toLocaleString();
}
```

**Kết quả hiển thị**:
- **Tổng số chiến dịch**: Đếm tổng số campaigns trong mảng
- **Đang hoạt động**: Đếm campaigns có status = 'ACTIVE'
- **Tạm dừng/khác**: Tổng - Active

#### Campaigns Table
**Dữ liệu đầu vào**: `data.campaigns`

**Xử lý**:
```javascript
function updateCampaignsTable(campaigns) {
    campaigns.forEach(c => {
        // Format dates
        const fmt = (s) => {
            if(!s) return '-';
            const d = new Date(s);
            return isNaN(d) ? s : d.toLocaleDateString('vi-VN');
        };
        
        // Format objective
        const titleCase = (s) => (s||'').toLowerCase()
            .replace(/_/g,' ')
            .replace(/\b\w/g, m => m.toUpperCase());
    });
}
```

### 2. Campaign Insights Section

#### Data Collection Process
**API Endpoint**: `/api/campaign-insights`

**Parameters**:
- `campaign_id`: ID của campaign cần lấy insights
- `status`: Trạng thái campaign
- `date_preset`: Khoảng thời gian (last_30d, last_90d, custom)
- `since`/`until`: Ngày bắt đầu/kết thúc (nếu custom)

#### Data Processing
```javascript
async function viewInsights(campaignId, status) {
    const response = await fetch(`/api/campaign-insights?campaign_id=${campaignId}&status=${status}&${q}`);
    const data = await response.json();
    
    // Update totals
    document.getElementById('insights-imp').textContent = (data.totals.impressions||0).toLocaleString('vi-VN');
    document.getElementById('insights-clicks').textContent = (data.totals.clicks||0).toLocaleString('vi-VN');
    document.getElementById('insights-spend').textContent = vndFmt.format(parseFloat(data.totals.spend||0));
}
```

#### Funnel Chart Calculation
```javascript
function renderFunnelChart(totals) {
    const impressions = parseInt(totals.impressions || 0);
    const clicks = parseInt(totals.clicks || 0);
    const linkClicks = parseInt(totals.inline_link_clicks || 0);
    const engagement = parseInt(totals.post_engagement || 0);
    const reach = parseInt(totals.reach || 0);
    const purchases = parseInt(totals.purchases || 0);
    const spend = parseFloat(totals.spend || 0);
    
    // Calculate cost metrics
    const cpm = impressions > 0 ? (spend / impressions) * 1000 : 0;
    const cpc = clicks > 0 ? spend / clicks : 0;
    const cpe = engagement > 0 ? spend / engagement : 0;
    const cpl = linkClicks > 0 ? spend / linkClicks : 0;
    const cpa = purchases > 0 ? spend / purchases : 0;
}
```

### 3. Daily Tracking Section

#### Data Collection
**API Endpoint**: `/api/daily-tracking`

**Parameters**:
- `date_preset`: Khoảng thời gian
- `campaign_id`: Lọc theo campaign (optional)
- `brand`: Lọc theo brand (optional)

#### Data Processing
```javascript
function updateDailyTrackingTable(data) {
    data.daily.forEach(day => {
        const spend = parseFloat(day.spend || 0);
        const reach = parseInt(day.reach || 0);
        const impressions = parseInt(day.impressions || 0);
        const clicks = parseInt(day.clicks || 0);
        const linkClicks = parseInt(day.inline_link_clicks || 0);
        const engagement = parseInt(day.post_engagement || 0);
        const messagingStarts = parseInt(day.messaging_contacts || day.messaging_starts || 0);
        const purchases = parseInt(day.purchases || 0);
        const purchaseValue = parseFloat(day.purchase_value || 0);
        
        // Calculate derived metrics
        const ctr = impressions > 0 ? (clicks / impressions) * 100 : 0;
        const linkCtr = impressions > 0 ? (linkClicks / impressions) * 100 : 0;
        const cpc = clicks > 0 ? spend / clicks : 0;
        const linkCpc = linkClicks > 0 ? spend / linkClicks : 0;
        const cpm = impressions > 0 ? (spend / impressions) * 1000 : 0;
        const cpe = engagement > 0 ? spend / engagement : 0;
        const roas = spend > 0 ? purchaseValue / spend : 0;
    });
}
```

#### Summary Cards Calculation
```javascript
function updateDailySummaryCards(data) {
    const totals = data.totals;
    const spend = parseFloat(totals.spend || 0);
    const reach = parseInt(totals.reach || 0);
    const impressions = parseInt(totals.impressions || 0);
    const clicks = parseInt(totals.clicks || 0);
    
    // Calculate averages
    const avgCtr = impressions > 0 ? (clicks / impressions) * 100 : 0;
    const avgCpc = clicks > 0 ? spend / clicks : 0;
    const avgCpm = impressions > 0 ? (spend / impressions) * 1000 : 0;
    const avgRoas = spend > 0 ? purchaseValue / spend : 0;
}
```

### 4. Meta Report Insights Section

#### Data Collection
**API Endpoints**:
- `/api/page-insights`: Dữ liệu tổng quan trang
- `/api/meta-report-content-insights`: Dữ liệu nội dung
- `/api/meta-report-insights`: Dữ liệu báo cáo meta
- `/api/agency-report`: Dữ liệu báo cáo đại lý

#### Page Insights Processing
```javascript
function updatePageInsightsUI(data) {
    const pageInfo = data.page_info || {};
    const summaryMetrics = data.summary_metrics || {};
    
    // Update metric cards với dữ liệu thực tế
    updateElement('total-likes', formatNumber(pageInfo.fan_count || 0));
    updateElement('new-likes', formatNumber(pageInfo.new_like_count || 0));
    
    // Sử dụng post impressions nếu có, fallback về page impressions
    const displayImpressions = summaryMetrics.total_post_impressions || summaryMetrics.total_impressions || 0;
    updateElement('page-impressions', formatNumber(displayImpressions));
}
```

#### Content Analysis Processing
```javascript
function updateContentTypesTable(contentTypes) {
    // Normalize label to plain post format
    const normalizeFormat = (label) => {
        if (!label) return 'status';
        const noEmoji = label.replace(/^([\p{Emoji}\uFE0F\u200D]+)\s*/u, '').trim();
        const l = noEmoji.toLowerCase();
        if (l.includes('reels')) return 'reels';
        if (l.includes('album')) return 'album';
        if (l.includes('video')) return 'video';
        if (l.includes('photo')) return 'photo';
        if (l.includes('link')) return 'link';
        return 'status';
    };
    
    // Aggregate counts by normalized format
    const aggregated = {};
    Object.entries(contentTypes).forEach(([format, count]) => {
        const clean = normalizeFormat(format);
        aggregated[clean] = (aggregated[clean] || 0) + (count || 0);
    });
}
```

#### Agency Report Processing
```javascript
function processAgencyReportData(data) {
    const funnel = (data.funnel || []).slice(0, 6);
    const max = Math.max(1, ...funnel.map(f => f.total || 0));
    
    // Calculate funnel metrics
    funnel.forEach(stage => {
        const spend = parseFloat(stage.spend || 0);
        const impressions = parseInt(stage.impressions || 0);
        const clicks = parseInt(stage.clicks || 0);
        
        // Calculate cost metrics
        const cpm = impressions > 0 ? (spend / impressions) * 1000 : 0;
        const cpc = clicks > 0 ? spend / clicks : 0;
    });
}
```

### 5. Pivot Advanced Section

#### Data Processing
```javascript
function updatePivotAdvanced(data) {
    if(!data || !data.daily) return;
    renderPivotAdvancedTable(data.daily);
    renderPivotAdvancedLine(data.daily);
    fetchPivotAdvancedBreakdowns();
}

function renderPivotAdvancedTable(rows) {
    let totalSpend = 0, totalReach = 0, totalImpr = 0, totalNew = 0, totalEng = 0, totalPV = 0;
    
    rows.forEach(day => {
        const spend = safeFloat(day.spend);
        const reach = safeInt(day.reach);
        const impr = safeInt(day.impressions);
        const newMsg = safeInt(day.messaging_new_contacts || 0);
        const eng = safeInt(day.post_engagement || 0);
        const pv = safeFloat(day.purchase_value || 0);
        
        // Calculate derived metrics
        const cpm = impr > 0 ? (spend/impr)*1000 : 0;
        const cpc = safeInt(day.clicks) > 0 ? (spend/safeInt(day.clicks)) : 0;
        const cpNew = newMsg > 0 ? (spend/newMsg) : 0;
        
        totalSpend += spend;
        totalReach += reach;
        totalImpr += impr;
        totalNew += newMsg;
        totalEng += eng;
        totalPV += pv;
    });
}
```

#### Breakdown Analysis
```javascript
async function fetchPivotAdvancedBreakdowns() {
    const res = await fetch(`/api/daily-breakdowns?date_preset=${encodeURIComponent(preset)}`);
    const d = await res.json();
    
    if(d.error) return;
    
    renderPivotAdvancedPies('pivot-adv-pie-gender', d.gender);
    renderPivotAdvancedPies('pivot-adv-pie-age', d.age);
    renderPivotAdvancedPies('pivot-adv-pie-geo', d.country);
    renderPivotAdvancedDistTable('pivot-adv-gender-tb', d.gender, 'Gender');
    renderPivotAdvancedDistTable('pivot-adv-age-tb', d.age, 'Age Range');
    renderPivotAdvancedDistTable('pivot-adv-geo-tb', d.country, 'Region');
}
```

## Global Filters System

### Filter Data Structure
```javascript
this.filters = {
    datePreset: 'last_30d',
    dateFrom: null,
    dateTo: null,
    brand: 'all',
    campaign: 'all',
    adset: 'all',
    ad: 'all'
};
```

### Filter Processing
```javascript
function handleGlobalFilterChange(filterParams, filters) {
    let filteredCampaigns = adsData.campaigns;
    
    // Apply brand filter
    if (filters.brand !== 'all') {
        filteredCampaigns = filteredCampaigns.filter(campaign => {
            const campaignName = campaign.campaign_name || '';
            return extractBrandFromCampaignName(campaignName) === filters.brand;
        });
    }
    
    // Apply campaign filter
    if (filters.campaign !== 'all') {
        filteredCampaigns = filteredCampaigns.filter(campaign => 
            campaign.campaign_id === filters.campaign
        );
    }
    
    // Update dashboard with filtered data
    updateCampaignsTable(filteredCampaigns);
    createCharts(filteredCampaigns);
}
```

## Data Refresh Mechanism

### Manual Refresh Process
```javascript
async function refreshData() {
    // Start background refresh
    const res = await fetch('/api/refresh', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({start_date: '2023-01-01'})
    });
    
    // Poll for status updates
    await pollRefreshStatus();
    
    // Reload data after completion
    await loadAdsData();
}
```

### Polling Status
```javascript
async function pollRefreshStatus(btn) {
    const pollInterval = setInterval(async () => {
        const res = await fetch('/api/refresh-status');
        const status = await res.json();
        
        btn.textContent = `${status.message} (${status.progress}%)`;
        
        if (status.status === 'completed') {
            clearInterval(pollInterval);
            btn.textContent = 'Hoàn thành!';
        }
    }, 2000);
}
```

## Error Handling và Fallback

### Token Expiration Handling
```javascript
if (errorMessage.includes('expired') || errorMessage.includes('Session has expired')) {
    errorMessage = 'Token Facebook đã hết hạn. Vui lòng cập nhật token mới trong file .env';
} else if (errorMessage.includes('190')) {
    errorMessage = 'Token Facebook không hợp lệ hoặc đã hết hạn. Vui lòng cập nhật token mới.';
}
```

### Demo Data Fallback
```javascript
if (!data.get('campaigns') || len(data['campaigns']) == 0) {
    logger.warning("Không tìm thấy chiến dịch nào trong tài khoản quảng cáo.");
    logger.info("Tạo dữ liệu mẫu để demo dashboard...");
    sample_data = extractor.generate_sample_data();
    extractor.save_to_json(sample_data, "ads_data.json");
}
```

## Performance Optimization

### Caching Strategy
- **Budget Cache**: Sử dụng `budget_cache.json` để lưu trữ thông tin ngân sách
- **Page Cache**: Cache thông tin trang để tránh gọi API lặp lại
- **Session Storage**: Lưu trữ trạng thái filter trong session

### Rate Limiting
```javascript
// Check for rate limit error
if (adsetsJson.error.code === 17 || adsetsJson.error.message?.includes('request limit')) {
    console.warn('Facebook API rate limit reached. Please wait before making more requests.');
    this.showApiLimitMessage('adsets');
}
```

## Security Features

### Password Protection
```javascript
function validatePassword() {
    const correctPassword = 'bbi1212';
    const enteredPassword = passwordInput.value.trim();
    
    if (enteredPassword === correctPassword) {
        isPasswordUnlocked = true;
        sessionStorage.setItem('daily-tracking-unlocked', 'true');
        hidePasswordOverlay();
    }
}
```

### Data Sanitization
```javascript
function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }[c]));
}
```

## Export Functionality

### CSV Export
```javascript
function exportDailyData() {
    const rows = dailyTrackingData.daily.map(day => {
        return {
            'Ngày': new Date(day.date_start || day.date).toLocaleDateString('vi-VN'),
            'Tổng chi tiêu': spend,
            'Reach': reach,
            'Impressions': impressions,
            'CTR': ctr,
            'CPC': cpc,
            // ... other fields
        };
    });
    
    const csv = toCSV(rows);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `daily-tracking-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
}
```

