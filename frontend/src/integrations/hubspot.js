import { useState, useEffect } from "react";
import {
  Box,
  Button,
  CircularProgress,
  Paper,
  Typography,
  Fade,
} from "@mui/material";
import axios from "axios";
import { useCredentials } from "../context/CredentialsContext";

export const HubspotIntegration = ({ user, org }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const { storeIntegrationCredentials, credentials } = useCredentials();

  useEffect(() => {
    setIsConnected(!!credentials?.Hubspot);
  }, [credentials]);

  // Function to open OAuth in a new window
  const handleConnectClick = async () => {
    try {
      setIsConnecting(true);
      const formData = new FormData();
      formData.append("user_id", user);
      formData.append("org_id", org);
      const response = await axios.post(
        `http://localhost:8000/integrations/hubspot/authorize`,
        formData
      );
      const authURL = response?.data;

      const newWindow = window.open(
        authURL,
        "Hubspot Authorization",
        "width=600, height=600"
      );

      const pollTimer = window.setInterval(() => {
        if (newWindow?.closed !== false) {
          window.clearInterval(pollTimer);
          handleWindowClosed();
        }
      }, 200);
    } catch (e) {
      setIsConnecting(false);
      alert(e?.response?.data?.detail);
    }
  };

  // Function to handle logic when the OAuth window closes
  const handleWindowClosed = async () => {
    try {
      const formData = new FormData();
      formData.append("user_id", user);
      formData.append("org_id", org);
      const response = await axios.post(
        `http://localhost:8000/integrations/hubspot/credentials`,
        formData
      );
      const newCredentials = response.data;
      if (newCredentials) {
        storeIntegrationCredentials("Hubspot", newCredentials, user, org);
        setIsConnecting(false);
        setIsConnected(true);
      }
    } catch (e) {
      setIsConnecting(false);
      alert(e?.response?.data?.detail);
    }
  };

  return (
    <Fade in={true}>
      <Paper
        elevation={2}
        sx={{
          mt: 2,
          p: 3,
          backgroundColor: isConnected ? "#f8fdf8" : "#ffffff",
          transition: "background-color 0.3s ease",
        }}
      >
        <Typography variant="h6" gutterBottom>
          HubSpot Integration
        </Typography>
        <Box
          display="flex"
          alignItems="center"
          justifyContent="center"
          sx={{ mt: 2 }}
        >
          <Button
            variant="contained"
            onClick={isConnected ? () => {} : handleConnectClick}
            color={isConnected ? "success" : "primary"}
            disabled={isConnecting}
            size="large"
            sx={{
              minWidth: 200,
              transition: "all 0.3s ease",
              "&:hover": {
                transform: isConnected ? "none" : "translateY(-2px)",
                boxShadow: isConnected ? "none" : 4,
              },
            }}
          >
            {isConnected ? (
              "✓ Connected to HubSpot"
            ) : isConnecting ? (
              <Box display="flex" alignItems="center" gap={1}>
                <CircularProgress size={20} color="inherit" />
                <span>Connecting...</span>
              </Box>
            ) : (
              "Connect HubSpot"
            )}
          </Button>
        </Box>
      </Paper>
    </Fade>
  );
};
