import { Play, X } from "lucide-react";

export default function MediaCard({ item, onClick, onRemove, personName }) {
  const isVideo = item.type === "video";

  return (
    <div
      onClick={onClick}
      className="group relative aspect-square bg-slate-900/40 border border-slate-900/60 hover:border-slate-800 rounded-xl overflow-hidden cursor-pointer transition-all"
    >
      {/* Media Thumbnail */}
      <img
        src={item.thumbnail_url}
        alt={item.filename}
        loading="lazy"
        className="w-full h-full object-cover select-none pointer-events-none transition-transform duration-300 group-hover:scale-105"
      />

      {/* Video Duration / Play Icon */}
      {isVideo && (
        <div className="absolute bottom-2 left-2 bg-slate-950/80 backdrop-blur-md px-1.5 py-0.5 rounded text-[10px] font-bold text-slate-100 flex items-center gap-1.5">
          <Play className="w-2.5 h-2.5 fill-current text-violet-400" />
          <span>Video</span>
        </div>
      )}

      {/* Quick remove/action option overlay on hover */}
      <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (confirm(`Remove this media from ${personName}?`)) {
              onRemove(item.id);
            }
          }}
          className="p-1 bg-slate-950/80 hover:bg-rose-950 hover:text-rose-200 border border-slate-900 text-slate-300 rounded-lg transition-colors"
          title="Remove Assignment"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
