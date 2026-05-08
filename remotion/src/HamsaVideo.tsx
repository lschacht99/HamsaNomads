import React from 'react';
import {AbsoluteFill, OffthreadVideo, useCurrentFrame, interpolate, staticFile} from 'remotion';
import {brand} from './brand';
import type {Recipe} from './recipe';
import {IntroCard} from './components/IntroCard';
import {CaptionDialogueBox} from './components/CaptionDialogueBox';
import {WrongVsRightOverlay} from './components/WrongVsRightOverlay';
import {PassportStampOverlay} from './components/PassportStampOverlay';
import {QuestBanner} from './components/QuestBanner';
import {RouteLine} from './components/RouteLine';
import {EndCard} from './components/EndCard';
import {BrandLogo} from './components/BrandLogo';

export const HamsaVideo: React.FC<{inputVideoSrc: string; recipe: Recipe; logoSrc?: string; logoFallback?: string}> = ({inputVideoSrc, recipe, logoSrc, logoFallback}) => {
  const frame = useCurrentFrame();
  const zoom = interpolate(frame, [0, 45, 180], [1.06, 1.025, 1.0], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{backgroundColor: brand.colors.warmCream, overflow: 'hidden'}}>
      <OffthreadVideo src={staticFile(inputVideoSrc)} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${zoom})`, filter: 'contrast(1.03) saturate(0.94)'}} />
      <AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(17,17,17,.10), transparent 24%, transparent 72%, rgba(17,17,17,.22))'}} />
      <RouteLine />
      {recipe.logo?.watermark && <AbsoluteFill style={{alignItems: 'flex-end', justifyContent: 'flex-end', padding: 44, opacity: .34}}><BrandLogo src={logoSrc} fallback={logoFallback} size="small" /></AbsoluteFill>}
      {recipe.intro_card?.enabled && <IntroCard intro={recipe.intro_card} beatMap={recipe.beat_map} logoSrc={logoSrc} logoFallback={logoFallback} />}
      <QuestBanner recipe={recipe} logoSrc={logoSrc} logoFallback={logoFallback} />
      <CaptionDialogueBox recipe={recipe} />
      {recipe.overlays?.map((overlay, index) => overlay.type === 'wrong_vs_right' ? <WrongVsRightOverlay key={index} overlay={overlay} /> : null)}
      {recipe.overlays?.map((overlay, index) => overlay.type === 'passport_stamp' ? <PassportStampOverlay key={index} overlay={overlay} /> : null)}
      <EndCard recipe={recipe} logoSrc={logoSrc} logoFallback={logoFallback} />
    </AbsoluteFill>
  );
};
