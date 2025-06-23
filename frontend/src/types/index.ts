export interface Server {
  server_id: number
  name: string
  icon_url?: string
  member_count?: number
  channel_count?: number
}

export interface Channel {
  channel_id: number
  server_id: number
  name: string
  type: string
  category_id?: number
  position: number
  topic?: string
  is_nsfw: boolean
  last_sync?: ChannelSyncState
}

export interface ChannelSyncState {
  channel_id: number
  server_id: number
  channel_name?: string
  last_message_id?: number
  last_message_timestamp?: string
  total_messages: number
  last_sync_at?: string
  needs_update: boolean
}

export interface ScrapingJob {
  job_id: string
  server_id: number
  channel_id: number
  channel_name?: string
  job_type: 'full' | 'incremental' | 'date_range'
  status: 'pending' | 'running' | 'completed' | 'failed' | 'paused'
  started_at: string
  completed_at?: string
  messages_scraped: number
  export_path?: string
  export_format: 'json' | 'html' | 'csv' | 'txt'
  error_message?: string
  progress_percent?: number
}

export interface CreateJobRequest {
  server_id: number
  channel_id: number
  channel_name?: string
  job_type: 'full' | 'incremental' | 'date_range'
  export_format: 'json' | 'html' | 'csv' | 'txt'
  date_range_start?: string
  date_range_end?: string
  bot_token?: string
}

export interface Stats {
  total_servers: number
  total_channels: number
  total_messages: number
  total_jobs: number
  active_jobs: number
  last_sync?: string
}