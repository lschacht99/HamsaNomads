import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {brand} from '../brand';

export const PassportStampOverlay: React.FC<{overlay: any}> = ({overlay}) => {
  const frame = useCurrentFrame();
  const start = Math.round((overlay.start_sec ?? 3.2) * 30);
  const scale = interpolate(frame, [start, start + 7], [2.2, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const opacity = interpolate(frame, [start, start + 4, start + 30], [0, 1, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', opacity}}>
    <div style={{transform: `rotate(-10deg) scale(${scale})`, border: `8px solid ${brand.colors.clay}`, color: brand.colors.clay, borderRadius: 18, padding: 28, fontFamily: brand.fonts.body, fontSize: 58, fontWeight: 900}}>{overlay.text ?? 'PASSPORT STAMP'}</div>
  </AbsoluteFill>;
};
