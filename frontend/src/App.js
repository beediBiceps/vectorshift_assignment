import { IntegrationForm } from "./integration-form";
import { CredentialsProvider } from "./context/CredentialsContext";

function App() {
  return (
    <CredentialsProvider>
      <IntegrationForm />
    </CredentialsProvider>
  );
}

export default App;
