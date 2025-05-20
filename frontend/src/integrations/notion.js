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

export const NotionIntegration = ({ user, org }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const { storeIntegrationCredentials, credentials } = useCredentials();

  useEffect(() => {
    setIsConnected(!!credentials?.Notion);
  }, [credentials]);

  const handleConnectClick = async () => {
    try {
      setIsConnecting(true);
      const formData = new FormData();
      formData.append("user_id", user);
      formData.append("org_id", org);
      const response = await axios.post(
        `http://localhost:8000/integrations/notion/authorize`,
        formData
      );
      const authURL = response?.data;

      const newWindow = window.open(
        authURL,
        "Notion Authorization",
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

  const handleWindowClosed = async () => {
    try {
      const formData = new FormData();
      formData.append("user_id", user);
      formData.append("org_id", org);
      const response = await axios.post(
        `http://localhost:8000/integrations/notion/credentials`,
        formData
      );
      const newCredentials = response.data;
      if (newCredentials) {
        storeIntegrationCredentials("Notion", newCredentials);
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
          Notion Integration
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
              "✓ Connected to Notion"
            ) : isConnecting ? (
              <Box display="flex" alignItems="center" gap={1}>
                <CircularProgress size={20} color="inherit" />
                <span>Connecting...</span>
              </Box>
            ) : (
              "Connect Notion"
            )}
          </Button>
        </Box>
      </Paper>
    </Fade>
  );
};
