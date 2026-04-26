import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { RequireAuth } from "@/components/RequireAuth";
import { RequireOnboarded } from "@/components/RequireOnboarded";
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

          {/* Public — Welcome and Sms self-redirect when a session is present. */}
          <Route path="/onboarding/welcome" element={<Welcome />} />
          <Route path="/onboarding/sms" element={<Sms />} />

          {/* Voice onboarding — needs a session, but NOT yet completed onboarding. */}
          <Route
            path="/onboarding/voice-call"
            element={
              <RequireAuth>
                <VoiceCall />
              </RequireAuth>
            }
          />

          {/* Everything below requires onboarded_at to be set on the backend. */}
          <Route
            path="/onboarding/permissions"
            element={
              <RequireOnboarded>
                <Permissions />
              </RequireOnboarded>
            }
          />
          <Route
            path="/groups/new/friends"
            element={
              <RequireOnboarded>
                <Friends />
              </RequireOnboarded>
            }
          />
          <Route
            path="/groups/new/name"
            element={
              <RequireOnboarded>
                <NameGroup />
              </RequireOnboarded>
            }
          />
          <Route
            path="/groups/new/frequency"
            element={
              <RequireOnboarded>
                <FrequencyPage />
              </RequireOnboarded>
            }
          />
          <Route
            path="/groups/new/window"
            element={
              <RequireOnboarded>
                <WindowPage />
              </RequireOnboarded>
            }
          />
          <Route
            path="/catchup/negotiating"
            element={
              <RequireOnboarded>
                <Negotiating />
              </RequireOnboarded>
            }
          />
          <Route
            path="/catchup/proposal"
            element={
              <RequireOnboarded>
                <Proposal />
              </RequireOnboarded>
            }
          />
          <Route
            path="/catchup/confirmed"
            element={
              <RequireOnboarded>
                <Confirmed />
              </RequireOnboarded>
            }
          />
          <Route
            path="/feedback/rating"
            element={
              <RequireOnboarded>
                <Rating />
              </RequireOnboarded>
            }
          />
          <Route
            path="/feedback/voice"
            element={
              <RequireOnboarded>
                <FeedbackVoice />
              </RequireOnboarded>
            }
          />
          <Route
            path="/home"
            element={
              <RequireOnboarded>
                <Home />
              </RequireOnboarded>
            }
          />
          <Route
            path="/memory"
            element={
              <RequireOnboarded>
                <Memory />
              </RequireOnboarded>
            }
          />

          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
