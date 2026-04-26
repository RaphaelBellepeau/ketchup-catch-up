import { create } from "zustand";

export type Frequency = "one-shot" | "recurring";
export type Vibe = "dinner" | "drinks" | "brunch" | "activity";

interface GroupCreationState {
  selectedFriendIds: string[];
  name: string;
  frequency: Frequency;
  /** Inclusive start of the meet-up window. */
  fromDate: Date | null;
  /** Inclusive end of the meet-up window. */
  untilDate: Date | null;
  vibe: Vibe;

  toggleFriend: (id: string) => void;
  setName: (n: string) => void;
  setFrequency: (f: Frequency) => void;
  setVibe: (v: Vibe) => void;
  setWindow: (from: Date | null, until: Date | null) => void;
  reset: () => void;
}

function defaultRange(): { fromDate: Date; untilDate: Date } {
  const now = new Date();
  const from = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const until = new Date(from);
  until.setDate(until.getDate() + 14);
  return { fromDate: from, untilDate: until };
}

const { fromDate: defaultFrom, untilDate: defaultUntil } = defaultRange();
const defaults = {
  selectedFriendIds: [] as string[],
  name: "The classics",
  frequency: "one-shot" as Frequency,
  fromDate: defaultFrom as Date | null,
  untilDate: defaultUntil as Date | null,
  vibe: "dinner" as Vibe,
};

export const useGroupCreation = create<GroupCreationState>((set) => ({
  ...defaults,
  toggleFriend: (id) =>
    set((s) => ({
      selectedFriendIds: s.selectedFriendIds.includes(id)
        ? s.selectedFriendIds.filter((x) => x !== id)
        : [...s.selectedFriendIds, id],
    })),
  setName: (name) => set({ name }),
  setFrequency: (frequency) => set({ frequency }),
  setVibe: (vibe) => set({ vibe }),
  setWindow: (fromDate, untilDate) => set({ fromDate, untilDate }),
  reset: () => set({ ...defaults }),
}));
