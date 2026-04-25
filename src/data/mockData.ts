// Mock data for the Ketchup app foundation.
// All ids are stable strings so they can be referenced across screens later.

export type User = {
  id: string;
  name: string;
  avatarColor: string; // tailwind brand token name
  initials: string;
  phone: string;
};

export type Group = {
  id: string;
  name: string;
  memberIds: string[];
  frequency: "weekly" | "biweekly" | "monthly";
  window: { day: string; start: string; end: string };
  createdAt: string;
};

export type CatchupStatus = "negotiating" | "proposed" | "confirmed" | "completed";

export type Catchup = {
  id: string;
  groupId: string;
  status: CatchupStatus;
  proposal: {
    date: string;
    time: string;
    venue: string;
  };
  participantIds: string[];
};

export type AgentMessage = {
  id: string;
  catchupId: string;
  authorId: string; // user id or "agent"
  text: string;
  timestamp: string;
};

export type Memory = {
  id: string;
  groupId: string;
  title: string;
  summary: string;
  date: string;
  emoji: string;
};

export type Feedback = {
  id: string;
  catchupId: string;
  userId: string;
  rating: 1 | 2 | 3 | 4 | 5;
  voiceNoteUrl?: string;
  note?: string;
};

export const users: Record<string, User> = {
  you: {
    id: "you",
    name: "You",
    avatarColor: "coral",
    initials: "Y",
    phone: "+1 555 010 0001",
  },
  marie: {
    id: "marie",
    name: "Marie",
    avatarColor: "lavender",
    initials: "M",
    phone: "+1 555 010 0002",
  },
  tom: {
    id: "tom",
    name: "Tom",
    avatarColor: "mint",
    initials: "T",
    phone: "+1 555 010 0003",
  },
};

export const exampleGroup: Group = {
  id: "group-1",
  name: "Sunday Crew",
  memberIds: ["you", "marie", "tom"],
  frequency: "biweekly",
  window: { day: "Sunday", start: "11:00", end: "15:00" },
  createdAt: "2025-04-01T10:00:00Z",
};

export const exampleCatchup: Catchup = {
  id: "catchup-1",
  groupId: "group-1",
  status: "proposed",
  proposal: {
    date: "Sun, Apr 27",
    time: "12:30 PM",
    venue: "Maple & Oak Café",
  },
  participantIds: ["you", "marie", "tom"],
};

export const agentMessages: AgentMessage[] = [
  {
    id: "m1",
    catchupId: "catchup-1",
    authorId: "agent",
    text: "Hey! Looking for a Sunday brunch slot that works for all three of you.",
    timestamp: "2025-04-22T09:00:00Z",
  },
  {
    id: "m2",
    catchupId: "catchup-1",
    authorId: "marie",
    text: "Sunday after 12 works great for me 🥞",
    timestamp: "2025-04-22T09:04:00Z",
  },
  {
    id: "m3",
    catchupId: "catchup-1",
    authorId: "tom",
    text: "I can do 12:30 onwards.",
    timestamp: "2025-04-22T09:11:00Z",
  },
  {
    id: "m4",
    catchupId: "catchup-1",
    authorId: "agent",
    text: "Locked in: Sun 12:30 PM at Maple & Oak Café ✅",
    timestamp: "2025-04-22T09:15:00Z",
  },
];

export const memories: Memory[] = [
  {
    id: "mem-1",
    groupId: "group-1",
    title: "Pancake Sunday",
    summary: "Marie tried the matcha stack, Tom won the coffee bet.",
    date: "2025-03-30",
    emoji: "🥞",
  },
  {
    id: "mem-2",
    groupId: "group-1",
    title: "Park picnic",
    summary: "Spontaneous frisbee, golden hour photos.",
    date: "2025-03-16",
    emoji: "🧺",
  },
];

export type NegotiationSender = "you" | "marie" | "tom" | "system";

export type NegotiationMessage = {
  id: string;
  sender: NegotiationSender;
  content: string;
  delay_ms: number;
};

export const negotiationMessages: NegotiationMessage[] = [
  { id: "n1", sender: "you", content: "Looking for dinner, 27 Apr – 11 May", delay_ms: 600 },
  { id: "n2", sender: "system", content: "Searching venues near Bastille…", delay_ms: 900 },
  { id: "n3", sender: "marie", content: "Thu 1 May or Tue 6 May. She likes early dinners.", delay_ms: 1400 },
  { id: "n4", sender: "tom", content: "Calling now…", delay_ms: 1200 },
  { id: "n5", sender: "you", content: "Searching venues near Bastille…", delay_ms: 1100 },
  { id: "n6", sender: "system", content: "Tavily · 4 places found", delay_ms: 900 },
];

export const feedbackSamples: Feedback[] = [
  {
    id: "fb-1",
    catchupId: "catchup-1",
    userId: "you",
    rating: 5,
    note: "Best brunch in months.",
  },
  {
    id: "fb-2",
    catchupId: "catchup-1",
    userId: "marie",
    rating: 4,
  },
];
