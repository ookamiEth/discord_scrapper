import { useNavigate } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { Box, Button, Paper, Typography, Container } from '@mui/material'
import { setAuth } from '../store/authSlice'
import { api } from '../services/api'

export default function Login() {
  const navigate = useNavigate()
  const dispatch = useDispatch()

  const handleLocalLogin = async () => {
    console.log('Login button clicked!')
    try {
      const response = await api.post('/auth/local-login')
      console.log('Login response:', response.data)
      const { access_token, user } = response.data
      
      localStorage.setItem('token', access_token)
      console.log('Token stored:', access_token)
      dispatch(setAuth({ user, token: access_token }))
      navigate('/')
    } catch (error) {
      console.error('Login failed:', error)
    }
  }

  return (
    <Container component="main" maxWidth="xs">
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Paper
          elevation={3}
          sx={{
            padding: 4,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            width: '100%',
          }}
        >
          <Typography component="h1" variant="h4" gutterBottom>
            Discord Self-Bot Scraper
          </Typography>
          <Typography variant="body1" color="text.secondary" align="center" sx={{ mb: 2 }}>
            Local access only - for personal use
          </Typography>
          <Typography variant="caption" color="warning.main" align="center" sx={{ mb: 3 }}>
            ⚠️ Using self-bots violates Discord ToS. Use at your own risk.
          </Typography>
          <Button
            fullWidth
            variant="contained"
            size="large"
            onClick={handleLocalLogin}
          >
            Enter Dashboard
          </Button>
        </Paper>
      </Box>
    </Container>
  )
}