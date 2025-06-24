import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import {
  Box,
  Typography,
  Button,
  Checkbox,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  CircularProgress,
  Alert,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  RadioGroup,
  FormControlLabel,
  Radio,
  TextField,
} from '@mui/material'
import {
  Refresh as RefreshIcon,
  Download as DownloadIcon,
  Tag as TagIcon,
} from '@mui/icons-material'
import { RootState, AppDispatch } from '../store'
import { fetchChannels } from '../store/serversSlice'
import { createJob } from '../store/jobsSlice'
import { Channel } from '../types'
import { authAPI } from '../services/api'
import TokenSetup from '../components/TokenSetup'

export default function ServerDetail() {
  const { serverId } = useParams<{ serverId: string }>()
  const dispatch = useDispatch<AppDispatch>()
  const channels = useSelector((state: RootState) => 
    state.servers.channels[serverId!] || []
  )
  const loading = useSelector((state: RootState) => state.servers.loading)
  const server = useSelector((state: RootState) => 
    state.servers.servers.find(s => s.server_id === serverId)
  )
  
  const [selectedChannels, setSelectedChannels] = useState<Set<string>>(new Set())
  const [exportDialogOpen, setExportDialogOpen] = useState(false)
  const [exportFormat, setExportFormat] = useState<'json' | 'html' | 'csv' | 'txt'>('json')
  const [jobType, setJobType] = useState<'full' | 'incremental'>('incremental')
  const [tokenStatus, setTokenStatus] = useState<any>(null)
  const [showTokenSetup, setShowTokenSetup] = useState(false)
  const [exportMode, setExportMode] = useState<'all' | 'last_messages' | 'last_days'>('all')
  const [lastMessagesCount, setLastMessagesCount] = useState<number>(100)
  const [lastDaysCount, setLastDaysCount] = useState<number>(7)

  useEffect(() => {
    if (serverId) {
      dispatch(fetchChannels(serverId))
    }
    checkTokenStatus()
  }, [dispatch, serverId])

  const checkTokenStatus = async () => {
    try {
      const response = await authAPI.getTokenStatus()
      setTokenStatus(response.data)
    } catch (error) {
      console.error('Failed to check token status')
    }
  }

  const handleChannelToggle = (channelId: string) => {
    const newSelected = new Set(selectedChannels)
    if (newSelected.has(channelId)) {
      newSelected.delete(channelId)
    } else {
      newSelected.add(channelId)
    }
    setSelectedChannels(newSelected)
  }

  const handleSelectAll = () => {
    if (selectedChannels.size === channels.length) {
      setSelectedChannels(new Set())
    } else {
      setSelectedChannels(new Set(channels.map(c => c.channel_id)))
    }
  }

  const handleExport = async () => {
    for (const channelId of selectedChannels) {
      const channel = channels.find(c => c.channel_id === channelId)
      
      // Calculate date range for last X days
      let dateRangeStart = undefined
      let messageLimit = undefined
      
      if (jobType === 'full' && exportMode === 'last_days') {
        const startDate = new Date()
        startDate.setDate(startDate.getDate() - lastDaysCount)
        dateRangeStart = startDate.toISOString()
      } else if (jobType === 'full' && exportMode === 'last_messages') {
        messageLimit = lastMessagesCount
      }
      
      await dispatch(createJob({
        server_id: serverId!,  // Keep as string
        channel_id: channelId,  // Already a string now
        channel_name: channel?.name,
        job_type: jobType,
        export_format: exportFormat,
        date_range_start: dateRangeStart,
        message_limit: messageLimit,
      }))
    }
    setExportDialogOpen(false)
    setSelectedChannels(new Set())
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          {server?.name || 'Server Channels'}
        </Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            sx={{ mr: 2 }}
            onClick={() => dispatch(fetchChannels(serverId!))}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<DownloadIcon />}
            disabled={selectedChannels.size === 0}
            onClick={() => setExportDialogOpen(true)}
          >
            Export Selected ({selectedChannels.size})
          </Button>
        </Box>
      </Box>

      {!tokenStatus?.has_token && (
        <Alert 
          severity="warning" 
          action={
            <Button color="inherit" size="small" onClick={() => setShowTokenSetup(true)}>
              Setup Token
            </Button>
          }
          sx={{ mb: 2 }}
        >
          Self-bot token required for scraping. This violates Discord ToS - use test accounts only.
        </Alert>
      )}

      <Paper>
        <Box p={2} borderBottom={1} borderColor="divider">
          <Button size="small" onClick={handleSelectAll}>
            {selectedChannels.size === channels.length ? 'Deselect All' : 'Select All'}
          </Button>
        </Box>
        
        <List>
          {channels.map((channel) => (
            <ListItem
              key={channel.channel_id}
              button
              onClick={() => handleChannelToggle(channel.channel_id)}
            >
              <ListItemIcon>
                <Checkbox
                  edge="start"
                  checked={selectedChannels.has(channel.channel_id)}
                  tabIndex={-1}
                  disableRipple
                />
              </ListItemIcon>
              <ListItemIcon>
                <TagIcon />
              </ListItemIcon>
              <ListItemText
                primary={channel.name}
                secondary={
                  <Box>
                    {channel.topic && (
                      <Typography variant="body2" color="text.secondary">
                        {channel.topic}
                      </Typography>
                    )}
                    {channel.last_sync && (
                      <Box mt={1}>
                        <Chip
                          size="small"
                          label={`${channel.last_sync.total_messages} messages`}
                          color="primary"
                          variant="outlined"
                        />
                        {channel.last_sync.needs_update && (
                          <Chip
                            size="small"
                            label="New messages available"
                            color="success"
                            sx={{ ml: 1 }}
                          />
                        )}
                      </Box>
                    )}
                  </Box>
                }
              />
            </ListItem>
          ))}
        </List>
      </Paper>

      {channels.length === 0 && (
        <Alert severity="info" sx={{ mt: 2 }}>
          No channels found. Make sure your bot has access to view channels in this server.
        </Alert>
      )}

      <Dialog open={exportDialogOpen} onClose={() => setExportDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Export Channels</DialogTitle>
        <DialogContent>
          <Box sx={{ minWidth: 400, pt: 2 }}>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Export Type</InputLabel>
              <Select
                value={jobType}
                label="Export Type"
                onChange={(e) => setJobType(e.target.value as 'full' | 'incremental')}
              >
                <MenuItem value="incremental">Incremental (New messages only)</MenuItem>
                <MenuItem value="full">Full Export</MenuItem>
              </Select>
            </FormControl>

            {jobType === 'full' && (
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>
                  Full Export Options:
                </Typography>
                <RadioGroup
                  value={exportMode}
                  onChange={(e) => setExportMode(e.target.value as any)}
                >
                  <FormControlLabel
                    value="all"
                    control={<Radio />}
                    label="Export all messages"
                  />
                  <FormControlLabel
                    value="last_messages"
                    control={<Radio />}
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <span>Export last</span>
                        <TextField
                          size="small"
                          type="number"
                          value={lastMessagesCount}
                          onChange={(e) => setLastMessagesCount(parseInt(e.target.value) || 100)}
                          onClick={(e) => {
                            e.stopPropagation();
                            setExportMode('last_messages');
                          }}
                          sx={{ width: 80 }}
                          inputProps={{ min: 1 }}
                        />
                        <span>messages</span>
                      </Box>
                    }
                  />
                  <FormControlLabel
                    value="last_days"
                    control={<Radio />}
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <span>Export messages from last</span>
                        <TextField
                          size="small"
                          type="number"
                          value={lastDaysCount}
                          onChange={(e) => setLastDaysCount(parseInt(e.target.value) || 7)}
                          onClick={(e) => {
                            e.stopPropagation();
                            setExportMode('last_days');
                          }}
                          sx={{ width: 80 }}
                          inputProps={{ min: 1 }}
                        />
                        <span>days</span>
                      </Box>
                    }
                  />
                </RadioGroup>
              </Box>
            )}
            
            <FormControl fullWidth>
              <InputLabel>Export Format</InputLabel>
              <Select
                value={exportFormat}
                label="Export Format"
                onChange={(e) => setExportFormat(e.target.value as any)}
              >
                <MenuItem value="json">JSON</MenuItem>
                <MenuItem value="html">HTML</MenuItem>
                <MenuItem value="csv">CSV</MenuItem>
                <MenuItem value="txt">Plain Text</MenuItem>
              </Select>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setExportDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleExport} variant="contained">
            Start Export
          </Button>
        </DialogActions>
      </Dialog>

      <TokenSetup 
        open={showTokenSetup}
        onClose={() => setShowTokenSetup(false)}
        onSuccess={() => {
          checkTokenStatus()
          setShowTokenSetup(false)
        }}
      />
    </Box>
  )
}