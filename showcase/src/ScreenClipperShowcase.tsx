import React from 'react';
import {
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

export const ScreenClipperShowcase: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Helper spring animations
  const introSpring = spring({ frame, fps, config: { damping: 14 } });
  
  // Scene timing
  // Scene 1: 0 - 85 frames (Hero intro)
  // Scene 2: 85 - 205 frames (UI buffer & F9 hotkey trigger)
  // Scene 3: 205 - 295 frames (Saved clip & features)
  // Scene 4: 295 - 360 frames (Outro & Download)

  const s1Opacity = interpolate(frame, [0, 15, 75, 88], [0, 1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const s1Scale = interpolate(frame, [0, 85], [0.92, 1.04], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  const s2Opacity = interpolate(frame, [85, 95, 195, 205], [0, 1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const s2TranslateY = interpolate(frame, [85, 100], [30, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  const s3Opacity = interpolate(frame, [205, 215, 285, 295], [0, 1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const s3Scale = interpolate(frame, [205, 220], [0.95, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  const s4Opacity = interpolate(frame, [295, 308, 350, 360], [0, 1, 1, 0.8], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const s4Scale = interpolate(frame, [295, 315], [0.94, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Scene 2 keyframe calculations
  const bufferFill = interpolate(frame, [90, 135], [20, 100], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const hotkeyPressFrame = 138;
  const isPressed = frame >= hotkeyPressFrame && frame < hotkeyPressFrame + 18;
  const isSaved = frame >= hotkeyPressFrame + 25;
  const shockwaveScale = interpolate(frame, [hotkeyPressFrame, hotkeyPressFrame + 30], [0.8, 3.2], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const shockwaveOpacity = interpolate(frame, [hotkeyPressFrame, hotkeyPressFrame + 28], [0.85, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <div
      style={{
        width: 1280,
        height: 720,
        backgroundColor: '#0c0e14',
        fontFamily: "'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif",
        color: '#e6e8ee',
        position: 'relative',
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {/* Background ambient lighting */}
      <div
        style={{
          position: 'absolute',
          top: -150,
          left: -100,
          width: 700,
          height: 700,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(91,95,240,0.18) 0%, rgba(0,0,0,0) 70%)',
          filter: 'blur(50px)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          bottom: -150,
          right: -100,
          width: 800,
          height: 800,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(67,56,202,0.15) 0%, rgba(0,0,0,0) 70%)',
          filter: 'blur(60px)',
        }}
      />

      {/* Subtle grid pattern */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            'linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
          opacity: 0.6,
        }}
      />

      {/* ========================================================================= */}
      {/* SCENE 1: HERO TITLE & BADGES (0s - 3s) */}
      {/* ========================================================================= */}
      {frame < 90 && (
        <div
          style={{
            position: 'absolute',
            opacity: s1Opacity,
            transform: `scale(${s1Scale})`,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            textAlign: 'center',
            maxWidth: 1000,
          }}
        >
          {/* Top category chip */}
          <div
            style={{
              padding: '6px 18px',
              borderRadius: 30,
              backgroundColor: 'rgba(91, 95, 240, 0.15)',
              border: '1px solid rgba(124, 131, 255, 0.35)',
              color: '#9aa3ff',
              fontSize: 14,
              fontWeight: 700,
              letterSpacing: 1.5,
              textTransform: 'uppercase',
              marginBottom: 24,
              boxShadow: '0 4px 20px rgba(91, 95, 240, 0.2)',
            }}
          >
            Instant Replay & Rolling Buffer for Windows
          </div>

          {/* App Icon + Title */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 24, marginBottom: 16 }}>
            {/* Animated Logo Icon */}
            <div
              style={{
                width: 88,
                height: 88,
                borderRadius: 22,
                background: 'linear-gradient(135deg, #7c83ff 0%, #4338ca 100%)',
                boxShadow: '0 12px 35px rgba(91, 95, 240, 0.45)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <div
                style={{
                  width: 0,
                  height: 0,
                  borderTop: '16px solid transparent',
                  borderBottom: '16px solid transparent',
                  borderLeft: '28px solid white',
                  marginLeft: 6,
                }}
              />
            </div>

            <h1
              style={{
                fontSize: 66,
                fontWeight: 800,
                letterSpacing: -1.5,
                margin: 0,
                background: 'linear-gradient(180deg, #ffffff 30%, #b8c2db 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              Screen Clipper
            </h1>
          </div>

          {/* Subtitle */}
          <p
            style={{
              fontSize: 22,
              color: '#9ba4ba',
              maxWidth: 720,
              lineHeight: 1.5,
              margin: '0 0 36px 0',
            }}
          >
            Continuously buffer your screen & audio in the background. Press a single hotkey to save the last 30s as a high-quality MP4.
          </p>

          {/* Pill row */}
          <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', justifyContent: 'center' }}>
            {[
              { label: '5s – 300s Ring Buffer', icon: '⏱️' },
              { label: 'WASAPI Desktop & Mic Audio', icon: '🔊' },
              { label: 'Customizable Hotkey (F9)', icon: '⌨️' },
              { label: 'Zero Bloat .EXE (No Install)', icon: '⚡' },
            ].map((pill, idx) => (
              <div
                key={idx}
                style={{
                  padding: '10px 18px',
                  borderRadius: 12,
                  backgroundColor: 'rgba(24, 27, 34, 0.85)',
                  border: '1px solid #282f42',
                  fontSize: 15,
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  boxShadow: '0 4px 15px rgba(0,0,0,0.3)',
                }}
              >
                <span>{pill.icon}</span>
                <span>{pill.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SCENE 2: INTERACTIVE DASHBOARD & HOTKEY TRIGGER (3s - 7s) */}
      {/* ========================================================================= */}
      {frame >= 85 && frame < 205 && (
        <div
          style={{
            position: 'absolute',
            width: 1080,
            opacity: s2Opacity,
            transform: `translateY(${s2TranslateY}px)`,
            display: 'flex',
            flexDirection: 'column',
            gap: 18,
          }}
        >
          {/* Top Title Banner */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 9,
                  background: 'linear-gradient(135deg, #7c83ff 0%, #4338ca 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <div style={{ width: 0, height: 0, borderTop: '6px solid transparent', borderBottom: '6px solid transparent', borderLeft: '10px solid white', marginLeft: 2 }} />
              </div>
              <span style={{ fontSize: 20, fontWeight: 700 }}>Screen Clipper Dashboard</span>
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <span style={{ background: '#1c2130', border: '1px solid #2a3248', padding: '5px 14px', borderRadius: 8, fontSize: 13, color: '#a0aabf' }}>
                Primary Monitor (2560×1440)
              </span>
              <span style={{ background: '#1c2130', border: '1px solid #2a3248', padding: '5px 14px', borderRadius: 8, fontSize: 13, color: '#a0aabf' }}>
                Audio: Stereo 48kHz
              </span>
            </div>
          </div>

          {/* Main Hero Card (Status + Buffer) */}
          <div
            style={{
              backgroundColor: '#161922',
              border: isPressed ? '1px solid #7c83ff' : '1px solid #252b3d',
              borderRadius: 18,
              padding: 24,
              boxShadow: isPressed ? '0 0 35px rgba(91,95,240,0.45)' : '0 10px 30px rgba(0,0,0,0.4)',
              transition: 'all 0.15s ease',
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            {/* Shockwave effect upon hotkey */}
            {frame >= hotkeyPressFrame && (
              <div
                style={{
                  position: 'absolute',
                  top: '50%',
                  right: 120,
                  width: 100,
                  height: 100,
                  borderRadius: '50%',
                  border: '3px solid #7c83ff',
                  transform: `translate(50%, -50%) scale(${shockwaveScale})`,
                  opacity: shockwaveOpacity,
                  pointerEvents: 'none',
                }}
              />
            )}

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 18 }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                  <div
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: '50%',
                      backgroundColor: isPressed ? '#ffb703' : isSaved ? '#4ade80' : '#22c55e',
                      boxShadow: isPressed ? '0 0 12px #ffb703' : '0 0 10px #22c55e',
                    }}
                  />
                  <span style={{ fontSize: 20, fontWeight: 700 }}>
                    {isPressed ? '🟡 Saving Clip Snapshot...' : isSaved ? '🟢 Buffering (Clip Saved!)' : '🟢 Buffering Active'}
                  </span>
                </div>
                <span style={{ fontSize: 14, color: '#8d97ac' }}>
                  {isPressed
                    ? 'Piping frames & WASAPI loopback audio to ffmpeg encoder...'
                    : 'Last 30 seconds continuously kept in memory ring buffer'}
                </span>
              </div>

              {/* F9 Hotkey Badge visual */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 14,
                  backgroundColor: '#1c2130',
                  padding: '10px 20px',
                  borderRadius: 14,
                  border: isPressed ? '2px solid #5b5ff0' : '1px solid #2d364e',
                  transform: isPressed ? 'scale(0.96)' : 'scale(1)',
                  boxShadow: isPressed ? '0 0 20px rgba(91,95,240,0.6)' : 'none',
                }}
              >
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 12, color: '#8892a7', fontWeight: 600 }}>INSTANT CLIP</div>
                  <div style={{ fontSize: 13, color: '#e6e8ee', fontWeight: 700 }}>HOTKEY</div>
                </div>
                <div
                  style={{
                    backgroundColor: isPressed ? '#5b5ff0' : '#272d40',
                    color: '#ffffff',
                    padding: '8px 16px',
                    borderRadius: 10,
                    fontWeight: 800,
                    fontSize: 18,
                    letterSpacing: 1,
                    boxShadow: '0 4px 10px rgba(0,0,0,0.4)',
                  }}
                >
                  F9
                </div>
              </div>
            </div>

            {/* Rolling buffer bar */}
            <div style={{ width: '100%', height: 10, backgroundColor: '#212636', borderRadius: 5, overflow: 'hidden', position: 'relative' }}>
              <div
                style={{
                  height: '100%',
                  width: `${bufferFill}%`,
                  background: 'linear-gradient(90deg, #4338ca 0%, #5b5ff0 70%, #60a5fa 100%)',
                  borderRadius: 5,
                  boxShadow: '0 0 10px rgba(91,95,240,0.5)',
                }}
              />
            </div>
          </div>

          {/* 4 Telemetry Stats cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
            {[
              { title: 'Buffer Length', val: '30 Seconds', sub: 'Customizable 5s–300s' },
              { title: 'Capture Target', val: '1080p Full HD', sub: 'Scaled from 1440p' },
              { title: 'Frame Rate', val: '60 FPS', sub: 'Silky smooth recording' },
              { title: 'Buffer Memory', val: '38.2 MB', sub: 'Low RAM JPEG ring buffer' },
            ].map((stat, i) => (
              <div
                key={i}
                style={{
                  backgroundColor: '#161922',
                  border: '1px solid #232838',
                  borderRadius: 14,
                  padding: '16px 18px',
                }}
              >
                <div style={{ fontSize: 13, color: '#8a93a6', marginBottom: 6 }}>{stat.title}</div>
                <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 4 }}>{stat.val}</div>
                <div style={{ fontSize: 12, color: '#5b6478' }}>{stat.sub}</div>
              </div>
            ))}
          </div>

          {/* Interactive notification banner when saved */}
          {isSaved && (
            <div
              style={{
                backgroundColor: 'rgba(34, 197, 94, 0.12)',
                border: '1px solid rgba(34, 197, 94, 0.35)',
                borderRadius: 14,
                padding: '14px 20px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ fontSize: 18 }}>📁</span>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#4ade80' }}>Clip Successfully Saved!</div>
                  <div style={{ fontSize: 12, color: '#94a3b8' }}>Videos\ScreenClipper\Clip_2026-11-03_20-15-00.mp4</div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 10 }}>
                <span style={{ background: '#1e293b', padding: '6px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600 }}>
                  Show in Explorer
                </span>
                <span style={{ background: '#1e293b', padding: '6px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600 }}>
                  Copy Path
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* SCENE 3: FEATURE HIGHLIGHTS & CLIPS BROWSER (7s - 10s) */}
      {/* ========================================================================= */}
      {frame >= 205 && frame < 295 && (
        <div
          style={{
            position: 'absolute',
            width: 1080,
            opacity: s3Opacity,
            transform: `scale(${s3Scale})`,
            display: 'flex',
            flexDirection: 'column',
            gap: 22,
          }}
        >
          <div style={{ textAlign: 'center', marginBottom: 6 }}>
            <h2 style={{ fontSize: 34, fontWeight: 800, margin: '0 0 8px 0' }}>
              Engineered For Gamers, Creators & Power Users
            </h2>
            <p style={{ fontSize: 16, color: '#8a94a6', margin: 0 }}>
              Zero latency background buffering with immediate access to your clips.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
            {[
              {
                icon: '⚡',
                title: 'Rolling Replay Buffer',
                desc: 'Only saves when you hit the hotkey. No wasting disk space with hour-long recordings just to find a 10s highlight.',
              },
              {
                icon: '🎙️',
                title: 'Dual WASAPI Audio',
                desc: 'Captures crisp desktop game audio through Windows WASAPI loopback, with an optional microphone channel mixed in.',
              },
              {
                icon: '🎯',
                title: 'Instant Path Finder',
                desc: 'One-click "Show in Explorer" highlights the exact MP4 immediately in Windows Explorer for rapid sharing to Discord.',
              },
              {
                icon: '⚙️',
                title: 'Precision Settings',
                desc: 'Configurable clip lengths (5s to 300s), target resolutions (480p to Native 4K), 15/30/60 FPS, and H.264 CRF quality.',
              },
              {
                icon: '⌨️',
                title: 'Global Win32 Hotkeys',
                desc: 'Direct Win32 RegisterHotKey integration works seamlessly across borderless games, fullscreen apps, and IDEs.',
              },
              {
                icon: '🪶',
                title: 'Single Standalone EXE',
                desc: '122 MB self-contained binary with bundled ffmpeg. No Python runtime, no installers, no cloud accounts, 100% offline.',
              },
            ].map((card, i) => (
              <div
                key={i}
                style={{
                  backgroundColor: '#151821',
                  border: '1px solid #232838',
                  borderRadius: 16,
                  padding: 22,
                  boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
                }}
              >
                <div style={{ fontSize: 28, marginBottom: 12 }}>{card.icon}</div>
                <div style={{ fontSize: 17, fontWeight: 700, marginBottom: 8, color: '#ffffff' }}>{card.title}</div>
                <div style={{ fontSize: 13, color: '#8e98ac', lineHeight: 1.5 }}>{card.desc}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* SCENE 4: CALL TO ACTION & GITHUB RELEASE (10s - 12s) */}
      {/* ========================================================================= */}
      {frame >= 295 && (
        <div
          style={{
            position: 'absolute',
            opacity: s4Opacity,
            transform: `scale(${s4Scale})`,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            textAlign: 'center',
            maxWidth: 900,
          }}
        >
          {/* Logo */}
          <div
            style={{
              width: 96,
              height: 96,
              borderRadius: 24,
              background: 'linear-gradient(135deg, #7c83ff 0%, #4338ca 100%)',
              boxShadow: '0 16px 45px rgba(91, 95, 240, 0.5)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: 24,
            }}
          >
            <div
              style={{
                width: 0,
                height: 0,
                borderTop: '18px solid transparent',
                borderBottom: '18px solid transparent',
                borderLeft: '32px solid white',
                marginLeft: 6,
              }}
            />
          </div>

          <h2 style={{ fontSize: 44, fontWeight: 800, margin: '0 0 12px 0' }}>
            Get Screen Clipper for Windows
          </h2>
          <p style={{ fontSize: 18, color: '#9ba4ba', margin: '0 0 32px 0', maxWidth: 640 }}>
            Download the latest standalone executable from GitHub Releases and start clipping immediately.
          </p>

          {/* Download Box */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 20,
              backgroundColor: '#181c26',
              border: '1px solid #333c56',
              padding: '16px 32px',
              borderRadius: 16,
              boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
            }}
          >
            <div style={{ textAlign: 'left' }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: '#ffffff' }}>ScreenClipper.exe</div>
              <div style={{ fontSize: 13, color: '#7c83ff' }}>v1.0.0 Release • Standalone 64-bit Windows</div>
            </div>
            <div
              style={{
                backgroundColor: '#5b5ff0',
                color: '#ffffff',
                fontWeight: 700,
                fontSize: 15,
                padding: '10px 24px',
                borderRadius: 10,
                boxShadow: '0 4px 15px rgba(91,95,240,0.4)',
              }}
            >
              Download
            </div>
          </div>

          <div style={{ marginTop: 28, fontSize: 14, color: '#68728a' }}>
            Open Source • github.com/Flopper1-1/screenclipper
          </div>
        </div>
      )}
    </div>
  );
};

