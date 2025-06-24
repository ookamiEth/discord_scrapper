import { useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Typography,
  Alert,
  Box,
  Stepper,
  Step,
  StepLabel,
  StepContent,
} from '@mui/material'
import { authAPI } from '../services/api'

interface TokenSetupProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function TokenSetup({ open, onClose, onSuccess }: TokenSetupProps) {
  const [token, setToken] = useState('')
  const [error, setError] = useState('')
  const [activeStep, setActiveStep] = useState(0)
  const [success, setSuccess] = useState(false)

  const steps = [
    {
      label: 'Open Discord in Browser',
      content: (
        <Box>
          <Typography>1. Open Discord in your web browser (not the app)</Typography>
          <Typography>2. Log in to your account</Typography>
          <Typography color="warning.main" variant="caption">
            ⚠️ Use a test account - self-bots violate Discord ToS
          </Typography>
        </Box>
      ),
    },
    {
      label: 'Open Developer Console',
      content: (
        <Box>
          <Typography>
            Press Cmd+Option+I (Mac) or F12 (Windows) or right-click → Inspect Element
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Note: Cmd+Shift+I may not work in Discord
          </Typography>
        </Box>
      ),
    },
    {
      label: 'Extract Token',
      content: (
        <Box>
          <Typography variant="h6" gutterBottom>Network Tab Method - Detailed Steps:</Typography>
          <Box component="ol" sx={{ pl: 2, mb: 3 }}>
            <li>
              <Typography variant="body2" paragraph>
                <strong>Open Discord in your browser</strong> (not the desktop app)
                <br />• Go to discord.com/app
                <br />• Make sure you're logged in
              </Typography>
            </li>
            <li>
              <Typography variant="body2" paragraph>
                <strong>Open Developer Tools</strong>
                <br />• Press Cmd+Option+I (Mac) or F12 (Windows)
                <br />• Or right-click anywhere → "Inspect Element"
              </Typography>
            </li>
            <li>
              <Typography variant="body2" paragraph>
                <strong>Navigate to the Network tab</strong>
                <br />• Click on "Network" at the top of developer tools
              </Typography>
            </li>
            <li>
              <Typography variant="body2" paragraph>
                <strong>Filter for API calls</strong>
                <br />• In the filter box, type: <code style={{ backgroundColor: '#2d2d2d', padding: '2px 4px', borderRadius: '3px' }}>api</code>
                <br />• This shows only Discord API requests
              </Typography>
            </li>
            <li>
              <Typography variant="body2" paragraph>
                <strong>Trigger a Discord API call</strong>
                <br />• Send a message in any channel
                <br />• Or switch between channels
                <br />• You'll see new requests appear
              </Typography>
            </li>
            <li>
              <Typography variant="body2" paragraph>
                <strong>Find and click any discord.com/api request</strong>
                <br />• Look for requests starting with "discord.com/api/"
                <br />• Click on any of these requests
              </Typography>
            </li>
            <li>
              <Typography variant="body2" paragraph>
                <strong>Extract the token</strong>
                <br />• In the right panel, click "Headers" tab
                <br />• Scroll to "Request Headers"
                <br />• Find <code style={{ backgroundColor: '#2d2d2d', padding: '2px 4px', borderRadius: '3px' }}>authorization:</code>
                <br />• Copy the value after it (entire string, no quotes)
              </Typography>
            </li>
          </Box>

          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2">
              The token looks like: <code>ODEwODEx...Gf6c0F.zdp9j-L3t...</code> (70+ characters)
            </Typography>
          </Alert>

          <Box sx={{ mt: 3, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
            <Typography variant="caption" color="text.secondary">
              Alternative: Console Script (if network tab doesn't work)
            </Typography>
            <Box
              component="pre"
              sx={{
                p: 1,
                mt: 1,
                bgcolor: 'grey.900',
                borderRadius: 1,
                overflow: 'auto',
                fontSize: '0.75rem',
              }}
            >
              <code>
{`(webpackChunkdiscord_app.push([[''],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken!==void 0).exports.default.getToken()`}
              </code>
            </Box>
          </Box>
        </Box>
      ),
    },
  ]

  const handleSubmit = async () => {
    setError('')
    setSuccess(false)
    
    try {
      await authAPI.setUserToken(token)
      setSuccess(true)
      setTimeout(() => {
        onSuccess()
        handleClose()
      }, 1500)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save token')
    }
  }

  const handleClose = () => {
    setToken('')
    setError('')
    setActiveStep(0)
    setSuccess(false)
    onClose()
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Setup Discord Token</DialogTitle>
      <DialogContent>
        <Alert severity="warning" sx={{ mb: 2 }}>
          Using self-bots violates Discord's Terms of Service and may result in 
          account termination. Only use test accounts.
        </Alert>

        <Stepper activeStep={activeStep} orientation="vertical">
          {steps.map((step, index) => (
            <Step key={step.label}>
              <StepLabel>{step.label}</StepLabel>
              <StepContent>
                {step.content}
                <Box sx={{ mb: 2, mt: 2 }}>
                  <Button
                    variant="contained"
                    onClick={() => setActiveStep(index + 1)}
                    sx={{ mt: 1, mr: 1 }}
                    disabled={index === steps.length - 1}
                  >
                    Continue
                  </Button>
                  {index > 0 && (
                    <Button
                      onClick={() => setActiveStep(index - 1)}
                      sx={{ mt: 1, mr: 1 }}
                    >
                      Back
                    </Button>
                  )}
                </Box>
              </StepContent>
            </Step>
          ))}
        </Stepper>

        {activeStep === steps.length - 1 && (
          <Box sx={{ mt: 3 }}>
            <TextField
              fullWidth
              label="Discord Token"
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              error={!!error}
              helperText={error}
              placeholder="Paste your token here"
              disabled={success}
            />
            {success && (
              <Alert severity="success" sx={{ mt: 2 }}>
                Token saved successfully! You can now start scraping.
              </Alert>
            )}
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button 
          onClick={handleSubmit} 
          variant="contained"
          disabled={!token || activeStep < steps.length - 1 || success}
        >
          {success ? 'Saved!' : 'Save Token'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}