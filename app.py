#!/usr/bin/env python3

import os
import json
import logging
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from flask import Flask, request, jsonify, render_template

from dotenv import load_dotenv
import requests
from facebook_ads_extractor import FacebookAdsExtractor
from budget_cache import budget_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
 
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

def get_access_token() -> str:
    # Ưu tiên Page Access Token cho page insights và posts
    page_token = os.getenv('PAGE_ACCESS_TOKEN')
    if page_token:
        return page_token
    
    # Fallback về User Token
    token = os.getenv('USER_TOKEN') or os.getenv('FACEBOOK_ACCESS_TOKEN')
    return token or ''

class OpenAIChatbot:
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.cache = {}
        self.cache_ttl = timedelta(hours=2)
        
        if not self.api_key:
            logger.warning("OPENAI_API_KEY không được cấu hình")
    
    def _get_cache_key(self, data: Dict[str, Any]) -> str:
        cache_data = {
            'campaign_id': data.get('campaign_id'),
            'total_impressions': data.get('summary_metrics', {}).get('total_impressions', 0),
            'total_clicks': data.get('summary_metrics', {}).get('total_clicks', 0),
            'total_spend': data.get('summary_metrics', {}).get('total_spend', 0),
            'avg_ctr': data.get('summary_metrics', {}).get('avg_ctr', 0)
        }
        return hashlib.md5(json.dumps(cache_data, sort_keys=True).encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        cache_time = datetime.fromisoformat(cache_entry['timestamp'])
        return datetime.now() - cache_time < self.cache_ttl
    
    def analyze_campaign_performance(self, campaign_data: Dict[str, Any]) -> Dict[str, str]:
        if not self.api_key:
            return {
                'insights': 'API key chưa được cấu hình. Vui lòng kiểm tra cài đặt.',
                'recommendations': 'Không thể đưa ra đề xuất do thiếu cấu hình API.',
                'cached': False
            }
        
        cache_key = self._get_cache_key(campaign_data)
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if self._is_cache_valid(cache_entry):
                logger.info(f"Sử dụng cache cho campaign analysis: {cache_key[:8]}...")
                return {
                    'insights': cache_entry['insights'],
                    'recommendations': cache_entry['recommendations'],
                    'cached': True
                }
            else:
                del self.cache[cache_key]
        
        try:
            optimized_data = self._optimize_data_for_ai(campaign_data)
            
            system_prompt = (
                "Bạn là một Chuyên gia Phân tích Dữ liệu Quảng cáo và Chuyên gia Tối ưu hóa Hiệu suất có 10 năm kinh nghiệm. Bạn có kiến thức chuyên sâu về nền tảng Meta Ads, các chỉ số cốt lõi, và các framework chẩn đoán vấn đề hiệu quả. Nhiệm vụ của bạn là biến dữ liệu thô của một chiến dịch quảng cáo thành các phát hiện quan trọng và các đề xuất hành động cụ thể.\n\n"
                
                "Phân tích toàn diện dữ liệu của một chiến dịch quảng cáo Meta Ads đã hoàn thành hoặc đang chạy, với các mục tiêu sau:\n"
                "1. Chẩn đoán vấn đề: Xác định các vấn đề hiệu suất chính dựa trên các chỉ số cốt lõi.\n"
                "2. Tìm kiếm phát hiện: Khám phá các xu hướng và mối quan hệ nhân quả trong dữ liệu.\n"
                "3. Đề xuất hành động: Cung cấp các kế hoạch hành động cụ thể, có thể thực thi ngay lập tức để tối ưu hóa hiệu suất chiến dịch trong tương lai.\n\n"
                
                "Dữ liệu sẽ được cung cấp dưới dạng bảng, bao gồm các cột chỉ số và kích thước sau:\n"
                "- Kích thước: Campaign Name, Ad Set Name, Ad Name.\n"
                "- Chỉ số: Amount Spent, Impressions, Reach, Frequency, Link Clicks, Outbound Clicks, CTR (Link Click-Through Rate), CPC (Cost per Link Click), CPM, Conversions, Cost Per Conversion (CPA), Total Conversion Value, ROAS (Return on Ad Spend).\n"
                "Ngoài ra, tôi sẽ cung cấp bối cảnh chiến dịch, bao gồm:\n"
                "- Mục tiêu chính của chiến dịch: [Điền mục tiêu]\n"
                "- Ngân sách chiến dịch: [Điền ngân sách]\n"
                "- Đối tượng mục tiêu: [Điền mô tả đối tượng]\n"
                "- Khoảng thời gian chạy: [Điền thời gian]\n\n"
                
                "Sử dụng các bước sau để phân tích:\n"
                "1. **Phân tích Cấp Chiến dịch (Campaign Level):** Đánh giá hiệu suất tổng thể của chiến dịch dựa trên CPA và ROAS. So sánh các chỉ số này với mục tiêu ban đầu của chiến dịch.\n"
                "2. **Phân tích Cấp Nhóm quảng cáo (Ad Set Level):** Chẩn đoán các vấn đề liên quan đến đối tượng và ngân sách. So sánh các chỉ số CPA và ROAS giữa các nhóm quảng cáo khác nhau. Xác định nhóm quảng cáo hoạt động tốt nhất và kém nhất. Phân tích chỉ số Frequency của từng nhóm quảng cáo.\n"
                "3. **Phân tích Cấp Quảng cáo (Ad Level):** Đánh giá hiệu suất của nội dung quảng cáo (Creative). So sánh các chỉ số CTR và CPC giữa các quảng cáo trong cùng một nhóm quảng cáo. Xác định các quảng cáo hiệu quả nhất và kém hiệu quả nhất.\n"
                "4. **Chẩn đoán Mối Quan Hệ:** Thiết lập mối quan hệ nhân quả giữa các chỉ số. Ví dụ:\n"
                "    - Nếu CPA cao và CTR thấp, vấn đề nằm ở nội dung quảng cáo hoặc đối tượng mục tiêu.\n"
                "    - Nếu CPA cao nhưng CTR cao, vấn đề có thể nằm ở trang đích hoặc tỷ lệ chuyển đổi.\n"
                "    - Nếu ROAS thấp, phân tích xem đó là do CPA cao hay giá trị đơn hàng trung bình thấp.\n\n"
                
                "- **Vấn đề `CTR` thấp:** Khi chỉ số này thấp hơn mức trung bình của ngành hoặc thấp hơn kỳ vọng của bạn, đó là dấu hiệu của nội dung không hấp dẫn hoặc nhắm sai đối tượng.\n"
                "- **Vấn đề `CPA` cao:** Khi chi phí để có một kết quả quá cao, đó là dấu hiệu của hiệu quả chuyển đổi kém hoặc chi phí đấu thầu cao.\n"
                "- **Vấn đề `ROAS` thấp:** Khi lợi nhuận trên chi tiêu quảng cáo không đạt mục tiêu, đó là dấu hiệu của hiệu suất tài chính kém.\n\n"
                
                "Trình bày kết quả phân tích trong một báo cáo có cấu trúc rõ ràng, sử dụng các tiêu đề phụ và gạch đầu dòng.\n"
                "**Phần 1: Tóm Tắt Phân Tích**\n"
                "- Tóm tắt tổng thể về hiệu suất chiến dịch (tốt, trung bình, kém).\n"
                "- Các chỉ số hiệu suất chính (CPA, ROAS, CTR) so với mục tiêu.\n\n"
                
                "**Phần 2: Phân Tích Chẩn Đoán Chi Tiết**\n"
                "- Bảng Phân tích theo Cấp Nhóm quảng cáo:\n"
                "    - Liệt kê các chỉ số chính (Amount Spent, Link Clicks, CTR, CPC, CPA, ROAS, Conversions) cho từng nhóm quảng cáo.\n"
                "    - So sánh và xếp hạng các nhóm quảng cáo dựa trên ROAS và CPA.\n"
                "- Bảng Phân tích theo Cấp Quảng cáo:\n"
                "    - Liệt kê các chỉ số chính (CTR, CPC) cho từng quảng cáo.\n"
                "    - Xác định quảng cáo chiến thắng (`winner`) và quảng cáo hoạt động kém (`loser`).\n\n"
                
                "**Phần 3: Các Phát Hiện và Đề Xuất Hành Động**\n"
                "- **Đề xuất Hành động cho Nhóm quảng cáo:** Dựa trên các phát hiện ở cấp độ này, đưa ra các đề xuất cụ thể (ví dụ: tắt các nhóm quảng cáo hoạt động kém, tinh chỉnh đối tượng mục tiêu, thử nghiệm các nhóm đối tượng mới).\n"
                "- **Đề xuất Hành động cho Quảng cáo:** Dựa trên các phát hiện ở cấp độ này, đưa ra các đề xuất cụ thể (ví dụ: tắt các quảng cáo hoạt động kém, A/B testing các biến thể creative mới, làm mới nội dung để chống `ad fatigue`).\n\n"
                
                "Tạo một kế hoạch hành động cụ thể, có thể thực thi. Ví dụ:\n"
                "- `Creative Optimization`: Đề xuất A/B testing các yếu tố nào (tiêu đề, hình ảnh, video).\n"
                "- `Audience Optimization`: Đề xuất thử nghiệm các tệp đối tượng mới (ví dụ: `lookalike audience` dựa trên khách hàng giá trị cao).\n"
                "- `Bidding & Budget Strategy`: Đề xuất các thay đổi về chiến lược đấu thầu (`cost cap`, `ROAS goal`) hoặc phân bổ ngân sách.\n"
            )
            
            user_prompt = (
                f"Dữ liệu campaign (tối ưu):\n{json.dumps(optimized_data, ensure_ascii=False, indent=2)}\n\n"
                "Hãy phân tích và trả lời theo format JSON:\n"
                "{\n"
                '  "insights": "3-4 insights chính về hiệu suất campaign (CTR, CPM, trends, outliers)",\n'
                '  "recommendations": "3-4 hành động cụ thể để tối ưu hiệu suất"\n'
                "}"
            )
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                'max_tokens': 600,  # Giảm từ 800 xuống 600
                'temperature': 0.3
            }
            
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            answer = result['choices'][0]['message']['content']
            
            logger.info(f"OpenAI raw response length: {len(answer)} chars")
            logger.debug(f"OpenAI raw response: {answer[:500]}...")
            
            try:
                ai_response = json.loads(answer)
                insights = ai_response.get('insights', 'Không có insights')
                recommendations = ai_response.get('recommendations', 'Không có đề xuất')
                
                insights_str = str(insights) if insights else 'Không có insights'
                recommendations_str = str(recommendations) if recommendations else 'Không có đề xuất'
                
                self.cache[cache_key] = {
                    'insights': insights_str,
                    'recommendations': recommendations_str,
                    'timestamp': datetime.now().isoformat()
                }
                
                logger.info(f"AI analysis hoàn thành và cached: {cache_key[:8]}...")
                
                return {
                    'insights': insights_str,
                    'recommendations': recommendations_str,
                    'cached': False
                }
                
            except json.JSONDecodeError:
                logger.warning(f"Không thể parse JSON response từ OpenAI: {answer[:200]}...")
                fallback_response = {
                    'insights': str(answer) if answer else 'Không thể phân tích dữ liệu',
                    'recommendations': 'Vui lòng xem insights để biết thêm chi tiết.',
                    'cached': False
                }
                
                self.cache[cache_key] = {
                    'insights': fallback_response['insights'],
                    'recommendations': fallback_response['recommendations'],
                    'timestamp': datetime.now().isoformat()
                }
                
                return fallback_response
            
        except requests.exceptions.Timeout:
            logger.error("OpenAI API timeout")
            return {
                'insights': 'Lỗi timeout khi kết nối OpenAI API. Vui lòng thử lại.',
                'recommendations': "Không thể đưa ra đề xuất do lỗi timeout.",
                'cached': False
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Lỗi API OpenAI: {e}")
            return {
                'insights': f"Lỗi kết nối OpenAI API: {str(e)}",
                'recommendations': "Không thể đưa ra đề xuất do lỗi kết nối.",
                'cached': False
            }
        except Exception as e:
            logger.error(f"Lỗi không mong muốn trong AI analysis: {e}")
            return {
                'insights': f"Lỗi xử lý: {str(e)}",
                'recommendations': "Không thể đưa ra đề xuất do lỗi hệ thống.",
                'cached': False
            }
    
    def analyze_posts_content(self, posts: list) -> Dict[str, Any]:
        """Phân tích danh sách bài viết Facebook để rút ra insights và đề xuất angles tháng tới."""
        if not self.api_key:
            logger.warning("OPENAI_API_KEY không được cấu hình")
            return {
                'insights': 'OPENAI_API_KEY chưa được cấu hình.',
                'angles': []
            }

        compact_posts = []
        for p in posts[:30]:  # giới hạn ngữ cảnh cho ổn định
            compact_posts.append({
                'id': p.get('id'),
                'created_time': p.get('created_time'),
                'message': (p.get('message') or '')[:2000],
                'permalink_url': p.get('permalink_url')
            })

        system_prompt = (
            "Bạn là chuyên gia nội dung Facebook. Phân tích danh sách bài viết (message + thời gian) để rút ra: \n"
            "1) Chủ đề/insight khách hàng đang quan tâm; 2) Top dạng nội dung/giọng điệu hiệu quả; \n"
            "3) Cấu trúc bài hiệu quả (mở, thân, CTA); 4) Lỗi thường gặp làm CTR thấp; \n"
            "5) Gợi ý 5-8 angles cho tháng tới (tiêu đề + mô tả ngắn + CTA). \n"
            "Trình bày ngắn gọn, có bullet rõ ràng, tập trung actionable."
        )

        user_prompt = (
            "Dưới đây là danh sách bài viết gần đây (rút gọn). Hãy phân tích và đưa ra đề xuất như yêu cầu ở trên.\n\n"
            f"Posts JSON (rút gọn):\n{json.dumps(compact_posts, ensure_ascii=False, indent=2)}\n"
        )

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        payload = {
            'model': os.getenv('OPENAI_CHAT_MODEL', 'gpt-4o-mini'),
            'messages': [
                { 'role': 'system', 'content': system_prompt },
                { 'role': 'user', 'content': user_prompt }
            ],
            'temperature': 0.2
        }

        try:
            res = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            res.raise_for_status()
            data = res.json()
            content = data['choices'][0]['message']['content'] if data.get('choices') else ''
            logger.info("OpenAI content insights generated")
            return { 'insights': content, 'angles': [] }
        except Exception as e:
            logger.error(f"Lỗi AI phân tích bài viết: {e}")
            return { 'insights': f'Lỗi AI: {str(e)}', 'angles': [] }
    
    def _optimize_data_for_ai(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        summary = campaign_data.get('summary_metrics', {})
        daily_trends = campaign_data.get('daily_trends', [])
        placement_breakdown = campaign_data.get('placement_breakdown', [])
        
        top_placements = sorted(placement_breakdown, 
                              key=lambda x: int(x.get('impressions', 0)), 
                              reverse=True)[:3]
        
        optimized = {
            'campaign_id': campaign_data.get('campaign_id'),
            'metrics': {
                'impressions': summary.get('total_impressions', 0),
                'clicks': summary.get('total_clicks', 0),
                'spend': round(summary.get('total_spend', 0), 2),
                'ctr': round(summary.get('avg_ctr', 0), 2),
                'cpc': round(summary.get('avg_cpc', 0), 2),
                'reach': summary.get('total_reach', 0)
            },
            'recent_trend': daily_trends[-3:] if len(daily_trends) >= 3 else daily_trends,
            'top_placements': top_placements
        }
        
        return optimized
    
    def _build_context_summary(self, context: Dict[str, Any]) -> str:
        """Xây dựng tóm tắt ngữ cảnh dashboard"""
        summary_parts = []
        
        # Thông tin cơ bản
        campaigns_count = context.get('campaigns_count', 0)
        extraction_date = context.get('extraction_date')
        summary_parts.append(f"**Tổng quan:** {campaigns_count} campaigns")
        
        if extraction_date:
            summary_parts.append(f"**Dữ liệu cập nhật:** {extraction_date}")
        
        # Tổng hợp số liệu từ TẤT CẢ campaigns, ưu tiên insights, fallback summary_metrics
        has_insights_data = False
        all_campaigns = context.get('all_campaigns', [])
        campaigns_with_insights = context.get('campaigns_with_insights', 0)
        campaigns_without_insights = context.get('campaigns_without_insights', 0)

        if all_campaigns:
            # Gộp theo ưu tiên: insights -> summary_metrics -> 0
            def _num(v, cast=float):
                try:
                    return cast(v)
                except Exception:
                    try:
                        return cast(float(v))
                    except Exception:
                        return 0

            total_spend = 0.0
            total_impressions = 0
            total_clicks = 0

            for c in all_campaigns:
                ins = (c.get('insights') or {}) if isinstance(c, dict) else {}
                summ = (c.get('summary_metrics') or {}) if isinstance(c, dict) else {}

                spend = _num(ins.get('spend') if ins.get('spend') is not None else summ.get('total_spend') or 0, float)
                impressions = int(_num(ins.get('impressions') if ins.get('impressions') is not None else summ.get('total_impressions') or 0, float))
                clicks = int(_num(ins.get('clicks') if ins.get('clicks') is not None else summ.get('total_clicks') or 0, float))

                total_spend += spend
                total_impressions += impressions
                total_clicks += clicks

            if total_spend > 0 or total_impressions > 0 or total_clicks > 0:
                has_insights_data = True
                summary_parts.append(f"**Dữ liệu campaigns:** {campaigns_with_insights}/{context.get('campaigns_count', 0)} có insights")
                summary_parts.append(f"**Tổng chi tiêu ({len(all_campaigns)} campaigns):** {int(total_spend):,}₫")
                summary_parts.append(f"**Tổng impressions:** {total_impressions:,}")
                summary_parts.append(f"**Tổng clicks:** {total_clicks:,}")

                if total_impressions > 0:
                    avg_ctr = (total_clicks / total_impressions) * 100
                    summary_parts.append(f"**CTR trung bình:** {avg_ctr:.2f}%")
                if total_clicks > 0:
                    avg_cpc = total_spend / total_clicks if total_clicks else 0
                summary_parts.append(f"**CPC trung bình:** {int(avg_cpc):,}₫")

                if campaigns_without_insights > 0:
                    summary_parts.append(f"**{campaigns_without_insights} campaigns chưa có dữ liệu insights**")
        
        # Thông tin campaigns gần đây (fallback)
        recent_campaigns = context.get('recent_campaigns', [])
        if recent_campaigns and not has_insights_data:
            campaigns_with_data = [c for c in recent_campaigns if c.get('spend', 0) > 0 or c.get('impressions', 0) > 0]
            if campaigns_with_data:
                has_insights_data = True
                total_spend = sum(c.get('spend', 0) for c in campaigns_with_data)
                total_impressions = sum(c.get('impressions', 0) for c in campaigns_with_data)
                summary_parts.append(f"**Chi tiêu {len(campaigns_with_data)} campaigns có dữ liệu:** ${total_spend:,.2f}")
                summary_parts.append(f"**Tổng impressions:** {total_impressions:,}")
            else:
                summary_parts.append(f"**Lưu ý:** {len(recent_campaigns)} campaigns nhưng chưa có dữ liệu insights")
        
        # Dữ liệu daily gần đây
        daily_data = context.get('daily_data', [])
        if daily_data:
            has_insights_data = True
            recent_spend = sum(d.get('spend', 0) for d in daily_data[-3:])  # 3 ngày gần nhất
            avg_ctr = sum(d.get('ctr', 0) for d in daily_data) / len(daily_data) if daily_data else 0
            summary_parts.append(f"**Chi tiêu 3 ngày gần:** {int(recent_spend):,}₫")
            summary_parts.append(f"**CTR trung bình:** {avg_ctr:.2f}%")
        
        # Thông báo nếu không có dữ liệu insights
        if not has_insights_data and campaigns_count > 0:
            summary_parts.append(f"**Tình trạng:** Không có dữ liệu insights cho các campaigns. Có thể do:")
            summary_parts.append(f"   • Tất cả campaigns đều PAUSED và chưa từng chạy")
            summary_parts.append(f"   • Token không có quyền truy cập insights")
            summary_parts.append(f"   • Cần refresh dữ liệu để lấy insights")
        
        # Filters hiện tại
        current_filters = context.get('current_filters', {})
        if current_filters:
            filter_parts = []
            if current_filters.get('date_range'):
                filter_parts.append(f"Khoảng thời gian: {current_filters['date_range']}")
            if current_filters.get('metric_focus'):
                filter_parts.append(f"Metric focus: {current_filters['metric_focus']}")
            if filter_parts:
                summary_parts.append(f"**Filters:** {', '.join(filter_parts)}")
        
        return "\n".join(summary_parts) if summary_parts else "Không có dữ liệu context"
    
    def _build_conversation_context(self, conversation_history: List[Dict[str, Any]]) -> str:
        """Xây dựng ngữ cảnh cuộc trò chuyện"""
        if not conversation_history:
            return "Chưa có lịch sử cuộc trò chuyện"
        
        context_parts = []
        for item in conversation_history[-3:]:  # Chỉ lấy 3 cuộc trò chuyện gần nhất
            if item.get('type') == 'user':
                context_parts.append(f"Hỏi: {item.get('question', '')}")
            elif item.get('type') == 'bot':
                # Chỉ lấy 100 ký tự đầu của câu trả lời để tránh quá dài
                answer = item.get('answer', '')
                if len(answer) > 100:
                    answer = answer[:100] + "..."
                context_parts.append(f"Trả lời: {answer}")
        
        return "\n".join(context_parts)
    
    def ask_question(self, question: str, context: Dict[str, Any]) -> str:
        if not self.api_key:
            return "Xin lỗi, API key chưa được cấu hình. Vui lòng kiểm tra cài đặt."
        
        try:
            # Xây dựng context phong phú hơn
            context_summary = self._build_context_summary(context)
            conversation_context = self._build_conversation_context(context.get('conversation_history', []))
            
            system_prompt = (
                "Bạn là chuyên gia phân tích Facebook Ads với 10+ năm kinh nghiệm. "
                "Nhiệm vụ của bạn:\n"
                "1. Phân tích dữ liệu quảng cáo một cách chính xác và sâu sắc\n"
                "2. Đưa ra insights có giá trị và đề xuất hành động cụ thể\n"
                "3. Sử dụng ngôn ngữ tiếng Việt tự nhiên, thân thiện\n"
                "4. Trả lời ngắn gọn nhưng đầy đủ thông tin\n"
                "5. Highlight các số liệu quan trọng bằng **bold**\n"
                "6. Nếu dữ liệu không đủ, hãy nói rõ và đề xuất cách lấy thêm dữ liệu\n\n"
                "**QUAN TRỌNG:** Nếu dashboard không có dữ liệu insights (tất cả campaigns đều PAUSED hoặc không có metrics), "
                "hãy:\n"
                "• Giải thích rõ ràng tại sao không có dữ liệu\n"
                "• Đưa ra hướng dẫn cụ thể để thu thập dữ liệu\n"
                "• Đề xuất các bước để bắt đầu campaigns mới\n"
                "• Cung cấp lời khuyên dựa trên best practices\n\n"
                "Luôn bắt đầu bằng việc tóm tắt ngắn gọn tình hình hiện tại trước khi trả lời câu hỏi cụ thể."
            )
            
            user_prompt = (
                f"**NGỮ CẢNH DASHBOARD:**\n{context_summary}\n\n"
                f"**LỊCH SỬ CUỘC TRÒ CHUYỆN:**\n{conversation_context}\n\n"
                f"**CÂU HỎI:** {question}\n\n"
                "**YÊU CẦU:** Trả lời chi tiết, có insights và đề xuất hành động cụ thể. "
                "Sử dụng format markdown để làm nổi bật thông tin quan trọng."
            )
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': os.getenv('OPENAI_CHAT_MODEL', 'gpt-4o-mini'),
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                'max_tokens': 800,
                'temperature': 0.7
            }
            
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            answer = result['choices'][0]['message']['content']
            
            logger.info(f"OpenAI API response: {answer[:200]}...")
            return answer
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Lỗi API OpenAI: {e}")
            return f"Xin lỗi, có lỗi khi kết nối đến OpenAI API: {str(e)}"
        except Exception as e:
            logger.error(f"Lỗi không mong muốn: {e}")
            return "Xin lỗi, có lỗi xảy ra khi xử lý yêu cầu."

def load_ads_data() -> Dict[str, Any]:
    import time
    max_retries = 3
    retry_delay = 0.1
    
    for attempt in range(max_retries):
        try:
            with open('ads_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate that we have campaigns data
            if not data.get('campaigns') or len(data.get('campaigns', [])) == 0:
                if attempt < max_retries - 1:
                    logger.warning(f"Empty campaigns data on attempt {attempt + 1}, retrying...")
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.warning("No campaigns found in data file")
                    return {
                        'extraction_date': datetime.now().isoformat(),
                        'campaigns': [],
                        'message': 'Không tìm thấy chiến dịch nào trong dữ liệu'
                    }
            
            return data
            
        except FileNotFoundError:
            logger.warning(f"File ads_data.json không tìm thấy, attempt {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            return {
                'extraction_date': datetime.now().isoformat(),
                'campaigns': [],
                'message': 'File dữ liệu không tồn tại'
            }
        except (json.JSONDecodeError, PermissionError, OSError) as e:
            logger.warning(f"Lỗi đọc file dữ liệu attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            logger.error(f"Lỗi khi đọc file dữ liệu sau {max_retries} attempts: {e}")
            return {'error': f'Lỗi đọc dữ liệu: {str(e)}'}
        except Exception as e:
            logger.error(f"Lỗi không mong muốn khi đọc file dữ liệu: {e}")
            return {'error': f'Lỗi đọc dữ liệu: {str(e)}'}
    
    # This should not be reached, but just in case
    return {'error': 'Không thể đọc dữ liệu sau nhiều lần thử'}

@app.route('/')
def index():
    return render_template('index_new.html')

@app.route('/old')
def index_old():
    return render_template('index.html')

@app.route('/api/ads-data')
def get_ads_data():
    try:
        data = load_ads_data()
        return jsonify(data)
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ask', methods=['POST'])
def ask_question():
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        context = data.get('context') or {}
        
        if not question:
            return jsonify({'error': 'Câu hỏi không được để trống'}), 400
        
        global_data = load_ads_data()
        if isinstance(context, dict):
            # Ưu tiên dữ liệu từ frontend nếu có, fallback về global_data
            context.setdefault('extraction_date', context.get('extraction_date') or global_data.get('extraction_date'))
            context['campaigns_count'] = context.get('campaigns_count') or len(global_data.get('campaigns', []))

            # Lấy tất cả campaigns (bao gồm đang chạy, tạm dừng, đã dừng)
            campaigns = global_data.get('campaigns', [])

            # Nếu frontend chưa cung cấp all_campaigns_data, sử dụng dữ liệu từ global_data (KHÔNG lọc theo insights)
            if not context.get('all_campaigns_data'):
                context.setdefault('all_campaigns', campaigns)
                context.setdefault('sample_campaigns', campaigns[:50])
            else:
                # Sử dụng dữ liệu từ frontend nguyên bản (KHÔNG lọc theo insights)
                all_campaigns_data = context.get('all_campaigns_data', [])
                context.setdefault('all_campaigns', all_campaigns_data)
                context.setdefault('sample_campaigns', all_campaigns_data[:50])

            # Tính lại số lượng campaigns có/không có insights dựa trên danh sách thực tế
            effective_campaigns = context.get('all_campaigns') or []
            with_insights = sum(1 for c in effective_campaigns if c.get('insights'))
            without_insights = max(len(effective_campaigns) - with_insights, 0)
            context['campaigns_with_insights'] = with_insights
            context['campaigns_without_insights'] = without_insights
        
        chatbot = OpenAIChatbot()
        
        answer = chatbot.ask_question(question, context)
        
        return jsonify({
            'question': question,
            'answer': answer,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Lỗi khi xử lý câu hỏi: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'openai_configured': bool(os.getenv('OPENAI_API_KEY'))
    })

@app.route('/api/debug-data')
def debug_data():
    """Debug endpoint để kiểm tra dữ liệu"""
    try:
        data = load_ads_data()
        campaigns_with_insights = [c for c in data.get('campaigns', []) if c.get('insights')]
        
        return jsonify({
            'total_campaigns': len(data.get('campaigns', [])),
            'campaigns_with_insights': len(campaigns_with_insights),
            'extraction_date': data.get('extraction_date'),
            'sample_campaign': campaigns_with_insights[0] if campaigns_with_insights else None,
            'status': 'success'
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'status': 'error'
        })

# Global refresh status tracking
refresh_status = {
    'status': 'idle',  # idle, running, completed, error
    'progress': 0,
    'message': '',
    'error': None,
    'campaigns_count': 0,
    'extraction_date': None
}

def background_refresh(start_date):
    """Background task to refresh data"""
    global refresh_status
    
    try:
        refresh_status['status'] = 'running'
        refresh_status['progress'] = 10
        refresh_status['message'] = 'Đang kiểm tra kết nối Facebook API...'
        
        extractor = FacebookAdsExtractor()
        if not extractor.test_connection():
            refresh_status.update({
                'status': 'error',
                'error': 'Không thể kết nối đến Facebook API. Vui lòng kiểm tra token và kết nối mạng.',
                'connection_error': True
            })
            return
        
        refresh_status['progress'] = 20
        refresh_status['message'] = 'Đang trích xuất dữ liệu campaigns...'
        logger.info(f"Bắt đầu refresh dữ liệu từ ngày: {start_date or '2023-01-01'}")
        
        data = extractor.extract_all_data(start_date or "2023-01-01")
        
        refresh_status['progress'] = 80
        refresh_status['message'] = 'Đang lưu dữ liệu...'
        
        if data.get('error'):
            refresh_status.update({
                'status': 'error',
                'error': data['error'],
                'extraction_error': True
            })
            return
        
        ok = extractor.save_to_json(data, "ads_data.json")
        
        if not ok:
            refresh_status.update({
                'status': 'error',
                'error': 'Không thể lưu dữ liệu vào file',
                'save_error': True
            })
            return
        
        refresh_status.update({
            'status': 'completed',
            'progress': 100,
            'message': 'Hoàn thành refresh dữ liệu',
            'campaigns_count': len(data.get('campaigns', [])),
            'extraction_date': data.get('extraction_date')
        })
        
        logger.info(f"Refresh thành công: {len(data.get('campaigns', []))} campaigns")
        
    except requests.exceptions.Timeout:
        logger.error("Timeout khi kết nối Facebook API")
        refresh_status.update({
            'status': 'error',
            'error': 'Timeout khi kết nối Facebook API',
            'timeout_error': True
        })
    except requests.exceptions.ConnectionError:
        logger.error("Lỗi kết nối mạng")
        refresh_status.update({
            'status': 'error',
            'error': 'Lỗi kết nối mạng đến Facebook API',
            'connection_error': True
        })
    except ValueError as e:
        logger.error(f"Lỗi cấu hình: {e}")
        refresh_status.update({
            'status': 'error',
            'error': f'Lỗi cấu hình: {str(e)}',
            'config_error': True
        })
    except Exception as e:
        logger.error(f"Lỗi refresh không mong muốn: {e}")
        refresh_status.update({
            'status': 'error',
            'error': f'Lỗi không mong muốn: {str(e)}',
            'unknown_error': True
        })

@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """Start background refresh task"""
    global refresh_status
    
    # Check if already running
    if refresh_status['status'] == 'running':
        return jsonify({
            'ok': False,
            'error': 'Refresh đang chạy, vui lòng chờ hoàn thành',
            'already_running': True
        }), 409
    
    try:
        start_date = request.json.get('start_date') if request.is_json else None
        
        # Reset status
        refresh_status.update({
            'status': 'running',
            'progress': 0,
            'message': 'Đang khởi tạo...',
            'error': None,
            'campaigns_count': 0,
            'extraction_date': None
        })
        
        # Start background task
        import threading
        thread = threading.Thread(target=background_refresh, args=(start_date,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'ok': True,
            'message': 'Đã bắt đầu refresh dữ liệu trong background',
            'status': 'started'
        })
        
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo refresh: {e}")
        refresh_status['status'] = 'error'
        refresh_status['error'] = str(e)
        return jsonify({
            'ok': False, 
            'error': f'Lỗi khi khởi tạo refresh: {str(e)}'
        }), 500

@app.route('/api/refresh-status')
def refresh_status_endpoint():
    """Get current refresh status"""
    return jsonify(refresh_status)

@app.route('/api/refresh-budgets')
def api_refresh_budgets():
    """Refresh budget cache for all campaigns"""
    try:
        token = os.getenv('FACEBOOK_ACCESS_TOKEN')
        if not token:
            return jsonify({'error': 'Facebook access token not found'}), 500
        
        # Load campaigns data
        ads_data = load_ads_data()
        campaigns = ads_data.get('campaigns', [])
        
        if not campaigns:
            return jsonify({'error': 'No campaigns found'}), 404
        
        base_url = 'https://graph.facebook.com/v23.0'
        updated_count = 0
        failed_count = 0
        
        # Process campaigns in small batches to avoid rate limiting
        batch_size = 3
        for i in range(0, min(len(campaigns), 10), batch_size):  # Limit to 10 campaigns
            batch = campaigns[i:i+batch_size]
            
            for campaign in batch:
                campaign_id = campaign.get('campaign_id')
                if not campaign_id:
                    continue
                
                try:
                    # Check if we already have valid cache
                    cached_budget = budget_cache.get_campaign_budget(campaign_id)
                    if cached_budget:
                        continue  # Skip if already cached
                    
                    # Fetch budget from Facebook API
                    url = f"{base_url}/{campaign_id}"
                    params = {
                        'access_token': token,
                        'fields': 'daily_budget,lifetime_budget,budget_remaining'
                    }
                    
                    response = requests.get(url, params=params, timeout=10)
                    if response.status_code == 200:
                        budget_info = response.json()
                        budget_data = {
                            'daily_budget': float(budget_info.get('daily_budget', 0) or 0),
                            'lifetime_budget': float(budget_info.get('lifetime_budget', 0) or 0),
                            'budget_remaining': float(budget_info.get('budget_remaining', 0) or 0)
                        }
                        
                        # Cache the budget data
                        budget_cache.set_campaign_budget(campaign_id, budget_data)
                        updated_count += 1
                        
                        logger.info(f"Updated budget cache for campaign {campaign_id}")
                    else:
                        logger.warning(f"Failed to get budget for campaign {campaign_id}: {response.status_code}")
                        failed_count += 1
                    
                    # Small delay to avoid rate limiting
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error fetching budget for campaign {campaign_id}: {e}")
                    failed_count += 1
            
            # Longer delay between batches
            if i + batch_size < len(campaigns):
                time.sleep(3)
        
        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'failed_count': failed_count,
            'cache_valid': budget_cache.is_cache_available(),
            'message': f'Updated budget cache for {updated_count} campaigns'
        })
        
    except Exception as e:
        logger.error(f"Error in /api/refresh-budgets: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/campaign-insights')
def api_campaign_insights():
    try:
        campaign_id = request.args.get('campaign_id', '').strip()
        since = request.args.get('since')
        until = request.args.get('until')
        date_preset = request.args.get('date_preset', '').strip()
        campaign_status = request.args.get('status', '').upper()
        if not campaign_id:
            return jsonify({'error': 'campaign_id is required'}), 400
        token = get_access_token()
        if not token:
            return jsonify({'error': 'Missing access token'}), 500

        base_url = 'https://graph.facebook.com/v23.0'
        url = f"{base_url}/{campaign_id}/insights"
        def fetch(params):
            r = requests.get(url, params=params, timeout=30)
            return r.status_code, r.json()

        initial_preset = 'last_7d' if campaign_status == 'ACTIVE' else 'last_30d'
        if date_preset:
            initial_preset = date_preset
        params = {
            'access_token': token,
            'fields': 'campaign_name,impressions,clicks,spend,ctr,cpc,cpm,reach,frequency,actions,conversion_values,inline_link_clicks,inline_link_click_ctr,unique_inline_link_clicks',
            'date_preset': initial_preset,
            'time_increment': 1
        }
        if since and until:
            params['date_preset'] = 'custom'
            params['since'] = since
            params['until'] = until

        status_code, data = fetch(params)
        if status_code != 200:
            err = data.get('error', {})
            if err.get('code') == 190:
                return jsonify({'error': err, 'token_expired': True, 'totals': {}, 'daily': []})
            params_f = {'access_token': token, 'fields': 'campaign_name,impressions,clicks,spend,ctr,cpc,cpm,reach,frequency', 'date_preset': 'lifetime'}
            st2, d2 = fetch(params_f)
            rows2 = d2.get('data', []) if st2 == 200 else []
            if rows2:
                return jsonify({'totals': {}, 'daily': rows2, 'note': 'Fallback to lifetime due to upstream error'})
            return jsonify({'error': err or {'message': 'Unknown error'}, 'totals': {}, 'daily': []})
        rows = data.get('data', [])

        if not rows:
            params2 = params.copy()
            if campaign_status == 'ACTIVE':
                params2['date_preset'] = 'last_30d'
            else:
                params2['date_preset'] = 'last_90d'
            status_code, data = fetch(params2)
            if status_code == 200:
                rows = data.get('data', [])

        if not rows and campaign_status == 'ACTIVE':
            for preset in ['yesterday', 'today']:
                params3a = params.copy()
                params3a['date_preset'] = preset
                sc_try, data = fetch(params3a)
                if sc_try == 200:
                    rows = data.get('data', [])
                    if rows:
                        break

        if not rows:
            params3 = {
                'access_token': token,
                'fields': 'campaign_name,impressions,clicks,spend,ctr,cpc,cpm,reach,frequency',
                'date_preset': 'lifetime'
            }
            status_code, data = fetch(params3)
            if status_code == 200:
                rows = data.get('data', [])
        def _row_date_key(r):
            return (r.get('date_start') or r.get('date') or r.get('date_stop') or '')
        try:
            rows = sorted(rows, key=_row_date_key)
        except Exception:
            pass

        totals = {
            'impressions': 0,
            'clicks': 0,
            'spend': 0.0,
            'reach': 0,
            'inline_link_clicks': 0,
            'post_engagement': 0,
            'photo_view': 0,
            'video_views': 0,
            'unique_inline_link_clicks': 0,
            # Custom aggregated actions for funnel
            'messaging_starts': 0,
            'messaging_contacts': 0,
            'messaging_new_contacts': 0,
            'purchases': 0,
        }

        def sum_video_actions(action_list):
            if not isinstance(action_list, list):
                return 0
            total = 0
            for a in action_list:
                try:
                    total += int(float(a.get('value', 0) or 0))
                except Exception:
                    continue
            return total

        for r in rows:
            totals['impressions'] += int(float(r.get('impressions', 0) or 0))
            totals['clicks'] += int(float(r.get('clicks', 0) or 0))
            totals['spend'] += float(r.get('spend', 0) or 0)
            totals['reach'] += int(float(r.get('reach', 0) or 0))

            totals['inline_link_clicks'] += int(float(r.get('inline_link_clicks', 0) or 0))
            totals['unique_inline_link_clicks'] += int(float(r.get('unique_inline_link_clicks', 0) or 0))

            for a in (r.get('actions') or []):
                at = (a.get('action_type') or '').lower()
                try:
                    val = int(float(a.get('value', 0) or 0))
                except Exception:
                    val = 0
                if at == 'post_engagement':
                    totals['post_engagement'] += val
                elif at == 'photo_view':
                    totals['photo_view'] += val
                elif at in ('link_click', 'landing_page_view'):
                    totals['inline_link_clicks'] += val
                # Messaging conversations/new connections
                elif ('messaging' in at and ('conversation' in at or 'new_messaging_connection' in at or 'first_reply' in at)) or \
                     at.startswith('onsite_conversion.messaging') or \
                     at in ['messaging_conversation_started', 'messaging_first_reply', 'onsite_conversion.messaging_conversation_started', 'onsite_conversion.messaging_first_reply']:
                    # Count total contacts
                    totals['messaging_contacts'] += val
                    # Count new contacts for start-type events
                    if ('conversation' in at or 'new_messaging_connection' in at) or \
                       at in ['messaging_conversation_started', 'onsite_conversion.messaging_conversation_started']:
                        totals['messaging_new_contacts'] += val
                    # Backward compatible counter
                    totals['messaging_starts'] += val
                # Purchases (cover multiple action type variants)
                elif at == 'purchase' or 'purchase' in at:
                    totals['purchases'] += val

            # Process conversion_values for messaging conversions
            for cv in (r.get('conversion_values') or []):
                cv_type = (cv.get('action_type') or '').lower()
                try:
                    cv_val = float(cv.get('value', 0) or 0)
                except Exception:
                    cv_val = 0
                # Handle messaging conversion values
                if (cv_type.startswith('onsite_conversion.messaging') or 
                    cv_type in ['messaging_conversation_started', 'messaging_first_reply', 'onsite_conversion.messaging_conversation_started', 'onsite_conversion.messaging_first_reply'] or
                    ('messaging' in cv_type and 'conversion' in cv_type)):
                    # Count total contacts
                    totals['messaging_contacts'] += int(cv_val)
                    # Count new contacts for start-type events
                    if ('conversation' in cv_type) or \
                       cv_type in ['messaging_conversation_started', 'onsite_conversion.messaging_conversation_started']:
                        totals['messaging_new_contacts'] += int(cv_val)
                    totals['messaging_starts'] += int(cv_val)

            totals['video_views'] += sum_video_actions(r.get('video_play_actions'))
            totals['video_views'] += sum_video_actions(r.get('video_3_sec_watched_actions'))
            totals['video_views'] += sum_video_actions(r.get('video_10_sec_watched_actions'))

        totals['ctr'] = (totals['clicks'] / max(totals['impressions'], 1)) * 100.0
        totals['frequency'] = (totals['impressions'] / max(totals['reach'], 1)) if totals['reach'] > 0 else 0.0

        return jsonify({'totals': totals, 'daily': rows})
    except Exception as e:
        logger.error(f"Lỗi /api/campaign-insights: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/campaign-breakdown')
def api_campaign_breakdown():
    try:
        campaign_id = request.args.get('campaign_id', '').strip()
        kind = request.args.get('kind', 'placement')
        date_preset = request.args.get('date_preset', 'last_30d')
        since = request.args.get('since')
        until = request.args.get('until')
        if not campaign_id:
            return jsonify({'error': 'campaign_id is required'}), 400
        token = get_access_token()
        base_url = 'https://graph.facebook.com/v23.0'
        breakdowns = {
            'placement': 'placement',
            'age_gender': 'age,gender',
            'country': 'country'
        }.get(kind, 'placement')
        params = {
            'access_token': token,
            'fields': 'impressions,clicks,spend,ctr,cpc,cpm,reach,frequency,actions,inline_link_clicks,video_play_actions',
            'breakdowns': breakdowns,
            'date_preset': date_preset
        }
        if since and until:
            params['date_preset'] = 'custom'
            params['since'] = since
            params['until'] = until
        res = requests.get(f"{base_url}/{campaign_id}/insights", params=params, timeout=30)
        data = res.json()
        rows = []
        if res.status_code == 200:
            rows = data.get('data', [])
        else:
            if since and until:
                p2 = params.copy()
                p2.pop('since', None); p2.pop('until', None)
                p2['date_preset'] = 'last_30d'
                res_try = requests.get(f"{base_url}/{campaign_id}/insights", params=p2, timeout=30)
                if res_try.status_code == 200:
                    rows = res_try.json().get('data', [])
                    data = res_try.json()
                    res = res_try
            if not rows and kind == 'placement':
                fb_params = (p2 if (since and until) else params).copy()
                fb_params['breakdowns'] = 'publisher_platform,platform_position'
                res2 = requests.get(f"{base_url}/{campaign_id}/insights", params=fb_params, timeout=30)
                if res2.status_code == 200:
                    rows_raw = res2.json().get('data', [])
                    for r in rows_raw:
                        r['placement'] = f"{r.get('publisher_platform','')}:{r.get('platform_position','')}"
                    rows = rows_raw
                else:
                    err = data.get('error', {})
                    if err.get('code') == 190:
                        return jsonify({'error': err, 'token_expired': True, 'rows': []})
                    return jsonify({'error': err or {'message': 'Unknown error'}, 'rows': []})
            elif not rows:
                err = data.get('error', {})
                if err.get('code') == 190:
                    return jsonify({'error': err, 'token_expired': True, 'rows': []})
                return jsonify({'error': err or {'message': 'Unknown error'}, 'rows': []})
        return jsonify({'rows': rows})
    except Exception as e:
        logger.error(f"Lỗi /api/campaign-breakdown: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/daily-breakdowns')
def api_daily_breakdowns():
    try:
        date_preset = request.args.get('date_preset', 'last_30d').strip()
        since = (request.args.get('since') or '').strip()
        until = (request.args.get('until') or '').strip()
        filter_brand = (request.args.get('brand') or '').strip()
        filter_campaign_id = (request.args.get('campaign_id') or '').strip()
        since = (request.args.get('since') or '').strip()
        until = (request.args.get('until') or '').strip()
        filter_brand = (request.args.get('brand') or '').strip()
        filter_campaign_id = (request.args.get('campaign_id') or '').strip()
        token = get_access_token()
        if not token:
            return jsonify({'error': 'Missing access token'}), 500

        ads_data = load_ads_data()
        if ads_data.get('error'):
            return jsonify({'error': ads_data['error']}), 500
        campaigns = ads_data.get('campaigns', [])
        base_url = 'https://graph.facebook.com/v23.0'

        agg = { 'gender': {}, 'age': {}, 'country': {} }

        def add_row(bucket, key, row):
            g = agg[bucket].setdefault(key or 'unknown', {'impressions':0,'clicks':0,'ctr':0.0,'new_messages':0})
            g['impressions'] += int(float(row.get('impressions',0) or 0))
            g['clicks'] += int(float(row.get('clicks',0) or 0))
            newm = 0
            for a in (row.get('actions') or []):
                at=(a.get('action_type') or '').lower()
                try:
                    val=int(float(a.get('value',0) or 0))
                except Exception:
                    val=0
                if (at in ['messaging_conversation_started','onsite_conversion.messaging_conversation_started','new_messaging_connection'] or 'conversation' in at):
                    newm += val
            g['new_messages'] += newm

        # Prefer querying at Ad Account level for reliable breakdowns
        account_id = None
        for c in campaigns:
            if c.get('account_id'):
                account_id = c['account_id']
                break
        # Fallback: try from env if not found
        if not account_id:
            account_id = os.getenv('FB_AD_ACCOUNT_ID')

        if not account_id:
            return jsonify({'error': 'Không xác định được ad account id để lấy breakdowns'}), 500

        for kind, breakdowns in [('gender','gender'),('age','age'),('region','region')]:
            params={
                'access_token': token,
                'fields':'impressions,clicks,actions',
                'breakdowns': breakdowns,
                'date_preset': date_preset
            }
            res = requests.get(f"{base_url}/{account_id}/insights", params=params, timeout=25)
            if res.status_code!=200:
                for fb in ['last_30d','last_90d','lifetime']:
                    params_fb=params.copy(); params_fb['date_preset']=fb
                    res = requests.get(f"{base_url}/{account_id}/insights", params=params_fb, timeout=25)
                    if res.status_code==200:
                        break
            if res.status_code!=200:
                continue
            for r in res.json().get('data', []):
                if kind=='gender':
                    add_row('gender', r.get('gender'), r)
                elif kind=='age':
                    add_row('age', r.get('age'), r)
                else:
                    add_row('country', (r.get('region') or r.get('country')), r)

        # finalize CTR
        for bucket in agg.values():
            for _,v in bucket.items():
                v['ctr'] = (v['clicks']/max(v['impressions'],1))*100.0

        return jsonify({'gender':agg['gender'],'age':agg['age'],'country':agg['country']})
    except Exception as e:
        logger.error(f"Lỗi /api/daily-breakdowns: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/campaign-ads')
def api_campaign_ads():
    try:
        campaign_id = request.args.get('campaign_id', '').strip()
        date_preset = request.args.get('date_preset', 'last_30d')
        if not campaign_id:
            return jsonify({'error': 'campaign_id is required'}), 400
        token = get_access_token()
        base_url = 'https://graph.facebook.com/v23.0'

        ads_res = requests.get(f"{base_url}/{campaign_id}/ads", params={'access_token': token, 'fields': 'id,name,adset_id,status,created_time', 'limit': 50}, timeout=30)
        ads_data = ads_res.json()
        if ads_res.status_code != 200:
            err = ads_data.get('error', {})
            if err.get('code') == 190:
                return jsonify({'error': err, 'token_expired': True, 'items': []})
            return jsonify({'error': err or {'message': 'Unknown error'}, 'items': []})
        ads = ads_data.get('data', [])

        result = []
        for ad in ads[:20]:
            ins_params = {
                'access_token': token,
                'fields': 'impressions,clicks,spend,ctr,cpc,cpm,reach',
                'date_preset': date_preset
            }
            ins_res = requests.get(f"{base_url}/{ad['id']}/insights", params=ins_params, timeout=30)
            ins = ins_res.json().get('data', []) if ins_res.status_code == 200 else []
            result.append({'ad': ad, 'insights': ins[0] if ins else {}})

        return jsonify({'items': result})
    except Exception as e:
        logger.error(f"Lỗi /api/campaign-ads: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/campaign-adsets')
def api_campaign_adsets():
    try:
        campaign_id = request.args.get('campaign_id', '').strip()
        if not campaign_id:
            return jsonify({'error': 'campaign_id is required', 'items': []}), 400
        token = get_access_token()
        base_url = 'https://graph.facebook.com/v23.0'
        res = requests.get(f"{base_url}/{campaign_id}/adsets", params={'access_token': token, 'fields': 'id,name,status,campaign_id', 'limit': 100}, timeout=30)
        data = res.json()
        if res.status_code != 200:
            err = data.get('error', {})
            if err.get('code') == 190:
                return jsonify({'error': err, 'token_expired': True, 'items': []})
            return jsonify({'error': err or {'message': 'Unknown error'}, 'items': []})
        return jsonify({'items': data.get('data', [])})
    except Exception as e:
        logger.error(f"Lỗi /api/campaign-adsets: {e}")
        return jsonify({'error': str(e), 'items': []}), 500

@app.route('/api/adset-ads')
def api_adset_ads():
    try:
        adset_id = request.args.get('adset_id', '').strip()
        date_preset = request.args.get('date_preset', 'last_30d')
        if not adset_id:
            return jsonify({'error': 'adset_id is required', 'items': []}), 400
        token = get_access_token()
        base_url = 'https://graph.facebook.com/v23.0'
        ads_res = requests.get(f"{base_url}/{adset_id}/ads", params={'access_token': token, 'fields': 'id,name,status,created_time', 'limit': 100}, timeout=30)
        ads_data = ads_res.json()
        if ads_res.status_code != 200:
            err = ads_data.get('error', {})
            if err.get('code') == 190:
                return jsonify({'error': err, 'token_expired': True, 'items': []})
            return jsonify({'error': err or {'message': 'Unknown error'}, 'items': []})
        ads = ads_data.get('data', [])
        result = []
        for ad in ads[:50]:
            ins_params = {'access_token': token, 'fields': 'impressions,clicks,spend,ctr,cpc,cpm,reach', 'date_preset': date_preset}
            ins_res = requests.get(f"{base_url}/{ad['id']}/insights", params=ins_params, timeout=30)
            ins = ins_res.json().get('data', []) if ins_res.status_code == 200 else []
            result.append({'ad': ad, 'insights': ins[0] if ins else {}})
        return jsonify({'items': result})
    except Exception as e:
        logger.error(f"Lỗi /api/adset-ads: {e}")
        return jsonify({'error': str(e), 'items': []}), 500

@app.route('/api/daily-tracking')
def api_daily_tracking():
    try:
        date_preset = request.args.get('date_preset', 'last_30d').strip()
        since = (request.args.get('since') or '').strip()
        until = (request.args.get('until') or '').strip()
        filter_brand = (request.args.get('brand') or '').strip()
        filter_campaign_id = (request.args.get('campaign_id') or '').strip()
        token = get_access_token()
        
        if not token:
            return jsonify({'error': 'Missing access token'}), 500
        
        # Get all campaigns from ads_data.json
        ads_data = load_ads_data()
        if ads_data.get('error'):
            return jsonify({'error': ads_data['error']}), 500
        
        campaigns = ads_data.get('campaigns', [])
        if not campaigns:
            return jsonify({'error': 'No campaigns found', 'daily': [], 'totals': {}})
        
        # Apply brand and campaign filters if provided
        def _extract_brand(name: str) -> str:
            try:
                return extract_brand_from_campaign_name(name or '')
            except Exception:
                return 'Unknown'
        
        filtered_campaigns = campaigns
        if filter_brand and filter_brand != 'all':
            filtered_campaigns = [c for c in filtered_campaigns if _extract_brand(c.get('campaign_name', '')) == filter_brand]
        if filter_campaign_id and filter_campaign_id != 'all':
            filtered_campaigns = [c for c in filtered_campaigns if c.get('campaign_id') == filter_campaign_id]
        
        # Fallback if filters remove all
        if not filtered_campaigns:
            filtered_campaigns = []
        
        base_url = 'https://graph.facebook.com/v23.0'
        all_daily_data = []
        
        # Aggregate data from all campaigns (limit to avoid timeout)
        successful_campaigns = 0
        failed_campaigns = 0
        max_campaigns = 20  # Increase limit to include more campaigns
        
        # Sort campaigns: ACTIVE first, then PAUSED, to prioritize active campaigns
        sorted_campaigns = sorted(filtered_campaigns, key=lambda x: (x.get('status', '') != 'ACTIVE', x.get('campaign_id', '')))
        
        for campaign in sorted_campaigns[:max_campaigns]:
            campaign_id = campaign.get('campaign_id')
            if not campaign_id:
                continue
                
            try:
                # Get budget data from cache
                cached_budget = budget_cache.get_campaign_budget(campaign_id)
                if cached_budget:
                    budget_data = cached_budget
                    logger.debug(f"Using cached budget for campaign {campaign_id}")
                else:
                    # Fallback to 0 if no cache available
                    budget_data = {
                        'daily_budget': 0.0,
                        'lifetime_budget': 0.0,
                        'budget_remaining': 0.0
                    }
                    logger.debug(f"No budget cache for campaign {campaign_id}")
                
                # Get insights data
                url = f"{base_url}/{campaign_id}/insights"
                campaign_status = campaign.get('status', 'UNKNOWN')
                
                # Request fields including actions for messaging, conversions, and ROAS
                params = {
                    'access_token': token,
                    'fields': 'campaign_name,impressions,clicks,spend,ctr,cpc,cpm,reach,frequency,actions,conversion_values,inline_link_clicks,inline_link_click_ctr,unique_inline_link_clicks',
                    'date_preset': date_preset,
                    'time_increment': 1
                }
                # Override with custom range if provided
                if since and until:
                    params['date_preset'] = 'custom'
                    params['since'] = since
                    params['until'] = until
                
                # For PAUSED campaigns, try with longer date range if initial request fails
                fallback_presets = ['last_90d', 'lifetime'] if campaign_status == 'PAUSED' else []
                
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    daily_rows = data.get('data', [])
                    if daily_rows:
                        # Add budget data to each daily row
                        for row in daily_rows:
                            row.update(budget_data)
                        all_daily_data.extend(daily_rows)
                        successful_campaigns += 1
                        
                        # Log successful campaign processing
                        if successful_campaigns == 1:
                            logger.info(f"Successfully processed first campaign {campaign_id} (status: {campaign_status})")
                    else:
                        # Try with fallback presets for campaigns with no data
                        found_data = False
                        for fallback_preset in fallback_presets:
                            params_fallback = params.copy()
                            params_fallback['date_preset'] = fallback_preset
                            response_fallback = requests.get(url, params=params_fallback, timeout=30)
                            if response_fallback.status_code == 200:
                                fallback_data = response_fallback.json()
                                fallback_rows = fallback_data.get('data', [])
                                if fallback_rows:
                                    # Add budget data to each daily row
                                    for row in fallback_rows:
                                        row.update(budget_data)
                                    all_daily_data.extend(fallback_rows)
                                    successful_campaigns += 1
                                    found_data = True
                                    logger.info(f"Got data for PAUSED campaign {campaign_id} with preset {fallback_preset}")
                                    break
                        
                        if not found_data:
                            failed_campaigns += 1
                else:
                    # Try with fallback presets for failed requests
                    found_data = False
                    for fallback_preset in fallback_presets:
                        params_fallback = params.copy()
                        params_fallback['date_preset'] = fallback_preset
                        response_fallback = requests.get(url, params=params_fallback, timeout=30)
                        if response_fallback.status_code == 200:
                            fallback_data = response_fallback.json()
                            fallback_rows = fallback_data.get('data', [])
                            if fallback_rows:
                                # Add budget data to each daily row
                                for row in fallback_rows:
                                    row.update(budget_data)
                                all_daily_data.extend(fallback_rows)
                                successful_campaigns += 1
                                found_data = True
                                logger.info(f"Got fallback data for campaign {campaign_id} (status: {campaign_status}) with preset {fallback_preset}")
                                break
                    
                    if not found_data:
                        failed_campaigns += 1
                        logger.warning(f"Failed to get insights for campaign {campaign_id} (status: {campaign_status}): {response.status_code}")
                    
            except Exception as e:
                failed_campaigns += 1
                logger.warning(f"Error fetching insights for campaign {campaign_id}: {e}")
                continue
        
        logger.info(f"Daily tracking: {successful_campaigns} successful, {failed_campaigns} failed campaigns (processed {min(len(campaigns), max_campaigns)} out of {len(campaigns)} total)")
        
        # Group by date and aggregate
        date_groups = {}
        for row in all_daily_data:
            date_key = row.get('date_start') or row.get('date') or row.get('date_stop') or 'unknown'
            if date_key not in date_groups:
                date_groups[date_key] = {
                    'date_start': date_key,
                    'impressions': 0,
                    'clicks': 0,
                    'spend': 0.0,
                    'reach': 0,
                    'inline_link_clicks': 0,
                    'post_engagement': 0,
                    'photo_view': 0,
                    'video_views': 0,
                    'video_2_sec_watched_actions': 0,
                    'messaging_starts': 0,
                    'purchases': 0,
                    'purchase_value': 0.0,
                    'campaign_count': 0,
                    'budget_remaining': 0.0,
                    'daily_budget': 0.0,
                    'lifetime_budget': 0.0
                }
            
            # Sum numeric fields
            group = date_groups[date_key]
            group['impressions'] += int(float(row.get('impressions', 0) or 0))
            group['clicks'] += int(float(row.get('clicks', 0) or 0))
            group['spend'] += float(row.get('spend', 0) or 0)
            group['reach'] += int(float(row.get('reach', 0) or 0))
            group['inline_link_clicks'] += int(float(row.get('inline_link_clicks', 0) or 0))
            group['post_engagement'] += int(float(row.get('post_engagement', 0) or 0))
            group['photo_view'] += int(float(row.get('photo_view', 0) or 0))
            group['video_views'] += int(float(row.get('video_views', 0) or 0))
            group['messaging_starts'] += int(float(row.get('messaging_starts', 0) or 0))
            group['purchases'] += int(float(row.get('purchases', 0) or 0))
            group['purchase_value'] += float(row.get('purchase_value', 0) or 0)
            group['budget_remaining'] += float(row.get('budget_remaining', 0) or 0)
            group['daily_budget'] += float(row.get('daily_budget', 0) or 0)
            group['lifetime_budget'] += float(row.get('lifetime_budget', 0) or 0)
            group['campaign_count'] += 1
            
            # Process actions array for messaging, conversions, and engagement
            for action in (row.get('actions') or []):
                action_type = (action.get('action_type') or '').lower()
                try:
                    value = int(float(action.get('value', 0) or 0))
                except Exception:
                    value = 0
                
                # Process messaging actions silently
                    
                # Handle different action types based on actual Facebook API response
                # Priority: Messaging actions first, then other conversions
                if action_type == 'post_engagement':
                    group['post_engagement'] += value
                elif action_type == 'photo_view':
                    group['photo_view'] += value
                # Messaging actions - check first to avoid conflicts with conversion actions
                elif (action_type.startswith('onsite_conversion.messaging') or 
                      action_type == 'messaging_starts' or 
                      action_type == 'onsite_conversion.messaging_conversation_started' or
                      action_type == 'onsite_conversion.messaging_first_reply' or
                      action_type == 'messaging_conversation_started' or
                      action_type == 'messaging_first_reply' or
                      action_type == 'new_messaging_connection' or
                      ('messaging' in action_type and 'conversion' in action_type)):
                    group['messaging_starts'] += value
                    group['messaging_contacts'] = group.get('messaging_contacts', 0) + value
                    if (action_type in ['messaging_conversation_started', 'onsite_conversion.messaging_conversation_started', 'new_messaging_connection'] or 
                        ('conversation' in action_type)):
                        group['messaging_new_contacts'] = group.get('messaging_new_contacts', 0) + value
                # Purchase/Conversion actions - only handle actual purchase actions
                elif (action_type == 'purchase' or 
                      action_type == 'offsite_conversion' or 
                      action_type.startswith('offsite_conversion')):
                    group['purchases'] += value
                    # For purchase actions, the value might be purchase value
                    if action_type == 'purchase':
                        try:
                            purchase_value = float(action.get('value', 0) or 0)
                            group['purchase_value'] += purchase_value
                        except Exception:
                            pass
                # Link clicks
                elif action_type == 'link_click' or action_type == 'landing_page_view':
                    group['inline_link_clicks'] += value
            
            # Process conversion_values for messaging conversions
            for cv in (row.get('conversion_values') or []):
                cv_type = (cv.get('action_type') or '').lower()
                try:
                    cv_val = float(cv.get('value', 0) or 0)
                except Exception:
                    cv_val = 0
                # Handle messaging conversion values
                if (cv_type.startswith('onsite_conversion.messaging') or 
                    cv_type in ['messaging_conversation_started', 'messaging_first_reply', 'onsite_conversion.messaging_conversation_started', 'onsite_conversion.messaging_first_reply', 'new_messaging_connection'] or
                    ('messaging' in cv_type and 'conversion' in cv_type)):
                    group['messaging_starts'] += int(cv_val)
                    group['messaging_contacts'] = group.get('messaging_contacts', 0) + int(cv_val)
                    if (cv_type in ['messaging_conversation_started', 'onsite_conversion.messaging_conversation_started', 'new_messaging_connection'] or 
                        ('conversation' in cv_type)):
                        group['messaging_new_contacts'] = group.get('messaging_new_contacts', 0) + int(cv_val)
            
            # Process video actions
            for video_action in (row.get('video_play_actions') or []):
                try:
                    group['video_views'] += int(float(video_action.get('value', 0) or 0))
                except Exception:
                    continue
            
            # Process video 2s+ actions
            for video_action in (row.get('video_2_sec_watched_actions') or []):
                try:
                    group['video_2_sec_watched_actions'] += int(float(video_action.get('value', 0) or 0))
                except Exception:
                    continue
        
        # Calculate derived metrics for each day
        daily_data = []
        for date_key, group in date_groups.items():
            # Calculate frequency
            group['frequency'] = (group['impressions'] / max(group['reach'], 1)) if group['reach'] > 0 else 0.0
            
            # Calculate CTR
            group['ctr'] = (group['clicks'] / max(group['impressions'], 1)) * 100.0
            
            # Calculate CPC
            group['cpc'] = (group['spend'] / max(group['clicks'], 1)) if group['clicks'] > 0 else 0.0
            
            # Calculate CPM
            group['cpm'] = (group['spend'] / max(group['impressions'], 1)) * 1000.0 if group['impressions'] > 0 else 0.0
            
            # Calculate ROAS
            group['roas'] = (group['purchase_value'] / max(group['spend'], 1)) if group['spend'] > 0 else 0.0
            
            # Calculate budget utilization
            total_budget = group['daily_budget'] + group['lifetime_budget']
            if total_budget > 0:
                group['budget_utilization'] = (group['spend'] / total_budget) * 100
            else:
                group['budget_utilization'] = 0.0
            
            daily_data.append(group)
        
        # Sort by date
        daily_data.sort(key=lambda x: x['date_start'])
        
        # Calculate totals
        totals = {
            'impressions': sum(d['impressions'] for d in daily_data),
            'clicks': sum(d['clicks'] for d in daily_data),
            'spend': sum(d['spend'] for d in daily_data),
            'reach': sum(d['reach'] for d in daily_data),
            'inline_link_clicks': sum(d['inline_link_clicks'] for d in daily_data),
            'post_engagement': sum(d['post_engagement'] for d in daily_data),
            'photo_view': sum(d['photo_view'] for d in daily_data),
            'video_views': sum(d['video_views'] for d in daily_data),
            'messaging_starts': sum(d['messaging_starts'] for d in daily_data),
            'messaging_contacts': sum(d.get('messaging_contacts', 0) for d in daily_data),
            'messaging_new_contacts': sum(d.get('messaging_new_contacts', 0) for d in daily_data),
            'purchases': sum(d['purchases'] for d in daily_data),
            'purchase_value': sum(d['purchase_value'] for d in daily_data),
            'budget_remaining': sum(d['budget_remaining'] for d in daily_data),
            'daily_budget': sum(d['daily_budget'] for d in daily_data),
            'lifetime_budget': sum(d['lifetime_budget'] for d in daily_data),
            'total_campaigns': len(campaigns),
            'active_days': len(daily_data)
        }
        
        # Calculate average metrics
        if daily_data:
            totals['avg_frequency'] = sum(d['frequency'] for d in daily_data) / len(daily_data)
            totals['avg_ctr'] = sum(d['ctr'] for d in daily_data) / len(daily_data)
            totals['avg_cpc'] = sum(d['cpc'] for d in daily_data) / len(daily_data)
            totals['avg_cpm'] = sum(d['cpm'] for d in daily_data) / len(daily_data)
            totals['avg_roas'] = sum(d['roas'] for d in daily_data) / len(daily_data)
        else:
            totals['avg_frequency'] = 0
            totals['avg_ctr'] = 0
            totals['avg_cpc'] = 0
            totals['avg_cpm'] = 0
            totals['avg_roas'] = 0
        
        return jsonify({
            'daily': daily_data,
            'totals': totals,
            'date_preset': date_preset,
            'extraction_date': datetime.now().isoformat(),
            'successful_campaigns': successful_campaigns,
            'failed_campaigns': failed_campaigns,
            'total_campaigns': len(campaigns),
            'processed_campaigns': min(len(campaigns), max_campaigns),
            'note': f'Processed {min(len(campaigns), max_campaigns)} out of {len(campaigns)} campaigns to prevent timeout'
        })
        
    except Exception as e:
        logger.error(f"Lỗi /api/daily-tracking: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/campaign-ai-insights', methods=['POST'])
def api_campaign_ai_insights():
    try:
        data = request.get_json()
        campaign_id = data.get('campaign_id', '').strip()
        
        if not campaign_id:
            return jsonify({'error': 'campaign_id is required'}), 400
        
        try:
            from flask import current_app
            with current_app.test_request_context(f'/api/campaign-insights?campaign_id={campaign_id}&status=ACTIVE'):
                insights_response_data = api_campaign_insights()
                if isinstance(insights_response_data, tuple):
                    insights_data = insights_response_data[0].get_json()
                else:
                    insights_data = insights_response_data.get_json()
                    
                if insights_data.get('error'):
                    return jsonify({'error': 'Không thể lấy dữ liệu insights: ' + str(insights_data.get('error'))}), 500
                    
        except Exception as e:
            logger.error(f"Lỗi khi lấy insights data: {e}")
            return jsonify({'error': 'Không thể lấy dữ liệu insights'}), 500
        
        try:
            with current_app.test_request_context(f'/api/campaign-breakdown?campaign_id={campaign_id}&kind=placement&date_preset=last_30d'):
                breakdown_response_data = api_campaign_breakdown()
                if isinstance(breakdown_response_data, tuple):
                    breakdown_data = breakdown_response_data[0].get_json()
                else:
                    breakdown_data = breakdown_response_data.get_json()
                    
                if breakdown_data.get('error'):
                    breakdown_data = {'rows': []}
                    
        except Exception as e:
            logger.error(f"Lỗi khi lấy breakdown data: {e}")
            breakdown_data = {'rows': []}
        
        campaign_analysis_data = {
            'campaign_id': campaign_id,
            'summary_metrics': {
                'total_impressions': insights_data.get('totals', {}).get('impressions', 0),
                'total_clicks': insights_data.get('totals', {}).get('clicks', 0),
                'total_spend': insights_data.get('totals', {}).get('spend', 0),
                'total_reach': insights_data.get('totals', {}).get('reach', 0),
                'avg_ctr': (insights_data.get('totals', {}).get('clicks', 0) / max(insights_data.get('totals', {}).get('impressions', 1), 1)) * 100,
                'avg_cpc': insights_data.get('totals', {}).get('spend', 0) / max(insights_data.get('totals', {}).get('clicks', 1), 1)
            },
            'daily_trends': insights_data.get('daily', [])[-7:],
            'placement_breakdown': breakdown_data.get('rows', [])[:10]
        }
        
        try:
            chatbot = OpenAIChatbot()
            ai_analysis = chatbot.analyze_campaign_performance(campaign_analysis_data)
            
            logger.info(f"AI analysis completed for campaign {campaign_id}, cached: {ai_analysis.get('cached', False)}")
            
            return jsonify({
                'success': True,
                'insights': ai_analysis['insights'],
                'recommendations': ai_analysis['recommendations'],
                'cached': ai_analysis.get('cached', False),
                'analysis_data': campaign_analysis_data,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as ai_error:
            logger.error(f"AI analysis failed for campaign {campaign_id}: {ai_error}")
            return jsonify({
                'error': f'Lỗi phân tích AI: {str(ai_error)}'
            }), 500
        
    except Exception as e:
        logger.error(f"Lỗi /api/campaign-ai-insights: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/meta-report-insights')
def api_meta_report_insights():
    """
    Meta Report Insights API - Tracking performance monthly
    Dimensions: Brand, Content Format, Time
    """
    try:
        date_preset = request.args.get('date_preset', 'last_30d').strip()
        since = (request.args.get('since') or '').strip()
        until = (request.args.get('until') or '').strip()
        filter_brand = (request.args.get('brand') or '').strip()
        filter_campaign_id = (request.args.get('campaign_id') or '').strip()
        token = get_access_token()
        
        if not token:
            return jsonify({'error': 'Missing access token'}), 500
        
        # Get all campaigns from ads_data.json
        ads_data = load_ads_data()
        if ads_data.get('error'):
            return jsonify({'error': ads_data['error']}), 500
        
        campaigns = ads_data.get('campaigns', [])
        if not campaigns:
            return jsonify({'error': 'No campaigns found', 'monthly_data': [], 'brand_analysis': {}, 'content_analysis': {}})
        
        # Apply brand and campaign filters if provided
        def _extract_brand(name: str) -> str:
            try:
                return extract_brand_from_campaign_name(name or '')
            except Exception:
                return 'Unknown'
        if filter_brand and filter_brand != 'all':
            campaigns = [c for c in campaigns if _extract_brand(c.get('campaign_name', '')) == filter_brand]
        if filter_campaign_id and filter_campaign_id != 'all':
            campaigns = [c for c in campaigns if c.get('campaign_id') == filter_campaign_id]
        
        base_url = 'https://graph.facebook.com/v23.0'
        
        # Initialize analysis data structures
        monthly_data = []
        brand_analysis = {}
        content_analysis = {}
        
        # Process campaigns for monthly insights
        successful_campaigns = 0
        failed_campaigns = 0
        max_campaigns = 15  # Limit to prevent timeout
        
        logger.info(f"Processing {min(len(campaigns), max_campaigns)} campaigns for Meta Report Insights")
        
        for campaign in campaigns[:max_campaigns]:
            campaign_id = campaign.get('campaign_id')
            if not campaign_id:
                continue
                
            try:
                # Get insights data for the campaign
                url = f"{base_url}/{campaign_id}/insights"
                params = {
                    'access_token': token,
                    'fields': 'impressions,clicks,spend,ctr,cpc,cpm,reach,actions,inline_link_clicks,video_play_actions',
                    'date_preset': date_preset,
                    'time_increment': 1
                }
                # Custom date range support if provided
                if since and until:
                    params['date_preset'] = 'custom'
                    params['since'] = since
                    params['until'] = until
                
                response = requests.get(url, params=params, timeout=10)
                logger.info(f"Campaign {campaign_id}: Status {response.status_code}")
                if response.status_code != 200:
                    logger.error(f"Campaign {campaign_id} error: {response.text}")
                if response.status_code == 200:
                    data = response.json()
                    daily_rows = data.get('data', [])
                    logger.info(f"Campaign {campaign_id}: Got {len(daily_rows)} daily rows")
                    
                    if daily_rows:
                        # Process daily data for monthly aggregation
                        for row in daily_rows:
                            date_key = row.get('date_start') or row.get('date') or row.get('date_stop') or 'unknown'
                            month_key = date_key[:7]  # YYYY-MM format
                            
                            # Find existing month data or create new
                            month_data = next((m for m in monthly_data if m['month'] == month_key), None)
                            if not month_data:
                                month_data = {
                                    'month': month_key,
                                    'campaigns': set(),
                                    'brands': set(),
                                    'content_formats': set(),
                                    'impressions': 0,
                                    'clicks': 0,
                                    'spend': 0.0,
                                    'reach': 0,
                                    'engagement': 0,
                                    'video_views': 0,
                                    'photo_views': 0,
                                    'link_clicks': 0
                                }
                                monthly_data.append(month_data)
                            if month_data:
                                # Extract brand from campaign name (simplified)
                                campaign_name = campaign.get('campaign_name', '')
                                brand = extract_brand_from_campaign_name(campaign_name)
                                content_format = extract_content_format_from_campaign_name(campaign_name)
                                
                                # Add to sets
                                month_data['campaigns'].add(campaign_id)
                                month_data['brands'].add(brand)
                                month_data['content_formats'].add(content_format)
                                
                                # Aggregate metrics
                                month_data['impressions'] += int(float(row.get('impressions', 0) or 0))
                                month_data['clicks'] += int(float(row.get('clicks', 0) or 0))
                                month_data['spend'] += float(row.get('spend', 0) or 0)
                                month_data['reach'] += int(float(row.get('reach', 0) or 0))
                                month_data['link_clicks'] += int(float(row.get('inline_link_clicks', 0) or 0))
                                
                                # Process actions for engagement metrics
                                for action in (row.get('actions') or []):
                                    action_type = (action.get('action_type') or '').lower()
                                    try:
                                        value = int(float(action.get('value', 0) or 0))
                                    except Exception:
                                        value = 0
                                    
                                    if action_type == 'post_engagement':
                                        month_data['engagement'] += value
                                    elif action_type == 'photo_view':
                                        month_data['photo_views'] += value
                                
                                # Process video actions
                                for video_action in (row.get('video_play_actions') or []):
                                    try:
                                        month_data['video_views'] += int(float(video_action.get('value', 0) or 0))
                                    except Exception:
                                        continue
                                
                                # Update brand analysis
                                if brand not in brand_analysis:
                                    brand_analysis[brand] = {
                                        'campaigns': set(),
                                        'total_impressions': 0,
                                        'total_clicks': 0,
                                        'total_spend': 0.0,
                                        'total_engagement': 0,
                                        'content_formats': set()
                                    }
                                
                                brand_analysis[brand]['campaigns'].add(campaign_id)
                                brand_analysis[brand]['total_impressions'] += int(float(row.get('impressions', 0) or 0))
                                brand_analysis[brand]['total_clicks'] += int(float(row.get('clicks', 0) or 0))
                                brand_analysis[brand]['total_spend'] += float(row.get('spend', 0) or 0)
                                brand_analysis[brand]['content_formats'].add(content_format)
                                
                                # Process engagement for brand analysis
                                for action in (row.get('actions') or []):
                                    action_type = (action.get('action_type') or '').lower()
                                    try:
                                        value = int(float(action.get('value', 0) or 0))
                                    except Exception:
                                        value = 0
                                    
                                    if action_type == 'post_engagement':
                                        brand_analysis[brand]['total_engagement'] += value
                                
                                # Update content format analysis
                                if content_format not in content_analysis:
                                    content_analysis[content_format] = {
                                        'campaigns': set(),
                                        'brands': set(),
                                        'total_impressions': 0,
                                        'total_clicks': 0,
                                        'total_spend': 0.0,
                                        'total_engagement': 0,
                                        'performance_score': 0.0
                                    }
                                
                                content_analysis[content_format]['campaigns'].add(campaign_id)
                                content_analysis[content_format]['brands'].add(brand)
                                content_analysis[content_format]['total_impressions'] += int(float(row.get('impressions', 0) or 0))
                                content_analysis[content_format]['total_clicks'] += int(float(row.get('clicks', 0) or 0))
                                content_analysis[content_format]['total_spend'] += float(row.get('spend', 0) or 0)
                                
                                # Process engagement for content analysis
                                for action in (row.get('actions') or []):
                                    action_type = (action.get('action_type') or '').lower()
                                    try:
                                        value = int(float(action.get('value', 0) or 0))
                                    except Exception:
                                        value = 0
                                    
                                    if action_type == 'post_engagement':
                                        content_analysis[content_format]['total_engagement'] += value
                        
                        successful_campaigns += 1
                    else:
                        failed_campaigns += 1
                else:
                    failed_campaigns += 1
                    logger.warning(f"Failed to get insights for campaign {campaign_id}: {response.status_code}")
                    
            except Exception as e:
                failed_campaigns += 1
                logger.warning(f"Error fetching insights for campaign {campaign_id}: {e}")
                continue
        
        # Convert sets to counts and calculate derived metrics
        for month_data in monthly_data:
            month_data['campaign_count'] = len(month_data['campaigns'])
            month_data['brand_count'] = len(month_data['brands'])
            month_data['content_format_count'] = len(month_data['content_formats'])
            month_data['ctr'] = (month_data['clicks'] / max(month_data['impressions'], 1)) * 100
            month_data['cpc'] = month_data['spend'] / max(month_data['clicks'], 1) if month_data['clicks'] > 0 else 0
            month_data['cpm'] = (month_data['spend'] / max(month_data['impressions'], 1)) * 1000 if month_data['impressions'] > 0 else 0
            month_data['engagement_rate'] = (month_data['engagement'] / max(month_data['impressions'], 1)) * 100 if month_data['impressions'] > 0 else 0
            
            # Convert sets to lists for JSON serialization
            month_data['campaigns'] = list(month_data['campaigns'])
            month_data['brands'] = list(month_data['brands'])
            month_data['content_formats'] = list(month_data['content_formats'])
        
        # Process brand analysis
        for brand, data in brand_analysis.items():
            data['campaign_count'] = len(data['campaigns'])
            data['content_format_count'] = len(data['content_formats'])
            data['ctr'] = (data['total_clicks'] / max(data['total_impressions'], 1)) * 100
            data['cpc'] = data['total_spend'] / max(data['total_clicks'], 1) if data['total_clicks'] > 0 else 0
            data['cpm'] = (data['total_spend'] / max(data['total_impressions'], 1)) * 1000 if data['total_impressions'] > 0 else 0
            data['engagement_rate'] = (data['total_engagement'] / max(data['total_impressions'], 1)) * 100 if data['total_impressions'] > 0 else 0
            
            # Convert sets to lists
            data['campaigns'] = list(data['campaigns'])
            data['content_formats'] = list(data['content_formats'])
        
        # Process content format analysis
        for content_format, data in content_analysis.items():
            data['campaign_count'] = len(data['campaigns'])
            data['brand_count'] = len(data['brands'])
            data['ctr'] = (data['total_clicks'] / max(data['total_impressions'], 1)) * 100
            data['cpc'] = data['total_spend'] / max(data['total_clicks'], 1) if data['total_clicks'] > 0 else 0
            data['cpm'] = (data['total_spend'] / max(data['total_impressions'], 1)) * 1000 if data['total_impressions'] > 0 else 0
            data['engagement_rate'] = (data['total_engagement'] / max(data['total_impressions'], 1)) * 100 if data['total_impressions'] > 0 else 0
            
            # Calculate performance score (CTR + Engagement Rate - CPC/1000)
            data['performance_score'] = data['ctr'] + data['engagement_rate'] - (data['cpc'] / 1000)
            
            # Convert sets to lists
            data['campaigns'] = list(data['campaigns'])
            data['brands'] = list(data['brands'])
        
        # Sort monthly data by month
        monthly_data.sort(key=lambda x: x['month'])
        
        # Sort brand analysis by total spend
        sorted_brand_analysis = dict(sorted(brand_analysis.items(), key=lambda x: x[1]['total_spend'], reverse=True))
        
        # Sort content analysis by performance score
        sorted_content_analysis = dict(sorted(content_analysis.items(), key=lambda x: x[1]['performance_score'], reverse=True))
        
        logger.info(f"Meta Report Insights: {successful_campaigns} successful, {failed_campaigns} failed campaigns")
        
        return jsonify({
            'monthly_data': monthly_data,
            'brand_analysis': sorted_brand_analysis,
            'content_analysis': sorted_content_analysis,
            'date_preset': date_preset,
            'extraction_date': datetime.now().isoformat(),
            'successful_campaigns': successful_campaigns,
            'failed_campaigns': failed_campaigns,
            'total_campaigns': len(campaigns),
            'processed_campaigns': min(len(campaigns), max_campaigns)
        })
        
    except Exception as e:
        logger.error(f"Lỗi /api/meta-report-insights: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/meta-report-content-insights')
def api_meta_report_content_insights():
    """Lấy danh sách bài viết Facebook của 1 page và tạo AI insights cho Meta Report."""
    try:
        # Always use fixed PAGE ID from environment
        page_id = (os.getenv('FB_PAGE_ID') or os.getenv('PAGE_ID') or '').strip()
        limit = int(request.args.get('limit', '50'))
        since = request.args.get('since', '').strip()
        until = request.args.get('until', '').strip()
        if not page_id:
            return jsonify({'error': 'page_id is required', 'posts': []}), 400

        # Use tokens from .env as requested: prefer FACEBOOK_ACCESS_TOKEN, then USER_TOKEN
        token = os.getenv('FACEBOOK_ACCESS_TOKEN') or os.getenv('USER_TOKEN') or get_access_token()
        if not token:
            return jsonify({'error': 'Missing access token', 'posts': []}), 500

        base_url = 'https://graph.facebook.com/v23.0'
        url = f"{base_url}/{page_id}/posts"
        params = {
            'access_token': token,
            'fields': 'id,message,created_time,permalink_url',
            'limit': max(5, min(50, limit))
        }
        if since and until:
            params['since'] = since
            params['until'] = until

        res = requests.get(url, params=params, timeout=20)
        if res.status_code != 200:
            try:
                err = res.json()
            except Exception:
                err = {'message': res.text}
            logger.warning(f"Fetch posts failed {res.status_code}: {err}")
            return jsonify({'error': err, 'posts': []}), 502

        posts = res.json().get('data', [])

        # Enrich posts with engagement metrics (shares, comments, reactions)
        detail_fields = 'shares,comments.summary(true),reactions.summary(true)'
        detailed_posts = []
        for p in posts[:max(5, min(50, limit))]:
            try:
                pid = p.get('id')
                if not pid:
                    continue
                dres = requests.get(
                    f"{base_url}/{pid}",
                    params={'access_token': token, 'fields': detail_fields},
                    timeout=15
                )
                shares_count = 0
                comments_count = 0
                reactions_count = 0
                if dres.status_code == 200:
                    d = dres.json()
                    shares_count = int(d.get('shares', {}).get('count', 0) or 0)
                    comments_count = int((d.get('comments', {}) or {}).get('summary', {}).get('total_count', 0) or 0)
                    reactions_count = int((d.get('reactions', {}) or {}).get('summary', {}).get('total_count', 0) or 0)
                p['shares_count'] = shares_count
                p['comments_count'] = comments_count
                p['reactions_count'] = reactions_count
                detailed_posts.append(p)
            except Exception:
                detailed_posts.append(p)
        posts = detailed_posts
        chatbot = OpenAIChatbot()
        # Enrich AI prompt with time window context
        if since and until:
            for p in posts:
                # no-op, we already filtered via API; just pass through
                pass
        ai = chatbot.analyze_posts_content(posts if isinstance(posts, list) else [])

        return jsonify({
            'page_id': page_id,
            'count': len(posts),
            'since': since or None,
            'until': until or None,
            'posts': posts,
            'ai': ai,
            'extraction_date': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Lỗi /api/meta-report-content-insights: {e}")
        return jsonify({'error': str(e), 'posts': []}), 500

def extract_brand_from_campaign_name(campaign_name):
    """Extract brand name from campaign name"""
    if not campaign_name:
        return 'Unknown'
    
    # Simple brand extraction logic - can be enhanced
    name_lower = campaign_name.lower()
    
    # Constrain to 3 brands only
    if 'ls2' in name_lower:
        return 'LS2'
    elif 'bulldog' in name_lower:
        return 'Bulldog'
    elif 'ego' in name_lower:
        return 'EGO'
    else:
        return 'Unknown'

def extract_content_format_from_campaign_name(campaign_name):
    """Extract content format from campaign name"""
    if not campaign_name:
        return 'Unknown'
    
    name_lower = campaign_name.lower()
    
    # Content format patterns
    if 'video' in name_lower or 'reel' in name_lower:
        return 'Video'
    elif 'image' in name_lower or 'photo' in name_lower or 'picture' in name_lower:
        return 'Image'
    elif 'carousel' in name_lower:
        return 'Carousel'
    elif 'story' in name_lower:
        return 'Story'
    elif 'post' in name_lower:
        return 'Post'
    elif 'ad' in name_lower:
        return 'Ad'
    else:
        return 'Mixed'

@app.route('/api/agency-report')
def api_agency_report():
    """Agency monthly performance report for page/agent funnel with MoM change."""
    try:
        # Get time filter parameters
        month_filter = (request.args.get('month') or '').strip()
        date_preset = request.args.get('date_preset', 'last_90d')
        since_date = request.args.get('since', '').strip()
        until_date = request.args.get('until', '').strip()
        
        token = get_access_token()
        if not token:
            return jsonify({'error': 'Missing access token'}), 500

        ads_data = load_ads_data()
        if ads_data.get('error'):
            return jsonify({'error': ads_data['error']}), 500
        campaigns = ads_data.get('campaigns', [])
        if not campaigns:
            return jsonify({'error': 'No campaigns found', 'months': {}, 'funnel': {}, 'groups': {}})

        base_url = 'https://graph.facebook.com/v23.0'

        # Aggregate by YYYY-MM across campaigns
        months = {}

        def ensure_month(mkey: str) -> dict:
            return months.setdefault(mkey, {
                'impressions': 0,
                'reach': 0,
                'clicks': 0,
                'spend': 0.0,
                'engagement': 0,
                'link_clicks': 0,
                'messaging_starts': 0,
                'purchases': 0,
                'purchase_value': 0.0,
            })

        # Limit to avoid timeout
        max_campaigns = 15
        for campaign in campaigns[:max_campaigns]:
            cid = campaign.get('campaign_id')
            if not cid:
                continue
            try:
                url = f"{base_url}/{cid}/insights"
                params = {
                    'access_token': token,
                    'fields': 'impressions,clicks,spend,ctr,cpc,cpm,reach,actions,conversion_values,inline_link_clicks,video_play_actions,video_3_sec_watched_actions,video_10_sec_watched_actions',
                    'time_increment': 1
                }
                
                # Set date range based on parameters
                if since_date and until_date:
                    params['time_range'] = f"{{\"since\":\"{since_date}\",\"until\":\"{until_date}\"}}"
                else:
                    params['date_preset'] = date_preset
                res = requests.get(url, params=params, timeout=25)
                # Fallbacks on failure/empty
                if res.status_code != 200 or not (res.json().get('data') if res.headers.get('content-type','').startswith('application/json') else []):
                    # Try different date presets as fallback
                    fallback_presets = ['last_180d', 'last_30d', 'lifetime']
                    for fb in fallback_presets:
                        p2 = params.copy()
                        if 'time_range' in p2:
                            del p2['time_range']
                        p2['date_preset'] = fb
                        try:
                            r2 = requests.get(url, params=p2, timeout=25)
                            if r2.status_code == 200 and (r2.json().get('data') or []):
                                res = r2
                                break
                        except Exception:
                            continue
                    if res.status_code != 200:
                        continue
                for row in res.json().get('data', []):
                    date_key = row.get('date_start') or row.get('date') or row.get('date_stop') or ''
                    if not date_key:
                        continue
                    mkey = date_key[:7]
                    g = ensure_month(mkey)
                    g['impressions'] += int(float(row.get('impressions', 0) or 0))
                    g['reach'] += int(float(row.get('reach', 0) or 0))
                    g['clicks'] += int(float(row.get('clicks', 0) or 0))
                    g['spend'] += float(row.get('spend', 0) or 0)
                    g['link_clicks'] += int(float(row.get('inline_link_clicks', 0) or 0))

                    for a in (row.get('actions') or []):
                        at = (a.get('action_type') or '').lower()
                        try:
                            val = int(float(a.get('value', 0) or 0))
                        except Exception:
                            val = 0
                        if at == 'post_engagement':
                            g['engagement'] += val
                        elif at in ['link_click', 'landing_page_view']:
                            g['link_clicks'] += val
                        elif (at.startswith('onsite_conversion.messaging') or
                              at in ['messaging_conversation_started', 'onsite_conversion.messaging_conversation_started', 'new_messaging_connection'] or
                              ('messaging' in at and ('conversation' in at or 'first_reply' in at))):
                            g['messaging_starts'] += val
                        elif at == 'purchase' or 'purchase' in at:
                            g['purchases'] += val

                    for cv in (row.get('conversion_values') or []):
                        cvt = (cv.get('action_type') or '').lower()
                        try:
                            v = float(cv.get('value', 0) or 0)
                        except Exception:
                            v = 0.0
                        if cvt == 'purchase' or 'purchase' in cvt:
                            g['purchase_value'] += v
                        elif (cvt.startswith('onsite_conversion.messaging') or
                              cvt in ['messaging_conversation_started', 'onsite_conversion.messaging_conversation_started']):
                            g['messaging_starts'] += int(v)

            except Exception:
                continue

        if not months:
            # Fallback: aggregate from daily-tracking endpoint which already consolidates metrics
            try:
                from flask import current_app
                # Build fallback URL with same time filters
                fallback_url = '/api/daily-tracking?'
                if since_date and until_date:
                    fallback_url += f'since={since_date}&until={until_date}'
                else:
                    fallback_url += f'date_preset={date_preset}'
                
                with current_app.test_request_context(fallback_url):
                    resp = api_daily_tracking()
                    payload = resp[0].get_json() if isinstance(resp, tuple) else resp.get_json()
                    daily = payload.get('daily', [])
                    for r in daily:
                        mkey = (r.get('date_start') or '')[:7]
                        if not mkey:
                            continue
                        g = ensure_month(mkey)
                        g['impressions'] += int(float(r.get('impressions',0) or 0))
                        g['reach'] += int(float(r.get('reach',0) or 0))
                        g['clicks'] += int(float(r.get('clicks',0) or 0))
                        g['spend'] += float(r.get('spend',0) or 0)
                        g['engagement'] += int(float(r.get('post_engagement',0) or 0))
                        g['link_clicks'] += int(float(r.get('inline_link_clicks',0) or 0))
                        g['messaging_starts'] += int(float(r.get('messaging_starts',0) or 0))
                        g['purchases'] += int(float(r.get('purchases',0) or 0))
                        g['purchase_value'] += float(r.get('purchase_value',0) or 0)
            except Exception:
                pass

        # Determine latest month and previous month
        sorted_months = sorted(months.keys())
        
        # Find the latest month with actual data (non-zero spend)
        latest = month_filter if month_filter in months else None
        if not latest:
            # Find the most recent month with data
            for month in reversed(sorted_months):
                if months[month].get('spend', 0) > 0 or months[month].get('impressions', 0) > 0:
                    latest = month
                    break
            # If no month with data found, use the latest month
            if not latest and sorted_months:
                latest = sorted_months[-1]
        
        prev = None
        if latest and latest in sorted_months:
            idx = sorted_months.index(latest)
            if idx > 0:
                prev = sorted_months[idx-1]

        def pct_delta(curr: float, past: float) -> float:
            if past == 0:
                return 0.0 if curr == 0 else 100.0
            return ((curr - past) / abs(past)) * 100.0

        cur = months.get(latest, {}) if latest else {}
        prv = months.get(prev, {}) if prev else {}

        # Derived metrics
        cur_ctr = (cur.get('clicks', 0) / max(cur.get('impressions', 1), 1)) * 100.0 if cur else 0.0
        prv_ctr = (prv.get('clicks', 0) / max(prv.get('impressions', 1), 1)) * 100.0 if prv else 0.0

        funnel = [
            {'key': 'impressions', 'title': 'Lượt hiển thị', 'label': 'Hiển thị', 'total': int(cur.get('impressions', 0)), 'delta_pct': pct_delta(cur.get('impressions', 0), prv.get('impressions', 0))},
            {'key': 'reach', 'title': 'Lượt tiếp cận', 'label': 'Tiếp cận', 'total': int(cur.get('reach', 0)), 'delta_pct': pct_delta(cur.get('reach', 0), prv.get('reach', 0))},
            {'key': 'engagement', 'title': 'Lượt tương tác', 'label': 'Tương tác', 'total': int(cur.get('engagement', 0)), 'delta_pct': pct_delta(cur.get('engagement', 0), prv.get('engagement', 0))},
            {'key': 'link_clicks', 'title': 'Lượt click vào liên kết', 'label': 'Clicks', 'total': int(cur.get('link_clicks', 0)), 'delta_pct': pct_delta(cur.get('link_clicks', 0), prv.get('link_clicks', 0))},
            {'key': 'messaging_starts', 'title': 'Bắt đầu trò chuyện', 'label': 'Quan tâm', 'total': int(cur.get('messaging_starts', 0)), 'delta_pct': pct_delta(cur.get('messaging_starts', 0), prv.get('messaging_starts', 0))},
            {'key': 'purchases', 'title': 'Lượt mua trên Meta', 'label': 'Chuyển đổi', 'total': int(cur.get('purchases', 0)), 'delta_pct': pct_delta(cur.get('purchases', 0), prv.get('purchases', 0))},
        ]

        groups = {
            'display': [
                {'key': 'impressions', 'title': 'Lượt hiển thị', 'total': int(cur.get('impressions', 0)), 'delta_pct': pct_delta(cur.get('impressions', 0), prv.get('impressions', 0))},
                {'key': 'reach', 'title': 'Lượt tiếp cận', 'total': int(cur.get('reach', 0)), 'delta_pct': pct_delta(cur.get('reach', 0), prv.get('reach', 0))},
                {'key': 'ctr', 'title': '%CTR (tất cả)', 'total': round(cur_ctr, 2), 'delta_pct': round(pct_delta(cur_ctr, prv_ctr), 2)}
            ],
            'engagement': [
                {'key': 'engagement', 'title': 'Lượt tương tác', 'total': int(cur.get('engagement', 0)), 'delta_pct': pct_delta(cur.get('engagement', 0), prv.get('engagement', 0))},
                {'key': 'link_clicks', 'title': 'Lượt click vào liên kết', 'total': int(cur.get('link_clicks', 0)), 'delta_pct': pct_delta(cur.get('link_clicks', 0), prv.get('link_clicks', 0))}
            ],
            'conversion': [
                {'key': 'messaging_starts', 'title': 'Bắt đầu trò chuyện qua tin nhắn', 'total': int(cur.get('messaging_starts', 0)), 'delta_pct': pct_delta(cur.get('messaging_starts', 0), prv.get('messaging_starts', 0))},
                {'key': 'purchases', 'title': 'Lượt mua trên meta', 'total': int(cur.get('purchases', 0)), 'delta_pct': pct_delta(cur.get('purchases', 0), prv.get('purchases', 0))},
                {'key': 'purchase_value', 'title': 'Giá trị chuyển đổi từ lượt mua', 'total': round(cur.get('purchase_value', 0.0), 2), 'delta_pct': round(pct_delta(cur.get('purchase_value', 0.0), prv.get('purchase_value', 0.0)), 2)}
            ]
        }

        return jsonify({
            'months': months,
            'latest_month': latest,
            'previous_month': prev,
            'funnel': funnel,
            'groups': groups,
            'spend': round(cur.get('spend', 0.0), 2),
            'purchase_value': round(cur.get('purchase_value', 0.0), 2),
            'extraction_date': datetime.now().isoformat(),
            'filters': {
                'date_preset': date_preset,
                'since_date': since_date,
                'until_date': until_date,
                'month_filter': month_filter
            },
            'total_months': len(months),
            'date_range': {
                'earliest': sorted_months[0] if sorted_months else None,
                'latest': sorted_months[-1] if sorted_months else None
            }
        })
    except Exception as e:
        logger.error(f"Lỗi /api/agency-report: {e}")
        # Do not hard fail; return an empty but valid payload for UI
        return jsonify({'error': str(e), 'months': {}, 'funnel': [], 'groups': {}}), 200

@app.route('/api/filter-options')
def api_filter_options():
    """API to get filter options for global filters"""
    try:
        ads_data = load_ads_data()
        if ads_data.get('error'):
            return jsonify({'error': ads_data['error']}), 500
        
        campaigns = ads_data.get('campaigns', [])
        if not campaigns:
            return jsonify({'brands': [], 'campaigns': [], 'adsets': [], 'ads': []})
        
        # Extract brands from campaign names
        brand_set = set()
        campaign_list = []
        adset_list = []
        ad_list = []
        
        for campaign in campaigns:
            # Extract brand
            brand = extract_brand_from_campaign_name(campaign.get('campaign_name', ''))
            if brand and brand != 'Unknown':
                brand_set.add(brand)
            
            # Add campaign
            campaign_list.append({
                'id': campaign.get('campaign_id'),
                'name': campaign.get('campaign_name', ''),
                'brand': brand,
                'status': campaign.get('status', ''),
                'objective': campaign.get('objective', '')
            })
            
            # For now, use campaigns as adsets and ads (in real implementation, fetch actual ad sets and ads)
            adset_list.append({
                'id': f"adset_{campaign.get('campaign_id')}",
                'name': f"Ad Set: {campaign.get('campaign_name', '')}",
                'campaign_id': campaign.get('campaign_id')
            })
            
            ad_list.append({
                'id': f"ad_{campaign.get('campaign_id')}",
                'name': f"Ad: {campaign.get('campaign_name', '')}",
                'campaign_id': campaign.get('campaign_id'),
                'adset_id': f"adset_{campaign.get('campaign_id')}"
            })
        
        return jsonify({
            'brands': sorted(list(brand_set)),
            'campaigns': campaign_list,
            'adsets': adset_list,
            'ads': ad_list,
            'total_campaigns': len(campaigns)
        })
        
    except Exception as e:
        logger.error(f"Lỗi /api/filter-options: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/filtered-data')
def api_filtered_data():
    """API to get filtered data based on global filter parameters"""
    try:
        # Get filter parameters
        date_preset = request.args.get('date_preset', 'last_30d')
        since = request.args.get('since')
        until = request.args.get('until')
        campaign_id = request.args.get('campaign_id')
        adset_id = request.args.get('adset_id')
        ad_id = request.args.get('ad_id')
        brand = request.args.get('brand')
        
        # Load base data
        ads_data = load_ads_data()
        if ads_data.get('error'):
            return jsonify({'error': ads_data['error']}), 500
        
        campaigns = ads_data.get('campaigns', [])
        
        # Apply filters
        filtered_campaigns = campaigns.copy()
        
        # Filter by brand
        if brand and brand != 'all':
            filtered_campaigns = [
                c for c in filtered_campaigns 
                if extract_brand_from_campaign_name(c.get('campaign_name', '')) == brand
            ]
        
        # Filter by specific campaign
        if campaign_id and campaign_id != 'all':
            filtered_campaigns = [
                c for c in filtered_campaigns 
                if c.get('campaign_id') == campaign_id
            ]
        
        # Prepare date parameters for API calls
        date_params = {'date_preset': date_preset}
        if since and until:
            date_params.update({
                'date_preset': 'custom',
                'since': since,
                'until': until
            })
        
        # Get insights for filtered campaigns
        token = get_access_token()
        if not token:
            return jsonify({'error': 'Missing access token'}), 500
        
        base_url = 'https://graph.facebook.com/v23.0'
        insights_data = []
        
        # Limit to avoid timeout
        max_campaigns = min(len(filtered_campaigns), 10)
        
        for campaign in filtered_campaigns[:max_campaigns]:
            campaign_id = campaign.get('campaign_id')
            if not campaign_id:
                continue
                
            try:
                url = f"{base_url}/{campaign_id}/insights"
                params = {
                    'access_token': token,
                    'fields': 'campaign_name,impressions,clicks,spend,ctr,cpc,cpm,reach,frequency,actions,conversion_values,inline_link_clicks',
                    'time_increment': 1,
                    **date_params
                }
                
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    daily_rows = data.get('data', [])
                    
                    for row in daily_rows:
                        row['campaign_id'] = campaign_id
                        row['campaign_name'] = campaign.get('campaign_name', '')
                        row['brand'] = extract_brand_from_campaign_name(campaign.get('campaign_name', ''))
                        insights_data.append(row)
                        
            except Exception as e:
                logger.warning(f"Error fetching insights for campaign {campaign_id}: {e}")
                continue
        
        # Aggregate data
        totals = {
            'impressions': sum(int(float(row.get('impressions', 0) or 0)) for row in insights_data),
            'clicks': sum(int(float(row.get('clicks', 0) or 0)) for row in insights_data),
            'spend': sum(float(row.get('spend', 0) or 0) for row in insights_data),
            'reach': sum(int(float(row.get('reach', 0) or 0)) for row in insights_data),
            'inline_link_clicks': sum(int(float(row.get('inline_link_clicks', 0) or 0)) for row in insights_data)
        }
        
        # Calculate derived metrics
        if totals['impressions'] > 0:
            totals['ctr'] = (totals['clicks'] / totals['impressions']) * 100
            totals['cpm'] = (totals['spend'] / totals['impressions']) * 1000
        else:
            totals['ctr'] = 0
            totals['cpm'] = 0
            
        if totals['clicks'] > 0:
            totals['cpc'] = totals['spend'] / totals['clicks']
        else:
            totals['cpc'] = 0
        
        if totals['reach'] > 0:
            totals['frequency'] = totals['impressions'] / totals['reach']
        else:
            totals['frequency'] = 0
        
        return jsonify({
            'totals': totals,
            'daily_data': insights_data,
            'filtered_campaigns': len(filtered_campaigns),
            'total_campaigns': len(campaigns),
            'date_params': date_params,
            'extraction_date': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Lỗi /api/filtered-data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/page-insights', methods=['GET'])
def get_page_insights():
    """Lấy dữ liệu page insights từ Facebook Graph API với bộ lọc thời gian."""
    try:
        page_id = (os.getenv('FB_PAGE_ID') or os.getenv('PAGE_ID') or '').strip()
        access_token = get_access_token()
        
        if not page_id or not access_token:
            return jsonify({'error': 'PAGE_ID hoặc ACCESS_TOKEN chưa được cấu hình'}), 400
        
        # Lấy tham số từ request
        since = request.args.get('since', '').strip()
        until = request.args.get('until', '').strip()
        post_type = request.args.get('post_type', 'all').strip()
        
        # Nếu không có thời gian, lấy 30 ngày gần nhất
        if not since or not until:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            since = start_date.strftime('%Y-%m-%d')
            until = end_date.strftime('%Y-%m-%d')
        
        base_url = "https://graph.facebook.com/v23.0"
        
        # Lấy page info
        page_url = f"{base_url}/{page_id}"
        page_params = {
            'access_token': access_token,
            'fields': 'name,fan_count,new_like_count'
        }
        page_response = requests.get(page_url, params=page_params)
        
        if page_response.status_code != 200:
            return jsonify({'error': f'Không thể lấy thông tin page: {page_response.text}'}), 400
        
        page_data = page_response.json()
        
        # Lấy page insights với metrics cơ bản và hợp lệ
        insights_data = {'data': []}
        
        # Thử các metrics cơ bản trước
        basic_metrics = ['page_impressions', 'page_post_engagements', 'page_video_views']
        
        for metric in basic_metrics:
            try:
                insights_url = f"{base_url}/{page_id}/insights"
                insights_params = {
                    'access_token': access_token,
                    'metric': metric,
                    'period': 'day',
                    'since': since,
                    'until': until
                }
                insights_response = requests.get(insights_url, params=insights_params)
                
                if insights_response.status_code == 200:
                    metric_data = insights_response.json()
                    if 'data' in metric_data and metric_data['data']:
                        insights_data['data'].extend(metric_data['data'])
                else:
                    logger.warning(f"Không thể lấy metric {metric}: {insights_response.text}")
            except Exception as e:
                logger.warning(f"Lỗi khi lấy metric {metric}: {str(e)}")
        
        logger.info(f"Đã lấy được {len(insights_data['data'])} metrics")
        
        # Lấy page posts với Page Access Token - sử dụng endpoint feed
        posts_url = f"{base_url}/{page_id}/feed"
        posts_params = {
            'access_token': access_token,
            'limit': 20  # Giảm số lượng posts để tránh timeout
        }
        posts_response = requests.get(posts_url, params=posts_params)
        
        # Xử lý lỗi posts một cách graceful
        posts_data = {'data': []}
        if posts_response.status_code == 200:
            posts_data = posts_response.json()
            logger.info(f"Đã lấy được {len(posts_data.get('data', []))} posts")
        else:
            logger.warning(f"Không thể lấy posts: {posts_response.text}")
            # Không tạo dữ liệu mẫu, để posts_data rỗng
        
        # Xử lý dữ liệu insights
        processed_insights = {}
        daily_data = []
        
        for insight in insights_data.get('data', []):
            metric_name = insight.get('name')
            values = insight.get('values', [])
            
            processed_insights[metric_name] = values
            
            # Tạo dữ liệu theo ngày
            for value in values:
                date_str = value.get('end_time', '').split('T')[0]
                metric_value = value.get('value', 0)
                
                # Tìm hoặc tạo entry cho ngày này
                day_entry = next((d for d in daily_data if d['date'] == date_str), None)
                if not day_entry:
                    day_entry = {'date': date_str}
                    daily_data.append(day_entry)
                
                day_entry[metric_name] = metric_value
        
        # Xử lý posts data
        processed_posts = []
        content_types = {}
        
        for post in posts_data.get('data', []):
            # Xác định post type từ dữ liệu có sẵn
            post_type_current = 'status'  # default
            if 'attachments' in post:
                attachments = post.get('attachments', {}).get('data', [])
                if attachments:
                    attachment = attachments[0]
                    if 'media' in attachment:
                        media = attachment['media']
                        if 'image' in media:
                            post_type_current = 'photo'
                        elif 'video' in media:
                            post_type_current = 'video'
                    elif 'type' in attachment:
                        if attachment['type'] == 'share':
                            post_type_current = 'link'
            
            # Lọc theo post type nếu được chỉ định
            if post_type != 'all' and post_type != post_type_current:
                continue
            
            # Lọc theo ngày tháng
            created_time = post.get('created_time', '')
            if created_time:
                try:
                    post_date = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
                    since_date_obj = datetime.fromisoformat(since)
                    until_date_obj = datetime.fromisoformat(until)
                    
                    if post_date.date() < since_date_obj.date() or post_date.date() > until_date_obj.date():
                        continue
                except:
                    pass  # Nếu không parse được date thì bỏ qua filter
            
            # Đếm content types
            content_types[post_type_current] = content_types.get(post_type_current, 0) + 1
            
            # Lấy insights và thông tin chi tiết cho mỗi post
            post_id = post.get('id')
            post_metrics = {
                'post_impressions': 0,
                'post_engaged_users': 0,  # Sẽ tính từ reactions
                'post_clicks': 0,
                'post_reactions_by_type_total': 0
            }
            
            # Lấy thông tin chi tiết của post (attachments, likes, comments)
            post_details = {
                'likes_count': 0,
                'comments_count': 0,
                'attachments': [],
                'thumbnail_url': None
            }
            
            try:
                # Lấy insights cho post này
                post_insights_url = f"{base_url}/{post_id}/insights"
                post_insights_params = {
                    'access_token': access_token,
                    'metric': 'post_impressions,post_clicks,post_reactions_by_type_total'
                }
                post_insights_response = requests.get(post_insights_url, params=post_insights_params)
                
                if post_insights_response.status_code == 200:
                    insights_data = post_insights_response.json()
                    for insight in insights_data.get('data', []):
                        metric_name = insight.get('name')
                        metric_value = insight.get('values', [{}])[0].get('value', 0)
                        
                        if metric_name == 'post_reactions_by_type_total':
                            # Tính tổng reactions
                            if isinstance(metric_value, dict):
                                total_reactions = sum(metric_value.values())
                                post_metrics['post_reactions_by_type_total'] = total_reactions
                                # Sử dụng reactions làm engagement
                                post_metrics['post_engaged_users'] = total_reactions
                            else:
                                post_metrics[metric_name] = metric_value
                        else:
                            post_metrics[metric_name] = metric_value
                else:
                    logger.warning(f"Không thể lấy insights cho post {post_id}: {post_insights_response.text}")
            except Exception as e:
                logger.warning(f"Lỗi khi lấy insights cho post {post_id}: {str(e)}")
            
            # Lấy thông tin chi tiết của post
            try:
                post_details_url = f"{base_url}/{post_id}"
                post_details_params = {
                    'access_token': access_token,
                    'fields': 'likes.summary(true),comments,attachments'
                }
                post_details_response = requests.get(post_details_url, params=post_details_params)
                
                if post_details_response.status_code == 200:
                    details_data = post_details_response.json()
                    
                    # Lấy likes count
                    post_details['likes_count'] = details_data.get('likes', {}).get('summary', {}).get('total_count', 0)
                    
                    # Lấy comments count
                    comments = details_data.get('comments', {}).get('data', [])
                    post_details['comments_count'] = len(comments)
                    
                    # Lấy attachments
                    attachments = details_data.get('attachments', {}).get('data', [])
                    for attachment in attachments:
                        attachment_info = {
                            'type': attachment.get('type', 'unknown'),
                            'media_url': None
                        }
                        
                        if 'media' in attachment:
                            media = attachment['media']
                            if 'image' in media:
                                attachment_info['media_url'] = media['image'].get('src')
                                if not post_details['thumbnail_url']:
                                    post_details['thumbnail_url'] = media['image'].get('src')
                            elif 'video' in media:
                                attachment_info['media_url'] = media['video'].get('src')
                                # Lấy thumbnail từ video
                                if not post_details['thumbnail_url'] and 'picture' in media['video']:
                                    post_details['thumbnail_url'] = media['video'].get('picture')
                        
                        post_details['attachments'].append(attachment_info)
                        
            except Exception as e:
                logger.warning(f"Lỗi khi lấy chi tiết post {post_id}: {str(e)}")
            
            # Tạo processed post với insights thực tế và thông tin chi tiết
            processed_post = {
                'id': post_id,
                'message': post.get('message', ''),
                'created_time': post.get('created_time'),
                'type': post_type_current,
                'permalink_url': f"https://facebook.com/{post_id}",
                'impressions': post_metrics['post_impressions'],
                'engagement': post_metrics['post_engaged_users'],
                'clicks': post_metrics['post_clicks'],
                'reactions': post_metrics['post_reactions_by_type_total'],
                'likes_count': post_details['likes_count'],
                'comments_count': post_details['comments_count'],
                'attachments': post_details['attachments'],
                'thumbnail_url': post_details['thumbnail_url']
            }
            
            processed_posts.append(processed_post)
        
        # Sắp xếp posts theo impressions
        processed_posts.sort(key=lambda x: x['impressions'], reverse=True)
        
        # Tính tổng các metrics từ insights thực tế
        total_impressions = 0
        total_engagements = 0
        total_video_views = 0
        
        for insight in insights_data.get('data', []):
            metric_name = insight.get('name')
            values = insight.get('values', [])
            
            for value in values:
                metric_value = value.get('value', 0)
                if metric_name == 'page_impressions':
                    total_impressions += metric_value
                elif metric_name == 'page_post_engagements':
                    total_engagements += metric_value
                elif metric_name == 'page_video_views':
                    total_video_views += metric_value
        
        # Tính tổng từ posts (nếu có)
        total_post_impressions = sum(post['impressions'] for post in processed_posts)
        total_post_engagements = sum(post['engagement'] for post in processed_posts)
        total_post_clicks = sum(post['clicks'] for post in processed_posts)
        total_post_reactions = sum(post['reactions'] for post in processed_posts)
        
        # Tạo response data
        response_data = {
            'page_info': {
                'name': page_data.get('name', 'Unknown Page'),
                'fan_count': page_data.get('fan_count', 0),
                'new_like_count': page_data.get('new_like_count', 0)
            },
            'date_range': {
                'since': since,
                'until': until
            },
            'summary_metrics': {
                'total_impressions': total_impressions,
                'total_engagements': total_engagements,
                'total_video_views': total_video_views,
                'total_posts': len(processed_posts),
                'total_post_impressions': total_post_impressions,
                'total_post_engagements': total_post_engagements,
                'total_post_clicks': total_post_clicks,
                'total_post_reactions': total_post_reactions
            },
            'daily_data': daily_data,
            'top_posts': processed_posts[:5],  # Top 5 posts
            'content_types': content_types,
            'filter_applied': {
                'post_type': post_type,
                'since': since,
                'until': until
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in get_page_insights: {str(e)}")
        return jsonify({'error': f'Lỗi khi lấy dữ liệu: {str(e)}'}), 500

@app.route('/api/page-posts-insights', methods=['GET'])
def get_page_posts_insights():
    """Lấy dữ liệu insights chi tiết của posts với bộ lọc."""
    try:
        page_id = (os.getenv('FB_PAGE_ID') or os.getenv('PAGE_ID') or '').strip()
        access_token = get_access_token()
        
        if not page_id or not access_token:
            return jsonify({'error': 'PAGE_ID hoặc ACCESS_TOKEN chưa được cấu hình'}), 400
        
        # Lấy tham số từ request
        since = request.args.get('since', '').strip()
        until = request.args.get('until', '').strip()
        post_type = request.args.get('post_type', 'all').strip()
        limit = int(request.args.get('limit', '50'))
        
        # Nếu không có thời gian, lấy 30 ngày gần nhất
        if not since or not until:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            since = start_date.strftime('%Y-%m-%d')
            until = end_date.strftime('%Y-%m-%d')
        
        base_url = "https://graph.facebook.com/v23.0"
        
        # Lấy page posts với insights chi tiết
        posts_url = f"{base_url}/{page_id}/posts"
        posts_params = {
            'access_token': access_token,
            'fields': 'id,message,created_time,type,permalink_url,insights.metric(post_impressions,post_engaged_users,post_clicks,post_reactions_by_type_total,post_comments,post_shares)',
            'since': since,
            'until': until,
            'limit': limit
        }
        posts_response = requests.get(posts_url, params=posts_params)
        
        # Xử lý lỗi posts một cách graceful
        posts_data = {'data': []}
        if posts_response.status_code == 200:
            posts_data = posts_response.json()
        else:
            logger.warning(f"Không thể lấy posts: {posts_response.text}")
            # Tiếp tục với dữ liệu rỗng thay vì fail
        
        # Xử lý posts data
        processed_posts = []
        content_types = {}
        total_metrics = {
            'impressions': 0,
            'engagement': 0,
            'clicks': 0,
            'reactions': 0,
            'comments': 0,
            'shares': 0
        }
        
        for post in posts_data.get('data', []):
            post_type_current = post.get('type', 'unknown')
            
            # Lọc theo post type nếu được chỉ định
            if post_type != 'all' and post_type != post_type_current:
                continue
            
            # Đếm content types
            content_types[post_type_current] = content_types.get(post_type_current, 0) + 1
            
            # Xử lý insights của post
            insights = post.get('insights', {}).get('data', [])
            post_metrics = {}
            
            for insight in insights:
                metric_name = insight.get('name')
                metric_value = insight.get('values', [{}])[0].get('value', 0)
                post_metrics[metric_name] = metric_value
            
            # Tính tổng các metrics
            impressions = post_metrics.get('post_impressions', 0)
            engagement = post_metrics.get('post_engaged_users', 0)
            clicks = post_metrics.get('post_clicks', 0)
            reactions = post_metrics.get('post_reactions_by_type_total', 0)
            comments = post_metrics.get('post_comments', 0)
            shares = post_metrics.get('post_shares', 0)
            
            total_metrics['impressions'] += impressions
            total_metrics['engagement'] += engagement
            total_metrics['clicks'] += clicks
            total_metrics['reactions'] += reactions
            total_metrics['comments'] += comments
            total_metrics['shares'] += shares
            
            processed_post = {
                'id': post.get('id'),
                'message': post.get('message', '')[:100] + '...' if len(post.get('message', '')) > 100 else post.get('message', ''),
                'full_message': post.get('message', ''),
                'created_time': post.get('created_time'),
                'type': post_type_current,
                'permalink_url': post.get('permalink_url'),
                'impressions': impressions,
                'engagement': engagement,
                'clicks': clicks,
                'reactions': reactions,
                'comments': comments,
                'shares': shares,
                'total_engagement': engagement + reactions + comments + shares
            }
            
            processed_posts.append(processed_post)
        
        # Sắp xếp posts theo các tiêu chí khác nhau
        top_by_impressions = sorted(processed_posts, key=lambda x: x['impressions'], reverse=True)[:5]
        top_by_likes = sorted(processed_posts, key=lambda x: x['reactions'], reverse=True)[:5]
        top_by_clicks = sorted(processed_posts, key=lambda x: x['clicks'], reverse=True)[:5]
        top_by_engagement = sorted(processed_posts, key=lambda x: x['total_engagement'], reverse=True)[:5]
        
        # Tạo response data
        response_data = {
            'date_range': {
                'since': since,
                'until': until
            },
            'filter_applied': {
                'post_type': post_type,
                'limit': limit
            },
            'summary_metrics': total_metrics,
            'content_types': content_types,
            'total_posts': len(processed_posts),
            'top_posts': {
                'by_impressions': top_by_impressions,
                'by_likes': top_by_likes,
                'by_clicks': top_by_clicks,
                'by_engagement': top_by_engagement
            },
            'all_posts': processed_posts
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error in get_page_posts_insights: {str(e)}")
        return jsonify({'error': f'Lỗi khi lấy dữ liệu posts: {str(e)}'}), 500

@app.route('/api/test', methods=['GET'])
def test_api():
    """Test API endpoint để kiểm tra server hoạt động."""
    return jsonify({
        'status': 'success',
        'message': 'API server is working',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/post-details/<post_id>', methods=['GET'])
def get_post_details(post_id):
    """Lấy thông tin chi tiết của một post bao gồm attachments và nội dung."""
    try:
        access_token = get_access_token()
        
        if not access_token:
            return jsonify({'error': 'ACCESS_TOKEN chưa được cấu hình'}), 400

        base_url = "https://graph.facebook.com/v23.0"
        
        # Lấy thông tin chi tiết của post
        post_url = f"{base_url}/{post_id}"
        post_params = {
            'access_token': access_token,
            'fields': 'id,message,created_time,attachments,comments,likes.summary(true)'
        }
        
        response = requests.get(post_url, params=post_params)
        
        if response.status_code != 200:
            return jsonify({'error': f'Không thể lấy thông tin post: {response.text}'}), 400
        
        post_data = response.json()
        
        return jsonify(post_data)
        
    except Exception as e:
        logger.error(f"Error in get_post_details: {str(e)}")
        return jsonify({'error': f'Lỗi: {str(e)}'}), 500

@app.route('/api/test-post-insights', methods=['GET'])
def test_post_insights():
    """Test endpoint để kiểm tra post insights."""
    try:
        page_id = (os.getenv('FB_PAGE_ID') or os.getenv('PAGE_ID') or '').strip()
        access_token = get_access_token()

        if not page_id or not access_token:
            return jsonify({'error': 'PAGE_ID hoặc ACCESS_TOKEN chưa được cấu hình'}), 400

        base_url = "https://graph.facebook.com/v23.0"
        
        # Lấy 1 post để test
        posts_url = f"{base_url}/{page_id}/feed"
        posts_params = {
            'access_token': access_token,
            'limit': 1
        }
        posts_response = requests.get(posts_url, params=posts_params)
        
        if posts_response.status_code != 200:
            return jsonify({'error': f'Không thể lấy posts: {posts_response.text}'}), 400
        
        posts_data = posts_response.json()
        posts = posts_data.get('data', [])
        
        if not posts:
            return jsonify({'error': 'Không có posts'}), 400
        
        post = posts[0]
        post_id = post['id']
        
        # Lấy insights cho post này
        insights_url = f"{base_url}/{post_id}/insights"
        insights_params = {
            'access_token': access_token,
            'metric': 'post_impressions,post_engaged_users,post_clicks,post_reactions_by_type_total'
        }
        insights_response = requests.get(insights_url, params=insights_params)
        
        if insights_response.status_code != 200:
            return jsonify({'error': f'Không thể lấy insights: {insights_response.text}'}), 400
        
        insights_data = insights_response.json()
        
        return jsonify({
            'post_id': post_id,
            'post_message': post.get('message', '')[:100],
            'post_created_time': post.get('created_time'),
            'insights': insights_data
        })
        
    except Exception as e:
        logger.error(f"Error in test_post_insights: {str(e)}")
        return jsonify({'error': f'Lỗi: {str(e)}'}), 500

@app.route('/api/page-insights-demo', methods=['GET'])
def get_page_insights_demo():
    """Demo API endpoint với dữ liệu mẫu để test frontend."""
    try:
        # Tạo dữ liệu mẫu
        demo_data = {
            'page_info': {
                'name': 'Demo Facebook Page',
                'fan_count': 1250,
                'new_like_count': 45
            },
            'date_range': {
                'since': '2024-09-01',
                'until': '2024-10-01'
            },
            'summary_metrics': {
                'total_impressions': 45678,
                'total_engagements': 2345,
                'total_video_views': 1234,
                'total_posts': 25
            },
            'daily_data': [
                {
                    'date': '2024-09-01',
                    'page_impressions': 1200,
                    'page_post_engagements': 150,
                    'page_video_views': 80,
                    'page_impressions_unique': 950
                },
                {
                    'date': '2024-09-02',
                    'page_impressions': 1350,
                    'page_post_engagements': 180,
                    'page_video_views': 120,
                    'page_impressions_unique': 1100
                },
                {
                    'date': '2024-09-03',
                    'page_impressions': 980,
                    'page_post_engagements': 120,
                    'page_video_views': 60,
                    'page_impressions_unique': 780
                }
            ],
            'top_posts': [
                {
                    'id': 'post_1',
                    'message': 'Bài viết demo với nội dung hay...',
                    'created_time': '2024-09-15T10:30:00+0000',
                    'type': 'photo',
                    'permalink_url': 'https://facebook.com/demo',
                    'impressions': 2500,
                    'engagement': 180,
                    'clicks': 45,
                    'reactions': 120
                },
                {
                    'id': 'post_2',
                    'message': 'Video demo về sản phẩm mới...',
                    'created_time': '2024-09-20T14:20:00+0000',
                    'type': 'video',
                    'permalink_url': 'https://facebook.com/demo2',
                    'impressions': 3200,
                    'engagement': 250,
                    'clicks': 80,
                    'reactions': 200
                }
            ],
            'content_types': {
                'photo': 15,
                'video': 8,
                'link': 2
            },
            'filter_applied': {
                'post_type': 'all',
                'since': '2024-09-01',
                'until': '2024-10-01'
            }
        }
        
        return jsonify(demo_data)
        
    except Exception as e:
        logger.error(f"Error in get_page_insights_demo: {str(e)}")
        return jsonify({'error': f'Lỗi khi tạo dữ liệu demo: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5002))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Khởi động Flask app trên port {port}")
    logger.info(f"Debug mode: {debug}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
