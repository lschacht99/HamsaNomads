import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {brand} from '../brand';
import {BrandLogo} from './BrandLogo';

export const EndCard: React.FC<{recipe: any; logoSrc?: string; logoFallback?: string}> = ({recipe, logoSrc, logoFallback}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [660, 690], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 70, opacity}}>
    <div style={{width: 820, background: brand.colors.ivoryParchment, color: brand.colors.inkBlack, borderRadius: 34, padding: '34px 42px', fontFamily: brand.fonts.body, fontSize: 36, fontWeight: 800, textAlign: 'center', border: `4px solid ${brand.colors.sand}`, boxShadow: '0 18px 50px rgba(0,0,0,.22)'}}>
      <div style={{display: 'flex', justifyContent: 'center', marginBottom: 24}}><BrandLogo src={logoSrc} fallback={logoFallback} size="medium" /></div>
      {recipe.cta?.text ?? 'Follow Hamsa Nomads for Jewish travel tips'}
    </div>
  </AbsoluteFill>;
};
