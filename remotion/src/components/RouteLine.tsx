import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {brand} from '../brand';

export const RouteLine: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 25, 160, 220], [0, .42, .34, .18], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return <AbsoluteFill style={{pointerEvents: 'none'}}>
    <svg width="1080" height="1920" viewBox="0 0 1080 1920" style={{opacity}}>
      <path d="M116 1648 C252 1438, 174 1206, 428 1036 S816 774, 716 562 S512 314, 872 182" fill="none" stroke={brand.colors.clay} strokeWidth="7" strokeDasharray="18 18" strokeLinecap="round" />
      <path d="M116 1648 C252 1438, 174 1206, 428 1036 S816 774, 716 562 S512 314, 872 182" fill="none" stroke={brand.colors.warmCream} strokeWidth="2" strokeDasharray="4 32" strokeLinecap="round" opacity=".8" />
      <circle cx="116" cy="1648" r="10" fill={brand.colors.oliveSage} />
      <circle cx="872" cy="182" r="12" fill={brand.colors.clay} />
    </svg>
  </AbsoluteFill>;
};
