import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit'
import { api } from '../services/api'
import { Server, Channel } from '../types'

interface ServersState {
  servers: Server[]
  channels: { [serverId: string]: Channel[] }
  loading: boolean
  error: string | null
}

const initialState: ServersState = {
  servers: [],
  channels: {},
  loading: false,
  error: null,
}

export const fetchServers = createAsyncThunk(
  'servers/fetchServers',
  async () => {
    const response = await api.get('/servers')
    return response.data
  }
)

export const fetchChannels = createAsyncThunk(
  'servers/fetchChannels',
  async (serverId: string) => {
    const response = await api.get(`/servers/${serverId}/channels`)
    return { serverId, channels: response.data }
  }
)

const serversSlice = createSlice({
  name: 'servers',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      // Fetch servers
      .addCase(fetchServers.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchServers.fulfilled, (state, action) => {
        state.loading = false
        state.servers = action.payload
      })
      .addCase(fetchServers.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'Failed to fetch servers'
      })
      // Fetch channels
      .addCase(fetchChannels.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchChannels.fulfilled, (state, action) => {
        state.loading = false
        state.channels[action.payload.serverId] = action.payload.channels
      })
      .addCase(fetchChannels.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'Failed to fetch channels'
      })
  },
})

export default serversSlice.reducer