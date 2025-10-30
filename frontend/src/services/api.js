import axios from 'axios';

const API_BASE = 'http://localhost:5000/api';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
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
  // Container endpoints
  getContainers: () => apiClient.get('/containers'),
  getContainerStatus: () => apiClient.get('/status'),
  syncContainers: () => apiClient.post('/sync'),
  
  // Container actions
  startContainer: (containerName) => 
    apiClient.post('/containers/start', { container_name: containerName }),
  stopContainer: (containerName) => 
    apiClient.post('/containers/stop', { container_name: containerName }),
  restartContainer: (containerName) => 
    apiClient.post('/containers/restart', { container_name: containerName }),
  removeContainer: (containerName) => 
    apiClient.post('/containers/remove', { container_name: containerName }),
  
  // Health and stats
  getContainerHealth: (containerName) => 
    apiClient.get(`/containers/${containerName}/health`),
  getAllContainersHealth: () => 
    apiClient.get('/containers/health'),
  getContainerStats: (containerName) => 
    apiClient.get(`/containers/${containerName}/stats`),
  
  // Network info
  getContainerNetwork: (containerName) => 
    apiClient.get(`/containers/${containerName}/network`),
  getAllNetworks: () => 
    apiClient.get('/containers/network/all'),
  getNetworkStats: () => 
    apiClient.get('/network/stats'),
  
  // Logs
  getLogs: () => apiClient.get('/logs'),
  getAdvancedLogs: (params) => 
    apiClient.get('/logs/advanced', { params }),
  exportLogs: (format, container) => 
    apiClient.get('/logs/export', { 
      params: { format, container },
      responseType: 'blob'
    }),
  
  // Images
  getImages: () => apiClient.get('/images'),
  searchImages: (query, limit = 25) => 
    apiClient.get('/images/search', { params: { q: query, limit } }),
  pullImage: (imageName) => 
    apiClient.post('/images/pull', { image_name: imageName }),
  removeImage: (imageName) => 
    apiClient.post('/images/remove', { image_name: imageName }),
  tagImage: (sourceImage, targetImage) => 
    apiClient.post('/images/tag', { source_image: sourceImage, target_image: targetImage }),
  getImageDetails: (imageName) => 
    apiClient.get(`/images/${imageName}/details`),
  getImageHistory: (imageName) => 
    apiClient.get(`/images/${imageName}/history`),
  
  // Webhooks
  triggerWebhook: (data) => 
    apiClient.post('/webhook', data),
  
  // Health check
  healthCheck: () => apiClient.get('/health')
};

export default apiService;