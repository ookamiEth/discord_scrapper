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
  Chip,
} from '@mui/material'
import { Warning as WarningIcon } from '@mui/icons-material'
import { api } from '../services/api'

interface AddServerDialogProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

export default function AddServerDialog({ open, onClose, onSuccess }: AddServerDialogProps) {
  const [activeStep, setActiveStep] = useState(0)
  const [serverId, setServerId] = useState('')
  const [serverName, setServerName] = useState('')
  const [channelId, setChannelId] = useState('')
  const [channelName, setChannelName] = useState('')
  const [error, setError] = useState('')
  const [verificationAcknowledged, setVerificationAcknowledged] = useState(false)

  const steps = [
    {
      label: 'Server Verification Warning',
      content: (
        <Box>
          <Alert severity="warning" icon={<WarningIcon />} sx={{ mb: 2 }}>
            <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
              Important: Server Verification Required
            </Typography>
            <Typography variant="body2" paragraph>
              Most Discord servers require verification (Captcha, reaction roles, etc.) before you can access channels.
            </Typography>
            <Typography variant="body2" paragraph>
              <strong>Before adding a server here:</strong>
            </Typography>
            <Box component="ul" sx={{ mt: 1, pl: 2 }}>
              <li>
                <Typography variant="body2">
                  Open Discord in your browser (where you extracted your token)
                </Typography>
              </li>
              <li>
                <Typography variant="body2">
                  Join the server and complete ALL verification steps
                </Typography>
              </li>
              <li>
                <Typography variant="body2">
                  Make sure you can see and read the channels you want to scrape
                </Typography>
              </li>
              <li>
                <Typography variant="body2">
                  Keep the browser tab open during scraping (helps avoid re-verification)
                </Typography>
              </li>
            </Box>
          </Alert>
          
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2">
              The scraper will fail if you haven't completed server verification!
            </Typography>
          </Alert>

          <Button
            variant="contained"
            onClick={() => {
              setVerificationAcknowledged(true)
              setActiveStep(1)
            }}
            fullWidth
          >
            I understand - I've completed server verification
          </Button>
        </Box>
      ),
    },
    {
      label: 'Get Server & Channel IDs',
      content: (
        <Box>
          <Typography variant="body2" paragraph>
            How to get Discord IDs:
          </Typography>
          <Box component="ol" sx={{ pl: 2 }}>
            <li>
              <Typography variant="body2">
                Enable Developer Mode: Settings → Advanced → Developer Mode
              </Typography>
            </li>
            <li>
              <Typography variant="body2">
                Right-click the server name → "Copy Server ID"
              </Typography>
            </li>
            <li>
              <Typography variant="body2">
                Right-click the channel → "Copy Channel ID"
              </Typography>
            </li>
          </Box>
          
          <Alert severity="warning" sx={{ mt: 2 }}>
            <Typography variant="body2">
              Only add channels you can currently see and access!
            </Typography>
          </Alert>
        </Box>
      ),
    },
    {
      label: 'Enter Server Details',
      content: (
        <Box>
          <TextField
            fullWidth
            label="Server ID"
            value={serverId}
            onChange={(e) => setServerId(e.target.value)}
            placeholder="e.g., 1234567890123456789"
            margin="normal"
            helperText="18-19 digit number"
          />
          <TextField
            fullWidth
            label="Server Name (optional)"
            value={serverName}
            onChange={(e) => setServerName(e.target.value)}
            placeholder="e.g., My Discord Server"
            margin="normal"
            helperText="For display purposes only"
          />
          <TextField
            fullWidth
            label="Channel ID"
            value={channelId}
            onChange={(e) => setChannelId(e.target.value)}
            placeholder="e.g., 9876543210987654321"
            margin="normal"
            helperText="The specific channel to scrape"
          />
          <TextField
            fullWidth
            label="Channel Name (optional)"
            value={channelName}
            onChange={(e) => setChannelName(e.target.value)}
            placeholder="e.g., general"
            margin="normal"
            helperText="For display purposes only"
          />
        </Box>
      ),
    },
  ]

  const handleSubmit = async () => {
    setError('')
    
    try {
      // Add the server manually
      await api.post('/servers/manual', {
        server_id: serverId,
        server_name: serverName || `Server ${serverId}`,
        channel_id: channelId,
        channel_name: channelName || `Channel ${channelId}`,
        is_verified: verificationAcknowledged,
      })
      
      onSuccess()
      handleClose()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add server')
    }
  }

  const handleClose = () => {
    setActiveStep(0)
    setServerId('')
    setServerName('')
    setChannelId('')
    setChannelName('')
    setError('')
    setVerificationAcknowledged(false)
    onClose()
  }

  const canSubmit = serverId && channelId && verificationAcknowledged

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        Add Server Manually
        {verificationAcknowledged && (
          <Chip 
            label="Verification Acknowledged" 
            size="small" 
            color="success" 
            sx={{ ml: 2 }}
          />
        )}
      </DialogTitle>
      <DialogContent>
        <Stepper activeStep={activeStep} orientation="vertical">
          {steps.map((step, index) => (
            <Step key={step.label}>
              <StepLabel>{step.label}</StepLabel>
              <StepContent>
                {step.content}
                {index > 0 && (
                  <Box sx={{ mb: 2, mt: 2 }}>
                    {index < steps.length - 1 && (
                      <Button
                        variant="contained"
                        onClick={() => setActiveStep(index + 1)}
                        sx={{ mt: 1, mr: 1 }}
                      >
                        Continue
                      </Button>
                    )}
                    <Button
                      onClick={() => setActiveStep(index - 1)}
                      sx={{ mt: 1, mr: 1 }}
                    >
                      Back
                    </Button>
                  </Box>
                )}
              </StepContent>
            </Step>
          ))}
        </Stepper>

        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button 
          onClick={handleSubmit} 
          variant="contained"
          disabled={!canSubmit || activeStep !== steps.length - 1}
        >
          Add Server
        </Button>
      </DialogActions>
    </Dialog>
  )
}