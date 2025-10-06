#!/usr/bin/env python3

import os
import json
import logging
import shutil
import time
from datetime import datetime, date
from typing import Dict, List, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv
from heroku_config import get_timeout_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FacebookAdsExtractor:
    
    def __init__(self):
        load_dotenv()
        # Sử dụng User Token cho ad accounts, Page Token cho insights
        self.user_token = os.getenv('USER_TOKEN') or os.getenv('FACEBOOK_ACCESS_TOKEN')
        self.page_token = os.getenv('PAGE_ACCESS_TOKEN')
        self.access_token = self.user_token  # Default cho ad accounts
        self.skip_insights = (os.getenv('SKIP_INSIGHTS', 'false').lower() in ['1', 'true', 'yes'])
        self.account_ids = os.getenv('FACEBOOK_ACCOUNT_IDS', '').split(',')
        self.base_url = "https://graph.facebook.com/v21.0"
        self._page_cache = {}
        
        # Cấu hình timeout và retry dựa trên environment
        timeout_config = get_timeout_config()
        self.timeout = timeout_config['request_timeout']
        self.max_retries = timeout_config['max_retries']
        self.backoff_factor = timeout_config['backoff_factor']
        
        # Tạo session với retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        if not self.access_token:
            raise ValueError("USER_TOKEN hoặc FACEBOOK_ACCESS_TOKEN không được cấu hình")
        if not self.account_ids or self.account_ids[0] == '':
            raise ValueError("FACEBOOK_ACCOUNT_IDS không được cấu hình")

    def _infer_campaign_page(self, campaign_id: str) -> Dict[str, str]:
        try:
            ads_res = self.session.get(
                f"{self.base_url}/{campaign_id}/ads",
                params={
                    'access_token': self.access_token,
                    'fields': 'id,adcreatives{object_story_id,object_id,instagram_actor_id}',
                    'limit': 3
                },
                timeout=self.timeout
            )
            if ads_res.status_code != 200:
                return {}
            ads = ads_res.json().get('data', [])
            page_id = None
            for ad in ads:
                creatives = (ad.get('adcreatives') or {}).get('data') or []
                for cr in creatives:
                    osid = cr.get('object_story_id') or ''
                    if '_' in osid:
                        page_id = osid.split('_')[0]
                        break
                if page_id:
                    break
            if not page_id:
                return {}
            if page_id in self._page_cache:
                return {'page_id': page_id, 'page_name': self._page_cache[page_id]}
            page_res = self.session.get(f"{self.base_url}/{page_id}", params={'access_token': self.access_token, 'fields': 'name'}, timeout=self.timeout)
            if page_res.status_code == 200:
                name = page_res.json().get('name') or ''
                self._page_cache[page_id] = name
                return {'page_id': page_id, 'page_name': name}
            return {'page_id': page_id, 'page_name': ''}
        except Exception:
            return {}
    
    def test_connection(self) -> bool:
        try:
            url = f"{self.base_url}/me/adaccounts"
            params = {
                'access_token': self.access_token,
                'fields': 'id,name'
            }
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Kết nối thành công! Tìm thấy {len(data.get('data', []))} tài khoản quảng cáo")
            return True
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout khi kết nối Facebook API (>{self.timeout}s)")
            return False
        except requests.exceptions.ConnectionError:
            logger.error("Lỗi kết nối mạng đến Facebook API")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Lỗi kết nối: {e}")
            return False
    
    def get_campaigns(self, account_id: str) -> List[Dict[str, Any]]:
        try:
            url = f"{self.base_url}/{account_id}/campaigns"
            params = {
                'access_token': self.access_token,
                'fields': 'id,name,status,objective,created_time,start_time,stop_time',
                'limit': 100
            }
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            campaigns = data.get('data', [])
            
            if 'error' in data:
                logger.warning(f"Lỗi API khi lấy campaigns: {data['error']}")
                return []
            
            logger.info(f"Lấy được {len(campaigns)} chiến dịch từ tài khoản {account_id}")
            
            if len(campaigns) == 0:
                logger.info("Không tìm thấy chiến dịch nào. Có thể tài khoản chưa có chiến dịch hoặc thiếu quyền truy cập.")
                
                try:
                    perm_url = f"{self.base_url}/me/permissions"
                    perm_response = self.session.get(perm_url, params={'access_token': self.access_token}, timeout=self.timeout)
                    if perm_response.status_code == 200:
                        permissions = perm_response.json().get('data', [])
                        ads_read_granted = any(p.get('permission') == 'ads_read' and p.get('status') == 'granted' for p in permissions)
                        if not ads_read_granted:
                            logger.warning("Thiếu quyền 'ads_read'. Cần cấp quyền này để đọc dữ liệu quảng cáo.")
                except:
                    pass
            
            return campaigns
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout khi lấy campaigns từ account {account_id} (>{self.timeout}s)")
            return []
        except requests.exceptions.ConnectionError:
            logger.error(f"Lỗi kết nối khi lấy campaigns từ account {account_id}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Lỗi khi lấy chiến dịch: {e}")
            return []
    
    def get_campaign_insights(self, account_id: str, campaign_id: str, start_date: str = "2023-01-01") -> Dict[str, Any]:
        try:
            url = f"{self.base_url}/{campaign_id}/insights"
            # Sử dụng page token cho insights nếu có
            token = self.page_token or self.access_token
            params = {
                'access_token': token,
                'level': 'campaign',
                'fields': 'campaign_name,impressions,clicks,spend,ctr,cpc,cpm,reach,frequency',
                'date_preset': 'maximum',  # Sử dụng maximum thay vì custom để lấy tất cả dữ liệu có sẵn
                'time_increment': 1
            }
            
            logger.info(f"Lấy insights cho campaign {campaign_id}")
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            insights = data.get('data', [])
            
            if insights:
                logger.info(f"Tìm thấy {len(insights)} insights cho campaign {campaign_id}")
                return insights[0]
            else:
                logger.warning(f"Không có insights data cho campaign {campaign_id}")
                return {}
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout khi lấy insights cho campaign {campaign_id} (>{self.timeout}s)")
            return {}
        except requests.exceptions.ConnectionError:
            logger.error(f"Lỗi kết nối khi lấy insights cho campaign {campaign_id}")
            return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"Lỗi khi lấy insights cho campaign {campaign_id}: {e}")
            return {}
    
    def extract_all_data(self, start_date: str = "2023-01-01") -> Dict[str, Any]:
        all_data = {
            'extraction_date': datetime.now().isoformat(),
            'start_date': start_date,
            'campaigns': []
        }
        
        for account_id in self.account_ids:
            account_id = account_id.strip()
            if not account_id:
                continue
                
            logger.info(f"Đang xử lý tài khoản: {account_id}")
            
            campaigns = self.get_campaigns(account_id)
            
            for campaign in campaigns:
                campaign_data = {
                    'account_id': account_id,
                    'campaign_id': campaign['id'],
                    'campaign_name': campaign.get('name', 'Unknown'),
                    'status': campaign.get('status', 'Unknown'),
                    'objective': campaign.get('objective', 'Unknown'),
                    'created_time': campaign.get('created_time', ''),
                    'start_time': campaign.get('start_time', ''),
                    'stop_time': campaign.get('stop_time', ''),
                    'insights': {}
                }
                page_info = self._infer_campaign_page(campaign['id'])
                if page_info:
                    campaign_data.update(page_info)
                
                if not self.skip_insights:
                    # Lấy insights cho cả ACTIVE và PAUSED campaigns
                    # vì campaigns PAUSED vẫn có thể có dữ liệu lịch sử
                    logger.info(f"Đang lấy insights cho campaign {campaign['id']} - {campaign.get('name', 'Unknown')}")
                    insights = self.get_campaign_insights(account_id, campaign['id'], start_date)
                    campaign_data['insights'] = insights
                    logger.info(f"Kết quả insights cho campaign {campaign['id']}: {len(insights) if insights else 0} fields")
                
                all_data['campaigns'].append(campaign_data)
        
        return all_data
    
    def save_to_json(self, data: Dict[str, Any], filename: str = "ads_data.json") -> bool:
        import tempfile
        
        try:
            # Write to a temporary file first to make the operation atomic
            temp_filename = filename + '.tmp'
            with open(temp_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Atomically replace the original file
            shutil.move(temp_filename, filename)
            
            logger.info(f"Dữ liệu đã được lưu vào {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu file: {e}")
            # Clean up temporary file if it exists
            try:
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)
            except:
                pass
            return False
    
    def generate_sample_data(self) -> Dict[str, Any]:
        sample_data = {
            'extraction_date': datetime.now().isoformat(),
            'start_date': '2023-01-01',
            'campaigns': [
                {
                    'account_id': 'act_123456789',
                    'campaign_id': '123456789',
                    'campaign_name': 'Campaign A - Brand Awareness',
                    'status': 'ACTIVE',
                    'objective': 'BRAND_AWARENESS',
                    'created_time': '2023-01-15T00:00:00+0000',
                    'start_time': '2023-01-15T00:00:00+0000',
                    'stop_time': None,
                    'insights': {
                        'campaign_name': 'Campaign A - Brand Awareness',
                        'impressions': '150000',
                        'clicks': '2500',
                        'spend': '5000.00',
                        'ctr': '1.67',
                        'cpc': '2.00',
                        'cpm': '33.33'
                    }
                },
                {
                    'account_id': 'act_123456789',
                    'campaign_id': '123456790',
                    'campaign_name': 'Campaign B - Conversions',
                    'status': 'ACTIVE',
                    'objective': 'CONVERSIONS',
                    'created_time': '2023-02-01T00:00:00+0000',
                    'start_time': '2023-02-01T00:00:00+0000',
                    'stop_time': None,
                    'insights': {
                        'campaign_name': 'Campaign B - Conversions',
                        'impressions': '80000',
                        'clicks': '4000',
                        'spend': '8000.00',
                        'ctr': '5.00',
                        'cpc': '2.00',
                        'cpm': '100.00'
                    }
                },
                {
                    'account_id': 'act_123456789',
                    'campaign_id': '123456791',
                    'campaign_name': 'Campaign C - Traffic',
                    'status': 'ACTIVE',
                    'objective': 'TRAFFIC',
                    'created_time': '2023-03-01T00:00:00+0000',
                    'start_time': '2023-03-01T00:00:00+0000',
                    'stop_time': None,
                    'insights': {
                        'campaign_name': 'Campaign C - Traffic',
                        'impressions': '120000',
                        'clicks': '3000',
                        'spend': '6000.00',
                        'ctr': '2.50',
                        'cpc': '2.00',
                        'cpm': '50.00'
                    }
                }
            ]
        }
        
        return sample_data

def main():
    try:
        extractor = FacebookAdsExtractor()
        
        if not extractor.test_connection():
            logger.warning("Không thể kết nối đến Facebook API. Tạo dữ liệu mẫu...")
            sample_data = extractor.generate_sample_data()
            extractor.save_to_json(sample_data, "ads_data.json")
            return
        
        logger.info("Bắt đầu trích xuất dữ liệu...")
        data = extractor.extract_all_data("2023-01-01")
        
        if not data.get('campaigns') or len(data['campaigns']) == 0:
            logger.warning("Không tìm thấy chiến dịch nào trong tài khoản quảng cáo.")
            logger.info("Có thể do:")
            logger.info("1. Tài khoản chưa có chiến dịch quảng cáo nào")
            logger.info("2. Thiếu quyền 'ads_read' (cần cấp quyền này)")
            logger.info("3. Chiến dịch đã bị xóa hoặc ẩn")
            logger.info("Tạo dữ liệu mẫu để demo dashboard...")
            
            sample_data = extractor.generate_sample_data()
            if extractor.save_to_json(sample_data, "ads_data.json"):
                logger.info("Đã tạo dữ liệu mẫu thành công!")
            else:
                logger.error("Lỗi khi tạo dữ liệu mẫu!")
        else:
            if extractor.save_to_json(data, "ads_data.json"):
                logger.info("Trích xuất dữ liệu hoàn tất thành công!")
            else:
                logger.error("Lỗi khi lưu dữ liệu!")
            
    except Exception as e:
        logger.error(f"Lỗi không mong muốn: {e}")

if __name__ == "__main__":
    main()
