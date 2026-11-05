import {loadFont} from '@remotion/fonts';
import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  random,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

export const FPS = 30;

export type Phrase = {text: string; start: number; end: number; number?: string; translation?: string};
export type Scene = {key: string; frames: number; start: number};
export type Look = 'stroke' | 'edges' | 'plate';

export type ClipProps = {
  reciter: string;
  phrases: Phrase[];
  scenes: Scene[];
  look: Look;
  audioEnd: number; // seconds; the end card follows
  total: number; // seconds
};

const NIGHT = '#0F1A17';
const BRASS = '#C9A861';
const PARCH = '#F2E8D4';

const VERSE_FONT = 'Scheherazade New';
const UI_FONT = 'El Messiri';
const BRAND_FONT = 'Aref Ruqaa';
const VERSE_SIZE = 84;

loadFont({family: VERSE_FONT, url: staticFile('fonts/ScheherazadeNew-Regular.ttf'), weight: '400'});
loadFont({family: UI_FONT, url: staticFile('fonts/ElMessiri[wght].ttf'), weight: '400 700'});
loadFont({family: BRAND_FONT, url: staticFile('fonts/ArefRuqaa-Bold.ttf'), weight: '700'});

const CROSSFADE = FPS; // frames

const cover: React.CSSProperties = {position: 'absolute', width: '100%', height: '100%', objectFit: 'cover'};

// Each scene is a numbered image sequence. Repeats fade in over the end of the pass before, so it never jumps.
const SceneLayer: React.FC<{scene: Scene; opacity: number}> = ({scene, opacity}) => {
  const frame = useCurrentFrame() - Math.round(scene.start * FPS);
  const step = scene.frames - CROSSFADE;
  const index = Math.max(0, frame) % step;
  const blending = frame >= step && index < CROSSFADE;
  const src = (i: number) => staticFile(`clip/bg/${scene.key}/${String(i + 1).padStart(4, '0')}.jpg`);
  return (
    <AbsoluteFill style={{opacity}}>
      {blending ? <Img src={src(index + step)} style={cover} /> : null}
      <Img src={src(index)} style={{...cover, opacity: blending ? index / CROSSFADE : 1}} />
    </AbsoluteFill>
  );
};

const Background: React.FC<{scenes: Scene[]}> = ({scenes}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const current = scenes.reduce((last, scene, i) => (scene.start * FPS <= frame ? i : last), 0);
  const sinceCut = frame - scenes[current].start * FPS;
  const fading = current > 0 && sinceCut < CROSSFADE;
  const zoom = interpolate(frame, [0, durationInFrames], [1.02, 1.1]);

  return (
    <AbsoluteFill style={{transform: `scale(${zoom})`, filter: 'brightness(0.74) saturate(1.05) contrast(1.1)'}}>
      {fading ? <SceneLayer scene={scenes[current - 1]} opacity={1} /> : null}
      <SceneLayer scene={scenes[current]} opacity={fading ? sinceCut / CROSSFADE : 1} />
    </AbsoluteFill>
  );
};

const Dust: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      {Array.from({length: 14}, (_, i) => {
        const x = random(`x${i}`) * 1080;
        const speed = 0.25 + random(`s${i}`) * 0.5;
        const y = ((random(`y${i}`) * 2100 - frame * speed + 2100 * 4) % 2100) - 90;
        const size = 3 + random(`r${i}`) * 5;
        const twinkle = 0.5 + 0.5 * Math.sin(frame / 22 + i * 1.7);
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: x,
              top: y,
              width: size,
              height: size,
              borderRadius: '50%',
              background: BRASS,
              opacity: 0.1 + twinkle * 0.28,
              filter: 'blur(1.5px)',
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

const Shade: React.FC = () => (
  <AbsoluteFill
    style={{background: `linear-gradient(180deg, ${NIGHT}99 0%, ${NIGHT}00 20%, ${NIGHT}00 72%, ${NIGHT}b3 100%)`}}
  />
);

const Star: React.FC<{size: string; fill: string; stroke: string}> = ({size, fill, stroke}) => (
  <svg viewBox="0 0 124 124" width={size} height={size} style={{display: 'block'}}>
    <g fill={fill} stroke={stroke} strokeWidth={6}>
      <rect x={24} y={24} width={76} height={76} />
      <rect x={24} y={24} width={76} height={76} transform="rotate(45 62 62)" />
    </g>
  </svg>
);

// Verse-end ornament, set in the line like the printed Mushaf
const AyahNumber: React.FC<{number: string}> = ({number}) => (
  <span
    style={{
      display: 'inline-block',
      position: 'relative',
      width: '1.02em',
      height: '1.02em',
      verticalAlign: '-0.28em',
      margin: '0 0.14em',
    }}
  >
    <Star size="100%" fill={`${NIGHT}b3`} stroke={BRASS} />
    <span
      style={{
        position: 'absolute',
        inset: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: UI_FONT,
        fontWeight: 600,
        fontSize: number.length > 2 ? '0.3em' : '0.38em',
        lineHeight: 1,
        textShadow: 'none',
        color: PARCH,
      }}
    >
      {number}
    </span>
  </span>
);

// Pause marks are separate tokens in the Uthmani text; they stay with the word before them
const splitWords = (text: string) =>
  text.split(' ').reduce<string[]>((words, token) => {
    if (words.length && !/[ء-يٱ]/.test(token)) {
      words[words.length - 1] += ` ${token}`;
    } else {
      words.push(token);
    }
    return words;
  }, []);

const ring = (r: number) =>
  Array.from({length: 12}, (_, i) => {
    const a = (i / 12) * Math.PI * 2;
    return `${(Math.cos(a) * r).toFixed(1)}px ${(Math.sin(a) * r).toFixed(1)}px 1px ${NIGHT}`;
  }).join(', ');

// Three ways to lift the words off the footage; the queue picks one per clip
const SHADOWS: Record<Look, string> = {
  stroke: `${ring(3.5)}, 0 4px 16px ${NIGHT}cc`,
  edges: `0 0 5px ${NIGHT}, 0 0 14px ${NIGHT}, 0 0 34px ${NIGHT}e6, 0 0 70px ${NIGHT}99`,
  plate: 'none',
};

const PhraseCard: React.FC<{phrase: Phrase; look: Look}> = ({phrase, look}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const words = splitWords(phrase.text);
  const stagger = Math.min(4, (durationInFrames * 0.35) / words.length);
  const exit = interpolate(frame, [durationInFrames - 7, durationInFrames], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const enter = spring({frame, fps, config: {damping: 200}, durationInFrames: 14});
  const plate: React.CSSProperties =
    look === 'plate'
      ? {
          background: `${NIGHT}a6`,
          borderRadius: 16,
          padding: '0.02em 0.32em 0.1em',
          boxDecorationBreak: 'clone',
          WebkitBoxDecorationBreak: 'clone',
        }
      : {};

  const word = (text: string, i: number) => {
    const p = spring({frame: frame - i * stagger, fps, config: {damping: 200}, durationInFrames: 18});
    return (
      <span
        style={{
          display: 'inline-block',
          opacity: p,
          transform: `translateY(${(1 - p) * 16}px)`,
          filter: `blur(${(1 - p) * 5}px)`,
        }}
      >
        {text}
      </span>
    );
  };
  const last = words.length - 1;

  return (
    <AbsoluteFill
      style={{
        opacity: exit,
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        gap: 26,
        padding: '0 80px',
        transform: 'translateY(-70px)',
      }}
    >
      <div
        style={{
          direction: 'rtl',
          fontFamily: VERSE_FONT,
          fontSize: VERSE_SIZE,
          lineHeight: look === 'plate' ? 1.95 : 1.75,
          color: PARCH,
          textAlign: 'center',
          textWrap: 'balance',
          textShadow: SHADOWS[look],
        }}
      >
        <span style={plate}>
          {words.slice(0, last).map((w, i) => (
            <React.Fragment key={i}>{word(w, i)} </React.Fragment>
          ))}
          {/* The last word and the verse number never split across lines */}
          <span style={{whiteSpace: 'nowrap'}}>
            {word(words[last], last)}
            {phrase.number ? <AyahNumber number={phrase.number} /> : null}
          </span>
        </span>
      </div>
      {phrase.translation ? (
        <div
          style={{
            direction: 'ltr',
            opacity: enter * 0.92,
            fontFamily: UI_FONT,
            fontSize: 36,
            lineHeight: 1.4,
            color: PARCH,
            textAlign: 'center',
            textWrap: 'balance',
            textShadow: `0 0 6px ${NIGHT}, 0 0 18px ${NIGHT}`,
          }}
        >
          {phrase.translation}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

const Brand: React.FC = () => (
  <div style={{position: 'absolute', top: 168, left: 0, right: 0, textAlign: 'center', direction: 'rtl'}}>
    <span style={{fontFamily: BRAND_FONT, fontWeight: 700, fontSize: 46, color: BRASS, textShadow: `0 0 12px ${NIGHT}`}}>
      أنصِت
    </span>
  </div>
);

const Credit: React.FC<{reciter: string}> = ({reciter}) => (
  <div
    style={{
      position: 'absolute',
      top: 1400,
      left: 0,
      right: 0,
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      gap: 12,
      direction: 'rtl',
      fontFamily: UI_FONT,
      fontWeight: 500,
      fontSize: 34,
      color: PARCH,
      textShadow: `0 0 8px ${NIGHT}, 0 0 20px ${NIGHT}`,
    }}
  >
    <Star size="0.62em" fill={BRASS} stroke={BRASS} />
    <span>{reciter}</span>
  </div>
);

const EndCard: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = spring({frame, fps, config: {damping: 200}, durationInFrames: 24});
  return (
    <AbsoluteFill
      style={{
        background: `${NIGHT}e0`,
        opacity: p,
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        gap: 12,
        direction: 'rtl',
      }}
    >
      <div
        style={{
          fontFamily: BRAND_FONT,
          fontWeight: 700,
          fontSize: 210,
          lineHeight: 1.5,
          color: BRASS,
          transform: `scale(${0.94 + p * 0.06})`,
        }}
      >
        أنصِت
      </div>
      <div style={{fontFamily: UI_FONT, fontSize: 56, color: PARCH}}>لعلّك تُرحم</div>
      <div style={{fontFamily: UI_FONT, fontSize: 40, color: PARCH, opacity: 0.75, direction: 'ltr', marginTop: 28}}>
        @ansit.quran
      </div>
    </AbsoluteFill>
  );
};

export const AyahClip: React.FC<ClipProps> = ({reciter, phrases, scenes, look, audioEnd}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const endFrame = Math.round(audioEnd * FPS);
  const fade = interpolate(frame, [0, 12, durationInFrames - 14, durationInFrames], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{backgroundColor: NIGHT}}>
      <AbsoluteFill style={{opacity: fade}}>
        {scenes.length ? <Background scenes={scenes} /> : null}
        <Shade />
        <Dust />
        <Sequence durationInFrames={endFrame} layout="none">
          <Brand />
          <Credit reciter={reciter} />
        </Sequence>
        {phrases.map((p, i) => {
          const from = Math.round(p.start * FPS);
          return (
            <Sequence key={i} from={from} durationInFrames={Math.max(1, Math.round(p.end * FPS) - from)}>
              <PhraseCard phrase={p} look={look} />
            </Sequence>
          );
        })}
        <Sequence from={endFrame}>
          <EndCard />
        </Sequence>
      </AbsoluteFill>
      <Audio src={staticFile('clip/audio.wav')} />
    </AbsoluteFill>
  );
};
