import React, { useState } from "react";

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
      style={{ backgroundColor: "rgba(7, 7, 9, 0.86)" }}
    >
      <div
        className="w-full max-w-[1180px] h-[82vh] rounded-[6px] flex flex-col overflow-hidden"
        style={{
          backgroundColor: "#0E0E12",
          border: "1px solid #2C2C38",
        }}
      >
        {/* Modal Header */}
        <div
          className="h-[48px] px-4 flex items-center justify-between shrink-0"
          style={{
            backgroundColor: "#0A0A0D",
            borderBottom: "1px solid #22222B",
          }}
        >
          <div className="flex items-center gap-3">
            <span className="text-[12px] font-bold tracking-[1.4px] text-[#F4F4F6]">
              NATIVE PYTHON (PyQt6) DESKTOP REPOSITORY // GITHUB EXPORT READY
            </span>
            <span className="font-mono text-[11px] text-[#10B981]">
              {repoFiles.length} FILES · {totalLines.toLocaleString()} LINES VERIFIED
            </span>
          </div>
          <div className="flex items-center gap-2">
            {activeFile && (
              <>
                <button
                  type="button"
                  onClick={() => handleCopy(activeFile.content, activeFile.path)}
                  className="h-[28px] px-3 rounded-[4px] text-[11px] font-semibold cursor-pointer"
                  style={{
                    backgroundColor: "#1C1C24",
                    border: "1px solid #2C2C38",
                    color: copiedFile === activeFile.path ? "#10B981" : "#F4F4F6",
                  }}
                >
                  {copiedFile === activeFile.path ? "COPIED TO CLIPBOARD" : `COPY ${activeFile.path}`}
                </button>
                <button
                  type="button"
                  onClick={() => handleDownloadFile(activeFile)}
                  className="h-[28px] px-3 rounded-[4px] text-[11px] font-semibold cursor-pointer"
                  style={{
                    backgroundColor: "#262118",
                    border: "1px solid #E5A93C",
                    color: "#E5A93C",
                  }}
                >
                  DOWNLOAD FILE
                </button>
              </>
            )}
            <button
              type="button"
              onClick={onClose}
              className="h-[28px] px-3 rounded-[4px] text-[11px] font-semibold cursor-pointer"
              style={{
                backgroundColor: "#1C1C24",
                border: "1px solid #2C2C38",
                color: "#F4F4F6",
              }}
            >
              CLOSE
            </button>
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
              REPOSITORY FILE TREE
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
                    backgroundColor: active ? "#262118" : "transparent",
                    border: active ? "1px solid #E5A93C" : "1px solid transparent",
                    color: active ? "#E5A93C" : "#F4F4F6",
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
                backgroundColor: "#15151B",
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
      style={{ backgroundColor: "rgba(7, 7, 9, 0.86)" }}
    >
      <div
        className="w-full max-w-[960px] h-[76vh] rounded-[6px] flex flex-col overflow-hidden"
        style={{
          backgroundColor: "#0E0E12",
          border: "1px solid #2C2C38",
        }}
      >
        <div
          className="h-[48px] px-4 flex items-center justify-between shrink-0"
          style={{
            backgroundColor: "#0A0A0D",
            borderBottom: "1px solid #22222B",
          }}
        >
          <div className="flex items-center gap-3">
            <span className="text-[12px] font-bold tracking-[1.4px] text-[#F4F4F6]">
              STUDIO MEDIA GALLERY // ~/Pictures/C270_Optix_Studio
            </span>
            <span className="font-mono text-[11px] text-[#E5A93C]">
              {captures.length} CAPTURED ASSETS
            </span>
          </div>
          <div className="flex items-center gap-2">
            {captures.length > 0 && (
              <button
                type="button"
                onClick={onClearGallery}
                className="h-[28px] px-3 rounded-[4px] text-[11px] font-semibold cursor-pointer"
                style={{
                  backgroundColor: "#1C1C24",
                  border: "1px solid #2C2C38",
                  color: "#9CA3AF",
                }}
              >
                CLEAR SESSION
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="h-[28px] px-3 rounded-[4px] text-[11px] font-semibold cursor-pointer"
              style={{
                backgroundColor: "#1C1C24",
                border: "1px solid #2C2C38",
                color: "#F4F4F6",
              }}
            >
              CLOSE
            </button>
          </div>
        </div>

        <div className="flex-1 p-4 overflow-y-auto">
          {captures.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center gap-2">
              <div className="text-[13px] font-semibold text-[#F4F4F6]">
                No Studio Stills Captured in Current Session
              </div>
              <div className="text-[11px] text-[#9CA3AF] max-w-md">
                Use the tactile Shutter Release or BURST 3X button on the Bottom Transport Deck to capture graded still frames with your active 1D/3D LUT and broadcast overlays.
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {captures.map((item) => (
                <div
                  key={item.id}
                  className="rounded-[6px] p-2.5 flex flex-col gap-2"
                  style={{
                    backgroundColor: "#15151B",
                    border: "1px solid #22222B",
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
                    download={`LEICA_C270_${item.timestamp}.${item.format.includes("JPG") ? "jpg" : "png"}`}
                    className="h-[28px] rounded-[4px] flex items-center justify-center text-[11px] font-semibold no-underline"
                    style={{
                      backgroundColor: "#262118",
                      border: "1px solid #E5A93C",
                      color: "#E5A93C",
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
