import React from 'react';
import { Composition } from 'remotion';
import { ScreenClipperShowcase } from './ScreenClipperShowcase';

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="ScreenClipperShowcase"
        component={ScreenClipperShowcase}
        durationInFrames={360}
        fps={30}
        width={1280}
        height={720}
      />
    </>
  );
};

