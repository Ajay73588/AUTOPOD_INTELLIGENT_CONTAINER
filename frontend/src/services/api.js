import axios from 'axios';

const API_BASE = 'http://localhost:5000/api';

export const apiService = {
  getContainers: () => axios.get(`${API_BASE}/containers`),
  getWebhooks: () => axios.get(`${API_BASE}/webhooks`),
  // Add more API calls as needed
};