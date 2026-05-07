import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {HamsaVideo} from './HamsaVideo';

export const RemotionRoot: React.FC = () => (
  <Composition
    id="HamsaVideo"
    component={HamsaVideo}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={750}
    defaultProps={{inputVideo: '../input/test.mp4', recipe: {project_title: 'Hamsa Nomads', renderer: 'remotion', input_video: {src: '', crop: 'vertical_center_face'}, style: {name: 'hamsa-clean', tone: 'warm'}, intro_card: {enabled: true, duration_sec: 1.8, label: 'HAMSA NOMADS', headline: 'Jewish travel note', subheadline: 'Warm and grounded'}, caption_system: {highlight_keywords: []}, overlays: [], transitions: [], section_cards: [], freeze_frames: [], thumbnail: {headline: 'Jewish travel note'}, cta: {enabled: true, start_sec: 22, text: 'Follow Hamsa Nomads for Jewish travel tips'}}}}
  />
);

registerRoot(RemotionRoot);
