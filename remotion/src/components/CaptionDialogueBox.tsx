import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {brand} from '../brand';

export const CaptionDialogueBox: React.FC<{recipe: any}> = ({recipe}) => {
  const frame = useCurrentFrame();
  const y = interpolate(frame % 90, [0, 10], [36, 0], {extrapolateRight: 'clamp'});
  const text = recipe.caption_system?.highlight_keywords?.length ? recipe.caption_system.highlight_keywords.join(' · ') : recipe.intro_card?.headline;
  return <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 210}}>
    <div style={{transform: `translateY(${y}px)`, maxWidth: 880, background: brand.colors.warmCream, color: brand.colors.inkBlack, border: `4px solid ${brand.colors.oliveSage}`, borderRadius: 28, padding: '32px 42px', fontFamily: brand.fonts.body, fontSize: 54, fontWeight: 800, textAlign: 'center'}}>{text}</div>
  </AbsoluteFill>;
};
