import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {brand} from '../brand';

export const IntroCard: React.FC<{intro: any}> = ({intro}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 10, 55, 70], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', opacity}}>
    <div style={{background: brand.colors.ivoryParchment, color: brand.colors.inkBlack, width: 860, padding: 54, borderRadius: 34, border: `5px solid ${brand.colors.clay}`, boxShadow: '0 20px 60px rgba(0,0,0,.28)'}}>
      <div style={{fontFamily: brand.fonts.body, color: brand.colors.oliveSage, letterSpacing: 7, fontWeight: 800}}>{intro.label}</div>
      <div style={{fontFamily: brand.fonts.headline, fontSize: 76, lineHeight: 1.02, marginTop: 24}}>{intro.headline}</div>
      <div style={{fontFamily: brand.fonts.handwritten, fontSize: 42, color: brand.colors.clay, marginTop: 18}}>{intro.subheadline}</div>
    </div>
  </AbsoluteFill>;
};
