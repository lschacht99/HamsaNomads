import React from 'react';
import {AbsoluteFill, useCurrentFrame, interpolate} from 'remotion';
import {brand} from '../brand';

export const WrongVsRightOverlay: React.FC<{overlay: any}> = ({overlay}) => {
  const frame = useCurrentFrame();
  const start = Math.round((overlay.start_sec ?? 2) * 30);
  const opacity = interpolate(frame, [start, start + 8, start + 85, start + 95], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{justifyContent: 'center', padding: 86, opacity}}>
    <div style={{fontFamily: brand.fonts.body, fontSize: 52, fontWeight: 900, background: brand.colors.ivoryParchment, padding: 28, borderRadius: 24}}>
      <div style={{color: brand.colors.clay}}>✕ {overlay.wrong ?? 'WRONG WORD'}</div>
      <div style={{height: 3, background: brand.colors.sand, margin: '20px 0'}} />
      <div style={{color: brand.colors.oliveSage}}>✓ {overlay.right ?? 'LOCAL TIP'}</div>
    </div>
  </AbsoluteFill>;
};
