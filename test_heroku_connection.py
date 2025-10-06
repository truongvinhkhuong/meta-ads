#!/usr/bin/env python3
"""
Test script for Heroku connection issues
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from facebook_ads_extractor import FacebookAdsExtractor
from heroku_config import is_heroku, get_heroku_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_environment():
    """Test environment configuration"""
    print("=== KIỂM TRA MÔI TRƯỜNG ===")
    print(f"Python version: {sys.version}")
    print(f"Running on Heroku: {is_heroku()}")
    print(f"DYNO: {os.getenv('DYNO', 'Not set')}")
    print(f"PORT: {os.getenv('PORT', 'Not set')}")
    
    if is_heroku():
        config = get_heroku_config()
        print(f"Heroku config: {config}")
    
    print()

def test_facebook_connection():
    """Test Facebook API connection"""
    print("=== KIỂM TRA KẾT NỐI FACEBOOK API ===")
    
    try:
        load_dotenv()
        
        # Check environment variables
        user_token = os.getenv('USER_TOKEN') or os.getenv('FACEBOOK_ACCESS_TOKEN')
        page_token = os.getenv('PAGE_ACCESS_TOKEN')
        account_ids = os.getenv('FACEBOOK_ACCOUNT_IDS', '').split(',')
        
        print(f"User Token: {'✓' if user_token else '✗'}")
        print(f"Page Token: {'✓' if page_token else '✗'}")
        print(f"Account IDs: {len([aid for aid in account_ids if aid.strip()])} accounts")
        
        if not user_token:
            print("❌ USER_TOKEN hoặc FACEBOOK_ACCESS_TOKEN không được cấu hình")
            return False
            
        if not account_ids or account_ids[0] == '':
            print("❌ FACEBOOK_ACCOUNT_IDS không được cấu hình")
            return False
        
        # Test connection
        extractor = FacebookAdsExtractor()
        print(f"Timeout config: {extractor.timeout}s, {extractor.max_retries} retries")
        
        if extractor.test_connection():
            print("✅ Kết nối Facebook API thành công")
            return True
        else:
            print("❌ Kết nối Facebook API thất bại")
            return False
            
    except Exception as e:
        print(f"❌ Lỗi khi test kết nối: {e}")
        return False

def test_data_extraction():
    """Test data extraction with limited scope"""
    print("\n=== KIỂM TRA TRÍCH XUẤT DỮ LIỆU ===")
    
    try:
        extractor = FacebookAdsExtractor()
        
        # Test với 1 account và 1 campaign để tránh timeout
        account_id = extractor.account_ids[0].strip()
        print(f"Testing với account: {account_id}")
        
        campaigns = extractor.get_campaigns(account_id)
        print(f"Tìm thấy {len(campaigns)} campaigns")
        
        if campaigns:
            campaign = campaigns[0]
            print(f"Test campaign: {campaign.get('name', 'N/A')} (ID: {campaign.get('id')})")
            
            # Test insights
            insights = extractor.get_campaign_insights(account_id, campaign['id'])
            if insights:
                print("✅ Insights data có sẵn")
            else:
                print("⚠️ Không có insights data")
        
        return True
        
    except Exception as e:
        print(f"❌ Lỗi khi test extraction: {e}")
        return False

def main():
    """Main test function"""
    print(f"=== HEROKU CONNECTION TEST - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    
    # Test environment
    test_environment()
    
    # Test Facebook connection
    connection_ok = test_facebook_connection()
    
    if connection_ok:
        # Test data extraction
        extraction_ok = test_data_extraction()
        
        if extraction_ok:
            print("\n✅ TẤT CẢ TESTS THÀNH CÔNG")
            return 0
        else:
            print("\n❌ TEST EXTRACTION THẤT BẠI")
            return 1
    else:
        print("\n❌ TEST CONNECTION THẤT BẠI")
        return 1

if __name__ == "__main__":
    sys.exit(main())
