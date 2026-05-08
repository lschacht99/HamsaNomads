import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {brand} from '../brand';
import {BrandLogo} from './BrandLogo';

export const IntroCard: React.FC<{intro: any; beatMap?: any[]; logoSrc?: string; logoFallback?: string}> = ({intro, beatMap = [], logoSrc, logoFallback}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const hookBeat = beatMap.find((beat: any) => beat.purpose === 'hook' || beat.visual_action === 'intro_overlay');
  const startFrame = Math.round(Number(hookBeat?.start_sec ?? 0) * fps);
  const endFrame = Math.round(Number(hookBeat?.end_sec ?? intro.duration_sec ?? 1.5) * fps);
  const opacity = interpolate(frame, [startFrame, startFrame + 10, Math.max(startFrame + 12, endFrame - 12), endFrame], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const scale = interpolate(frame, [startFrame, startFrame + 14], [0.96, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  if (frame > endFrame) return null;
  return <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', opacity}}>
    <div style={{transform: `scale(${scale})`, background: `linear-gradient(180deg, ${brand.colors.warmCream}, ${brand.colors.ivoryParchment})`, color: brand.colors.inkBlack, width: 860, padding: 54, borderRadius: 34, border: `5px solid ${brand.colors.clay}`, boxShadow: '0 20px 60px rgba(0,0,0,.28)'}}>
      <div style={{display: 'flex', justifyContent: 'center', marginBottom: 28}}><BrandLogo src={logoSrc} fallback={logoFallback} size="small" /></div>
      <div style={{fontFamily: brand.fonts.body, color: brand.colors.oliveSage, letterSpacing: 7, fontWeight: 800, textAlign: 'center'}}>{intro.label}</div>
      <div style={{fontFamily: brand.fonts.headline, fontSize: 76, lineHeight: 1.02, marginTop: 24, textAlign: 'center'}}>{intro.headline}</div>
      <div style={{fontFamily: brand.fonts.handwritten, fontSize: 42, color: brand.colors.clay, marginTop: 18, textAlign: 'center'}}>{intro.subheadline}</div>
    </div>
  </AbsoluteFill>;
};
