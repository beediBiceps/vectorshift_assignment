import React, { createContext, useContext, useState } from "react";

const CredentialsContext = createContext(null);

export const CredentialsProvider = ({ children }) => {
  const [credentials, setCredentials] = useState({});
  const [userInfo, setUserInfo] = useState({ user_id: null, org_id: null });

  const storeIntegrationCredentials = (
    integrationType,
    creds,
    userId,
    orgId
  ) => {
    setCredentials((prev) => ({
      ...prev,
      [integrationType]: {
        ...creds,
        user_id: userId,
        org_id: orgId,
      },
    }));
    setUserInfo({ user_id: userId, org_id: orgId });
  };

  const getIntegrationCredentials = (integrationType) => {
    return credentials[integrationType] || null;
  };

  const clearIntegrationCredentials = (integrationType) => {
    setCredentials((prev) => {
      const newCreds = { ...prev };
      delete newCreds[integrationType];
      return newCreds;
    });
  };

  const value = {
    credentials,
    userInfo,
    storeIntegrationCredentials,
    getIntegrationCredentials,
    clearIntegrationCredentials,
  };

  return (
    <CredentialsContext.Provider value={value}>
      {children}
    </CredentialsContext.Provider>
  );
};

export const useCredentials = () => {
  const context = useContext(CredentialsContext);
  if (!context) {
    throw new Error("useCredentials must be used within a CredentialsProvider");
  }
  return context;
};
