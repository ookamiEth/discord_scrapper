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
} from '@mui/material'
import { Search as SearchIcon } from '@mui/icons-material'
import { RootState, AppDispatch } from '../store'
import { fetchServers } from '../store/serversSlice'
import { scrapingAPI } from '../services/api'
import { Stats } from '../types'

export default function Dashboard() {
  const navigate = useNavigate()
  const dispatch = useDispatch<AppDispatch>()
  const { servers, loading, error } = useSelector((state: RootState) => state.servers)
  const [stats, setStats] = useState<Stats | null>(null)
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    dispatch(fetchServers())
    fetchStats()
  }, [dispatch])

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
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      
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

      <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
        Your Servers
      </Typography>
      
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
            {searchTerm ? 'No servers found matching your search.' : 'No servers found. Make sure your bot is added to at least one server.'}
          </Typography>
        </Box>
      )}
    </Box>
  )
}