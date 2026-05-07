import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {brand} from '../brand';

export const QuestBanner: React.FC<{recipe: any}> = ({recipe}) => {
  const frame = useCurrentFrame();
  const show = recipe.style?.name === 'video_game_dialogue' || recipe.style?.name === 'game';
  const y = interpolate(frame, [45, 58], [-160, 70], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  if (!show) return null;
  return <AbsoluteFill style={{alignItems: 'center'}}><div style={{marginTop: y, background: brand.colors.oliveSage, color: brand.colors.warmCream, padding: '18px 44px', borderRadius: 999, fontFamily: brand.fonts.body, fontSize: 38, fontWeight: 900}}>QUEST BANNER REVEAL</div></AbsoluteFill>;
};
