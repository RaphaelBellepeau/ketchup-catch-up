import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import SplashScreen from "./components/SplashScreen.tsx";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <SplashScreen>
    <App />
  </SplashScreen>
);
