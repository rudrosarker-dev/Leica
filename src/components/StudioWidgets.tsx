import React, { useState, useRef } from "react";

/**
 * Geometric 6-Blade Leica Aperture SVG Icon (20x20px, #E5A93C) — Zero Emojis
 */
export const ApertureLogoSvg: React.FC<{ size?: number }> = ({ size = 20 }) => {
  const cx = 10;
  const cy = 10;
  const rOuter = 8.4;
  const rInner = 3.6;

  const blades: { x1: number; y1: number; x2: number; y2: number }[] = [];
  for (let i = 0; i < 6; i++) {
    const a1 = ((i * 60 + 15) * Math.PI) / 180;
    const a2 = ((i * 60 + 70) * Math.PI) / 180;
    blades.push({
      x1: cx + rInner * Math.cos(a1),
      y1: cy + rInner * Math.sin(a1),
      x2: cx + rOuter * 0.94 * Math.cos(a2),
      y2: cy + rOuter * 0.94 * Math.sin(a2),
    });
  }

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      aria-hidden="true"
      className="shrink-0"
    >
      <circle cx={cx} cy={cy} r={rOuter} stroke="#E5A93C" strokeWidth="1.5" />
      {blades.map((b, idx) => (
        <line
          key={idx}
          x1={b.x1}
          y1={b.y1}
          x2={b.x2}
          y2={b.y2}
          stroke="#E5A93C"
          strokeWidth="1.4"
          strokeLinecap="round"
        />
      ))}
    </svg>
  );
};

/**
 * Circular Arrow Arc Refresh Vector Icon (14x14px inside 28x28px button)
 */
export const RefreshIconSvg: React.FC = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path
      d="M13.5 8A5.5 5.5 0 1 1 11.8 4.1"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
    />
    <path
      d="M12.2 1.8V4.6H9.4"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

/**
 * Elevated Card / Section Group Container (#15151B, 1px solid #22222B, 6px radius)
 */
export const InspectorCard: React.FC<{
  title: string;
  children: React.ReactNode;
}> = ({ title, children }) => (
  <section
    className="rounded-[6px] p-3 flex flex-col gap-2.5"
    style={{
      backgroundColor: "#15151B",
      border: "1px solid #22222B",
    }}
  >
    <div className="flex items-center justify-between border-b border-[#22222B] pb-1.5">
      <h3
        className="text-[10px] font-bold uppercase tracking-[1.2px] select-none"
        style={{ color: "#71717A" }}
      >
        {title}
      </h3>
    </div>
    <div className="flex flex-col gap-2">{children}</div>
  </section>
);

/**
 * PrecisionSlider Compound Widget (Fixed Height: 44px)
 * - Top Row: Parameter Title (#9CA3AF -> #F4F4F6 on hover) + Formatted Readout (Consolas 11px #E5A93C)
 * - Bottom Row: Custom Groove Slider with Bipolar/Unipolar fill, Double-Click reset to defaultValue,
 *   and Shift-Wheel protection so parent scroll areas scroll smoothly.
 */
export interface PrecisionSliderProps {
  title: string;
  min: number;
  max: number;
  defaultValue: number;
  value: number;
  step?: number;
  decimals?: number;
  suffix?: string;
  bipolar?: boolean;
  showPlus?: boolean;
  onChange: (val: number) => void;
}

export const PrecisionSlider: React.FC<PrecisionSliderProps> = ({
  title,
  min,
  max,
  defaultValue,
  value,
  step = 1,
  decimals = 0,
  suffix = "",
  bipolar = false,
  showPlus = false,
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

  const formatValue = (v: number): string => {
    const clean = Math.abs(v) < 1e-6 ? 0 : v;
    const str = decimals === 0 ? `${Math.round(clean)}` : clean.toFixed(decimals);
    const prefix = (bipolar || showPlus) && clean > 1e-5 ? "+" : "";
    return `${prefix}${str}${suffix}`;
  };

  const updateFromClientX = (clientX: number) => {
    if (!trackRef.current) return;
    const rect = trackRef.current.getBoundingClientRect();
    const pad = 7;
    const usable = Math.max(1, rect.width - pad * 2);
    const norm = Math.max(0, Math.min(1, (clientX - (rect.left + pad)) / usable));
    const nextVal = clampAndSnap(min + norm * (max - min));
    onChange(nextVal);
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    e.preventDefault();
    setDragging(true);
    updateFromClientX(e.clientX);

    const onMouseMove = (me: MouseEvent) => {
      updateFromClientX(me.clientX);
    };
    const onMouseUp = () => {
      setDragging(false);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
  };

  const handleDoubleClick = () => {
    onChange(defaultValue);
  };

  const handleWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    // Scroll-wheel protection: only adjust slider if Shift is held
    if (!e.shiftKey) return;
    e.preventDefault();
    e.stopPropagation();
    const dir = e.deltaY < 0 ? 1 : -1;
    onChange(clampAndSnap(value + dir * step));
  };

  const span = Math.max(1e-6, max - min);
  const normVal = Math.max(0, Math.min(1, (value - min) / span));
  const normZero = Math.max(0, Math.min(1, (0 - min) / span));

  let fillLeftPct = 0;
  let fillWidthPct = normVal * 100;

  if (bipolar && min < 0 && max > 0) {
    const leftNorm = Math.min(normZero, normVal);
    const rightNorm = Math.max(normZero, normVal);
    fillLeftPct = leftNorm * 100;
    fillWidthPct = (rightNorm - leftNorm) * 100;
  }

  return (
    <div
      className="h-[44px] flex flex-col justify-between select-none"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onDoubleClick={handleDoubleClick}
      onWheel={handleWheel}
      title="Double-click to reset to default. Hold Shift + Scroll for fine step adjustment."
    >
      <div className="flex items-center justify-between">
        <span
          className="text-[11px] transition-colors truncate"
          style={{
            color: hovered || dragging ? "#F4F4F6" : "#9CA3AF",
            fontWeight: hovered || dragging ? 500 : 400,
          }}
        >
          {title}
        </span>
        <span
          className="font-mono text-[11px] font-semibold tabular-nums shrink-0"
          style={{ color: "#E5A93C" }}
        >
          {formatValue(value)}
        </span>
      </div>

      <div
        ref={trackRef}
        role="slider"
        aria-label={title}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={value}
        tabIndex={0}
        onMouseDown={handleMouseDown}
        onKeyDown={(e) => {
          if (e.key === "ArrowRight" || e.key === "ArrowUp") {
            e.preventDefault();
            onChange(clampAndSnap(value + step));
          } else if (e.key === "ArrowLeft" || e.key === "ArrowDown") {
            e.preventDefault();
            onChange(clampAndSnap(value - step));
          } else if (e.key === "Home") {
            e.preventDefault();
            onChange(defaultValue);
          }
        }}
        className="relative h-[20px] flex items-center cursor-pointer px-[7px]"
      >
        <div className="relative w-full h-[4px] rounded-[2px] bg-[#262630]">
          {bipolar && min < 0 && max > 0 && (
            <div
              className="absolute top-[-3px] w-[1px] h-[10px] bg-[#71717A]"
              style={{ left: `${normZero * 100}%` }}
            />
          )}
          <div
            className="absolute top-0 h-[4px] rounded-[2px]"
            style={{
              left: `${fillLeftPct}%`,
              width: `${fillWidthPct}%`,
              backgroundColor: "#E5A93C",
            }}
          />
          <div
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-[14px] h-[14px] rounded-full transition-colors"
            style={{
              left: `${normVal * 100}%`,
              backgroundColor: hovered || dragging ? "#E5A93C" : "#F4F4F6",
              border: "2px solid #0E0E12",
            }}
          />
        </div>
      </div>
    </div>
  );
};

/**
 * Custom Toggle Switch Widget
 */
export const ToggleSwitch: React.FC<{
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}> = ({ label, checked, onChange }) => (
  <button
    type="button"
    role="switch"
    aria-checked={checked}
    onClick={() => onChange(!checked)}
    className="w-full h-[24px] flex items-center justify-between text-left cursor-pointer group focus:outline-none"
  >
    <span
      className="text-[11px] truncate pr-2 transition-colors"
      style={{
        color: checked ? "#F4F4F6" : "#9CA3AF",
        fontWeight: checked ? 500 : 400,
      }}
    >
      {label}
    </span>
    <span
      className="relative w-[34px] h-[18px] rounded-full shrink-0 transition-colors"
      style={{
        backgroundColor: checked ? "rgba(229, 169, 60, 0.22)" : "#1C1C24",
        border: checked ? "1px solid #E5A93C" : "1px solid #2C2C38",
      }}
    >
      <span
        className="absolute top-1/2 -translate-y-1/2 w-[12px] h-[12px] rounded-full transition-transform"
        style={{
          left: checked ? "18px" : "3px",
          backgroundColor: checked ? "#E5A93C" : "#71717A",
        }}
      />
    </span>
  </button>
);

/**
 * Custom Segmented Bar (for 2-option Super-Resolution or 3-Tab Right Dock)
 */
export const SegmentedBar: React.FC<{
  options: string[];
  activeIndex: number;
  onSelect: (index: number) => void;
  height?: number;
}> = ({ options, activeIndex, onSelect, height = 30 }) => (
  <div className="flex items-center gap-1 w-full" style={{ height: `${height}px` }}>
    {options.map((label, idx) => {
      const active = idx === activeIndex;
      return (
        <button
          key={label}
          type="button"
          onClick={() => onSelect(idx)}
          className="flex-1 h-full px-1.5 rounded-[4px] text-[9.5px] font-bold tracking-[0.5px] uppercase whitespace-nowrap shrink-0 cursor-pointer transition-colors"
          style={{
            backgroundColor: active ? "#262118" : "#15151B",
            border: active ? "1px solid #E5A93C" : "1px solid #22222B",
            color: active ? "#E5A93C" : "#9CA3AF",
          }}
        >
          {label}
        </button>
      );
    })}
  </div>
);

/**
 * Primary Shutter Release Button (Still Photo, 52x52px)
 * Outer 2px ring #F4F4F6 (48x48px), inner solid #F4F4F6 circle (38x38px, turns #E5A93C on hover,
 * shrinks to 34x34px on mouse press).
 */
export const ShutterReleaseButton: React.FC<{ onClick: () => void }> = ({ onClick }) => {
  const [hovered, setHovered] = useState(false);
  const [pressed, setPressed] = useState(false);

  return (
    <button
      type="button"
      aria-label="Capture Still Photo"
      title="Capture Still Photo (Shutter Release)"
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => {
        setHovered(false);
        setPressed(false);
      }}
      onMouseDown={() => setPressed(true)}
      onMouseUp={() => setPressed(false)}
      className="w-[52px] h-[52px] flex items-center justify-center cursor-pointer focus:outline-none shrink-0"
    >
      <svg width="52" height="52" viewBox="0 0 52 52">
        <circle
          cx="26"
          cy="26"
          r="23"
          fill="#0A0A0D"
          stroke={hovered ? "#E5A93C" : "#F4F4F6"}
          strokeWidth="2"
        />
        <circle
          cx="26"
          cy="26"
          r={pressed ? 17 : 19}
          fill={hovered ? "#E5A93C" : "#F4F4F6"}
        />
      </svg>
    </button>
  );
};

/**
 * Primary Cinema Record Button (Video, 52x52px)
 * Outer 2px ring #71717A (#E11D48 when recording), inner 34x34px circle #E11D48 when idle;
 * morphs into a 20x20px rounded crimson square (4px radius) when recording is active.
 */
export const CinemaRecordButton: React.FC<{
  recording: boolean;
  onClick: () => void;
}> = ({ recording, onClick }) => {
  const [hovered, setHovered] = useState(false);

  return (
    <button
      type="button"
      aria-label={recording ? "Stop Video Recording" : "Start Video Recording"}
      title={recording ? "Stop Master MP4 Recording" : "Start Master MP4 Recording"}
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="w-[52px] h-[52px] flex items-center justify-center cursor-pointer focus:outline-none shrink-0"
    >
      <svg width="52" height="52" viewBox="0 0 52 52">
        <circle
          cx="26"
          cy="26"
          r="23"
          fill="#0A0A0D"
          stroke={recording || hovered ? "#E11D48" : "#71717A"}
          strokeWidth="2"
        />
        {recording ? (
          <rect x="16" y="16" width="20" height="20" rx="4" fill="#E11D48" />
        ) : (
          <circle cx="26" cy="26" r="17" fill="#E11D48" />
        )}
      </svg>
    </button>
  );
};

/**
 * Pause / Resume Recording Button (36x36px)
 */
export const PauseRecordButton: React.FC<{
  enabled: boolean;
  paused: boolean;
  onClick: () => void;
}> = ({ enabled, paused, onClick }) => (
  <button
    type="button"
    disabled={!enabled}
    aria-label={paused ? "Resume Recording" : "Pause Recording"}
    title="Pause / Resume Active Recording"
    onClick={onClick}
    className="w-[36px] h-[36px] flex items-center justify-center cursor-pointer disabled:cursor-not-allowed focus:outline-none shrink-0"
  >
    <svg width="36" height="36" viewBox="0 0 36 36">
      <circle
        cx="18"
        cy="18"
        r="16.5"
        fill={enabled ? "#1C1C24" : "#121217"}
        stroke={paused ? "#E5A93C" : enabled ? "#3E3E4E" : "#22222B"}
        strokeWidth="1.5"
      />
      {paused ? (
        <polygon points="14,12 24.5,18 14,24" fill="#E5A93C" />
      ) : (
        <g fill={enabled ? "#F4F4F6" : "#52525B"}>
          <rect x="13" y="12" width="3.2" height="12" rx="1" />
          <rect x="19.8" y="12" width="3.2" height="12" rx="1" />
        </g>
      )}
    </svg>
  </button>
);
