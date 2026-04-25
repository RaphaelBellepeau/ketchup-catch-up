import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { RequireAuth } from "@/components/RequireAuth";
import NotFound from "./pages/NotFound.tsx";
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
import Home from "./pages/Home.tsx";
import Memory from "./pages/Memory.tsx";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/onboarding/welcome" replace />} />
          <Route path="/onboarding/welcome" element={<Welcome />} />
          <Route path="/onboarding/sms" element={<Sms />} />
          <Route path="/onboarding/voice-call" element={<RequireAuth><VoiceCall /></RequireAuth>} />
          <Route path="/onboarding/permissions" element={<RequireAuth><Permissions /></RequireAuth>} />
          <Route path="/groups/new/friends" element={<RequireAuth><Friends /></RequireAuth>} />
          <Route path="/groups/new/name" element={<RequireAuth><NameGroup /></RequireAuth>} />
          <Route path="/groups/new/frequency" element={<RequireAuth><FrequencyPage /></RequireAuth>} />
          <Route path="/groups/new/window" element={<RequireAuth><WindowPage /></RequireAuth>} />
          <Route path="/catchup/negotiating" element={<RequireAuth><Negotiating /></RequireAuth>} />
          <Route path="/catchup/proposal" element={<RequireAuth><Proposal /></RequireAuth>} />
          <Route path="/catchup/confirmed" element={<RequireAuth><Confirmed /></RequireAuth>} />
          <Route path="/feedback/rating" element={<RequireAuth><Rating /></RequireAuth>} />
          <Route path="/feedback/voice" element={<RequireAuth><FeedbackVoice /></RequireAuth>} />
          <Route path="/home" element={<RequireAuth><Home /></RequireAuth>} />
          <Route path="/memory" element={<RequireAuth><Memory /></RequireAuth>} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
