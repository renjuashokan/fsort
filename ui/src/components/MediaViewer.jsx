import { useEffect, useRef, useCallback } from "react";
import { X, ChevronLeft, ChevronRight, Info, User } from "lucide-react";

export default function MediaViewer({
  media,
  viewerIndex,
  onClose,
  onNavigate,
  selectedPerson,
  viewerPeople,
  onReassign,
  onCreateNewPerson,
}) {
  const viewerRef = useRef(null);
  const currentViewerMedia =
    viewerIndex !== null && media ? media[viewerIndex] : null;

  const navigateViewer = useCallback(
    (direction) => {
      if (viewerIndex === null) return;
      const newIdx = viewerIndex + direction;
      if (newIdx >= 0 && newIdx < media.length) {
        onNavigate(newIdx);
      }
    },
    [viewerIndex, media.length, onNavigate]
  );

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (viewerIndex === null) return;
      if (e.key === "ArrowLeft") {
        navigateViewer(-1);
      } else if (e.key === "ArrowRight") {
        navigateViewer(1);
      } else if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [viewerIndex, navigateViewer, onClose]);

  // Touch swipe support
  useEffect(() => {
    const el = viewerRef.current;
    if (!el) return;

    let startX = null;
    let startY = null;

    const onTouchStart = (e) => {
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
    };

    const onTouchEnd = (e) => {
      if (startX === null) return;
      const dx = e.changedTouches[0].clientX - startX;
      const dy = Math.abs(e.changedTouches[0].clientY - startY);
      if (Math.abs(dx) > 50 && Math.abs(dx) > dy * 1.2) {
        const direction = dx < 0 ? 1 : -1;
        const next = viewerIndex + direction;
        if (next >= 0 && next < media.length) {
          onNavigate(next);
        }
      }
      startX = null;
      startY = null;
    };

    el.addEventListener("touchstart", onTouchStart, { passive: true });
    el.addEventListener("touchend", onTouchEnd, { passive: true });
    return () => {
      el.removeEventListener("touchstart", onTouchStart);
      el.removeEventListener("touchend", onTouchEnd);
    };
  }, [viewerIndex, media.length, onNavigate]);

  if (!currentViewerMedia) return null;

  return (
    <div
      ref={viewerRef}
      className="fixed inset-0 z-40 bg-slate-950/97 backdrop-blur-md flex flex-col animate-fade-in"
    >
      {/* Top bar: close + counter */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-950/60 backdrop-blur-sm border-b border-slate-900/60 shrink-0 z-50">
        <button
          onClick={onClose}
          className="p-2 bg-slate-900/60 border border-slate-800 text-slate-300 hover:text-white rounded-xl backdrop-blur-md outline-none active:scale-95"
        >
          <X className="w-5 h-5" />
        </button>
        <span className="text-xs font-semibold text-slate-400">
          {viewerIndex + 1} / {media.length}
        </span>
        <div className="w-9" /> {/* spacer */}
      </div>

      {/* Content area */}
      <div className="flex flex-col md:flex-row flex-1 min-h-0">
        {/* Main media container */}
        <div className="viewer-image-area md:flex-1 bg-black/30 w-full relative flex items-center justify-center">
          {/* Prev button */}
          {viewerIndex > 0 && (
            <button
              onClick={() => navigateViewer(-1)}
              className="absolute left-3 z-30 p-2.5 sm:p-3 bg-slate-900/70 border border-slate-800 text-slate-300 hover:text-white rounded-2xl backdrop-blur-md outline-none active:scale-95"
            >
              <ChevronLeft className="w-5 h-5 sm:w-6 sm:h-6" />
            </button>
          )}

          {/* Next button */}
          {viewerIndex < media.length - 1 && (
            <button
              onClick={() => navigateViewer(1)}
              className="absolute right-3 z-30 p-2.5 sm:p-3 bg-slate-900/70 border border-slate-800 text-slate-300 hover:text-white rounded-2xl backdrop-blur-md outline-none active:scale-95"
            >
              <ChevronRight className="w-5 h-5 sm:w-6 sm:h-6" />
            </button>
          )}

          {/* Media element */}
          {currentViewerMedia.type === "video" ? (
            <video
              key={currentViewerMedia.id}
              src={currentViewerMedia.media_url}
              controls
              autoPlay
              className="viewer-media rounded-xl border border-slate-900/60 shadow-2xl"
              onError={(e) => {
                // iOS Safari can reject blob:// video URLs. Fall back to the
                // original server URL if one is stored (set by offline cache).
                const fallback = currentViewerMedia.original_media_url;
                if (fallback && e.target.src !== fallback) {
                  e.target.src = fallback;
                }
              }}
            />
          ) : (
            <img
              key={currentViewerMedia.id}
              src={currentViewerMedia.media_url}
              alt={currentViewerMedia.filename}
              className="viewer-media rounded-xl border border-slate-900/60 shadow-2xl select-none"
              draggable={false}
            />
          )}
        </div>

        {/* Info & Editing Sidebar */}
        <div className="w-full md:w-80 bg-slate-900/40 border-t md:border-t-0 md:border-l border-slate-900 flex flex-col overflow-y-auto shrink-0 max-h-[220px] md:max-h-none">
          <div className="flex flex-col h-full p-4 sm:p-6 gap-4">
            {/* Filename & meta */}
            <div className="flex items-start gap-3">
              <Info className="w-4 h-4 text-violet-400 mt-0.5 flex-shrink-0" />
              <div className="min-w-0">
                <h4 className="text-xs sm:text-sm font-semibold text-slate-200 break-all">
                  {currentViewerMedia.filename}
                </h4>
                <p className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider mt-0.5">
                  {currentViewerMedia.type}
                </p>
                {currentViewerMedia.created && (
                  <p className="text-[10px] text-slate-500 font-medium mt-0.5">
                    Date: {currentViewerMedia.created}
                  </p>
                )}
              </div>
            </div>

            <div className="flex flex-col sm:flex-row md:flex-col gap-3 flex-1">
              {/* Current assignment display */}
              <div className="flex-1">
                <span className="block text-[10px] uppercase font-bold text-slate-500 tracking-wider mb-1.5">
                  Assigned Person
                </span>
                <div className="px-3 py-2 bg-slate-950/60 border border-slate-900 rounded-xl flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <User className="w-4 h-4 text-violet-400" />
                    <span className="text-xs font-semibold text-slate-200 truncate max-w-[100px]">
                      {selectedPerson ? selectedPerson.display_name : "Unknown"}
                    </span>
                  </div>
                  <button
                    onClick={() => {
                      if (confirm("Remove this face assignment?")) {
                        onReassign(currentViewerMedia.id, null);
                      }
                    }}
                    className="text-xs font-semibold text-rose-400 hover:text-rose-300 hover:bg-rose-950/20 px-2 py-1 rounded-lg transition-all whitespace-nowrap"
                  >
                    Remove
                  </button>
                </div>
              </div>

              {/* Reassign dropdown */}
              <div className="flex-1 flex flex-col gap-1.5">
                <span className="block text-[10px] uppercase font-bold text-slate-500 tracking-wider">
                  Reassign
                </span>
                <select
                  onChange={(e) => {
                    const val = e.target.value;
                    if (val === "__new__") {
                      onCreateNewPerson();
                    } else if (val) {
                      onReassign(currentViewerMedia.id, val);
                    }
                    e.target.value = "";
                  }}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-violet-600 px-3 py-2 text-xs text-slate-300 rounded-xl outline-none cursor-pointer"
                >
                  <option value="">-- Select Person --</option>
                  <option value="__new__" className="text-violet-400 font-bold">
                    + Create New Person
                  </option>
                  {viewerPeople
                    .filter((p) => !selectedPerson || p.id !== selectedPerson.id)
                    .map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.display_name}
                      </option>
                    ))}
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
