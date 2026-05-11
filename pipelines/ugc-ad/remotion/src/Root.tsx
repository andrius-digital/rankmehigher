import {Composition, staticFile} from 'remotion';
import {HelloWorld} from './HelloWorld';
import {UgcAd} from './UgcAd';

const DEFAULT_ALIGNMENT = {
  characters: [],
  character_start_times_seconds: [],
  character_end_times_seconds: [],
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="HelloWorld"
        component={HelloWorld}
        durationInFrames={120}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{title: 'Hermes UGC pipeline — smoke test'}}
      />
      <Composition
        id="UgcAd"
        component={UgcAd}
        durationInFrames={600}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          portrait: staticFile('portrait.jpg'),
          voiceover: staticFile('voiceover.mp3'),
          lipsync: undefined as string | undefined,
          alignment: DEFAULT_ALIGNMENT,
          script: '',
          brand: 'CDL AGENCY',
          cta: 'cdlagency.com',
        }}
      />
    </>
  );
};
