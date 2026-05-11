import {AbsoluteFill, Img, Video, Audio, useCurrentFrame, useVideoConfig, interpolate, Easing, staticFile} from 'remotion';

type Alignment = {
  characters: string[];
  character_start_times_seconds: number[];
  character_end_times_seconds: number[];
};

type Props = {
  portrait: string;    // staticFile('portrait.jpg')
  voiceover: string;   // staticFile('voiceover.mp3')
  lipsync?: string;    // staticFile('lipsync.mp4') — if present, overrides portrait
  alignment: Alignment;
  script: string;
  brand: string;
  cta: string;
};

function wordPhrases(alignment: Alignment): {word: string; start: number; end: number}[] {
  const words: {word: string; start: number; end: number}[] = [];
  let buf = '';
  let start = 0;
  for (let i = 0; i < alignment.characters.length; i++) {
    const ch = alignment.characters[i];
    if (buf === '') start = alignment.character_start_times_seconds[i];
    if (ch === ' ' || ch === '\n') {
      if (buf.trim().length > 0) {
        words.push({word: buf.trim(), start, end: alignment.character_end_times_seconds[i - 1] ?? alignment.character_end_times_seconds[i]});
      }
      buf = '';
    } else {
      buf += ch;
    }
  }
  if (buf.trim().length > 0) {
    const lastIdx = alignment.characters.length - 1;
    words.push({word: buf.trim(), start, end: alignment.character_end_times_seconds[lastIdx]});
  }
  return words;
}

function chunkPhrases(words: {word: string; start: number; end: number}[], chunkSize = 4) {
  const phrases: {text: string; start: number; end: number}[] = [];
  for (let i = 0; i < words.length; i += chunkSize) {
    const chunk = words.slice(i, i + chunkSize);
    phrases.push({
      text: chunk.map((w) => w.word).join(' '),
      start: chunk[0].start,
      end: chunk[chunk.length - 1].end,
    });
  }
  return phrases;
}

export const UgcAd: React.FC<Props> = ({portrait, voiceover, lipsync, alignment, brand, cta}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const now = frame / fps;

  const words = wordPhrases(alignment);
  const phrases = chunkPhrases(words, 4);
  const audioDur = alignment.character_end_times_seconds[alignment.character_end_times_seconds.length - 1] ?? 15;

  // Ken Burns only used when we fall back to still portrait
  const zoom = interpolate(frame, [0, durationInFrames], [1.0, 1.12], {easing: Easing.linear});
  const driftY = interpolate(frame, [0, durationInFrames], [0, -20], {easing: Easing.linear});

  const activePhrase = phrases.find((p) => now >= p.start && now <= p.end + 0.15);
  const showCta = now >= audioDur - 2.0;

  return (
    <AbsoluteFill style={{background: 'black'}}>
      {/* Audio track — if lipsync already contains audio we'd NOT add this, but sync-lipsync returns video only */}
      {!lipsync && <Audio src={voiceover} />}

      {/* Background visual: lipsync video if we have it, else Ken-Burns portrait */}
      <AbsoluteFill style={{overflow: 'hidden'}}>
        {lipsync ? (
          <Video
            src={lipsync.startsWith('http') ? lipsync : staticFile(lipsync)}
            style={{width: '100%', height: '100%', objectFit: 'cover'}}
          />
        ) : (
          <Img
            src={portrait}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              transform: `scale(${zoom}) translateY(${driftY}px)`,
              transformOrigin: 'center 40%',
            }}
          />
        )}
      </AbsoluteFill>

      {/* Vignette for caption legibility */}
      <AbsoluteFill
        style={{
          background: 'linear-gradient(180deg, rgba(0,0,0,0.0) 40%, rgba(0,0,0,0.55) 75%, rgba(0,0,0,0.85) 100%)',
        }}
      />

      {activePhrase && !showCta && (
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            bottom: 280,
            display: 'flex',
            justifyContent: 'center',
            padding: '0 60px',
          }}
        >
          <div
            style={{
              background: 'rgba(0,0,0,0.85)',
              color: 'white',
              fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
              fontWeight: 900,
              fontSize: 72,
              lineHeight: 1.1,
              padding: '28px 40px',
              borderRadius: 16,
              textAlign: 'center',
              letterSpacing: '-0.02em',
              textTransform: 'uppercase',
              maxWidth: '95%',
              boxShadow: '0 16px 48px rgba(0,0,0,0.4)',
            }}
          >
            {activePhrase.text}
          </div>
        </div>
      )}

      <div
        style={{
          position: 'absolute',
          top: 80,
          left: 0,
          right: 0,
          textAlign: 'center',
          color: 'white',
          fontFamily: 'Inter, sans-serif',
          fontSize: 36,
          fontWeight: 700,
          textShadow: '0 4px 16px rgba(0,0,0,0.6)',
        }}
      >
        {brand}
      </div>

      {showCta && (
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            bottom: 300,
            textAlign: 'center',
            padding: '0 40px',
          }}
        >
          <div
            style={{
              color: 'white',
              fontFamily: 'Inter, sans-serif',
              fontSize: 96,
              fontWeight: 900,
              lineHeight: 1.05,
              textShadow: '0 6px 24px rgba(0,0,0,0.8)',
              letterSpacing: '-0.02em',
            }}
          >
            GET HIRED<br />FAST
          </div>
          <div
            style={{
              marginTop: 32,
              color: '#ffcc00',
              fontFamily: 'Inter, sans-serif',
              fontSize: 56,
              fontWeight: 700,
              textShadow: '0 4px 16px rgba(0,0,0,0.8)',
            }}
          >
            {cta}
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};
