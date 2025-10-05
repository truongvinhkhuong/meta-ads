// JavaScript for Chatbot functionality

class ChatbotManager {
    constructor() {
        this.conversationHistory = [];
        this.isProcessing = false;
        this.initializeElements();
        this.bindEvents();
    }

    initializeElements() {
        this.toggleBtn = document.getElementById('chatbot-toggle');
        this.container = document.getElementById('chatbot-container');
        this.input = document.getElementById('chatbot-input');
        this.sendBtn = document.getElementById('chatbot-send');
        this.clearBtn = document.getElementById('chatbot-clear');
        this.expandBtn = document.getElementById('chatbot-expand');
        this.messagesContainer = document.getElementById('chatbot-messages');
        this.typingIndicator = null;
    }

    bindEvents() {
        this.toggleBtn.addEventListener('click', () => this.toggleContainer());
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.clearBtn.addEventListener('click', () => this.clearHistory());
        if (this.expandBtn) {
            this.expandBtn.addEventListener('click', () => this.toggleExpand());
        }
        
        this.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Nút gợi ý nhanh
        document.querySelectorAll('[data-suggest]').forEach(btn => {
            btn.addEventListener('click', () => {
                const suggestion = btn.getAttribute('data-suggest');
                this.sendMessage(suggestion);
            });
        });

        // Auto-focus input khi mở chatbot
        this.toggleBtn.addEventListener('click', () => {
            setTimeout(() => {
                if (this.container.style.display !== 'none') {
                    this.input.focus();
                }
            }, 100);
        });
    }

    toggleContainer() {
        const isVisible = this.container.style.display !== 'none';
        this.container.style.display = isVisible ? 'none' : 'block';
        
        if (!isVisible) {
            this.input.focus();
        }
    }

    toggleExpand() {
        const isExpanded = this.container.classList.contains('expanded');
        if (isExpanded) {
            this.container.classList.remove('expanded');
            if (this.expandBtn) this.expandBtn.textContent = 'Mở rộng';
        } else {
            this.container.classList.add('expanded');
            if (this.expandBtn) this.expandBtn.textContent = 'Thu nhỏ';
        }
        // Ensure messages area adjusts
        setTimeout(() => this.scrollToBottom(), 100);
    }

    buildContext() {
        // Lấy dữ liệu đang có trong trang làm context cho bot
        const campaigns = window.adsData?.campaigns || [];
        const campaignsWithInsights = campaigns.filter(c => c.insights);
        const campaignsWithoutInsights = campaigns.filter(c => !c.insights);
        
        const ctx = {
            campaigns_count: campaigns.length,
            campaigns_with_insights: campaignsWithInsights.length,
            campaigns_without_insights: campaignsWithoutInsights.length,
            extraction_date: window.adsData?.extraction_date,
            current_page: window.location.pathname,
            current_filters: this.getCurrentFilters(),
            recent_campaigns: this.getRecentCampaigns(),
            daily_data: this.getDailyData(),
            conversation_history: this.conversationHistory.slice(-3), // Chỉ gửi 3 câu hỏi gần nhất
            
            // Thêm thông tin chi tiết về campaigns
            all_campaigns_data: campaigns.map(c => ({
                id: c.campaign_id || c.id,
                name: c.campaign_name || c.name,
                status: c.status,
                objective: c.objective,
                created_time: c.created_time,
                start_time: c.start_time,
                stop_time: c.stop_time,
                insights: c.insights,
                page_id: c.page_id,
                page_name: c.page_name
            }))
        };
        return ctx;
    }
    
    getCurrentFilters() {
        // Lấy filter hiện tại từ dashboard
        const filters = {};
        try {
            // Kiểm tra xem có global filters không
            if (window.globalFilters) {
                filters.date_range = window.globalFilters.dateRange;
                filters.campaign_ids = window.globalFilters.campaignIds;
                filters.metric_focus = window.globalFilters.metricFocus;
            }
            
            // Lấy filter từ URL params
            const urlParams = new URLSearchParams(window.location.search);
            urlParams.forEach((value, key) => {
                filters[key] = value;
            });
        } catch (e) {
            console.warn('Không thể lấy filters:', e);
        }
        return filters;
    }

    getRecentCampaigns() {
        try {
            if (!window.adsData?.campaigns) return [];
            
            // Trả về TẤT CẢ campaigns thay vì chỉ 5 campaigns đầu
            return window.adsData.campaigns.map(campaign => ({
                id: campaign.campaign_id || campaign.id,
                name: campaign.campaign_name || campaign.name,
                status: campaign.status,
                spend: campaign.insights?.spend ? parseFloat(campaign.insights.spend) : (campaign.summary_metrics?.total_spend || 0),
                impressions: campaign.insights?.impressions ? parseInt(campaign.insights.impressions) : (campaign.summary_metrics?.total_impressions || 0),
                clicks: campaign.insights?.clicks ? parseInt(campaign.insights.clicks) : (campaign.summary_metrics?.total_clicks || 0),
                ctr: campaign.insights?.ctr ? parseFloat(campaign.insights.ctr) : (campaign.summary_metrics?.avg_ctr || 0),
                cpc: campaign.insights?.cpc ? parseFloat(campaign.insights.cpc) : (campaign.summary_metrics?.avg_cpc || 0),
                reach: campaign.insights?.reach ? parseInt(campaign.insights.reach) : 0,
                frequency: campaign.insights?.frequency ? parseFloat(campaign.insights.frequency) : 0,
                has_insights: !!campaign.insights
            }));
        } catch (e) {
            console.warn('Không thể lấy recent campaigns:', e);
            return [];
        }
    }

    getDailyData() {
        try {
            // Lấy dữ liệu daily từ biểu đồ nếu có
            if (window.dailyData && window.dailyData.length > 0) {
                const recent = window.dailyData.slice(-7); // 7 ngày gần nhất
                return recent.map(day => ({
                    date: day.date,
                    spend: day.spend || 0,
                    impressions: day.impressions || 0,
                    clicks: day.clicks || 0,
                    ctr: day.ctr || 0,
                    cpc: day.cpc || 0
                }));
            }
            return [];
        } catch (e) {
            console.warn('Không thể lấy daily data:', e);
            return [];
        }
    }

    showTypingIndicator() {
        this.typingIndicator = document.createElement('div');
        this.typingIndicator.className = 'message bot-message typing-indicator';
        this.typingIndicator.innerHTML = `
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
            <span class="typing-text">Đang phân tích...</span>
        `;
        this.messagesContainer.appendChild(this.typingIndicator);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        if (this.typingIndicator) {
            this.typingIndicator.remove();
            this.typingIndicator = null;
        }
    }

    sendMessage(customQuestion = null) {
        if (this.isProcessing) return;
        
        const question = customQuestion || this.input.value.trim();
        if (!question) return;

        this.isProcessing = true;
        this.sendBtn.disabled = true;
        this.input.disabled = true;

        // Thêm câu hỏi vào lịch sử
        this.conversationHistory.push({
            question: question,
            timestamp: new Date().toISOString(),
            type: 'user'
        });

        // Hiển thị câu hỏi của user
        this.addMessage(question, 'user');
        this.input.value = '';
        
        // Hiển thị typing indicator
        this.showTypingIndicator();

        // Gửi request
        fetch('/api/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: question,
                context: this.buildContext()
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            this.hideTypingIndicator();
            
            if (data.error) {
                this.addMessage(`Lỗi: ${data.error}`, 'bot', 'error');
            } else {
                this.addMessage(data.answer, 'bot');
                
                // Thêm câu trả lời vào lịch sử
                this.conversationHistory.push({
                    answer: data.answer,
                    timestamp: new Date().toISOString(),
                    type: 'bot'
                });
            }
        })
        .catch(error => {
            this.hideTypingIndicator();
            console.error('Chatbot error:', error);
            
            let errorMessage = 'Lỗi kết nối. Vui lòng thử lại.';
            if (error.message.includes('timeout')) {
                errorMessage = 'Timeout. Vui lòng thử lại với câu hỏi ngắn hơn.';
            } else if (error.message.includes('500')) {
                errorMessage = 'Lỗi server. Vui lòng thử lại sau.';
            }
            
            this.addMessage(`${errorMessage}`, 'bot', 'error');
        })
        .finally(() => {
            this.isProcessing = false;
            this.sendBtn.disabled = false;
            this.input.disabled = false;
            this.input.focus();
        });
    }

    addMessage(text, type, messageType = 'normal') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message ${messageType === 'error' ? 'error-message' : ''}`;
        
        // Format message với markdown cơ bản
        const formattedText = this.formatMessage(text);
        messageDiv.innerHTML = formattedText;
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    formatMessage(text) {
        // Basic markdown formatting
        let formatted = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>')
            .replace(/(\d+%)/g, '<span class="highlight-metric">$1</span>')
            .replace(/(\$\s?([0-9]{1,3}(,[0-9]{3})*|[0-9]+)(\.[0-9]+)?)/g, (m)=>{
                const n = m.replace(/[^0-9.]/g,'');
                const v = Math.round(parseFloat(n||'0'));
                return `<span class="highlight-money">${v.toLocaleString('vi-VN')}₫</span>`;
            })
            .replace(/\bUSD\b/g, 'VND');
        // If any plain VND amounts appear like 1000000d, normalize to ₫ with grouping
        formatted = formatted.replace(/\b([0-9]{4,})d\b/gi, (_,num)=>`${Number(num).toLocaleString('vi-VN')}₫`);
        return formatted;
    }

    scrollToBottom() {
        setTimeout(() => {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }, 100);
    }

    clearHistory() {
        this.conversationHistory = [];
        this.messagesContainer.innerHTML = `
            <div class="message bot-message">
                Xin chào! Hãy hỏi tôi bất kỳ câu hỏi nào về dữ liệu quảng cáo.
            </div>
        `;
    }
}

function initializeChatbot() {
    window.chatbot = new ChatbotManager();
}

