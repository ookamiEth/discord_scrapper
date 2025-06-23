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
          <Typography>Press F12 or right-click → Inspect Element</Typography>
          <Typography>Navigate to the Console tab</Typography>
        </Box>
      ),
    },
    {
      label: 'Extract Token',
      content: (
        <Box>
          <Typography gutterBottom>Paste this code in the console:</Typography>
          <Box
            component="pre"
            sx={{
              p: 2,
              bgcolor: 'grey.900',
              borderRadius: 1,
              overflow: 'auto',
            }}
          >
            <code>
{`webpackChunkdiscord_app.push([[''],{},e=>{
  m=[];for(let c in e.c)m.push(e.c[c])
}]);
m.find(m=>m?.exports?.default?.getToken)
  .exports.default.getToken()`}
            </code>
          </Box>
          <Typography variant="caption" color="text.secondary">
            Copy the token that appears (without quotes)
          </Typography>
        </Box>
      ),
    },
  ]

  const handleSubmit = async () => {
    setError('')
    
    try {
      await authAPI.setUserToken(token)
      onSuccess()
      onClose()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save token')
    }
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
            />
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button 
          onClick={handleSubmit} 
          variant="contained"
          disabled={!token || activeStep < steps.length - 1}
        >
          Save Token
        </Button>
      </DialogActions>
    </Dialog>
  )
}