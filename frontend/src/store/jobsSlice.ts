import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { api } from '../services/api'
import { ScrapingJob, CreateJobRequest } from '../types'

interface JobsState {
  jobs: ScrapingJob[]
  activeJobs: number
  loading: boolean
  error: string | null
}

const initialState: JobsState = {
  jobs: [],
  activeJobs: 0,
  loading: false,
  error: null,
}

export const fetchJobs = createAsyncThunk(
  'jobs/fetchJobs',
  async () => {
    const response = await api.get('/scraping/jobs')
    return response.data
  }
)

export const createJob = createAsyncThunk(
  'jobs/createJob',
  async (jobData: CreateJobRequest) => {
    const response = await api.post('/scraping/jobs', jobData)
    return response.data
  }
)

export const cancelJob = createAsyncThunk(
  'jobs/cancelJob',
  async (jobId: string) => {
    await api.put(`/scraping/jobs/${jobId}/cancel`)
    return jobId
  }
)

const jobsSlice = createSlice({
  name: 'jobs',
  initialState,
  reducers: {
    updateJobProgress: (state, action) => {
      const { jobId, progress } = action.payload
      const job = state.jobs.find(j => j.job_id === jobId)
      if (job) {
        job.progress_percent = progress
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch jobs
      .addCase(fetchJobs.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchJobs.fulfilled, (state, action) => {
        state.loading = false
        state.jobs = action.payload
        state.activeJobs = action.payload.filter(
          (job: ScrapingJob) => ['pending', 'running'].includes(job.status)
        ).length
      })
      .addCase(fetchJobs.rejected, (state, action) => {
        state.loading = false
        state.error = action.error.message || 'Failed to fetch jobs'
      })
      // Create job
      .addCase(createJob.fulfilled, (state, action) => {
        state.jobs.unshift(action.payload)
        state.activeJobs += 1
      })
      // Cancel job
      .addCase(cancelJob.fulfilled, (state, action) => {
        const job = state.jobs.find(j => j.job_id === action.payload)
        if (job) {
          job.status = 'failed'
          job.error_message = 'Cancelled by user'
          state.activeJobs = Math.max(0, state.activeJobs - 1)
        }
      })
  },
})

export const { updateJobProgress } = jobsSlice.actions
export default jobsSlice.reducer