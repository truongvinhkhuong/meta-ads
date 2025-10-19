# Hướng dẫn lấy dữ liệu từ Global Filters Component

## Tổng quan

Global Filters Component đã được cải thiện để dễ dàng lấy dữ liệu Quảng cáo (Ads) và Nhóm quảng cáo (Adsets). Tất cả dữ liệu được load tự động và có thể truy cập thông qua các helper functions.

## Các API endpoints được sử dụng

- `/api/ads-data` - Lấy dữ liệu campaigns
- `/api/campaign-adsets?campaign_id={id}` - Lấy adsets cho campaign cụ thể
- `/api/adset-ads?adset_id={id}` - Lấy ads cho adset cụ thể

## Cách lấy dữ liệu

### 1. Helper Functions (Được khuyến nghị)

```javascript
// Lấy tất cả dữ liệu filter
const allData = window.getGlobalFilterData();
console.log(allData);

// Lấy dữ liệu adsets hiện tại
const adsets = window.getAdsetsData();
console.log('Adsets:', adsets);

// Lấy dữ liệu ads hiện tại
const ads = window.getAdsData();
console.log('Ads:', ads);

// Lấy dữ liệu campaigns
const campaigns = window.getCampaignsData();
console.log('Campaigns:', campaigns);

// Lấy dữ liệu brands
const brands = window.getBrandsData();
console.log('Brands:', brands);

// Refresh dữ liệu adsets và ads
await window.refreshGlobalFilterData();
```

### 2. Truy cập trực tiếp qua globalFilters object

```javascript
// Truy cập trực tiếp
const globalFilters = window.globalFilters;
const adsets = globalFilters.getAdsetsData();
const ads = globalFilters.getAdsData();
const allData = globalFilters.getAllFilterData();
```

### 3. Lắng nghe thay đổi filter

```javascript
// Đăng ký callback để lắng nghe thay đổi
window.globalFilters.onFilterChange((params, filters) => {
    const adsets = window.getAdsetsData();
    const ads = window.getAdsData();
    console.log('Filter changed:', { adsets, ads, params, filters });
});
```

## Cấu trúc dữ liệu

### Adsets Data Structure
```javascript
[
    {
        id: "120235022367920520",
        name: "VN_25-35_Scooters/Uni/Corp/Touring",
        campaign_id: "120235022367910520",
        status: "ACTIVE"
    }
]
```

### Ads Data Structure
```javascript
[
    {
        ad: {
            id: "120235022367900520",
            name: "CTKM2510_Post Multi_926550947199387",
            status: "ACTIVE",
            created_time: "2025-10-03T23:48:07+0700"
        },
        insights: {
            clicks: "1095",
            cpc: "1193.434703",
            cpm: "56768.505647",
            ctr: "4.756733",
            impressions: "23020",
            reach: "10853",
            spend: "1306811"
        },
        adset_id: "120235022367920520"
    }
]
```

## Cách sử dụng trong các component khác

### 1. Trong dashboard.js
```javascript
// Lấy dữ liệu khi component khởi tạo
document.addEventListener('DOMContentLoaded', () => {
    const adsets = window.getAdsetsData();
    const ads = window.getAdsData();
    
    // Sử dụng dữ liệu để render UI
    renderAdsetsTable(adsets);
    renderAdsChart(ads);
});
```

### 2. Trong event handler
```javascript
// Lắng nghe thay đổi filter và cập nhật UI
window.globalFilters.onFilterChange((params, filters) => {
    const adsets = window.getAdsetsData();
    const ads = window.getAdsData();
    
    // Cập nhật bảng adsets
    updateAdsetsTable(adsets);
    
    // Cập nhật biểu đồ ads
    updateAdsChart(ads);
});
```

### 3. Refresh dữ liệu khi cần
```javascript
// Refresh dữ liệu khi user thay đổi campaign
document.getElementById('filter-campaign').addEventListener('change', async () => {
    await window.refreshGlobalFilterData();
    
    const adsets = window.getAdsetsData();
    const ads = window.getAdsData();
    
    console.log('New adsets:', adsets);
    console.log('New ads:', ads);
});
```

## Lưu ý quan trọng

1. **Dữ liệu được load tự động**: Khi user chọn campaign, adsets sẽ tự động load. Khi chọn adset, ads sẽ tự động load.

2. **Dữ liệu luôn được cập nhật**: Các helper functions luôn trả về dữ liệu mới nhất.

3. **Async operations**: Một số operations như `refreshGlobalFilterData()` là async, cần sử dụng `await`.

4. **Error handling**: Luôn wrap các API calls trong try-catch để xử lý lỗi.

## Demo

Mở file `global-filters-data-demo.html` trong browser để xem demo cách lấy dữ liệu từ Global Filters Component.

## Troubleshooting

### Nếu dữ liệu không load được:
1. Kiểm tra console để xem có lỗi API không
2. Đảm bảo server đang chạy trên port 5002
3. Kiểm tra network tab để xem API calls có thành công không

### Nếu helper functions không hoạt động:
1. Đảm bảo global-filters.js đã được load
2. Kiểm tra console để xem có lỗi JavaScript không
3. Đảm bảo DOM đã load xong trước khi gọi functions
