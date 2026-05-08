import React from 'react';
import {staticFile} from 'remotion';
import {brand} from '../brand';

export const BrandLogo: React.FC<{src?: string; fallback?: string; size?: 'small' | 'medium' | 'large'; opacity?: number}> = ({src, fallback = 'Hamsa Nomads', size = 'small', opacity = 1}) => {
  const widths = {small: 150, medium: 230, large: 320};
  if (src) {
    return <img src={staticFile(src)} style={{width: widths[size], height: 'auto', objectFit: 'contain', opacity, filter: 'drop-shadow(0 6px 16px rgba(17,17,17,.12))'}} />;
  }
  return <div style={{fontFamily: brand.fonts.headline, fontSize: size === 'large' ? 54 : size === 'medium' ? 42 : 30, color: brand.colors.inkBlack, opacity, letterSpacing: 1.5, fontWeight: 700}}>{fallback}</div>;
};
