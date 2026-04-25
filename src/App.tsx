import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import Index from "./pages/Index.tsx";
import NotFound from "./pages/NotFound.tsx";
import PlaceholderPage from "./pages/PlaceholderPage.tsx";
import Welcome from "./pages/onboarding/Welcome.tsx";
import Sms from "./pages/onboarding/Sms.tsx";
import VoiceCall from "./pages/onboarding/VoiceCall.tsx";

const queryClient = new QueryClient();

const placeholderRoutes: { path: string; title: string }[] = [
  { path: "/home", title: "Home" },
  { path: "/onboarding/permissions", title: "Permissions" },
  { path: "/groups/new/friends", title: "Add friends" },
  { path: "/groups/new/name", title: "Name your group" },
  { path: "/groups/new/frequency", title: "How often?" },
  { path: "/groups/new/window", title: "Pick a window" },
  { path: "/catchup/negotiating", title: "Negotiating" },
  { path: "/catchup/proposal", title: "Proposal" },
  { path: "/catchup/confirmed", title: "Confirmed" },
  { path: "/feedback/rating", title: "Rate the catchup" },
  { path: "/feedback/voice", title: "Leave a voice note" },
  { path: "/memory", title: "Memory" },
];

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/onboarding/welcome" element={<Welcome />} />
          <Route path="/onboarding/sms" element={<Sms />} />
          <Route path="/onboarding/voice-call" element={<VoiceCall />} />
          {placeholderRoutes.map((r) => (
            <Route
              key={r.path}
              path={r.path}
              element={<PlaceholderPage title={r.title} path={r.path} />}
            />
          ))}
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
