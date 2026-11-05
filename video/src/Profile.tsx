import {loadFont} from '@remotion/fonts';
import React from 'react';
import {AbsoluteFill, staticFile} from 'remotion';

const NIGHT = '#0F1A17';
const DEEP = '#1D5446';
const BRASS = '#D2B26B';

loadFont({family: 'Scheherazade New', url: staticFile('fonts/ScheherazadeNew-Bold.ttf'), weight: '700'});

export type ProfileProps = {variant: 'word' | 'star'};

const Mark: React.FC<{size: number}> = ({size}) => (
  <div style={{fontFamily: 'Scheherazade New', fontWeight: 700, fontSize: size, lineHeight: 1, color: BRASS, direction: 'rtl', paddingBottom: size * 0.12}}>
    أنصِت
  </div>
);

// Profile pictures are cropped to a circle and shown tiny, so everything sits well inside the centre
export const Profile: React.FC<ProfileProps> = ({variant}) => (
  <AbsoluteFill
    style={{
      background: `radial-gradient(70% 70% at 50% 46%, ${DEEP} 0%, ${NIGHT} 78%)`,
      alignItems: 'center',
      justifyContent: 'center',
    }}
  >
    {variant === 'star' ? (
      <>
        <svg viewBox="0 0 124 124" width={900} height={900} style={{position: 'absolute'}}>
          <g fill="none" stroke={BRASS} strokeWidth={1.5}>
            <rect x={24} y={24} width={76} height={76} />
            <rect x={24} y={24} width={76} height={76} transform="rotate(45 62 62)" />
          </g>
        </svg>
        <Mark size={300} />
      </>
    ) : (
      <Mark size={350} />
    )}
  </AbsoluteFill>
);
