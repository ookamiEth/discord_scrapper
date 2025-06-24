import { api } from './api';

export interface SystemStatus {
  status: string;
  services?: string;
  error?: string;
}

export interface ShutdownResponse {
  status: string;
  message: string;
}

export const systemService = {
  async getStatus(): Promise<SystemStatus> {
    const response = await api.get<SystemStatus>('/system/status');
    return response.data;
  },

  async shutdown(): Promise<ShutdownResponse> {
    const response = await api.post<ShutdownResponse>('/system/shutdown');
    return response.data;
  },
};