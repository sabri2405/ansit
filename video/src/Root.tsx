import {Composition} from 'remotion';
import {AyahClip, ClipProps, FPS} from './AyahClip';
import {Profile} from './Profile';

const sample: ClipProps = {reciter: '', phrases: [], scenes: [], look: 'edges', audioEnd: 1, total: 3};

export const Root = () => (
  <>
    <Composition
      id="AyahClip"
      component={AyahClip}
      width={1080}
      height={1920}
      fps={FPS}
      durationInFrames={FPS * 3}
      defaultProps={sample}
      calculateMetadata={({props}) => ({durationInFrames: Math.ceil(props.total * FPS)})}
    />
    <Composition
      id="Profile"
      component={Profile}
      width={1080}
      height={1080}
      fps={FPS}
      durationInFrames={1}
      defaultProps={{variant: 'word' as const}}
    />
  </>
);
