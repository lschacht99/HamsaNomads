import React from 'react';
import {AbsoluteFill} from 'remotion';
import {brand} from '../brand';

export const RouteLine: React.FC = () => <AbsoluteFill style={{pointerEvents: 'none'}}>
  <svg width="1080" height="1920" viewBox="0 0 1080 1920" style={{opacity: .55}}>
    <path d="M120 1650 C260 1440, 160 1180, 430 1030 S820 760, 710 560 S500 300, 870 180" fill="none" stroke={brand.colors.clay} strokeWidth="8" strokeDasharray="20 18" strokeLinecap="round" />
  </svg>
</AbsoluteFill>;
