import { useState } from "react";
import { Box, Autocomplete, TextField } from "@mui/material";
import { AirtableIntegration } from "./integrations/airtable";
import { NotionIntegration } from "./integrations/notion";
import { HubspotIntegration } from "./integrations/hubspot";
import { DataForm } from "./data-form";
import { useCredentials } from "./context/CredentialsContext";

const integrationMapping = {
  Notion: NotionIntegration,
  Airtable: AirtableIntegration,
  Hubspot: HubspotIntegration,
};

export const IntegrationForm = () => {
  const [user, setUser] = useState("TestUser");
  const [org, setOrg] = useState("TestOrg");
  const [currType, setCurrType] = useState(null);
  const { credentials } = useCredentials();
  const CurrIntegration = integrationMapping[currType];

  return (
    <Box
      display="flex"
      justifyContent="center"
      alignItems="center"
      flexDirection="column"
      sx={{ width: "100%" }}
    >
      <Box display="flex" flexDirection="column">
        <TextField
          label="User"
          value={user}
          onChange={(e) => setUser(e.target.value)}
          sx={{ mt: 2 }}
        />
        <TextField
          label="Organization"
          value={org}
          onChange={(e) => setOrg(e.target.value)}
          sx={{ mt: 2 }}
        />
        <Autocomplete
          id="integration-type"
          options={Object.keys(integrationMapping)}
          sx={{ width: 300, mt: 2 }}
          renderInput={(params) => (
            <TextField {...params} label="Integration Type" />
          )}
          onChange={(e, value) => setCurrType(value)}
          value={currType}
        />
      </Box>
      {currType && (
        <Box>
          <CurrIntegration user={user} org={org} />
          {credentials[currType] && (
            <Box sx={{ mt: 2 }}>
              <DataForm
                integrationType={currType}
                credentials={credentials[currType]}
              />
            </Box>
          )}
        </Box>
      )}
    </Box>
  );
};
