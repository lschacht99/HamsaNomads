export type Overlay = {type: string; start_sec?: number; duration_sec?: number; text?: string; wrong?: string; right?: string};
export type Recipe = {
  project_title: string;
  renderer: string;
  input_video: {src: string; crop: string};
  style: {name: string; tone: string};
  intro_card: {enabled: boolean; duration_sec: number; label: string; headline: string; subheadline: string};
  caption_system: {highlight_keywords: string[]};
  overlays: Overlay[];
  transitions: Overlay[];
  section_cards: {title: string; start_sec: number; duration_sec: number}[];
  freeze_frames: {time_sec: number; duration_sec: number; overlay: string}[];
  thumbnail: {headline: string};
  cta: {enabled: boolean; start_sec: number; text: string};
};
