import axios from 'axios';

const API_BASE = 'http://localhost:5000/api';

// Create axios instance with longer timeout for webhook operations
const apiClient = axios.create({
  baseURL: 'http://localhost:5000',
  timeout: 300000, // 5 minutes timeout for long operations like deployments
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

export const apiService = {
  // Container endpoints - normal timeout
  getContainers: () => axios.get('/api/containers', { timeout: 10000 }),
  getContainerStatus: () => axios.get('/api/status', { timeout: 10000 }),
  syncContainers: () => axios.post('/api/sync', {}, { timeout: 10000 }),
  
  // Container actions - normal timeout
  startContainer: (containerName) => 
    apiClient.post('/api/containers/start', { container_name: containerName }, { timeout: 30000 }),
  stopContainer: (containerName) => 
    apiClient.post('/api/containers/stop', { container_name: containerName }, { timeout: 30000 }),
  restartContainer: (containerName) => 
    apiClient.post('/api/containers/restart', { container_name: containerName }, { timeout: 30000 }),
  removeContainer: (containerName) => 
    apiClient.post('/api/containers/remove', { container_name: containerName }, { timeout: 30000 }),
  
  // Webhooks - LONG timeout for deployment operations
  triggerWebhook: (data) => 
    apiClient.post('/webhook', data, { timeout: 300000 }), // 5 minutes
  
  // ... rest of your API endpoints with normal timeouts
  getLogs: () => axios.get('/api/logs', { timeout: 10000 }),
  getAdvancedLogs: (params) => 
    axios.get('/api/logs/advanced', { params, timeout: 10000 }),
  
  // Images - longer timeout for pull operations
  getImages: () => axios.get('/api/images', { timeout: 10000 }),
  searchImages: (query, limit = 25) => 
    axios.get('/api/images/search', { params: { q: query, limit }, timeout: 10000 }),
  pullImage: (imageName) => 
    apiClient.post('/api/images/pull', { image_name: imageName }, { timeout: 300000 }),
  
  // Health check - quick timeout
  healthCheck: () => axios.get('/health', { timeout: 5000 })
};

export default apiClient;