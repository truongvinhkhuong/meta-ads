// Main JavaScript file for Facebook Ads Dashboard

let adsData = null;
let charts = {};

document.addEventListener('DOMContentLoaded', function() {
    loadAdsData();
    initializeChatbot();
    initializeDailyTracking();
    
    // Initialize global filters integration
    if (window.globalFilters) {
        window.globalFilters.onFilterChange(handleGlobalFilterChange);
    }
});

async function loadAdsData() {
    try {
        const response = await fetch('/api/ads-data');
        adsData = await response.json();
        if (adsData.error) return;
        updateDashboard(adsData);
    } catch (e) { 
        console.error(e); 
    }
}

function updateDashboard(data) {
    const lastUpdate = document.getElementById('last-update');
    if (data.extraction_date) {
        const d = new Date(data.extraction_date);
        lastUpdate.textContent = d.toLocaleString('vi-VN');
    }
    const total = data.campaigns.length;
    const active = data.campaigns.filter(c => c.status === 'ACTIVE').length;
    const paused = total - active;
    document.getElementById('total-campaigns').textContent = total.toLocaleString();
    document.getElementById('active-campaigns').textContent = active.toLocaleString();
    document.getElementById('paused-campaigns').textContent = paused.toLocaleString();
    updateCampaignsTable(data.campaigns);
    createCharts(data.campaigns);
}

// Global filter change handler
function handleGlobalFilterChange(filterParams, filters) {
    console.log('Global filter changed:', filterParams, filters);
    
    // Apply filters to campaigns table
    if (adsData && adsData.campaigns) {
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
        
        // Update metric cards
        const total = filteredCampaigns.length;
        const active = filteredCampaigns.filter(c => c.status === 'ACTIVE').length;
        const paused = total - active;
        document.getElementById('total-campaigns').textContent = total.toLocaleString();
        document.getElementById('active-campaigns').textContent = active.toLocaleString();
        document.getElementById('paused-campaigns').textContent = paused.toLocaleString();
    }
    
    // Trigger other sections to update with new filters
    if (typeof updateDailyTrackingWithFilters === 'function') {
        updateDailyTrackingWithFilters(filterParams);
    }
    
    if (typeof updateMetaReportWithFilters === 'function') {
        updateMetaReportWithFilters(filterParams);
    }
    
    if (typeof updatePivotAdvancedWithFilters === 'function') {
        updatePivotAdvancedWithFilters(filterParams);
    }
}

// Helper function to extract brand from campaign name (same as backend)
function extractBrandFromCampaignName(campaignName) {
    if (!campaignName) return 'Unknown';
    
    const nameLower = campaignName.toLowerCase();
    
    if (nameLower.includes('ls2')) return 'LS2';
    if (nameLower.includes('bulldog')) return 'Bulldog';
    if (nameLower.includes('ego')) return 'EGO';
    return 'Unknown';
}

// Manual refresh
document.addEventListener('DOMContentLoaded',()=>{
    const btn=document.getElementById('btn-refresh');
    if(btn){
        btn.addEventListener('click',async ()=>{
            btn.disabled=true; 
            btn.textContent='Đang khởi tạo...';
            try{
                // Start background refresh
                const res=await fetch('/api/refresh',{
                    method:'POST',
                    headers:{'Content-Type':'application/json'},
                    body:JSON.stringify({start_date:'2023-01-01'})
                });
                
                if(!res.ok){
                    if(res.status !== 503) {
                        console.error(`API refresh failed: ${res.status} ${res.statusText}`);
                    }
                    alert('Không thể khởi tạo refresh: Service Unavailable'); 
                    return;
                }
                
                const j=await res.json();
                if(!j.ok){ 
                    alert('Không thể khởi tạo refresh: '+(j.error||'unknown')); 
                    return;
                }
                
                // Poll for status updates
                await pollRefreshStatus(btn);
                await loadAdsData();
                
            }catch(e){ 
                if(!e.message?.includes('503') && !e.message?.includes('Service Unavailable')) {
                    console.error('Refresh error:', e);
                }
                alert('Lỗi kết nối khi cập nhật'); 
            }
            finally{ 
                btn.disabled=false; 
                btn.textContent='Cập nhật dữ liệu'; 
            }
        });
    }
});

// Poll refresh status function
async function pollRefreshStatus(btn) {
    return new Promise((resolve, reject) => {
        const pollInterval = setInterval(async () => {
            try {
                const res = await fetch('/api/refresh-status');
                if (!res.ok) {
                    clearInterval(pollInterval);
                    reject(new Error('Failed to get refresh status'));
                    return;
                }
                
                const status = await res.json();
                
                // Update button text with progress
                btn.textContent = `${status.message} (${status.progress}%)`;
                
                if (status.status === 'completed') {
                    clearInterval(pollInterval);
                    btn.textContent = 'Hoàn thành!';
                    resolve(status);
                } else if (status.status === 'error') {
                    clearInterval(pollInterval);
                    reject(new Error(status.error || 'Unknown error'));
                }
                // Continue polling if still running
                
            } catch (e) {
                clearInterval(pollInterval);
                reject(e);
            }
        }, 2000); // Poll every 2 seconds
        
        // Timeout after 10 minutes
        setTimeout(() => {
            clearInterval(pollInterval);
            reject(new Error('Refresh timeout'));
        }, 600000);
    });
}

function computeKetQua(c){
    // Kết quả theo mục tiêu: ưu tiên link clicks, engagement, video views
    const ins=c.insights||{};
    const obj=(c.objective||'').toUpperCase();
    if(obj.includes('TRAFFIC')){
        return `${(ins.inline_link_clicks||ins.clicks||0)} Link clicks`;
    }
    if(obj.includes('ENGAGEMENT')){
        const pe=ins.post_engagement||0; 
        return `${pe} Engagement`;
    }
    if(obj.includes('VIDEO')){
        const vv=ins.video_views||ins.video_play_actions||0; 
        return `${vv} Video views`;
    }
    return `${ins.clicks||0} Clicks`;
}

function updateCampaignsTable(campaigns) {
    const tbody = document.getElementById('campaigns-table');
    tbody.innerHTML = '';
    campaigns.forEach(c => {
        const tr = document.createElement('tr');
        const fmt = (s)=>{ 
            if(!s) return '-'; 
            const d=new Date(s); 
            return isNaN(d)? s : d.toLocaleDateString('vi-VN'); 
        };
        const titleCase = (s)=> (s||'').toLowerCase().replace(/_/g,' ').replace(/\b\w/g, m=>m.toUpperCase());
        tr.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${c.campaign_name}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full ${c.status === 'ACTIVE' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}">${c.status}</span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${titleCase(c.objective)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${fmt(c.created_time)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${fmt(c.start_time)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${fmt(c.stop_time)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm">
                <button class="px-3 py-1 text-white rounded btn-primary" onclick="viewInsights('${c.campaign_id}', '${c.status}')">Xem</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function createCharts(campaigns) {
    const truncate = (s, n=20) => (s||'').length>n ? (s.slice(0,n-1)+'…') : (s||'Unknown');
    const objCounts = {};
    const statusCounts = {};
    campaigns.forEach(c=>{ 
        objCounts[c.objective]=(objCounts[c.objective]||0)+1; 
        statusCounts[c.status]=(statusCounts[c.status]||0)+1; 
    });
    const objEntries = Object.entries(objCounts).sort((a,b)=>b[1]-a[1]).slice(0,10);
    const objLabels = objEntries.map(([k])=>truncate(k));
    const objValues = objEntries.map(([,v])=>v);
    const statusLabels = Object.keys(statusCounts);
    const statusValues = Object.values(statusCounts);
    const objCtx = document.getElementById('objectiveChart').getContext('2d');
    charts.objective && charts.objective.destroy();
    charts.objective = new Chart(objCtx,{
        type:'bar',
        data:{
            labels:objLabels,
            datasets:[{
                label:'Số chiến dịch',
                data:objValues,
                backgroundColor:'#247ba0'
            }]
        },
        options:{
            responsive:true,
            maintainAspectRatio:false,
            scales:{
                x:{ticks:{autoSkip:true,maxRotation:0}},
                y:{beginAtZero:true,precision:0}
            }
        }
    });
    const stCtx = document.getElementById('statusChart').getContext('2d');
    charts.status && charts.status.destroy();
    charts.status = new Chart(stCtx,{
        type:'doughnut',
        data:{
            labels:statusLabels,
            datasets:[{
                data:statusValues,
                backgroundColor:['#10b981','#f59e0b','#6b7280','#ef4444','#3b82f6']
            }]
        },
        options:{
            responsive:true,
            maintainAspectRatio:false,
            plugins:{
                legend:{position:'bottom'}
            }
        }
    });
}

// Utility functions
function toCSV(rows){ 
    if(!rows||!rows.length) return ''; 
    const keys=Object.keys(rows[0]); 
    const esc=s=>`"${String(s??'').replace(/"/g,'""')}"`; 
    return [keys.join(','),...rows.map(r=>keys.map(k=>esc(r[k])).join(','))].join('\n'); 
}

const VND_FMT = new Intl.NumberFormat('vi-VN',{ style:'currency', currency:'VND', maximumFractionDigits:0 });
const NUM_FMT = new Intl.NumberFormat('vi-VN');
