import { useState, useRef, useMemo } from "react";
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
  Search,
  Sparkles,
  X,
  ImageOff,
} from "lucide-react";
import MediaGrid from "../components/MediaGrid";
import { api } from "../api/facesortApi";

const SCORE_COLOR = (score) => {
  const pct = Math.round(score * 100);
  if (pct >= 25) return "text-emerald-400";
  if (pct >= 15) return "text-violet-400";
  return "text-slate-500";
};

export default function GalleryPage({
  selectedPerson,
  galleryState,
  offlineCache,
  onGoHome,
  onRenameOpen,
  onMergeOpen,
  onViewMedia,
  onRemoveMedia,
  onViewSemanticResult,
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

  const effectiveMedia = useMemo(() => {
    if (!isCached) return media;
    return media.map((item) => resolveMediaItem(personId, item));
  }, [media, isCached, personId, resolveMediaItem]);

  const handleDownload = () => {
    downloadPersonCache(selectedPerson, {
      onMediaLoaded: (items, total) => {
        setMedia(items);
        setTotalMedia(total);
        setMediaSkip(items.length);
      },
    });
  };

  const progressPct =
    progress.total > 0 ? Math.round((progress.done / progress.total) * 100) : 0;

  // ── Semantic search within gallery ─────────────────────────────────────────
  const [searchQuery, setSearchQuery]         = useState("");
  const [semanticResults, setSemanticResults] = useState(null); // null = not searched
  const [semanticLoading, setSemanticLoading] = useState(false);
  const [semanticDisabled, setSemanticDisabled] = useState(false);
  const inputRef = useRef(null);

  const handleSemanticSearch = async (q = searchQuery) => {
    const trimmed = q.trim();
    if (!trimmed) return;
    setSemanticLoading(true);
    try {
      const data = await api.semanticSearch(trimmed, 60);
      if (!data.enabled) {
        setSemanticDisabled(true);
        setSemanticResults(null);
      } else {
        setSemanticDisabled(false);
        setSemanticResults(data.results || []);
      }
    } catch {
      setSemanticResults([]);
    } finally {
      setSemanticLoading(false);
    }
  };

  const clearSearch = () => {
    setSearchQuery("");
    setSemanticResults(null);
    setSemanticDisabled(false);
  };

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
                {progress.total > 0 ? `${progress.done} / ${progress.total}` : "Fetching…"}
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
              <button
                onClick={onRenameOpen}
                className="flex items-center gap-2 px-3 py-2 text-xs font-semibold bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-200 rounded-xl transition-all active:scale-95"
              >
                <Edit3 className="w-4 h-4 text-violet-400" />
                <span>Rename</span>
              </button>

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

      {/* Semantic Search Bar */}
      <div className="flex items-center gap-2 bg-slate-900/20 border border-slate-900 rounded-xl p-3">
        <Sparkles className="w-3.5 h-3.5 text-violet-400 shrink-0" />
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-600 pointer-events-none" />
          <input
            ref={inputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSemanticSearch()}
            placeholder='Search photos by content — "hat", "outdoors", "dog"…'
            className="w-full bg-slate-950 border border-slate-800 focus:border-violet-500 pl-9 pr-8 py-1.5 text-xs text-slate-300 placeholder-slate-600 rounded-lg outline-none transition-all"
          />
          {searchQuery && (
            <button
              onClick={clearSearch}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-600 hover:text-slate-400 transition-colors"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
        <button
          onClick={() => handleSemanticSearch()}
          disabled={semanticLoading || !searchQuery.trim()}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-violet-700/30 hover:bg-violet-700/50 border border-violet-700/50 hover:border-violet-600 disabled:opacity-40 disabled:cursor-not-allowed text-violet-300 rounded-lg transition-all active:scale-95"
        >
          {semanticLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
          Search
        </button>
      </div>

      {/* Semantic Results */}
      {semanticDisabled && (
        <div className="flex items-start gap-3 p-4 bg-amber-950/30 border border-amber-800/40 rounded-xl text-sm text-amber-300">
          <Sparkles className="w-4 h-4 mt-0.5 shrink-0 text-amber-400" />
          <div>
            <p className="font-semibold">Photo search is not enabled</p>
            <p className="text-xs text-amber-400/70 mt-0.5">
              Set <code className="bg-amber-900/40 px-1 rounded">clip_enabled: true</code> in{" "}
              <code className="bg-amber-900/40 px-1 rounded">config.yaml</code> and run{" "}
              <code className="bg-amber-900/40 px-1 rounded">face-sort clip-index</code>.
            </p>
          </div>
        </div>
      )}

      {!semanticLoading && semanticResults !== null && semanticResults.length === 0 && (
        <div className="flex flex-col items-center justify-center py-10 gap-3 text-slate-500">
          <ImageOff className="w-8 h-8 text-slate-700" />
          <p className="text-xs font-medium">No photos found for "{searchQuery}"</p>
        </div>
      )}

      {!semanticLoading && semanticResults && semanticResults.length > 0 && (
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-violet-400" />
            <p className="text-xs text-slate-400 font-medium">
              <span className="text-violet-400 font-semibold">{semanticResults.length}</span>{" "}
              photo{semanticResults.length !== 1 ? "s" : ""} matched "{searchQuery}"
            </p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {semanticResults.map((item, idx) => (
              <div
                key={item.id}
                onClick={() => onViewSemanticResult(semanticResults, idx)}
                className="group relative aspect-square bg-slate-900/40 border border-slate-900/60 hover:border-violet-700/60 rounded-xl overflow-hidden cursor-pointer transition-all"
              >
                <img
                  src={item.thumbnail_url}
                  alt={item.filename}
                  loading="lazy"
                  className="w-full h-full object-cover select-none pointer-events-none transition-transform duration-300 group-hover:scale-105"
                />
                <div className={`absolute top-2 left-2 px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-950/80 backdrop-blur-md ${SCORE_COLOR(item.score)}`}>
                  {Math.round(item.score * 100)}%
                </div>
                <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-slate-950/90 to-transparent p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <p className="text-[10px] text-slate-300 font-medium truncate">{item.filename}</p>
                </div>
              </div>
            ))}
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
          onClick={() => setMediaOrder((prev) => (prev === "asc" ? "desc" : "asc"))}
          className="px-3 py-1.5 text-xs font-semibold bg-slate-950 border border-slate-900 text-slate-300 rounded-lg transition-all active:scale-95"
        >
          {mediaOrder.toUpperCase()}
        </button>
      </div>

      {/* Media Grid */}
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
