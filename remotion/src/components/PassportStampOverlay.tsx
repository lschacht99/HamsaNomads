import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {brand} from '../brand';

export const PassportStampOverlay: React.FC<{overlay: any}> = ({overlay}) => {
  const frame = useCurrentFrame();
  const start = Math.round((overlay.start_sec ?? 3.2) * 30);
  const scale = interpolate(frame, [start, start + 8], [1.55, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const opacity = interpolate(frame, [start, start + 4, start + 42, start + 60], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', opacity}}>
    <div style={{transform: `rotate(-8deg) scale(${scale})`, color: brand.colors.clay, borderRadius: 22, padding: '24px 34px', fontFamily: brand.fonts.body, fontSize: 52, fontWeight: 950, letterSpacing: 2, textTransform: 'uppercase', background: 'rgba(236,231,219,.74)', boxShadow: `inset 0 0 0 5px ${brand.colors.clay}, inset 0 0 0 12px rgba(220,199,161,.55), 0 16px 36px rgba(17,17,17,.20)`}}>
      ✦ {overlay.text ?? 'PASSPORT STAMP'} ✦
    </div>
  </AbsoluteFill>;
};
