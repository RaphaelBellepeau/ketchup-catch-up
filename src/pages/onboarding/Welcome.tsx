import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";
import { BottleLogo } from "@/components/BottleLogo";

const Welcome = () => {
  const navigate = useNavigate();
  const [phone, setPhone] = useState("");

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmed = phone.trim();
    if (!trimmed) return;
    navigate("/onboarding/sms", { state: { phone: trimmed } });
  };

  return (
    <Layout className="bg-cream">
      <div className="relative flex-1 flex flex-col bg-cream overflow-hidden">
        {/* Decorative blobs */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -top-20 -right-20 w-64 h-64 rounded-full bg-coral opacity-50"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-10 -left-24 w-64 h-64 rounded-full bg-mint opacity-50"
        />

        {/* Content */}
        <div className="relative flex-1 flex flex-col px-6 pt-8 pb-8">
          <div className="flex-1 flex flex-col items-center justify-center text-center gap-4">
            <BottleLogo size={96} />
            <h1 className="text-h1 text-ketchup-red lowercase">ketchup</h1>
            <p className="text-body text-charcoal max-w-[280px]">
              your agent talks to your friends'
              <br />
              so you actually see them
            </p>
          </div>

          <form onSubmit={handleSubmit} className="relative flex flex-col gap-3">
            <Input
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              placeholder="+33 6 12 34 56 78"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              aria-label="Phone number"
            />
            <Button type="submit" variant="primary" size="lg" fullWidth>
              Get a call from my agent
            </Button>
            <p className="text-meta normal-case tracking-normal text-slate text-center mt-1">
              No password. Just pick up.
            </p>
          </form>
        </div>
      </div>
    </Layout>
  );
};

export default Welcome;
