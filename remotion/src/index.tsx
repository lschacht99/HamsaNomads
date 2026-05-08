import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {HamsaNomadsVideo} from './HamsaNomadsVideo';
import type {HamsaVideoProps} from './types';

const defaultProps: HamsaVideoProps = {
  videoSrc: '',
  recipe: {
    project_title: 'Hamsa Nomads Edit',
    style: 'hamsa-clean',
    renderer: 'remotion',
    output_settings: {
      width: 1080,
      height: 1920,
      duration_seconds: 30,
    },
  },
};

const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="HamsaNomadsVideo"
      component={HamsaNomadsVideo}
      durationInFrames={Math.round((defaultProps.recipe.output_settings?.duration_seconds ?? 30) * 30)}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={defaultProps}
      calculateMetadata={({props}) => ({
        durationInFrames: Math.round((props.recipe.output_settings?.duration_seconds ?? 30) * 30),
        fps: 30,
        width: props.recipe.output_settings?.width ?? 1080,
        height: props.recipe.output_settings?.height ?? 1920,
      })}
    />
  );
};

registerRoot(RemotionRoot);
