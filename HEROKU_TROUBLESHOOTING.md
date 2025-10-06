# Hướng dẫn khắc phục lỗi kết nối trên Heroku Production

## Các vấn đề đã được khắc phục

### 1. **Timeout và Connection Issues**
- ✅ Thêm cấu hình timeout linh hoạt (30s local, 60s Heroku)
- ✅ Implement retry mechanism với exponential backoff
- ✅ Sử dụng requests.Session với HTTPAdapter
- ✅ Xử lý riêng biệt các loại lỗi (Timeout, ConnectionError, RequestException)

### 2. **Error Handling Improvements**
- ✅ Cải thiện error handling trong `/api/refresh` endpoint
- ✅ Thêm kiểm tra kết nối trước khi bắt đầu refresh
- ✅ Timeout toàn bộ quá trình refresh (5 phút)
- ✅ Phân loại lỗi chi tiết với HTTP status codes phù hợp

### 3. **Heroku-specific Optimizations**
- ✅ Cấu hình environment variables cho Heroku
- ✅ Tối ưu hóa cho Heroku dyno timeout
- ✅ Thêm script test kết nối

## Cách sử dụng

### 1. **Deploy với cải tiến**
```bash
./deploy_improved.sh
```

### 2. **Test kết nối trước khi deploy**
```bash
python test_heroku_connection.py
```

### 3. **Kiểm tra logs Heroku**
```bash
heroku logs --tail
```

## Environment Variables cần thiết

### **Required**
- `USER_TOKEN` hoặc `FACEBOOK_ACCESS_TOKEN`: Facebook API token
- `FACEBOOK_ACCOUNT_IDS`: Danh sách account IDs (comma-separated)
- `PAGE_ACCESS_TOKEN`: Page access token (optional)

### **Optional (có giá trị mặc định)**
- `REQUEST_TIMEOUT`: 60 (seconds)
- `MAX_RETRIES`: 5
- `BACKOFF_FACTOR`: 0.5
- `SKIP_INSIGHTS`: false

## Các lỗi thường gặp và cách khắc phục

### 1. **"Không thể kết nối đến Facebook API"**
**Nguyên nhân:**
- Token hết hạn hoặc không hợp lệ
- Lỗi kết nối mạng
- Facebook API down

**Khắc phục:**
```bash
# Kiểm tra token
heroku config:get USER_TOKEN

# Test kết nối
heroku run python test_heroku_connection.py
```

### 2. **"Timeout khi kết nối Facebook API"**
**Nguyên nhân:**
- Mạng chậm
- Facebook API phản hồi chậm
- Quá nhiều requests đồng thời

**Khắc phục:**
```bash
# Tăng timeout
heroku config:set REQUEST_TIMEOUT=120

# Giảm số lượng campaigns xử lý đồng thời
heroku config:set MAX_CAMPAIGNS=5
```

### 3. **"Refresh timeout sau 5 phút"**
**Nguyên nhân:**
- Quá nhiều dữ liệu cần xử lý
- API calls chậm

**Khắc phục:**
```bash
# Tăng timeout tổng thể
heroku config:set DYNO_TIMEOUT=600

# Hoặc giảm phạm vi dữ liệu
# Chỉ refresh dữ liệu 30 ngày gần nhất
curl -X POST https://your-app.herokuapp.com/api/refresh \
  -H "Content-Type: application/json" \
  -d '{"start_date": "2024-12-01"}'
```

### 4. **"Lỗi kết nối mạng"**
**Nguyên nhân:**
- Heroku dyno không thể kết nối ra ngoài
- Firewall hoặc network restrictions

**Khắc phục:**
```bash
# Restart dyno
heroku restart

# Kiểm tra network connectivity
heroku run curl -I https://graph.facebook.com
```

## Monitoring và Debugging

### 1. **Kiểm tra logs real-time**
```bash
heroku logs --tail --source app
```

### 2. **Kiểm tra metrics**
```bash
heroku ps
heroku config
```

### 3. **Test API endpoints**
```bash
# Health check
curl https://your-app.herokuapp.com/api/health

# Test refresh
curl -X POST https://your-app.herokuapp.com/api/refresh \
  -H "Content-Type: application/json" \
  -d '{}'
```

## Best Practices

### 1. **Trước khi deploy**
- Luôn test local trước
- Kiểm tra environment variables
- Test kết nối Facebook API

### 2. **Trong production**
- Monitor logs thường xuyên
- Set up alerts cho errors
- Backup dữ liệu quan trọng

### 3. **Khi có lỗi**
- Kiểm tra logs trước
- Test kết nối riêng biệt
- Restart dyno nếu cần
- Rollback nếu cần thiết

## Contact Support

Nếu vẫn gặp vấn đề, hãy cung cấp:
1. Logs từ `heroku logs --tail`
2. Kết quả từ `python test_heroku_connection.py`
3. Mô tả chi tiết lỗi và thời điểm xảy ra
