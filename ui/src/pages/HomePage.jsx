import { Search, SlidersHorizontal, ChevronLeft, ChevronRight } from "lucide-react";
import PeopleGrid from "../components/PeopleGrid";
import { getPaginationPages } from "../utils/pagination";

export default function HomePage({ peopleState, onSelectPerson, onScrollToTop }) {
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

  return (
    <div className="flex flex-col gap-6">
      {/* Filters / Search Toolbar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/40 border border-slate-900 rounded-2xl p-4">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search people..."
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
            onClick={() =>
              setPeopleOrder((prev) => (prev === "asc" ? "desc" : "asc"))
            }
            className="px-3 py-2 text-xs font-semibold bg-slate-950 border border-slate-900 text-slate-300 hover:border-slate-800 rounded-xl transition-all active:scale-95"
          >
            {peopleOrder.toUpperCase()}
          </button>
        </div>
      </div>

      {/* People Grid */}
      <PeopleGrid
        people={people}
        loading={peopleLoading}
        onSelectPerson={onSelectPerson}
      />

      {/* --- Pagination --- */}
      {!peopleLoading && totalPeoplePages > 1 && (
        <div className="flex items-center justify-center gap-1.5 flex-wrap py-4">
          {/* Prev */}
          <button
            disabled={peoplePage === 1}
            onClick={() => handlePageChange(peoplePage - 1)}
            className="flex items-center gap-1 px-3 py-2 text-xs font-semibold bg-slate-900 border border-slate-800 text-slate-300 rounded-xl transition-all active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed hover:border-slate-700 hover:bg-slate-800"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Prev</span>
          </button>

          {/* Page numbers */}
          {getPaginationPages(peoplePage, totalPeoplePages).map((page, idx) =>
            page === "..." ? (
              <span
                key={`ellipsis-${idx}`}
                className="px-2 py-2 text-xs text-slate-600 select-none"
              >
                …
              </span>
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

          {/* Next */}
          <button
            disabled={peoplePage === totalPeoplePages}
            onClick={() => handlePageChange(peoplePage + 1)}
            className="flex items-center gap-1 px-3 py-2 text-xs font-semibold bg-slate-900 border border-slate-800 text-slate-300 rounded-xl transition-all active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed hover:border-slate-700 hover:bg-slate-800"
          >
            <span className="hidden sm:inline">Next</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>

          {/* Page info */}
          <span className="text-xs text-slate-500 ml-2 font-medium">
            Page {peoplePage} of {totalPeoplePages} · {totalPeople} people
          </span>
        </div>
      )}
    </div>
  );
}
