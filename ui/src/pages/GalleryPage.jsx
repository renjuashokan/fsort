import { useMemo } from "react";
import {
  ChevronLeft,
  Edit3,
  Merge,
  SlidersHorizontal,
  Download,
  Trash2,
  Wifi,
  WifiOff,
  Loader2,
} from "lucide-react";
import MediaGrid from "../components/MediaGrid";

export default function GalleryPage({
  selectedPerson,
  galleryState,
  offlineCache,
  onGoHome,
  onRenameOpen,
  onMergeOpen,
  onViewMedia,
  onRemoveMedia,
}) {
  const {
    media,
    totalMedia,
    mediaLoading,
    mediaSortBy,
    setMediaSortBy,
    mediaOrder,
    setMediaOrder,
    setMedia,
    setTotalMedia,
    setMediaSkip,
  } = galleryState;

  const {
    cacheStatus,
    cacheProgress,
    downloadPersonCache,
    clearPersonCache,
    resolveMediaItem,
  } = offlineCache;

  const personId = selectedPerson.id;
  const status = cacheStatus[personId] ?? "idle";
  const progress = cacheProgress[personId] ?? { done: 0, total: 0 };
  const isDownloading = status === "downloading";
  const isCached = status === "cached";

  // Swap in blob:// URLs when cached — no changes needed anywhere downstream
  const effectiveMedia = useMemo(() => {
    if (!isCached) return media;
    return media.map((item) => resolveMediaItem(personId, item));
  }, [media, isCached, personId, resolveMediaItem]);

  const handleDownload = () => {
    downloadPersonCache(selectedPerson, {
      onMediaLoaded: (items, total) => {
        // Hydrate gallery state with the full list so all items are visible
        // offline — even if the user hasn't scrolled through all pages yet.
        setMedia(items);
        setTotalMedia(total);
        setMediaSkip(items.length);
      },
    });
  };

  const progressPct =
    progress.total > 0
      ? Math.round((progress.done / progress.total) * 100)
      : 0;

  return (
    <div className="flex flex-col gap-6">
      {/* Gallery Top Toolbar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-900 pb-6">
        <div className="flex items-center gap-3">
          <button
            onClick={onGoHome}
            className="p-2 bg-slate-900 hover:bg-slate-800 text-slate-300 rounded-xl transition-colors outline-none"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center gap-2.5 flex-wrap">
              <h2 className="text-xl sm:text-2xl font-bold text-slate-100">
                {selectedPerson.display_name}
              </h2>
              <span className="text-xs px-2 py-0.5 bg-slate-900 text-slate-400 rounded-full font-medium">
                {totalMedia} files
              </span>
              {/* Cached badge */}
              {isCached && (
                <span className="flex items-center gap-1 text-xs px-2 py-0.5 bg-emerald-950/60 text-emerald-400 border border-emerald-900/60 rounded-full font-semibold">
                  <WifiOff className="w-3 h-3" />
                  Cached
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 font-medium mt-0.5">
              ID: {selectedPerson.id}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Offline Cache Controls */}
          {!isCached && !isDownloading && (
            <button
              onClick={handleDownload}
              className="flex items-center gap-2 px-3 py-2 text-xs font-semibold bg-slate-900 hover:bg-violet-950 hover:border-violet-800 border border-slate-800 text-slate-200 hover:text-violet-200 rounded-xl transition-all active:scale-95"
              title="Download all media to memory for offline viewing"
            >
              <Download className="w-4 h-4 text-violet-400" />
              <span>Cache Offline</span>
            </button>
          )}

          {isDownloading && (
            <div className="flex items-center gap-2 px-3 py-2 text-xs font-semibold bg-slate-900 border border-slate-800 text-slate-400 rounded-xl cursor-default">
              <Loader2 className="w-4 h-4 text-violet-400 animate-spin" />
              <span>
                {progress.total > 0
                  ? `${progress.done} / ${progress.total}`
                  : "Fetching…"}
              </span>
            </div>
          )}

          {isCached && (
            <button
              onClick={() => clearPersonCache(personId)}
              className="flex items-center gap-2 px-3 py-2 text-xs font-semibold bg-slate-900 hover:bg-rose-950 hover:border-rose-900 border border-slate-800 text-slate-200 hover:text-rose-200 rounded-xl transition-all active:scale-95"
              title="Clear in-memory cache — media will reload from server"
            >
              <Trash2 className="w-4 h-4 text-rose-400" />
              <span>Clear Cache</span>
            </button>
          )}

          {!selectedPerson.id.startsWith("_") && (
            <>
              {/* Rename */}
              <button
                onClick={onRenameOpen}
                className="flex items-center gap-2 px-3 py-2 text-xs font-semibold bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-200 rounded-xl transition-all active:scale-95"
              >
                <Edit3 className="w-4 h-4 text-violet-400" />
                <span>Rename</span>
              </button>

              {/* Merge */}
              <button
                onClick={onMergeOpen}
                className="flex items-center gap-2 px-3 py-2 text-xs font-semibold bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-200 rounded-xl transition-all active:scale-95"
              >
                <Merge className="w-4 h-4 text-indigo-400" />
                <span>Merge</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Download Progress Bar */}
      {isDownloading && progress.total > 0 && (
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span className="flex items-center gap-1.5">
              <Wifi className="w-3.5 h-3.5 text-violet-400" />
              Caching to memory…
            </span>
            <span className="text-violet-400 font-semibold">{progressPct}%</span>
          </div>
          <div className="w-full h-1.5 bg-slate-900 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-violet-600 to-indigo-500 rounded-full transition-all duration-300"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      )}

      {/* Media Sorting */}
      <div className="flex items-center justify-end gap-3 bg-slate-900/20 border border-slate-900 rounded-xl p-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
          <SlidersHorizontal className="w-3.5 h-3.5" />
          <span>Sort media:</span>
        </div>
        <select
          value={mediaSortBy}
          onChange={(e) => setMediaSortBy(e.target.value)}
          className="bg-slate-950 border border-slate-900 text-xs font-medium text-slate-300 px-3 py-1.5 rounded-lg outline-none cursor-pointer"
        >
          <option value="filename">Filename</option>
          <option value="created">Created Date</option>
          <option value="filesize">Filesize</option>
          <option value="type">Type</option>
        </select>

        <button
          onClick={() =>
            setMediaOrder((prev) => (prev === "asc" ? "desc" : "asc"))
          }
          className="px-3 py-1.5 text-xs font-semibold bg-slate-950 border border-slate-900 text-slate-300 rounded-lg transition-all active:scale-95"
        >
          {mediaOrder.toUpperCase()}
        </button>
      </div>

      {/* Media Grid — uses blob:// URLs when cached, server URLs otherwise */}
      <MediaGrid
        media={effectiveMedia}
        loading={mediaLoading}
        personName={selectedPerson.display_name}
        onViewMedia={onViewMedia}
        onRemoveMedia={onRemoveMedia}
      />
    </div>
  );
}
