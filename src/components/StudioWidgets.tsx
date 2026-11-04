import React, { useState, useRef } from 'react';

/**
 * LAW 1 & SECTION 3.1: 3D Metallic & Sapphire-Glass Camera Lens Emblem (`Lumixa3DLensLogo`)
 * Draws:
 * 1. Outer machined titanium barrel ring (conical metallic gradient #4A4A58 to #181820)
 * 2. Knurled grip ridges around circumference
 * 3. Deep recessed matte black lens barrel (#08080C)
 * 4. Multi-coated optical sapphire/amber glass element (#0EA5E9 cyan glint, #E5A93C warm reflex, #050508 core)
 * 5. 6 geometric iris aperture blades + crisp specular white reflection arc
 */
export const Lumixa3DLensLogo: React.FC<{ size?: number }> = ({ size = 34 }) => {
  const ridges: { x1: number; y1: number; x2: number; y2: number }[] = [];
  for (let i = 0; i < 24; i++) {
    const rad = (i * 15 * Math.PI) / 180;
    ridges.push({
      x1: 32 + 27.5 * Math.cos(rad),
      y1: 32 + 27.5 * Math.sin(rad),
      x2: 32 + 30.2 * Math.cos(rad),
      y2: 32 + 30.2 * Math.sin(rad),
    });
  }

  const blades: { x1: number; y1: number; x2: number; y2: number }[] = [];
  for (let i = 0; i < 6; i++) {
    const a1 = ((i * 60 + 18) * Math.PI) / 180;
    const a2 = ((i * 60 + 72) * Math.PI) / 180;
    blades.push({
      x1: 32 + 6.8 * Math.cos(a1),
      y1: 32 + 6.8 * Math.sin(a1),
      x2: 32 + 16.5 * Math.cos(a2),
      y2: 32 + 16.5 * Math.sin(a2),
    });
  }

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      aria-hidden="true"
      className="shrink-0"
    >
      <defs>
        <linearGradient id="lumixaTitaniumRing" x1="0" y1="0" x2="64" y2="64">
          <stop offset="0%" stopColor="#565666" />
          <stop offset="30%" stopColor="#22222C" />
          <stop offset="55%" stopColor="#4A4A58" />
          <stop offset="80%" stopColor="#14141B" />
          <stop offset="100%" stopColor="#4A4A58" />
        </linearGradient>
        <linearGradient id="lumixaBarrel" x1="32" y1="8" x2="32" y2="56">
          <stop offset="0%" stopColor="#050508" />
          <stop offset="100%" stopColor="#181822" />
        </linearGradient>
        <radialGradient id="lumixaSapphireGlass" cx="38%" cy="36%" r="65%">
          <stop offset="0%" stopColor="#0EA5E9" />
          <stop offset="34%" stopColor="#0D2538" />
          <stop offset="68%" stopColor="#050508" />
          <stop offset="92%" stopColor="#E5A93C" />
          <stop offset="100%" stopColor="#050508" />
        </radialGradient>
      </defs>

      {/* 1. Outer Machined Titanium Barrel Ring */}
      <circle
        cx="32"
        cy="32"
        r="30.5"
        fill="url(#lumixaTitaniumRing)"
        stroke="#060609"
        strokeWidth="1.2"
      />

      {/* 2. Knurled Grip Ridges */}
      {ridges.map((r, i) => (
        <line
          key={i}
          x1={r.x1}
          y1={r.y1}
          x2={r.x2}
          y2={r.y2}
          stroke="rgba(255,255,255,0.24)"
          strokeWidth="1"
        />
      ))}

      {/* Gold/Amber Anodized Index Ring */}
      <circle
        cx="32"
        cy="32"
        r="25.5"
        fill="#08080C"
        stroke="#E5A93C"
        strokeWidth="1.4"
      />

      {/* 3. Deep Recessed Matte Black Lens Barrel */}
      <circle
        cx="32"
        cy="32"
        r="22.5"
        fill="url(#lumixaBarrel)"
        stroke="#262634"
        strokeWidth="1"
      />

      {/* 4. Multi-Coated Optical Sapphire/Amber Glass Element */}
      <circle
        cx="32"
        cy="32"
        r="19"
        fill="url(#lumixaSapphireGlass)"
        stroke="#1E293B"
        strokeWidth="1"
      />

      {/* 5. 6 Geometric Iris Aperture Blades */}
      {blades.map((b, idx) => (
        <line
          key={idx}
          x1={b.x1}
          y1={b.y1}
          x2={b.x2}
          y2={b.y2}
          stroke="rgba(229, 169, 60, 0.72)"
          strokeWidth="1.3"
          strokeLinecap="round"
        />
      ))}

      {/* Specular White Reflection Arc */}
      <path
        d="M 20 23 A 14.5 14.5 0 0 1 34 17.5"
        stroke="rgba(255, 255, 255, 0.76)"
        strokeWidth="1.8"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
};

export const ApertureLogoSvg = Lumixa3DLensLogo;

/**
 * LAW 2 & SECTION 3.2: 3D Machined Hardware Button (`HardwareButton` / `TactileHardwareButton`)
 * - Vertical metallic gradient (`#262632` top to `#14141B` bottom)
 * - `1px` top specular highlight (`#3E3E50` idle, `#E5A93C` or `#10B981` active)
 * - `1px` dark bottom bevel (`#08080B`)
 * - Built-in `7x7px` glowing 3D LED indicator dot (`#10B981` emerald or `#E5A93C` tungsten amber when active, recessed `#2A2A35` when off)
 * - Physical `+1px` travel and inverted gradient when pressed
 */
export interface HardwareButtonProps {
  label: string;
  active?: boolean;
  ledColor?: 'amber' | 'emerald' | 'crimson' | 'none';
  showLed?: boolean;
  fullWidth?: boolean;
  onClick: () => void;
  disabled?: boolean;
  title?: string;
  className?: string;
  height?: number;
}

export const HardwareButton: React.FC<HardwareButtonProps> = ({
  label,
  active = false,
  ledColor = 'amber',
  showLed,
  fullWidth = false,
  onClick,
  disabled = false,
  title,
  className = '',
  height = 32,
}) => {
  const [pressed, setPressed] = useState(false);
  const [hovered, setHovered] = useState(false);

  const shouldShowLed = showLed !== undefined ? showLed : ledColor !== 'none';

  const getGradient = () => {
    if (pressed && !disabled) {
      return 'linear-gradient(180deg, #111117 0%, #191922 100%)';
    }
    if (active) {
      if (ledColor === 'emerald') {
        return 'linear-gradient(180deg, #162E27 0%, #0D1C18 100%)';
      }
      if (ledColor === 'crimson') {
        return 'linear-gradient(180deg, #31151E 0%, #190B10 100%)';
      }
      return 'linear-gradient(180deg, #2D2518 0%, #17130C 100%)';
    }
    if (hovered && !disabled) {
      return 'linear-gradient(180deg, #2E2E3E 0%, #1A1A24 100%)';
    }
    return 'linear-gradient(180deg, #262632 0%, #14141B 100%)';
  };

  const getTopBorder = () => {
    if (active) {
      if (ledColor === 'emerald') return '#10B981';
      if (ledColor === 'crimson') return '#E11D48';
      return '#E5A93C';
    }
    return hovered && !disabled ? '#525268' : '#3E3E50';
  };

  const getTextColor = () => {
    if (disabled) return '#525260';
    if (active) {
      if (ledColor === 'emerald') return '#10B981';
      if (ledColor === 'crimson') return '#FB7185';
      return '#F5B945';
    }
    return hovered ? '#FFFFFF' : '#E4E4EC';
  };

  const getLedStyle = (): React.CSSProperties => {
    if (!active) {
      return {
        background: 'radial-gradient(circle at 35% 35%, #2A2A35 0%, #121218 100%)',
        boxShadow: 'inset 0 1px 2px #060608',
        border: '1px solid #08080B',
      };
    }
    if (ledColor === 'emerald') {
      return {
        background: 'radial-gradient(circle at 35% 35%, #6EE7B7 0%, #10B981 65%, #064E3B 100%)',
        boxShadow: '0 0 7px 1px rgba(16, 185, 129, 0.75)',
        border: '1px solid #052E16',
      };
    }
    if (ledColor === 'crimson') {
      return {
        background: 'radial-gradient(circle at 35% 35%, #FDA4AF 0%, #E11D48 65%, #881337 100%)',
        boxShadow: '0 0 7px 1px rgba(225, 29, 72, 0.75)',
        border: '1px solid #4C0519',
      };
    }
    return {
      background: 'radial-gradient(circle at 35% 35%, #FDE68A 0%, #E5A93C 65%, #78350F 100%)',
      boxShadow: '0 0 7px 1px rgba(229, 169, 60, 0.75)',
      border: '1px solid #451A03',
    };
  };

  return (
    <button
      type="button"
      disabled={disabled}
      title={title || label}
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => {
        setHovered(false);
        setPressed(false);
      }}
      onMouseDown={() => setPressed(true)}
      onMouseUp={() => setPressed(false)}
      className={`relative rounded-[5px] px-2.5 text-[10.5px] font-bold tracking-[0.25px] flex items-center ${
        fullWidth ? 'w-full' : ''
      } ${
        shouldShowLed ? 'justify-start gap-1.5' : 'justify-center'
      } select-none cursor-pointer disabled:cursor-not-allowed transition-transform focus:outline-none ${className}`}
      style={{
        height: `${height}px`,
        background: getGradient(),
        borderTop: `1px solid ${getTopBorder()}`,
        borderLeft: `1px solid ${active ? getTopBorder() : '#2A2A36'}`,
        borderRight: `1px solid ${active ? getTopBorder() : '#2A2A36'}`,
        borderBottom: '1px solid #08080B',
        boxShadow: pressed
          ? 'inset 0 2px 3px rgba(0,0,0,0.75)'
          : '0 1px 2px #060608',
        color: getTextColor(),
        transform: pressed && !disabled ? 'translateY(1px)' : 'translateY(0)',
      }}
    >
      {shouldShowLed && (
        <span
          className="w-[6px] h-[6px] rounded-full shrink-0"
          style={getLedStyle()}
        />
      )}
      <span className="truncate whitespace-nowrap">
        {label}
      </span>
    </button>
  );
};

export const TactileHardwareButton = HardwareButton;

/**
 * LAW 2 & SECTION 3.2: 3D Machined Fader Slider (`PrecisionHardwareSlider` / `MachinedFaderSlider`)
 * - Height: 48px
 * - Top row: Parameter Name (#D4D4D8 11px medium) + Value Readout Pill (#101015 recessed box with #E5A93C Consolas 11px bold readout)
 * - Bottom row: 11 engraved metallic ruler tick marks (#323240), recessed 5px groove (#09090D),
 *   active illuminated amber light-pipe bar (linear-gradient #B47B18 to #F5B945),
 *   and 3D Machined Titanium Fader Cap (20x14px rounded bevel rectangle with glowing #E5A93C center index line)
 * - Double-clicking resets to defaultValue.
 */
export interface PrecisionHardwareSliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  defaultValue: number;
  step?: number;
  decimals?: number;
  unit?: string;
  bipolar?: boolean;
  onChange: (val: number) => void;
}

export const PrecisionHardwareSlider: React.FC<PrecisionHardwareSliderProps> = ({
  label,
  value,
  min,
  max,
  defaultValue,
  step = 1,
  decimals = 0,
  unit = '',
  bipolar = false,
  onChange,
}) => {
  const [hovered, setHovered] = useState(false);
  const [dragging, setDragging] = useState(false);
  const trackRef = useRef<HTMLDivElement | null>(null);

  const clampAndSnap = (raw: number): number => {
    const clamped = Math.max(min, Math.min(max, raw));
    const steps = Math.round((clamped - min) / step);
    const snapped = Math.max(min, Math.min(max, min + steps * step));
    return Number(snapped.toFixed(Math.max(0, decimals + 1)));
  };

  const formatVal = (v: number): string => {
    const clean = Math.abs(v) < 1e-6 ? 0 : v;
    const str = decimals === 0 ? `${Math.round(clean)}` : clean.toFixed(decimals);
    const plus = bipolar && clean > 1e-5 ? '+' : '';
    return `${plus}${str}${unit}`;
  };

  const updateFromClientX = (clientX: number) => {
    if (!trackRef.current) return;
    const rect = trackRef.current.getBoundingClientRect();
    const pad = 10;
    const usable = Math.max(1, rect.width - pad * 2);
    const norm = Math.max(0, Math.min(1, (clientX - (rect.left + pad)) / usable));
    onChange(clampAndSnap(min + norm * (max - min)));
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    e.preventDefault();
    setDragging(true);
    updateFromClientX(e.clientX);

    const onMove = (me: MouseEvent) => updateFromClientX(me.clientX);
    const onUp = () => {
      setDragging(false);
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  };

  const span = Math.max(1e-6, max - min);
  const normVal = Math.max(0, Math.min(1, (value - min) / span));
  const normZero = Math.max(0, Math.min(1, (0 - min) / span));

  let fillLeftPct = 0;
  let fillWidthPct = normVal * 100;
  if (bipolar && min < 0 && max > 0) {
    const l = Math.min(normZero, normVal);
    const r = Math.max(normZero, normVal);
    fillLeftPct = l * 100;
    fillWidthPct = (r - l) * 100;
  }

  return (
    <div
      className="h-[48px] flex flex-col justify-between select-none"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onDoubleClick={() => onChange(defaultValue)}
      title="Double-click anywhere on fader to reset to factory default"
    >
      {/* Top Row: Parameter Name + Recessed Readout Box */}
      <div className="flex items-center justify-between gap-2">
        <span
          className="text-[11px] font-semibold truncate"
          style={{ color: hovered || dragging ? '#F4F4F6' : '#D4D4D8' }}
        >
          {label}
        </span>
        <span
          className="h-[19px] min-w-[52px] px-1.5 rounded-[3px] flex items-center justify-center font-mono text-[11px] font-bold tabular-nums shrink-0"
          style={{
            backgroundColor: '#101015',
            border: '1px solid #262634',
            color: '#E5A93C',
          }}
        >
          {formatVal(value)}
        </span>
      </div>

      {/* Bottom Row: 11 Engraved Ruler Ticks + 5px Groove + 3D Titanium Fader Cap */}
      <div
        ref={trackRef}
        role="slider"
        aria-label={label}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={value}
        tabIndex={0}
        onMouseDown={handleMouseDown}
        onKeyDown={(e) => {
          if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
            e.preventDefault();
            onChange(clampAndSnap(value + step));
          } else if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
            e.preventDefault();
            onChange(clampAndSnap(value - step));
          } else if (e.key === 'Home') {
            e.preventDefault();
            onChange(defaultValue);
          }
        }}
        className="relative h-[24px] flex items-center px-[10px] cursor-pointer focus:outline-none"
      >
        <div className="relative w-full h-full flex items-center">
          {/* 11 Engraved Metallic Ruler Tick Marks */}
          {Array.from({ length: 11 }).map((_, idx) => {
            const major = idx === 0 || idx === 5 || idx === 10;
            return (
              <span
                key={idx}
                className="absolute top-1/2 -translate-y-1/2 pointer-events-none"
                style={{
                  left: `${idx * 10}%`,
                  width: '1px',
                  height: major ? '16px' : '11px',
                  backgroundColor: major ? '#48485A' : '#323240',
                }}
              />
            );
          })}

          {/* Recessed 5px Groove */}
          <div
            className="relative w-full h-[5px] rounded-[2.5px] overflow-hidden"
            style={{
              backgroundColor: '#09090D',
              border: '1px solid #262634',
            }}
          >
            <div
              className="absolute top-0 bottom-0 rounded-[2px]"
              style={{
                left: `${fillLeftPct}%`,
                width: `${fillWidthPct}%`,
                background: 'linear-gradient(90deg, #B47B18 0%, #F5B945 100%)',
              }}
            />
          </div>

          {/* 3D Machined Titanium Fader Cap (20x14px with glowing #E5A93C center index line) */}
          <div
            className="pointer-events-none absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-[20px] h-[14px] rounded-[3px] flex items-center justify-center"
            style={{
              left: `${normVal * 100}%`,
              background:
                hovered || dragging
                  ? 'linear-gradient(180deg, #4A4A5C 0%, #2E2E3C 50%, #181822 100%)'
                  : 'linear-gradient(180deg, #3E3E4E 0%, #252532 50%, #14141C 100%)',
              border: `1px solid ${hovered || dragging ? '#62627A' : '#3E3E50'}`,
              boxShadow: '0 2px 4px rgba(0,0,0,0.75)',
            }}
          >
            {/* Glowing #E5A93C vertical center index line */}
            <span
              className="w-[2px] h-[10px] rounded-[1px]"
              style={{
                backgroundColor: '#E5A93C',
                boxShadow: '0 0 4px rgba(229, 169, 60, 0.8)',
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export const MachinedFaderSlider = PrecisionHardwareSlider;

/**
 * 60x60px 3-Layer 3D Metallic Mechanical Shutter Button
 */
export const MechanicalShutterButton: React.FC<{ onClick: () => void }> = ({
  onClick,
}) => {
  const [hovered, setHovered] = useState(false);
  const [pressed, setPressed] = useState(false);

  return (
    <button
      type="button"
      aria-label="Take Photo Snapshot"
      title="3D Mechanical Shutter Release (Capture Master Still)"
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => {
        setHovered(false);
        setPressed(false);
      }}
      onMouseDown={() => setPressed(true)}
      onMouseUp={() => setPressed(false)}
      className="w-[60px] h-[60px] flex items-center justify-center cursor-pointer focus:outline-none shrink-0"
    >
      <svg width="60" height="60" viewBox="0 0 60 60">
        <defs>
          <linearGradient id="shutterBezel" x1="0" y1="0" x2="60" y2="60">
            <stop offset="0%" stopColor="#68687C" />
            <stop offset="35%" stopColor="#22222C" />
            <stop offset="70%" stopColor="#525264" />
            <stop offset="100%" stopColor="#1A1A22" />
          </linearGradient>
          <radialGradient id="shutterPlunger" cx="38%" cy="35%" r="65%">
            <stop offset="0%" stopColor={hovered ? '#FFFBEB' : '#FFFFFF'} />
            <stop offset="65%" stopColor={hovered ? '#F5B945' : '#E4E4EC'} />
            <stop offset="100%" stopColor={hovered ? '#B47B18' : '#9E9EAE'} />
          </radialGradient>
        </defs>
        <circle
          cx="30"
          cy="30"
          r="27.5"
          fill="url(#shutterBezel)"
          stroke={hovered ? '#E5A93C' : '#08080C'}
          strokeWidth="1.5"
        />
        <circle
          cx="30"
          cy="30"
          r="22"
          fill="#0B0B10"
          stroke="#09090D"
          strokeWidth="1.2"
        />
        <circle
          cx="30"
          cy={pressed ? 31 : 30}
          r={pressed ? 17.5 : 19.5}
          fill="url(#shutterPlunger)"
          stroke="#181820"
          strokeWidth="1"
        />
      </svg>
    </button>
  );
};

/**
 * 60x60px 3-Layer 3D Metallic Cinema Record Button with Crimson Tally Halo
 */
export const CinemaRecordButton: React.FC<{
  recording: boolean;
  onClick: () => void;
}> = ({ recording, onClick }) => {
  const [hovered, setHovered] = useState(false);
  const [pressed, setPressed] = useState(false);

  return (
    <button
      type="button"
      aria-label={recording ? 'Stop Recording' : 'Start Video Recording'}
      title={
        recording
          ? 'Stop 1.0x Wall-Clock CFR Recording'
          : 'Start 1.0x Wall-Clock CFR Recording'
      }
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => {
        setHovered(false);
        setPressed(false);
      }}
      onMouseDown={() => setPressed(true)}
      onMouseUp={() => setPressed(false)}
      className="w-[60px] h-[60px] flex items-center justify-center cursor-pointer focus:outline-none shrink-0"
    >
      <svg width="60" height="60" viewBox="0 0 60 60">
        <defs>
          <linearGradient id="recBezel" x1="0" y1="0" x2="60" y2="60">
            <stop offset="0%" stopColor="#646478" />
            <stop offset="35%" stopColor="#1E1E28" />
            <stop offset="70%" stopColor="#4E4E60" />
            <stop offset="100%" stopColor="#181820" />
          </linearGradient>
          <radialGradient id="recPlunger" cx="38%" cy="35%" r="65%">
            <stop offset="0%" stopColor="#FB7185" />
            <stop offset="55%" stopColor="#E11D48" />
            <stop offset="100%" stopColor="#881337" />
          </radialGradient>
        </defs>
        <circle
          cx="30"
          cy="30"
          r="27.5"
          fill="url(#recBezel)"
          stroke={recording || hovered ? '#E11D48' : '#08080C'}
          strokeWidth={recording ? '2' : '1.4'}
        />
        <circle
          cx="30"
          cy="30"
          r="22"
          fill="#0B0B10"
          stroke="#09090D"
          strokeWidth="1.2"
        />
        {recording ? (
          <rect
            x={pressed ? 20.5 : 19.5}
            y={pressed ? 21.5 : 19.5}
            width={pressed ? 19 : 21}
            height={pressed ? 19 : 21}
            rx="4.5"
            fill="url(#recPlunger)"
            stroke="#181820"
            strokeWidth="1"
          />
        ) : (
          <circle
            cx="30"
            cy={pressed ? 31 : 30}
            r={pressed ? 16.5 : 18}
            fill="url(#recPlunger)"
            stroke="#181820"
            strokeWidth="1"
          />
        )}
      </svg>
    </button>
  );
};

/**
 * 3D Machined Hardware Card Container
 */
export const StudioHardwareCard: React.FC<{
  title: string;
  children: React.ReactNode;
}> = ({ title, children }) => (
  <section
    className="rounded-[6px] p-[13px] flex flex-col gap-[10px]"
    style={{
      background: 'linear-gradient(180deg, #171720 0%, #111118 100%)',
      borderTop: '1px solid #2E2E3C',
      borderLeft: '1px solid #242430',
      borderRight: '1px solid #242430',
      borderBottom: '1px solid #09090D',
      boxShadow: '0 2px 5px rgba(0,0,0,0.45)',
    }}
  >
    <div className="flex items-center justify-between border-b border-[#242432] pb-1.5">
      <h3
        className="text-[10px] font-bold uppercase tracking-[1.2px]"
        style={{ color: '#A1A1B0' }}
      >
        {title}
      </h3>
    </div>
    <div className="flex flex-col gap-2.5">{children}</div>
  </section>
);
