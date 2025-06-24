import axios from 'axios'
import { store } from '../store'
import { clearAuth } from '../store/authSlice'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.log('API Error:', error.response?.status, error.response?.data)
    if (error.response?.status === 401) {
      console.log('401 Unauthorized - Clearing auth and redirecting to login')
      store.dispatch(clearAuth())
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authAPI = {
  login: () => api.get('/auth/discord/login'),
  logout: () => api.post('/auth/logout'),
  getMe: () => api.get('/auth/me'),
  setUserToken: (token: string) => api.post('/auth/discord/set-token', { token }),
  getTokenStatus: () => api.get('/auth/discord/token-status'),
}

// Servers API
export const serversAPI = {
  getServers: () => api.get('/servers'),
  getChannels: (serverId: string) => api.get(`/servers/${serverId}/channels`),
  refreshServer: (serverId: string) => api.post(`/servers/${serverId}/refresh`),
}

// Scraping API
export const scrapingAPI = {
  getJobs: (params?: any) => api.get('/scraping/jobs', { params }),
  createJob: (data: any) => api.post('/scraping/jobs', data),
  getJob: (jobId: string) => api.get(`/scraping/jobs/${jobId}`),
  cancelJob: (jobId: string) => api.put(`/scraping/jobs/${jobId}/cancel`),
  checkUpdates: (channelIds: number[]) => 
    api.post('/scraping/check-updates', { channel_ids: channelIds }),
  getChannelHistory: (channelId: number) => 
    api.get(`/scraping/history/${channelId}`),
  getStats: () => api.get('/scraping/stats'),
}