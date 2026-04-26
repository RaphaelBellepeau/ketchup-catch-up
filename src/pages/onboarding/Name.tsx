import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Layout } from "@/components/Layout";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { useProfile } from "@/hooks/useProfile";
import { api } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

const Name = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { session, profile, isOnboarded, loading } = useProfile();

  const [name, setName] = useState("");

  // Pre-fill if a name is already on the profile (rare but possible if the
  // user reopens this screen after setting it — they'd get bounced anyway).
  useEffect(() => {
    if (profile?.name && !name) setName(profile.name);
  }, [profile?.name, name]);

  // Forward the user to the right step if this screen doesn't apply.
  useEffect(() => {
    if (loading || !session) return;
    if (isOnboarded) {
      navigate("/onboarding/permissions", { replace: true });
      return;
    }
    if (profile?.name?.trim()) {
      navigate("/onboarding/voice-call", { replace: true });
    }
  }, [loading, session, profile?.name, isOnboarded, navigate]);

  const mutation = useMutation({
    mutationFn: (newName: string) =>
      api<{ id: string; name: string }>("/users/me", {
        method: "PATCH",
        json: { name: newName },
      }),
    onSuccess: async () => {
      // Refresh the cached profile so the redirect chain sees the new name.
      await queryClient.invalidateQueries({ queryKey: ["users", "me"] });
      navigate("/onboarding/voice-call", { replace: true });
    },
    onError: (err) => {
      const message = err instanceof Error ? err.message : "Could not save name";
      toast({ title: "Couldn't save your name", description: message, variant: "destructive" });
    },
  });

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    mutation.mutate(trimmed);
  };

  return (
    <Layout>
      <div className="flex-1 flex flex-col px-6 pt-4 pb-6">
        <div className="text-meta text-slate">STEP 2 OF 4</div>
        <h1 className="text-h1 text-navy mt-2">What's your name?</h1>
        <p className="text-body text-slate mt-2">
          Your agent will use it when chatting with your friends'.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-3">
          <Input
            type="text"
            autoComplete="given-name"
            placeholder="Léa Martin"
            value={name}
            onChange={(e) => setName(e.target.value)}
            aria-label="Your name"
            autoFocus
          />
        </form>

        <div className="flex-1" />

        <Button
          type="submit"
          variant="primary"
          size="lg"
          fullWidth
          disabled={!name.trim() || mutation.isPending}
          onClick={() => mutation.mutate(name.trim())}
        >
          {mutation.isPending ? "Saving…" : "Continue"}
        </Button>
      </div>
    </Layout>
  );
};

export default Name;
