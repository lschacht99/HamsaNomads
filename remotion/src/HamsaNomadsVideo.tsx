import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  OffthreadVideo,
  Sequence,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {brand} from './brand';
import type {Caption, HamsaVideoProps, Overlay} from './types';

const secondsToFrames = (seconds = 0, fps: number) => Math.round(seconds * fps);

const RouteLine: React.FC<{top: number; left?: number; width?: number}> = ({top, left = 120, width = 840}) => (
  <div
    style={{
      position: 'absolute',
      top,
      left,
      width,
      height: 70,
      borderTop: `7px solid ${brand.colors.clay}`,
      borderRadius: '48% 52% 45% 55%',
      transform: 'rotate(-2deg)',
      opacity: 0.95,
    }}
  >
    <div
      style={{
        position: 'absolute',
        top: -13,
        left: width * 0.48,
        width: 20,
        height: 20,
        background: brand.colors.oliveSage,
        borderRadius: 999,
      }}
    />
  </div>
);

const IntroCard: React.FC<{title: string; label: string}> = ({title, label}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame, fps, config: {damping: 18}});
  return (
    <AbsoluteFill style={{backgroundColor: brand.colors.warmCream, color: brand.colors.inkBlack}}>
      <div
        style={{
          position: 'absolute',
          inset: '250px 70px',
          background: brand.colors.ivoryParchment,
          border: `5px solid ${brand.colors.sand}`,
          borderRadius: 36,
          boxShadow: `0 30px 80px rgba(17,17,17,0.12)`,
          transform: `translateY(${interpolate(enter, [0, 1], [45, 0])}px)`,
          opacity: enter,
        }}
      />
      <RouteLine top={610} />
      <div style={{position: 'absolute', top: 430, width: '100%', textAlign: 'center', color: brand.colors.oliveSage, font: `700 34px ${brand.fonts.body}`, letterSpacing: 3}}>
        {label || 'JEWISH TRAVEL NOTE'}
      </div>
      <div style={{position: 'absolute', top: 760, left: 130, right: 130, textAlign: 'center', font: `700 86px ${brand.fonts.headline}`, lineHeight: 1.08}}>
        {title}
      </div>
      <div style={{position: 'absolute', bottom: 520, width: '100%', textAlign: 'center', color: brand.colors.clay, font: `600 38px ${brand.fonts.body}`}}>
        Hamsa Nomads
      </div>
    </AbsoluteFill>
  );
};

const PassportStamp: React.FC<{text: string}> = ({text}) => (
  <div
    style={{
      display: 'inline-block',
      transform: 'rotate(-4deg)',
      border: `5px solid ${brand.colors.clay}`,
      borderRadius: 18,
      color: brand.colors.clay,
      padding: '14px 24px',
      font: `800 38px ${brand.fonts.body}`,
      letterSpacing: 2,
      textTransform: 'uppercase',
      background: 'rgba(246,242,231,0.86)',
    }}
  >
    {text}
  </div>
);

const DialogueCaption: React.FC<{caption: Caption}> = ({caption}) => (
  <div style={{position: 'absolute', left: 80, right: 80, bottom: 150, background: brand.colors.warmCream, border: `6px solid ${brand.colors.oliveSage}`, borderRadius: 28, padding: 34, color: brand.colors.inkBlack, font: `650 52px ${brand.fonts.body}`, lineHeight: 1.18}}>
    <div style={{color: brand.colors.clay, fontSize: 30, marginBottom: 14, letterSpacing: 2}}>HAMSA NOMADS</div>
    {caption.text}
  </div>
);

const WrongRightOverlay: React.FC<{caption: Caption}> = ({caption}) => {
  const lines = caption.text.split('\n');
  return (
    <div style={{position: 'absolute', left: 80, right: 80, bottom: 230, background: brand.colors.ivoryParchment, border: `5px solid ${brand.colors.sand}`, borderRadius: 30, padding: 34, font: `800 50px ${brand.fonts.body}`, lineHeight: 1.24}}>
      <div style={{fontSize: 30, letterSpacing: 2, marginBottom: 16}}>ASK IT BETTER</div>
      {lines.map((line, index) => (
        <div key={line} style={{color: index === 0 ? brand.colors.clay : brand.colors.oliveSage}}>{line}</div>
      ))}
    </div>
  );
};

const CaptionOverlay: React.FC<{caption: Caption; style: string}> = ({caption, style}) => {
  if (style === 'video-game-dialogue') return <DialogueCaption caption={caption} />;
  if (style === 'wrong-vs-right') return <WrongRightOverlay caption={caption} />;
  return (
    <div style={{position: 'absolute', left: 90, right: 90, bottom: 230, background: 'rgba(246,242,231,0.92)', border: `4px solid ${brand.colors.oliveSage}`, borderRadius: 26, padding: 30, color: brand.colors.inkBlack, font: `750 56px ${brand.fonts.body}`, lineHeight: 1.15, textAlign: 'center'}}>
      {style === 'paris-tip' ? <PassportStamp text="Paris Tip" /> : null}
      {style === 'game' ? <div style={{color: brand.colors.oliveSage, fontSize: 32, letterSpacing: 2, marginBottom: 8}}>QUEST UNLOCKED</div> : null}
      <div style={{marginTop: style === 'paris-tip' ? 22 : 0}}>{caption.text}</div>
    </div>
  );
};

const TimedCaption: React.FC<{caption: Caption; style: string}> = ({caption, style}) => {
  const {fps} = useVideoConfig();
  return (
    <Sequence from={secondsToFrames(caption.start, fps)} durationInFrames={Math.max(1, secondsToFrames(caption.end - caption.start, fps))}>
      <CaptionOverlay caption={caption} style={style} />
    </Sequence>
  );
};

const TimedOverlay: React.FC<{overlay: Overlay}> = ({overlay}) => {
  const {fps} = useVideoConfig();
  return (
    <Sequence from={secondsToFrames(overlay.start, fps)} durationInFrames={Math.max(1, secondsToFrames(overlay.end - overlay.start, fps))}>
      <div style={{position: 'absolute', top: 260, left: 90}}>
        {overlay.kind === 'passport' ? <PassportStamp text={overlay.text} /> : <PassportStamp text={overlay.text} />}
      </div>
    </Sequence>
  );
};

const EndCard: React.FC<{text?: string}> = ({text}) => (
  <AbsoluteFill style={{background: brand.colors.ivoryParchment, alignItems: 'center', justifyContent: 'center', color: brand.colors.inkBlack}}>
    <RouteLine top={720} left={180} width={720} />
    <div style={{font: `700 78px ${brand.fonts.headline}`, marginBottom: 30}}>Hamsa Nomads</div>
    <div style={{font: `600 42px ${brand.fonts.body}`, maxWidth: 780, textAlign: 'center', color: brand.colors.oliveSage}}>{text}</div>
  </AbsoluteFill>
);

export const HamsaNomadsVideo: React.FC<HamsaVideoProps> = ({recipe, videoSrc}) => {
  const {fps, durationInFrames} = useVideoConfig();
  const introFrames = recipe.intro_card?.enabled ? secondsToFrames(recipe.intro_card.duration_seconds ?? 1.5, fps) : 0;
  const ctaFrames = 90;
  const mainFrames = Math.max(1, durationInFrames - introFrames - ctaFrames);
  const style = recipe.style ?? 'hamsa-clean';

  return (
    <AbsoluteFill style={{backgroundColor: brand.colors.inkBlack}}>
      {introFrames > 0 ? (
        <Sequence durationInFrames={introFrames}>
          <IntroCard title={recipe.intro_card?.title || recipe.project_title} label={recipe.intro_card?.label || 'JEWISH TRAVEL NOTE'} />
        </Sequence>
      ) : null}
      <Sequence from={introFrames} durationInFrames={mainFrames}>
        <AbsoluteFill>
          <OffthreadVideo src={videoSrc} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
          <RouteLine top={1550} left={160} width={760} />
          {(recipe.captions ?? []).map((caption) => <TimedCaption key={`${caption.start}-${caption.text}`} caption={caption} style={style} />)}
          {(recipe.overlays ?? []).map((overlay) => <TimedOverlay key={`${overlay.start}-${overlay.text}`} overlay={overlay} />)}
        </AbsoluteFill>
      </Sequence>
      <Sequence from={introFrames + mainFrames} durationInFrames={ctaFrames}>
        <EndCard text={recipe.cta?.text || 'Follow Hamsa Nomads for more Jewish travel notes.'} />
      </Sequence>
    </AbsoluteFill>
  );
};
