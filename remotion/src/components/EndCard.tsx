import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {brand} from '../brand';

export const EndCard: React.FC<{recipe: any}> = ({recipe}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [660, 690], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 70, opacity}}>
    <div style={{background: brand.colors.ivoryParchment, color: brand.colors.inkBlack, borderRadius: 26, padding: '24px 38px', fontFamily: brand.fonts.body, fontSize: 36, fontWeight: 800}}>{recipe.cta?.text ?? 'Follow Hamsa Nomads for Jewish travel tips'}</div>
  </AbsoluteFill>;
};
