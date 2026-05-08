import React from 'react';
import {AbsoluteFill, useCurrentFrame, interpolate} from 'remotion';
import {brand} from '../brand';

export const WrongVsRightOverlay: React.FC<{overlay: any}> = ({overlay}) => {
  const frame = useCurrentFrame();
  const start = Math.round((overlay.start_sec ?? 2) * 30);
  const opacity = interpolate(frame, [start, start + 10, start + 85, start + 98], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const y = interpolate(frame, [start, start + 12], [42, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{justifyContent: 'center', padding: 86, opacity}}>
    <div style={{transform: `translateY(${y}px)`, fontFamily: brand.fonts.body, background: `linear-gradient(180deg, ${brand.colors.warmCream}, ${brand.colors.ivoryParchment})`, padding: 34, borderRadius: 32, border: `4px solid ${brand.colors.sand}`, boxShadow: '0 18px 55px rgba(17,17,17,.25)'}}>
      <div style={{fontSize: 24, letterSpacing: 5, fontWeight: 900, color: brand.colors.clay, marginBottom: 20}}>WRONG VS RIGHT</div>
      <div style={{fontSize: 48, fontWeight: 900, color: brand.colors.clay, lineHeight: 1.15}}>❌ {overlay.wrong ?? 'Don’t ask: Cholov Yisroel'}</div>
      <div style={{height: 2, background: brand.colors.sand, margin: '24px 0'}} />
      <div style={{fontSize: 52, fontWeight: 950, color: brand.colors.oliveSage, lineHeight: 1.15}}>✅ {overlay.right ?? 'Ask: Chamour'}</div>
    </div>
  </AbsoluteFill>;
};
