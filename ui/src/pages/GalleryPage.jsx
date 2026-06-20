import { ChevronLeft, Edit3, Merge, SlidersHorizontal } from "lucide-react";
import MediaGrid from "../components/MediaGrid";

export default function GalleryPage({
  selectedPerson,
  galleryState,
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
  } = galleryState;

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
            </div>
            <p className="text-xs text-slate-500 font-medium mt-0.5">
              ID: {selectedPerson.id}
            </p>
          </div>
        </div>

        {!selectedPerson.id.startsWith("_") && (
          <div className="flex items-center gap-3">
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
          </div>
        )}
      </div>

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

      {/* Media Grid */}
      <MediaGrid
        media={media}
        loading={mediaLoading}
        personName={selectedPerson.display_name}
        onViewMedia={onViewMedia}
        onRemoveMedia={onRemoveMedia}
      />
    </div>
  );
}
