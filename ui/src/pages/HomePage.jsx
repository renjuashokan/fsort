import { useState, useEffect, useRef } from "react";
import { Search, SlidersHorizontal, ChevronLeft, ChevronRight, Sparkles, Loader2, ImageOff } from "lucide-react";
import PeopleGrid from "../components/PeopleGrid";
import { getPaginationPages } from "../utils/pagination";
import { api } from "../api/facesortApi";

const SCORE_COLOR = (score) => {
  const pct = Math.round(score * 100);
  if (pct >= 25) return "text-emerald-400";
  if (pct >= 15) return "text-violet-400";
  return "text-slate-500";
};

export default function HomePage({ peopleState, onSelectPerson, onScrollToTop, offlineCache, onViewSemanticResult }) {
  const {
    people,
    totalPeople,
    peoplePage,
    peopleLoading,
    searchQuery,
    setSearchQuery,
    peopleSortBy,
    setPeopleSortBy,
    peopleOrder,
    setPeopleOrder,
    loadPeople,
  } = peopleState;

  const totalPeoplePages = Math.max(1, Math.ceil(totalPeople / 30));

  const handlePageChange = (page) => {
    loadPeople(page);
    onScrollToTop();
  };

  // ── Semantic search fallback ────────────────────────────────────────────────
  const [semanticResults, setSemanticResults]   = useState(null);
  const [semanticLoading, setSemanticLoading]   = useState(false);
  const [semanticDisabled, setSemanticDisabled] = useState(false);
  const debounceRef = useRef(null);

  const noPeopleFound = !peopleLoading && people.length === 0 && searchQuery.trim().length > 0;

  useEffect(() => {
    if (!noPeopleFound) {
      // Semantic section is hidden by the noPeopleFound guard in JSX —
      // stale results are never visible, so no synchronous reset is needed.
      return;
    }
    // Debounce: wait 400ms after user stops typing before firing
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setSemanticLoading(true);
      try {
        const data = await api.semanticSearch(searchQuery.trim(), 30);
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
    }, 400);
    return () => clearTimeout(debounceRef.current);
  }, [noPeopleFound, searchQuery]);

  return (
    <div className="flex flex-col gap-6">
      {/* Filters / Search Toolbar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/40 border border-slate-900 rounded-2xl p-4">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search people…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-900 hover:border-slate-800 focus:border-violet-600 pl-10 pr-4 py-2 text-sm text-slate-200 placeholder-slate-600 rounded-xl transition-all outline-none"
          />
        </div>

        {/* Sorting options */}
        <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>Sort:</span>
          </div>
          <select
            value={peopleSortBy}
            onChange={(e) => setPeopleSortBy(e.target.value)}
            className="bg-slate-950 border border-slate-900 text-xs font-medium text-slate-300 px-3 py-2 rounded-xl outline-none focus:border-violet-600 cursor-pointer"
          >
            <option value="name">Name</option>
            <option value="media_count">Media Count</option>
            <option value="image_count">Image Count</option>
            <option value="video_count">Video Count</option>
            <option value="created">Created</option>
          </select>

          <button
            onClick={() => setPeopleOrder((prev) => (prev === "asc" ? "desc" : "asc"))}
            className="px-3 py-2 text-xs font-semibold bg-slate-950 border border-slate-900 text-slate-300 hover:border-slate-800 rounded-xl transition-all active:scale-95"
          >
            {peopleOrder.toUpperCase()}
          </button>
        </div>
      </div>

      {/* People Grid (when query matches people or no query) */}
      {!noPeopleFound && (
        <PeopleGrid
          people={people}
          loading={peopleLoading}
          onSelectPerson={onSelectPerson}
          offlineCache={offlineCache}
        />
      )}

      {/* Pagination */}
      {!noPeopleFound && !peopleLoading && totalPeoplePages > 1 && (
        <div className="flex items-center justify-center gap-1.5 flex-wrap py-4">
          <button
            disabled={peoplePage === 1}
            onClick={() => handlePageChange(peoplePage - 1)}
            className="flex items-center gap-1 px-3 py-2 text-xs font-semibold bg-slate-900 border border-slate-800 text-slate-300 rounded-xl transition-all active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed hover:border-slate-700 hover:bg-slate-800"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Prev</span>
          </button>

          {getPaginationPages(peoplePage, totalPeoplePages).map((page, idx) =>
            page === "..." ? (
              <span key={`ellipsis-${idx}`} className="px-2 py-2 text-xs text-slate-600 select-none">…</span>
            ) : (
              <button
                key={page}
                onClick={() => handlePageChange(page)}
                className={`min-w-[36px] px-2.5 py-2 text-xs font-semibold rounded-xl transition-all active:scale-95 border ${
                  page === peoplePage
                    ? "bg-gradient-to-r from-violet-600 to-indigo-600 border-violet-500 text-white shadow-lg shadow-violet-900/30"
                    : "bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700 hover:bg-slate-800"
                }`}
              >
                {page}
              </button>
            )
          )}

          <button
            disabled={peoplePage === totalPeoplePages}
            onClick={() => handlePageChange(peoplePage + 1)}
            className="flex items-center gap-1 px-3 py-2 text-xs font-semibold bg-slate-900 border border-slate-800 text-slate-300 rounded-xl transition-all active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed hover:border-slate-700 hover:bg-slate-800"
          >
            <span className="hidden sm:inline">Next</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>

          <span className="text-xs text-slate-500 ml-2 font-medium">
            Page {peoplePage} of {totalPeoplePages} · {totalPeople} people
          </span>
        </div>
      )}

      {/* ── Semantic fallback: shown when no people match the query ── */}
      {noPeopleFound && (
        <div className="flex flex-col gap-4">
          {/* Section header */}
          <div className="flex items-center gap-2.5 border-t border-slate-900 pt-5">
            <Sparkles className="w-4 h-4 text-violet-400" />
            <p className="text-sm font-semibold text-slate-300">
              No people named <span className="text-violet-400">"{searchQuery}"</span> — showing photo results
            </p>
            {semanticLoading && <Loader2 className="w-3.5 h-3.5 text-violet-400 animate-spin ml-auto" />}
          </div>

          {/* CLIP disabled notice */}
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

          {/* Loading skeleton */}
          {semanticLoading && (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="aspect-square rounded-xl bg-slate-900/60 border border-slate-900 animate-pulse" />
              ))}
            </div>
          )}

          {/* No semantic results */}
          {!semanticLoading && semanticResults !== null && semanticResults.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 gap-3 text-slate-500">
              <ImageOff className="w-10 h-10 text-slate-700" />
              <p className="text-sm font-medium">No photos found for "{searchQuery}"</p>
            </div>
          )}

          {/* Semantic results grid */}
          {!semanticLoading && semanticResults && semanticResults.length > 0 && (
            <>
              <p className="text-xs text-slate-500 font-medium -mt-1">
                {semanticResults.length} photo{semanticResults.length !== 1 ? "s" : ""} matched
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                {semanticResults.map((item, idx) => (
                  <SemanticCard
                    key={item.id}
                    item={item}
                    onClick={() => onViewSemanticResult(semanticResults, idx)}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function SemanticCard({ item, onClick }) {
  const pct = Math.round(item.score * 100);
  return (
    <div
      onClick={onClick}
      className="group relative aspect-square bg-slate-900/40 border border-slate-900/60 hover:border-violet-700/60 rounded-xl overflow-hidden cursor-pointer transition-all"
    >
      <img
        src={item.thumbnail_url}
        alt={item.filename}
        loading="lazy"
        className="w-full h-full object-cover select-none pointer-events-none transition-transform duration-300 group-hover:scale-105"
      />
      <div className={`absolute top-2 left-2 px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-950/80 backdrop-blur-md ${SCORE_COLOR(item.score)}`}>
        {pct}%
      </div>
      <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-slate-950/90 to-transparent p-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <p className="text-[10px] text-slate-300 font-medium truncate">{item.filename}</p>
      </div>
    </div>
  );
}
