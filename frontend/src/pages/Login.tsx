import { Box, Button, Paper, Typography, Container } from '@mui/material'
import { useAuth } from '../hooks/useAuth'

export default function Login() {
  const { login } = useAuth()

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
            Discord Scraper
          </Typography>
          <Typography variant="body1" color="text.secondary" align="center" sx={{ mb: 3 }}>
            Login with Discord to view and manage your server exports
          </Typography>
          <Button
            fullWidth
            variant="contained"
            size="large"
            onClick={login}
            sx={{
              backgroundColor: '#5865F2',
              '&:hover': {
                backgroundColor: '#4752C4',
              },
            }}
          >
            Login with Discord
          </Button>
        </Paper>
      </Box>
    </Container>
  )
}