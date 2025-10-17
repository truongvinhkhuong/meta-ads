/**
 * Global Filters Management
 * Handles filtering across all dashboard sections
 */

class GlobalFilters {
    constructor() {
        this.filters = {
            datePreset: 'last_30d',
            dateFrom: null,
            dateTo: null,
            brand: 'all',
            campaign: 'all',
            adset: 'all',
            ad: 'all'
        };
        
        this.data = {
            campaigns: [],
            adsets: [],
            ads: [],
            brands: []
        };
        
        this.callbacks = [];
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadInitialData();
    }
    
    bindEvents() {
        // Date preset change
        document.getElementById('filter-date-preset').addEventListener('change', (e) => {
            this.handleDatePresetChange(e.target.value);
        });
        
        // Custom date inputs
        document.getElementById('filter-date-from').addEventListener('change', () => {
            this.updateDateRange();
        });
        
        document.getElementById('filter-date-to').addEventListener('change', () => {
            this.updateDateRange();
        });
        
        // Filter dropdowns
        document.getElementById('filter-brand').addEventListener('change', (e) => {
            this.filters.brand = e.target.value;
            this.updateCampaignOptions();
            this.notifyChange();
        });
        
        document.getElementById('filter-campaign').addEventListener('change', (e) => {
            this.filters.campaign = e.target.value;
            // reset dependent selections
            this.filters.adset = 'all';
            this.filters.ad = 'all';
            
            console.log('Campaign changed to:', this.filters.campaign);
            
            // fetch adsets for selected campaign, then update options
            this.loadAdsetsAndAds().then(() => {
                this.updateAdsetOptions();
                this.updateAdOptions();
                this.notifyChange();
            }).catch(error => {
                console.error('Error loading adsets after campaign change:', error);
                this.updateAdsetOptions();
                this.updateAdOptions();
                this.notifyChange();
            });
        });
        
        document.getElementById('filter-adset').addEventListener('change', (e) => {
            this.filters.adset = e.target.value;
            // reset ad selection
            this.filters.ad = 'all';
            
            console.log('Adset changed to:', this.filters.adset);
            
            // fetch ads for selected adset, then update options
            this.loadAdsetsAndAds().then(() => {
                this.updateAdOptions();
                this.notifyChange();
            }).catch(error => {
                console.error('Error loading ads after adset change:', error);
                this.updateAdOptions();
                this.notifyChange();
            });
        });
        
        document.getElementById('filter-ad').addEventListener('change', (e) => {
            this.filters.ad = e.target.value;
            this.notifyChange();
        });
        
        // Control buttons
        document.getElementById('btn-apply-filters').addEventListener('click', () => {
            this.applyFilters();
        });
        
        document.getElementById('btn-reset-filters').addEventListener('click', () => {
            this.resetFilters();
        });
    }
    
    async loadInitialData() {
        try {
            console.log('Loading initial data...');
            
            // Load campaigns data
            const response = await fetch('/api/ads-data');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('Campaigns data loaded:', data);
            
            if (data.campaigns) {
                this.data.campaigns = data.campaigns;
                this.extractBrands();
                this.populateFilterOptions();
                console.log('Filter options populated');
            }
            
            // Load additional data if needed
            await this.loadAdsetsAndAds();
            
        } catch (error) {
            console.error('Error loading initial data:', error);
        }
    }
    
    extractBrands() {
        const brandSet = new Set();
        
        this.data.campaigns.forEach(campaign => {
            const brand = this.extractBrandFromCampaignName(campaign.campaign_name);
            if (brand && brand !== 'Unknown') {
                brandSet.add(brand);
            }
        });
        
        this.data.brands = Array.from(brandSet).sort();
    }
    
    extractBrandFromCampaignName(campaignName) {
        if (!campaignName) return 'Unknown';
        
        const nameLower = campaignName.toLowerCase();
        
        // Constrain to 3 brands: LS2, Bulldog, EGO
        if (nameLower.includes('ls2')) return 'LS2';
        if (nameLower.includes('bulldog')) return 'Bulldog';
        if (nameLower.includes('ego')) return 'EGO';
        
        return 'Unknown';
    }
    
    async loadAdsetsAndAds() {
        try {
            const selectedCampaignId = this.filters.campaign !== 'all' ? this.filters.campaign : null;
            if (!selectedCampaignId) {
                this.data.adsets = [];
                this.data.ads = [];
                console.log('No campaign selected, clearing adsets and ads');
                return;
            }
            
            console.log('Loading adsets for campaign:', selectedCampaignId);
            
            // Add loading state
            this.setLoadingState('adset', true);
            
            // Load adsets for selected campaign
            const adsetsRes = await fetch(`/api/campaign-adsets?campaign_id=${encodeURIComponent(selectedCampaignId)}`);
            if (!adsetsRes.ok) {
                throw new Error(`HTTP ${adsetsRes.status}: ${adsetsRes.statusText}`);
            }
            
            const adsetsJson = await adsetsRes.json();
            console.log('Adsets response:', adsetsJson);
            
            if (adsetsJson.error) {
                console.error('Error in adsets response:', adsetsJson.error);
                this.data.adsets = [];
            } else {
                this.data.adsets = Array.isArray(adsetsJson.items) ? adsetsJson.items : [];
            }
            
            // Remove loading state
            this.setLoadingState('adset', false);
            
            // If adset is selected, load ads for that adset
            if (this.filters.adset && this.filters.adset !== 'all') {
                console.log('Loading ads for adset:', this.filters.adset);
                
                // Add loading state
                this.setLoadingState('ad', true);
                
                const adsRes = await fetch(`/api/adset-ads?adset_id=${encodeURIComponent(this.filters.adset)}`);
                if (!adsRes.ok) {
                    throw new Error(`HTTP ${adsRes.status}: ${adsRes.statusText}`);
                }
                
                const adsJson = await adsRes.json();
                console.log('Ads response:', adsJson);
                
                if (adsJson.error) {
                    console.error('Error in ads response:', adsJson.error);
                    this.data.ads = [];
                } else {
                    // Normalize to flat structure id/name
                    this.data.ads = Array.isArray(adsJson.items) ? adsJson.items.map(x => ({
                        id: x.ad?.id || x.id,
                        name: x.ad?.name || x.name,
                        adset_id: this.filters.adset
                    })) : [];
                }
                
                // Remove loading state
                this.setLoadingState('ad', false);
            } else {
                this.data.ads = [];
            }
        } catch (e) {
            console.error('Failed to load adsets/ads', e);
            this.data.adsets = [];
            this.data.ads = [];
            this.setLoadingState('adset', false);
            this.setLoadingState('ad', false);
        }
    }
    
    populateFilterOptions() {
        this.populateBrandOptions();
        this.populateCampaignOptions();
        this.populateAdsetOptions();
        this.populateAdOptions();
    }
    
    populateBrandOptions() {
        const select = document.getElementById('filter-brand');
        select.innerHTML = '<option value="all" selected>Tất cả Brand</option>';
        const allowed = ['LS2','Bulldog','EGO'];
        allowed.forEach(brand => {
            const option = document.createElement('option');
            option.value = brand;
            option.textContent = brand;
            select.appendChild(option);
        });
    }
    
    populateCampaignOptions() {
        const select = document.getElementById('filter-campaign');
        select.innerHTML = '<option value="all" selected>Tất cả Chiến dịch</option>';
        
        let filteredCampaigns = this.data.campaigns;
        
        // Filter by brand if selected
        if (this.filters.brand !== 'all') {
            filteredCampaigns = filteredCampaigns.filter(campaign => 
                this.extractBrandFromCampaignName(campaign.campaign_name) === this.filters.brand
            );
        }
        
        filteredCampaigns.forEach(campaign => {
            const option = document.createElement('option');
            option.value = campaign.campaign_id;
            option.textContent = campaign.campaign_name || campaign.campaign_id;
            select.appendChild(option);
        });
    }
    
    populateAdsetOptions() {
        const select = document.getElementById('filter-adset');
        select.innerHTML = '<option value="all" selected>Tất cả Nhóm QC</option>';
        
        // Use loaded adsets filtered by selected campaign
        const adsets = (this.data.adsets || []).filter(a => a.campaign_id === this.filters.campaign);
        console.log('Populating adset options with:', adsets);
        
        adsets.forEach(as => {
            const option = document.createElement('option');
            option.value = as.id;
            option.textContent = as.name || as.id;
            select.appendChild(option);
        });
        
        // Update the select value if adset is already selected
        if (this.filters.adset !== 'all') {
            select.value = this.filters.adset;
        }
    }
    
    populateAdOptions() {
        const select = document.getElementById('filter-ad');
        select.innerHTML = '<option value="all" selected>Tất cả Quảng Cáo</option>';
        
        // Use loaded ads tied to selected adset
        const ads = (this.data.ads || []);
        console.log('Populating ad options with:', ads);
        
        ads.forEach(ad => {
            const option = document.createElement('option');
            option.value = ad.id;
            option.textContent = ad.name || ad.id;
            select.appendChild(option);
        });
        
        // Update the select value if ad is already selected
        if (this.filters.ad !== 'all') {
            select.value = this.filters.ad;
        }
    }
    
    updateCampaignOptions() {
        this.populateCampaignOptions();
        // Reset dependent filters
        this.filters.campaign = 'all';
        this.filters.adset = 'all';
        this.filters.ad = 'all';
        this.updateAdsetOptions();
        this.updateAdOptions();
    }
    
    updateAdsetOptions() {
        this.populateAdsetOptions();
        // Reset dependent filters
        this.filters.adset = 'all';
        this.filters.ad = 'all';
        this.updateAdOptions();
    }
    
    updateAdOptions() {
        this.populateAdOptions();
        // Reset dependent filters
        this.filters.ad = 'all';
    }
    
    handleDatePresetChange(preset) {
        this.filters.datePreset = preset;
        
        const customRange = document.getElementById('custom-date-range');
        if (preset === 'custom') {
            customRange.classList.remove('hidden');
        } else {
            customRange.classList.add('hidden');
        }
        
        this.updateDateRange();
    }
    
    updateDateRange() {
        if (this.filters.datePreset === 'custom') {
            this.filters.dateFrom = document.getElementById('filter-date-from').value;
            this.filters.dateTo = document.getElementById('filter-date-to').value;
        } else {
            this.filters.dateFrom = null;
            this.filters.dateTo = null;
        }
        
        this.notifyChange();
    }
    
    getFilterParams() {
        const params = {};
        
        // Date parameters
        if (this.filters.datePreset === 'custom' && this.filters.dateFrom && this.filters.dateTo) {
            params.date_preset = 'custom';
            params.since = this.filters.dateFrom;
            params.until = this.filters.dateTo;
        } else {
            params.date_preset = this.filters.datePreset;
        }
        
        // Entity filters
        if (this.filters.campaign !== 'all') {
            params.campaign_id = this.filters.campaign;
        }
        
        if (this.filters.adset !== 'all') {
            params.adset_id = this.filters.adset;
        }
        
        if (this.filters.ad !== 'all') {
            params.ad_id = this.filters.ad;
        }
        
        // Brand filter (will be handled in frontend filtering)
        if (this.filters.brand !== 'all') {
            params.brand = this.filters.brand;
        }
        
        return params;
    }
    
    getActiveFilters() {
        const active = [];
        
        if (this.filters.datePreset !== 'last_30d') {
            active.push(`Thời gian: ${this.getDatePresetLabel()}`);
        }
        
        if (this.filters.brand !== 'all') {
            active.push(`Brand: ${this.filters.brand}`);
        }
        
        if (this.filters.campaign !== 'all') {
            const campaign = this.data.campaigns.find(c => c.campaign_id === this.filters.campaign);
            active.push(`Chiến dịch: ${campaign?.campaign_name || this.filters.campaign}`);
        }
        
        if (this.filters.adset !== 'all') {
            active.push(`Nhóm QC: ${this.filters.adset}`);
        }
        
        if (this.filters.ad !== 'all') {
            active.push(`Quảng cáo: ${this.filters.ad}`);
        }
        
        return active;
    }
    
    getDatePresetLabel() {
        const labels = {
            'last_7d': '7 ngày qua',
            'last_30d': '30 ngày qua',
            'last_90d': '90 ngày qua',
            'last_180d': '180 ngày qua',
            'lifetime': 'Toàn thời gian',
            'custom': 'Tùy chỉnh'
        };
        return labels[this.filters.datePreset] || this.filters.datePreset;
    }
    
    applyFilters() {
        this.notifyChange();
        this.updateFilterStatus();
    }
    
    resetFilters() {
        console.log('Resetting filters...');
        
        this.filters = {
            datePreset: 'last_30d',
            dateFrom: null,
            dateTo: null,
            brand: 'all',
            campaign: 'all',
            adset: 'all',
            ad: 'all'
        };
        
        // Clear adsets and ads data
        this.data.adsets = [];
        this.data.ads = [];
        
        // Reset UI
        document.getElementById('filter-date-preset').value = 'last_30d';
        document.getElementById('filter-brand').value = 'all';
        document.getElementById('filter-campaign').value = 'all';
        document.getElementById('filter-adset').value = 'all';
        document.getElementById('filter-ad').value = 'all';
        
        document.getElementById('custom-date-range').classList.add('hidden');
        
        this.populateFilterOptions();
        this.notifyChange();
        this.updateFilterStatus();
        
        console.log('Filters reset completed');
    }
    
    updateFilterStatus() {
        const activeFilters = this.getActiveFilters();
        const statusText = document.getElementById('filter-status-text');
        
        if (activeFilters.length === 0) {
            statusText.textContent = 'Chưa áp dụng bộ lọc';
        } else {
            statusText.textContent = `Đã áp dụng: ${activeFilters.join(', ')}`;
        }
        
        // Update results count (this would be calculated based on filtered data)
        const resultsCount = this.getFilteredDataCount();
        document.getElementById('filter-results-count').textContent = resultsCount;
    }
    
    getFilteredDataCount() {
        // Calculate the actual count based on current filters
        let filteredCampaigns = this.data.campaigns || [];
        
        // Apply brand filter
        if (this.filters.brand !== 'all') {
            filteredCampaigns = filteredCampaigns.filter(campaign => 
                this.extractBrandFromCampaignName(campaign.campaign_name) === this.filters.brand
            );
        }
        
        // Apply campaign filter
        if (this.filters.campaign !== 'all') {
            filteredCampaigns = filteredCampaigns.filter(campaign => 
                campaign.campaign_id === this.filters.campaign
            );
        }
        
        return filteredCampaigns.length;
    }
    
    // Register callback for when filters change
    onFilterChange(callback) {
        this.callbacks.push(callback);
    }
    
    notifyChange() {
        this.callbacks.forEach(callback => {
            try {
                callback(this.getFilterParams(), this.filters);
            } catch (error) {
                console.error('Error in filter callback:', error);
            }
        });
    }
    
    // Public method to get current filter state
    getCurrentFilters() {
        return {
            ...this.filters,
            params: this.getFilterParams()
        };
    }
    
    // Set loading state for filter dropdowns
    setLoadingState(filterType, isLoading) {
        const selectElement = document.getElementById(`filter-${filterType}`);
        if (selectElement) {
            if (isLoading) {
                selectElement.classList.add('filter-loading');
                selectElement.disabled = true;
            } else {
                selectElement.classList.remove('filter-loading');
                selectElement.disabled = false;
            }
        }
    }
}

// Initialize global filters when DOM is loaded
let globalFilters;

document.addEventListener('DOMContentLoaded', () => {
    globalFilters = new GlobalFilters();
    
    // Make it available globally
    window.globalFilters = globalFilters;
    // Trigger initial apply so all sections receive default filters
    try { globalFilters.applyFilters(); } catch (e) { console.warn('Initial filter apply failed', e); }
});

