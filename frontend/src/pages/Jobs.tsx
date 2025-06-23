import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  LinearProgress,
  Button,
  CircularProgress,
} from '@mui/material'
import {
  Cancel as CancelIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material'
import { RootState, AppDispatch } from '../store'
import { fetchJobs, cancelJob } from '../store/jobsSlice'
import { format } from 'date-fns'

export default function Jobs() {
  const dispatch = useDispatch<AppDispatch>()
  const { jobs, loading } = useSelector((state: RootState) => state.jobs)

  useEffect(() => {
    dispatch(fetchJobs())
    
    // Refresh jobs every 5 seconds if there are active jobs
    const interval = setInterval(() => {
      const hasActiveJobs = jobs.some(job => 
        ['pending', 'running'].includes(job.status)
      )
      if (hasActiveJobs) {
        dispatch(fetchJobs())
      }
    }, 5000)

    return () => clearInterval(interval)
  }, [dispatch, jobs])

  const handleCancelJob = async (jobId: string) => {
    if (confirm('Are you sure you want to cancel this job?')) {
      await dispatch(cancelJob(jobId))
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success'
      case 'failed':
        return 'error'
      case 'running':
        return 'primary'
      case 'pending':
        return 'warning'
      default:
        return 'default'
    }
  }

  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), 'MMM dd, yyyy HH:mm')
    } catch {
      return dateString
    }
  }

  if (loading && jobs.length === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Scraping Jobs</Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={() => dispatch(fetchJobs())}
        >
          Refresh
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Channel</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Progress</TableCell>
              <TableCell>Messages</TableCell>
              <TableCell>Started</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {jobs.map((job) => (
              <TableRow key={job.job_id}>
                <TableCell>{job.channel_name || `Channel ${job.channel_id}`}</TableCell>
                <TableCell>
                  <Chip 
                    label={job.job_type} 
                    size="small" 
                    variant="outlined"
                  />
                </TableCell>
                <TableCell>
                  <Chip
                    label={job.status}
                    color={getStatusColor(job.status) as any}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  {job.status === 'running' && job.progress_percent !== undefined ? (
                    <Box display="flex" alignItems="center">
                      <Box width="100%" mr={1}>
                        <LinearProgress 
                          variant="determinate" 
                          value={job.progress_percent} 
                        />
                      </Box>
                      <Box minWidth={35}>
                        <Typography variant="body2" color="text.secondary">
                          {`${job.progress_percent}%`}
                        </Typography>
                      </Box>
                    </Box>
                  ) : (
                    '-'
                  )}
                </TableCell>
                <TableCell>{job.messages_scraped.toLocaleString()}</TableCell>
                <TableCell>{formatDate(job.started_at)}</TableCell>
                <TableCell>
                  {['pending', 'running'].includes(job.status) && (
                    <IconButton
                      size="small"
                      onClick={() => handleCancelJob(job.job_id)}
                      title="Cancel job"
                    >
                      <CancelIcon />
                    </IconButton>
                  )}
                  {job.status === 'completed' && job.export_path && (
                    <IconButton
                      size="small"
                      href={`/api/v1/exports/${job.job_id}/download`}
                      title="Download export"
                    >
                      <DownloadIcon />
                    </IconButton>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {jobs.length === 0 && (
        <Box textAlign="center" py={4}>
          <Typography variant="body1" color="text.secondary">
            No scraping jobs yet. Go to a server and select channels to export.
          </Typography>
        </Box>
      )}
    </Box>
  )
}