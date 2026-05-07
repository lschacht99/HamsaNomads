export type Caption = {
  start: number;
  end: number;
  text: string;
};

export type Overlay = Caption & {
  kind?: string;
};

export type IntroCard = {
  enabled?: boolean;
  title?: string;
  label?: string;
  duration_seconds?: number;
};

export type Recipe = {
  project_title: string;
  video_goal?: string;
  style: string;
  tone?: string;
  brand?: string;
  renderer?: 'ffmpeg' | 'remotion';
  intro_card?: IntroCard;
  captions?: Caption[];
  overlays?: Overlay[];
  keyword_highlights?: string[];
  thumbnail?: {timestamp?: string; title?: string};
  cta?: {text?: string; start?: number | null};
  output_settings?: {
    width?: number;
    height?: number;
    video_name?: string;
    thumbnail_name?: string;
    duration_seconds?: number;
  };
};

export type HamsaVideoProps = {
  recipe: Recipe;
  videoSrc: string;
};
