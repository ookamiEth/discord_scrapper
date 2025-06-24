import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import {
  Grid,
  Card,
  CardContent,
  CardMedia,
  Typography,
  Box,
  CircularProgress,
  Alert,
  TextField,
  InputAdornment,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
} from '@mui/material'
import { Search as SearchIcon, Add as AddIcon, CheckCircle as CheckCircleIcon, Warning as WarningIcon } from '@mui/icons-material'
import { RootState, AppDispatch } from '../store'
import { fetchServers } from '../store/serversSlice'
import { scrapingAPI, authAPI } from '../services/api'
import { Stats } from '../types'
import AddServerDialog from '../components/AddServerDialog'
import TokenSetup from '../components/TokenSetup'

export default function Dashboard() {
  const navigate = useNavigate()
  const dispatch = useDispatch<AppDispatch>()
  const { servers, loading, error } = useSelector((state: RootState) => state.servers)
  const [stats, setStats] = useState<Stats | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [addServerOpen, setAddServerOpen] = useState(false)
  const [tokenSetupOpen, setTokenSetupOpen] = useState(false)
  const [tokenStatus, setTokenStatus] = useState<{ has_token: boolean } | null>(null)

  useEffect(() => {
    dispatch(fetchServers())
    fetchStats()
    checkTokenStatus()
  }, [dispatch])

  const checkTokenStatus = async () => {
    try {
      const response = await authAPI.getTokenStatus()
      setTokenStatus(response.data)
    } catch (error) {
      console.error('Failed to check token status')
    }
  }

  const fetchStats = async () => {
    try {
      const response = await scrapingAPI.getStats()
      setStats(response.data)
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    }
  }

  const filteredServers = servers.filter(server =>
    server.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return <Alert severity="error">{error}</Alert>
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">
          Dashboard
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          {tokenStatus && (
            <Chip
              icon={tokenStatus.has_token ? <CheckCircleIcon /> : <WarningIcon />}
              label={tokenStatus.has_token ? "Discord Token Configured" : "No Discord Token"}
              color={tokenStatus.has_token ? "success" : "warning"}
              variant={tokenStatus.has_token ? "filled" : "outlined"}
            />
          )}
          <Button
            variant={tokenStatus?.has_token ? "outlined" : "contained"}
            onClick={() => setTokenSetupOpen(true)}
            color={tokenStatus?.has_token ? "primary" : "warning"}
          >
            {tokenStatus?.has_token ? "Update Token" : "Setup Discord Token"}
          </Button>
        </Box>
      </Box>
      
      {tokenStatus && !tokenStatus.has_token && (
        <Alert 
          severity="warning" 
          sx={{ mb: 3 }}
          action={
            <Button color="inherit" size="small" onClick={() => setTokenSetupOpen(true)}>
              Setup Now
            </Button>
          }
        >
          Discord token required for scraping. Self-bot usage violates Discord ToS - use test accounts only.
        </Alert>
      )}
      
      {stats && (
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Total Servers
                </Typography>
                <Typography variant="h4">{stats.total_servers}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Total Channels
                </Typography>
                <Typography variant="h4">{stats.total_channels}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Messages Scraped
                </Typography>
                <Typography variant="h4">
                  {stats.total_messages.toLocaleString()}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Active Jobs
                </Typography>
                <Typography variant="h4">{stats.active_jobs}</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      <Box sx={{ mb: 3 }}>
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Search servers..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />
      </Box>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 4, mb: 2 }}>
        <Typography variant="h5">
          Your Servers
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setAddServerOpen(true)}
        >
          Add Server Manually
        </Button>
      </Box>
      
      <Grid container spacing={3}>
        {filteredServers.map((server) => (
          <Grid item xs={12} sm={6} md={4} key={server.server_id}>
            <Card
              sx={{
                cursor: 'pointer',
                '&:hover': {
                  boxShadow: 6,
                },
              }}
              onClick={() => navigate(`/servers/${server.server_id}`)}
            >
              {server.icon_url && (
                <CardMedia
                  component="img"
                  height="140"
                  image={server.icon_url}
                  alt={server.name}
                  sx={{ objectFit: 'contain', bgcolor: 'background.paper' }}
                />
              )}
              <CardContent>
                <Typography gutterBottom variant="h6" component="div">
                  {server.name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {server.member_count ? `${server.member_count.toLocaleString()} members` : 'Click to view channels'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {filteredServers.length === 0 && (
        <Box textAlign="center" py={4}>
          <Typography variant="body1" color="text.secondary">
            {searchTerm ? 'No servers found matching your search.' : 'No servers found. Click "Add Server Manually" to get started.'}
          </Typography>
        </Box>
      )}

      <AddServerDialog
        open={addServerOpen}
        onClose={() => setAddServerOpen(false)}
        onSuccess={() => {
          setAddServerOpen(false)
          dispatch(fetchServers())
        }}
      />

      <TokenSetup
        open={tokenSetupOpen}
        onClose={() => setTokenSetupOpen(false)}
        onSuccess={() => {
          setTokenSetupOpen(false)
          checkTokenStatus() // Refresh token status
        }}
      />
    </Box>
  )
}