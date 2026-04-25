// Friend list shown in /groups/new/friends.
// `onKetchup` means the user already has the app — others get an SMS invite.

export type Friend = {
  id: string;
  name: string;
  initials: string;
  avatarColor: string;
  onKetchup: boolean;
};

export const friends: Friend[] = [
  { id: "marie", name: "Marie A.", initials: "MA", avatarColor: "mint", onKetchup: true },
  { id: "tom", name: "Tom O.", initials: "TO", avatarColor: "sunshine", onKetchup: false },
  { id: "lea", name: "Léa B.", initials: "LE", avatarColor: "lavender", onKetchup: false },
  { id: "romain", name: "Romain C.", initials: "RO", avatarColor: "sky", onKetchup: false },
];

export const suggestedGroupNames = ["The classics", "Bordeaux crew", "EFREI gang"];
