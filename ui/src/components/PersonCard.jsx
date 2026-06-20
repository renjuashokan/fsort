import { Download, Loader2, WifiOff, Folder, User } from "lucide-react";

export default function PersonCard({ person, onClick, offlineCache }) {
  const isSpecial = person.id.startsWith("_");

  const { cacheStatus, cacheProgress, downloadPersonCache, clearPersonCache } =
    offlineCache;

  const status = cacheStatus[person.id] ?? "idle";
  const progress = cacheProgress[person.id] ?? { done: 0, total: 0 };
  const isDownloading = status === "downloading";
  const isCached = status === "cached";

  const progressPct =
    progress.total > 0
      ? Math.round((progress.done / progress.total) * 100)
      : 0;

  const handleCacheClick = (e) => {
    e.stopPropagation();
    if (isCached) {
      clearPersonCache(person.id);
    } else if (!isDownloading) {
      downloadPersonCache(person);
    }
  };

  return (
    <div
      onClick={onClick}
      className="group relative bg-slate-900/30 hover:bg-slate-900/60 border border-slate-900 hover:border-slate-800/70 rounded-2xl p-3 sm:p-4 flex flex-col items-center text-center cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-violet-950/10"
    >
      {/* Cache action button — top-right corner */}
      <button
        onClick={handleCacheClick}
        title={
          isCached
            ? "Clear in-memory cache"
            : isDownloading
            ? `Caching… ${progressPct}%`
            : "Cache offline"
        }
        className={`absolute top-2 right-2 z-10 p-1.5 rounded-lg border transition-all active:scale-95 opacity-100 md:opacity-0 md:group-hover:opacity-100 ${
          isCached
            ? "bg-emerald-950/80 border-emerald-900/60 text-emerald-400 hover:bg-rose-950 hover:border-rose-900 hover:text-rose-400"
            : isDownloading
            ? "bg-slate-950/80 border-slate-800 text-violet-400 cursor-default"
            : "bg-slate-950/80 border-slate-800 text-slate-400 hover:text-violet-400 hover:border-violet-800"
        }`}
      >
        {isDownloading ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : isCached ? (
          <WifiOff className="w-3.5 h-3.5" />
        ) : (
          <Download className="w-3.5 h-3.5" />
        )}
      </button>

      {/* Circle Cover Photo */}
      <div
        className={`relative w-20 h-20 sm:w-24 sm:h-24 rounded-full overflow-hidden mb-3 sm:mb-4 border-2 transition-colors shadow-inner bg-slate-950 flex items-center justify-center ${
          isCached
            ? "border-emerald-700"
            : "border-slate-800 group-hover:border-violet-600"
        }`}
      >
        {isSpecial ? (
          <Folder className="w-8 h-8 text-slate-600 absolute z-0" />
        ) : (
          <User className="w-8 h-8 text-slate-700 absolute z-0" />
        )}
        <img
          src={person.thumbnail_url}
          alt={person.display_name}
          loading="lazy"
          className="relative z-10 w-full h-full object-cover select-none pointer-events-none transition-transform duration-500 group-hover:scale-110"
          onError={(e) => {
            e.target.style.display = "none";
          }}
        />

        {/* Download progress ring overlay */}
        {isDownloading && progress.total > 0 && (
          <div className="absolute inset-0 z-20 flex items-center justify-center bg-slate-950/60 rounded-full">
            <svg className="w-12 h-12 -rotate-90" viewBox="0 0 36 36">
              <circle
                cx="18"
                cy="18"
                r="15.9"
                fill="none"
                stroke="#1e1b4b"
                strokeWidth="2.5"
              />
              <circle
                cx="18"
                cy="18"
                r="15.9"
                fill="none"
                stroke="#7c3aed"
                strokeWidth="2.5"
                strokeDasharray={`${progressPct} ${100 - progressPct}`}
                strokeDashoffset="0"
                strokeLinecap="round"
                className="transition-all duration-300"
              />
            </svg>
            <span className="absolute text-[9px] font-bold text-violet-300">
              {progressPct}%
            </span>
          </div>
        )}
      </div>

      {/* Name */}
      <h3 className="font-semibold text-xs sm:text-sm text-slate-200 truncate w-full group-hover:text-violet-400 transition-colors">
        {person.display_name}
      </h3>

      {/* Counts */}
      <p className="text-xs text-slate-500 mt-1 font-medium">
        {person.media_count} item{person.media_count !== 1 && "s"}
      </p>

      {/* Tiny badges */}
      {!isSpecial && (
        <div className="flex gap-2 mt-2 text-[10px] font-semibold">
          {isCached ? (
            <span className="flex items-center gap-1 text-emerald-500">
              <WifiOff className="w-2.5 h-2.5" />
              cached
            </span>
          ) : (
            <>
              <span className="text-slate-600">{person.image_count} img</span>
              <span className="text-slate-600">•</span>
              <span className="text-slate-600">{person.video_count} vid</span>
            </>
          )}
        </div>
      )}
    </div>
  );
}
