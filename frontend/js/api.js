/**
 * ⚡ 配网调度智能预测系统 - API 调用封装
 */

// API 基础配置
const BASE_PATH = (window.BASE_PATH || '');
const API_CONFIG = {
    BASE_URL: window.location.origin + BASE_PATH,
    ENDPOINTS: {
        STREAM_RUN: BASE_PATH + 'stream_run',
        RUN: BASE_PATH + 'run',
        HEALTH: BASE_PATH + 'health'
    }
};

/**
 * API 调用类
 */
class DispatchAPI {
    constructor() {
        this.baseUrl = API_CONFIG.BASE_URL;
    }

    /**
     * 发送流式请求
     */
    async streamRun(message, onMessage, onError, onComplete) {
        try {
            const response = await fetch(`${this.baseUrl}${API_CONFIG.ENDPOINTS.STREAM_RUN}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    const cleanLine = line.replace('\r', '').trim();
                    if (cleanLine === '') continue;
                    
                    if (cleanLine.startsWith('data: ')) {
                        const data = cleanLine.slice(6).trim();
                        try {
                            const parsed = JSON.parse(data);
                            onMessage(parsed);
                        } catch (e) {
                            console.warn('SSE parse error:', e.message, '| data:', data);
                        }
                    }
                }
            }

            if (onComplete) onComplete();
        } catch (error) {
            console.error('Stream API error:', error);
            if (onError) onError(error);
        }
    }

    /**
     * 发送普通请求
     */
    async run(message) {
        try {
            const response = await fetch(`${this.baseUrl}${API_CONFIG.ENDPOINTS.RUN}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API error:', error);
            throw error;
        }
    }
}

// 创建全局 API 实例
const api = new DispatchAPI();

// 导出
window.DispatchAPI = DispatchAPI;
window.api = api;
