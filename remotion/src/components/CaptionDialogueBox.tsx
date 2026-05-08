import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {brand} from '../brand';

const keywordColor = (recipe: any, token: string): string | undefined => {
  const highlights = recipe.caption_system?.keyword_highlights ?? [];
  const hit = highlights.find((item: any) => token.toLowerCase().includes(String(item.word ?? '').toLowerCase()) || String(item.word ?? '').toLowerCase().includes(token.toLowerCase()));
  return hit?.color;
};

const activeCaption = (recipe: any, seconds: number): string => {
  const captions = recipe.captions ?? [];
  const hit = captions.find((caption: any) => seconds >= Number(caption.start ?? 0) && seconds <= Number(caption.end ?? 0));
  if (hit?.text) return hit.text;
  const beat = (recipe.beat_map ?? []).find((item: any) => seconds >= Number(item.start_sec ?? 0) && seconds <= Number(item.end_sec ?? 0) && item.text);
  if (beat?.text) return beat.text;
  if (recipe.caption_system?.highlight_keywords?.length) return recipe.caption_system.highlight_keywords.join(' · ');
  return recipe.intro_card?.headline ?? '';
};

const wordsForDisplay = (text: string, maxWords: number): string[] => text.split(/\s+/).filter(Boolean).slice(0, Math.max(5, maxWords));

export const CaptionDialogueBox: React.FC<{recipe: any}> = ({recipe}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const seconds = frame / fps;
  const y = interpolate(frame % 90, [0, 10], [42, 0], {extrapolateRight: 'clamp'});
  const scale = interpolate(frame % 90, [0, 10], [0.97, 1], {extrapolateRight: 'clamp'});
  const style = recipe.style?.name ?? 'hamsa-clean';
  const label = style === 'paris-tip' ? 'PARIS TIP' : style === 'wrong-vs-right' ? 'LOCAL TIP' : style === 'video_game_dialogue' || style === 'game' ? 'TRAVEL QUEST' : 'HAMSA NOTE';
  const captionText = activeCaption(recipe, seconds);
  if (!captionText || seconds < 1.0) return null;
  const words = wordsForDisplay(captionText, recipe.caption_system?.max_words_per_caption ?? 6);
  return <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 210}}>
    <div style={{transform: `translateY(${y}px) scale(${scale})`, maxWidth: 900, background: `linear-gradient(180deg, ${brand.colors.warmCream}, ${brand.colors.ivoryParchment})`, color: brand.colors.inkBlack, border: `5px solid ${style === 'paris-tip' ? brand.colors.clay : brand.colors.oliveSage}`, borderRadius: 34, padding: '30px 42px 36px', fontFamily: brand.fonts.body, fontSize: 54, fontWeight: 850, lineHeight: 1.16, textAlign: 'center', boxShadow: '0 18px 46px rgba(0,0,0,.25)'}}>
      <div style={{fontSize: 24, letterSpacing: 5, color: brand.colors.clay, marginBottom: 14, fontWeight: 900}}>{label}</div>
      <div>{words.map((word: string, index: number) => <React.Fragment key={`${word}-${index}`}><span style={{color: keywordColor(recipe, word) ?? brand.colors.inkBlack}}>{word}</span>{index < words.length - 1 ? ' ' : null}</React.Fragment>)}</div>
      <svg width="210" height="18" viewBox="0 0 210 18" style={{marginTop: 18, opacity: .75}}><path d="M4 10 C40 0, 82 18, 124 8 S180 4, 206 12" fill="none" stroke={brand.colors.clay} strokeWidth="4" strokeLinecap="round" strokeDasharray="10 10" /></svg>
    </div>
  </AbsoluteFill>;
};
