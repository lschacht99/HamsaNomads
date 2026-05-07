import React from 'react';
import {brand} from '../brand';

export const BrandLogo: React.FC<{src?: string; fallback?: string; size?: 'small' | 'medium' | 'large'; opacity?: number}> = ({src, fallback = 'Hamsa Nomads', size = 'small', opacity = 1}) => {
  const widths = {small: 150, medium: 230, large: 320};
  if (src) {
    return <img src={src} style={{width: widths[size], height: 'auto', objectFit: 'contain', opacity}} />;
  }
  return <div style={{fontFamily: brand.fonts.headline, fontSize: size === 'large' ? 54 : size === 'medium' ? 42 : 30, color: brand.colors.inkBlack, opacity, letterSpacing: 1.5, fontWeight: 700}}>{fallback}</div>;
};
