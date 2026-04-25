import { create } from "zustand";

export type Frequency = "one-shot" | "recurring";
export type Vibe = "dinner" | "drinks" | "brunch" | "activity";

interface GroupCreationState {
  selectedFriendIds: string[];
  name: string;
  frequency: Frequency;
  fromDate: string; // human-readable for now
  untilDate: string;
  vibe: Vibe;

  toggleFriend: (id: string) => void;
  setName: (n: string) => void;
  setFrequency: (f: Frequency) => void;
  setVibe: (v: Vibe) => void;
  setWindow: (from: string, until: string) => void;
  reset: () => void;
}

const defaults = {
  selectedFriendIds: [] as string[],
  name: "The classics",
  frequency: "one-shot" as Frequency,
  fromDate: "Mon 27 Apr",
  untilDate: "Sun 11 May",
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
