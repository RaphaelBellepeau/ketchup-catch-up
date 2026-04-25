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
import Permissions from "./pages/onboarding/Permissions.tsx";
import Friends from "./pages/groups/Friends.tsx";
import NameGroup from "./pages/groups/NameGroup.tsx";
import FrequencyPage from "./pages/groups/FrequencyPage.tsx";
import WindowPage from "./pages/groups/WindowPage.tsx";
import Negotiating from "./pages/catchup/Negotiating.tsx";
import Proposal from "./pages/catchup/Proposal.tsx";
import Confirmed from "./pages/catchup/Confirmed.tsx";
import Rating from "./pages/feedback/Rating.tsx";
import FeedbackVoice from "./pages/feedback/Voice.tsx";

const queryClient = new QueryClient();

const placeholderRoutes: { path: string; title: string }[] = [
  { path: "/home", title: "Home" },
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
          <Route path="/onboarding/permissions" element={<Permissions />} />
          <Route path="/groups/new/friends" element={<Friends />} />
          <Route path="/groups/new/name" element={<NameGroup />} />
          <Route path="/groups/new/frequency" element={<FrequencyPage />} />
          <Route path="/groups/new/window" element={<WindowPage />} />
          <Route path="/catchup/negotiating" element={<Negotiating />} />
          <Route path="/catchup/proposal" element={<Proposal />} />
          <Route path="/catchup/confirmed" element={<Confirmed />} />
          <Route path="/feedback/rating" element={<Rating />} />
          <Route path="/feedback/voice" element={<FeedbackVoice />} />
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
