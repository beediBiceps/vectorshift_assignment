import { useState, useEffect } from "react";
import {
  Box,
  TextField,
  Button,
  Typography,
  Paper,
  CircularProgress,
} from "@mui/material";
import axios from "axios";
import {
  Refresh as RefreshIcon,
  Clear as ClearIcon,
} from "@mui/icons-material";

const endpointMapping = {
  Notion: "notion",
  Airtable: "airtable",
  Hubspot: "hubspot",
};

export const DataForm = ({ integrationType, credentials }) => {
  const [loadedData, setLoadedData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const endpoint = endpointMapping[integrationType];

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const formData = new FormData();
      formData.append("credentials", JSON.stringify(credentials));
      const response = await axios.post(
        `http://localhost:8000/integrations/${endpoint}/load`,
        formData
      );
      const data = response.data;
      const formattedData = JSON.stringify(data, null, 2);
      setLoadedData(formattedData);
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Paper
      elevation={3}
      sx={{ p: 3, mt: 3, width: "100%", backgroundColor: "#f8f9fa" }}
    >
      <Typography variant="h6" gutterBottom>
        Integration Data
      </Typography>
      <Box display="flex" flexDirection="column" gap={2} width="100%">
        {loading ? (
          <Box display="flex" justifyContent="center" p={3}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Box sx={{ color: "error.main", mb: 2 }}>
            <Typography color="error">{error}</Typography>
            <Button
              variant="outlined"
              color="primary"
              onClick={loadData}
              sx={{ mt: 1 }}
            >
              Retry
            </Button>
          </Box>
        ) : (
          <>
            <TextField
              label="Integration Data"
              value={loadedData || ""}
              multiline
              rows={8}
              InputProps={{
                readOnly: true,
                sx: {
                  fontFamily: "monospace",
                  backgroundColor: "#ffffff",
                },
              }}
              sx={{ width: "100%" }}
            />
            <Box display="flex" gap={1}>
              <Button
                variant="contained"
                onClick={loadData}
              >
                Load
              </Button>
              <Button
                variant="outlined"
                onClick={() => setLoadedData(null)}
              >
                Clear
              </Button>
            </Box>
          </>
        )}
      </Box>
    </Paper>
  );
};
