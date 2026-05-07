import React from 'react';
import {AbsoluteFill, Video, useCurrentFrame, interpolate, staticFile} from 'remotion';
import {brand} from './brand';
import type {Recipe} from './recipe';
import {IntroCard} from './components/IntroCard';
import {CaptionDialogueBox} from './components/CaptionDialogueBox';
import {WrongVsRightOverlay} from './components/WrongVsRightOverlay';
import {PassportStampOverlay} from './components/PassportStampOverlay';
import {QuestBanner} from './components/QuestBanner';
import {RouteLine} from './components/RouteLine';
import {EndCard} from './components/EndCard';

export const HamsaVideo: React.FC<{inputVideo: string; recipe: Recipe}> = ({inputVideo, recipe}) => {
  const frame = useCurrentFrame();
  const zoom = interpolate(frame, [0, 45, 180], [1.08, 1.02, 1.0], {extrapolateRight: 'clamp'});
  const source = inputVideo.startsWith('http') ? inputVideo : `file://${inputVideo}`;
  return (
    <AbsoluteFill style={{backgroundColor: brand.colors.warmCream, overflow: 'hidden'}}>
      <Video src={source} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${zoom})`}} />
      <RouteLine />
      {recipe.intro_card?.enabled && <IntroCard intro={recipe.intro_card} />}
      <QuestBanner recipe={recipe} />
      <CaptionDialogueBox recipe={recipe} />
      {recipe.overlays?.map((overlay, index) => overlay.type === 'wrong_vs_right' ? <WrongVsRightOverlay key={index} overlay={overlay} /> : null)}
      {recipe.overlays?.map((overlay, index) => overlay.type === 'passport_stamp' ? <PassportStampOverlay key={index} overlay={overlay} /> : null)}
      <EndCard recipe={recipe} />
    </AbsoluteFill>
  );
};
