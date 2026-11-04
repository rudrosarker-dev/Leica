import React, { useState } from "react";
import { HardwareButton } from "./StudioWidgets";

export interface RepoFileEntry {
  path: string;
  exists: boolean;
  lines: number;
  sizeBytes: number;
  content: string;
}

export interface CapturedItem {
  id: string;
  timestamp: string;
  format: string;
  resolution: string;
  dataUrl: string;
}

export const PythonRepoModal: React.FC<{
  open: boolean;
  onClose: () => void;
  repoFiles: RepoFileEntry[];
}> = ({ open, onClose, repoFiles }) => {
  const [selectedPath, setSelectedPath] = useState<string>("README.md");
  const [copiedFile, setCopiedFile] = useState<string>("");

  if (!open) return null;

  const activeFile = repoFiles.find((f) => f.path === selectedPath) || repoFiles[0];
  const totalLines = repoFiles.reduce((acc, f) => acc + f.lines, 0);

  const handleCopy = (text: string, label: string) => {
    navigator.clipboard?.writeText(text);
    setCopiedFile(label);
    setTimeout(() => setCopiedFile(""), 2000);
  };

  const handleDownloadFile = (entry: RepoFileEntry) => {
    const blob = new Blob([entry.content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = entry.path.replace(/\//g, "_");
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Python Desktop Repository and GitHub Export Inspector"
      className="fixed inset-0 z-50 flex items-center justify-center p-6"
      style={{ backgroundColor: "rgba(7, 7, 9, 0.88)" }}
    >
      <div
        className="w-full max-w-[1180px] h-[82vh] rounded-[6px] flex flex-col overflow-hidden"
        style={{
          background: "linear-gradient(180deg, #16161D 0%, #0E0E13 100%)",
          border: "1px solid #2A2A35",
          boxShadow: "0 16px 40px rgba(0,0,0,0.75)",
        }}
      >
        {/* Modal Header */}
        <div
          className="h-[48px] px-4 flex items-center justify-between shrink-0"
          style={{
            background: "linear-gradient(180deg, #1A1A22 0%, #0E0E13 100%)",
            borderBottom: "1px solid #262632",
          }}
        >
          <div className="flex items-center gap-3">
            <span className="text-[12px] font-bold tracking-[1.4px] text-[#F4F4F6]">
              LUMIXA PRO // NATIVE PYTHON (PyQt6) DESKTOP REPOSITORY
            </span>
            <span className="font-mono text-[11px] text-[#10B981]">
              {repoFiles.length} FILES · {totalLines.toLocaleString()} LINES VERIFIED
            </span>
          </div>
          <div className="flex items-center gap-2">
            {activeFile && (
              <>
                <HardwareButton
                  label={
                    copiedFile === activeFile.path
                      ? "COPIED TO CLIPBOARD"
                      : `COPY ${activeFile.path}`
                  }
                  active={copiedFile === activeFile.path}
                  ledColor="emerald"
                  onClick={() => handleCopy(activeFile.content, activeFile.path)}
                />
                <HardwareButton
                  label="DOWNLOAD FILE"
                  active={true}
                  ledColor="amber"
                  onClick={() => handleDownloadFile(activeFile)}
                />
              </>
            )}
            <HardwareButton label="CLOSE" showLed={false} onClick={onClose} />
          </div>
        </div>

        {/* Body: Left File Tree + Right Source Code Viewer */}
        <div className="flex-1 flex min-h-0">
          <aside
            className="w-[270px] shrink-0 overflow-y-auto p-3 flex flex-col gap-1"
            style={{
              backgroundColor: "#0A0A0D",
              borderRight: "1px solid #22222B",
            }}
          >
            <div className="text-[10px] font-bold uppercase tracking-[1.2px] text-[#71717A] mb-1 px-2">
              REPOSITORY FILE TREE ({repoFiles.length})
            </div>
            {repoFiles.map((file) => {
              const active = activeFile?.path === file.path;
              return (
                <button
                  key={file.path}
                  type="button"
                  onClick={() => setSelectedPath(file.path)}
                  className="w-full px-2.5 py-2 rounded-[4px] flex items-center justify-between text-left cursor-pointer transition-colors"
                  style={{
                    background: active
                      ? "linear-gradient(180deg, #2D261B 0%, #1B1710 100%)"
                      : "linear-gradient(180deg, #181820 0%, #101016 100%)",
                    borderTop: active ? "1px solid #E5A93C" : "1px solid #262632",
                    borderBottom: "1px solid #08080B",
                    borderLeft: active ? "1px solid #B88222" : "1px solid #1C1C26",
                    borderRight: active ? "1px solid #B88222" : "1px solid #1C1C26",
                    color: active ? "#F5D08A" : "#D4D4DC",
                  }}
                >
                  <span className="font-mono text-[11px] truncate">{file.path}</span>
                  <span className="font-mono text-[10px] text-[#9CA3AF] shrink-0 ml-2">
                    {file.lines}L
                  </span>
                </button>
              );
            })}
          </aside>

          <div className="flex-1 flex flex-col min-w-0 bg-[#070709]">
            <div
              className="h-[34px] px-4 flex items-center justify-between text-[11px] font-mono"
              style={{
                background: "linear-gradient(180deg, #16161E 0%, #0E0E14 100%)",
                borderBottom: "1px solid #22222B",
              }}
            >
              <span className="text-[#E5A93C] font-semibold">{activeFile?.path}</span>
              <span className="text-[#9CA3AF]">
                {activeFile?.lines} lines · {((activeFile?.sizeBytes ?? 0) / 1024).toFixed(1)} KB · UTF-8
              </span>
            </div>
            <pre className="flex-1 p-4 overflow-auto font-mono text-[11.5px] leading-[1.55] text-[#F4F4F6] select-text">
              <code>{activeFile?.content || ""}</code>
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};

export const StudioGalleryModal: React.FC<{
  open: boolean;
  onClose: () => void;
  captures: CapturedItem[];
  onClearGallery: () => void;
}> = ({ open, onClose, captures, onClearGallery }) => {
  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Studio Media Gallery"
      className="fixed inset-0 z-50 flex items-center justify-center p-6"
      style={{ backgroundColor: "rgba(7, 7, 9, 0.88)" }}
    >
      <div
        className="w-full max-w-[960px] h-[76vh] rounded-[6px] flex flex-col overflow-hidden"
        style={{
          background: "linear-gradient(180deg, #16161D 0%, #0E0E13 100%)",
          border: "1px solid #2A2A35",
          boxShadow: "0 16px 40px rgba(0,0,0,0.75)",
        }}
      >
        <div
          className="h-[48px] px-4 flex items-center justify-between shrink-0"
          style={{
            background: "linear-gradient(180deg, #1A1A22 0%, #0E0E13 100%)",
            borderBottom: "1px solid #262632",
          }}
        >
          <div className="flex items-center gap-3">
            <span className="text-[12px] font-bold tracking-[1.4px] text-[#F4F4F6]">
              LUMIXA PRO MEDIA GALLERY // ~/Pictures/Lumixa_Pro_Studio
            </span>
            <span className="font-mono text-[11px] text-[#E5A93C]">
              {captures.length} CAPTURED ASSETS
            </span>
          </div>
          <div className="flex items-center gap-2">
            {captures.length > 0 && (
              <HardwareButton
                label="CLEAR SESSION"
                showLed={false}
                onClick={onClearGallery}
              />
            )}
            <HardwareButton label="CLOSE" showLed={false} onClick={onClose} />
          </div>
        </div>

        <div className="flex-1 p-4 overflow-y-auto">
          {captures.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center gap-2">
              <div className="text-[13px] font-semibold text-[#F4F4F6]">
                No Studio Stills Captured in Current Session
              </div>
              <div className="text-[11px] text-[#9CA3AF] max-w-md">
                Use the 60px Mechanical Shutter Release or BURST 3X button on the Bottom EVF Bar to capture graded still frames with your active 1D/3D LUT and broadcast overlays.
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {captures.map((item) => (
                <div
                  key={item.id}
                  className="rounded-[6px] p-2.5 flex flex-col gap-2"
                  style={{
                    background: "linear-gradient(180deg, #16161D 0%, #0F0F14 100%)",
                    border: "1px solid #262632",
                  }}
                >
                  <img
                    src={item.dataUrl}
                    alt={`Studio capture ${item.timestamp}`}
                    referrerPolicy="no-referrer"
                    className="w-full aspect-video object-cover rounded-[4px] border border-[#2C2C38]"
                  />
                  <div className="flex items-center justify-between text-[11px] font-mono">
                    <span className="text-[#F4F4F6]">{item.timestamp}</span>
                    <span className="text-[#E5A93C]">
                      {item.resolution} · {item.format}
                    </span>
                  </div>
                  <a
                    href={item.dataUrl}
                    download={`LUMIXA_C270_${item.timestamp}.${item.format.includes("JPG") ? "jpg" : "png"}`}
                    className="h-[28px] rounded-[4px] flex items-center justify-center text-[11px] font-semibold no-underline"
                    style={{
                      background: "linear-gradient(180deg, #2D261B 0%, #1B1710 100%)",
                      border: "1px solid #E5A93C",
                      color: "#F5D08A",
                    }}
                  >
                    DOWNLOAD MASTER FRAME
                  </a>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
