import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {brand} from '../brand';
import {BrandLogo} from './BrandLogo';

export const QuestBanner: React.FC<{recipe: any; logoSrc?: string; logoFallback?: string}> = ({recipe, logoSrc, logoFallback}) => {
  const frame = useCurrentFrame();
  const show = recipe.style?.name === 'video_game_dialogue' || recipe.style?.name === 'game';
  const y = interpolate(frame, [45, 58], [-160, 70], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const scale = interpolate(frame, [45, 60], [0.96, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  if (!show) return null;
  return <AbsoluteFill style={{alignItems: 'center'}}>
    <div style={{marginTop: y, transform: `scale(${scale})`, background: brand.colors.warmCream, color: brand.colors.inkBlack, padding: '16px 34px', borderRadius: 999, fontFamily: brand.fonts.body, fontSize: 36, fontWeight: 900, border: `4px solid ${brand.colors.clay}`, display: 'flex', gap: 18, alignItems: 'center', boxShadow: '0 14px 32px rgba(0,0,0,.22)'}}>
      <BrandLogo src={logoSrc} fallback={logoFallback} size="small" opacity={0.9} />
      <span style={{color: brand.colors.oliveSage}}>QUEST UNLOCKED</span>
    </div>
  </AbsoluteFill>;
};
