import { useState, useEffect, useRef } from "react";
import { 
  User, 
  Search, 
  ChevronLeft, 
  ChevronRight, 
  X, 
  Play, 
  Plus, 
  Merge, 
  Edit3, 
  RotateCw, 
  Folder, 
  Info,
  SlidersHorizontal,
  FolderPlus,
  Grid
} from "lucide-react";
import "./App.css";

// API helper functions
const api = {
  getPeople: async ({ skip = 0, limit = 30, sortBy = "name", order = "asc", search = "" }) => {
    const params = new URLSearchParams({
      skip: String(skip),
      limit: String(limit),
      sort_by: sortBy,
      order: order,
    });
    if (search) params.append("search", search);
    const res = await fetch(`/api/people?${params.toString()}`);
    return res.json();
  },

  getPerson: async (id) => {
    const res = await fetch(`/api/person/${id}`);
    if (!res.ok) throw new Error("Person not found");
    return res.json();
  },

  getPersonMedia: async (id, { skip = 0, limit = 100, sortBy = "filename", order = "asc" }) => {
    const params = new URLSearchParams({
      skip: String(skip),
      limit: String(limit),
      sort_by: sortBy,
      order: order,
    });
    const res = await fetch(`/api/person/${id}/media?${params.toString()}`);
    return res.json();
  },

  renamePerson: async (id, newName) => {
    const res = await fetch("/api/person/rename", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ person: id, new_name: newName }),
    });
    return res.json();
  },

  mergePerson: async (targetId, sourceId) => {
    const res = await fetch("/api/person/merge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target: targetId, source: sourceId }),
    });
    return res.json();
  },

  reassignMedia: async (mediaId, personId) => {
    const res = await fetch("/api/media/reassign", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ media_id: mediaId, person_id: personId }),
    });
    return res.json();
  },

  createPerson: async (name) => {
    const res = await fetch("/api/person/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    return res.json();
  },

  search: async (query) => {
    const res = await fetch(`/api/search?query=${encodeURIComponent(query)}`);
    return res.json();
  }
};

function App() {
  // Navigation & view states
  const [view, setView] = useState("home"); // "home", "gallery"
  const [selectedPerson, setSelectedPerson] = useState(null);
  
  // People page states
  const [people, setPeople] = useState([]);
  const [totalPeople, setTotalPeople] = useState(0);
  const [peopleSkip, setPeopleSkip] = useState(0);
  const [peopleLoading, setPeopleLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [peopleSortBy, setPeopleSortBy] = useState("name");
  const [peopleOrder, setPeopleOrder] = useState("asc");

  // Gallery page states
  const [media, setMedia] = useState([]);
  const [totalMedia, setTotalMedia] = useState(0);
  const [mediaSkip, setMediaSkip] = useState(0);
  const [mediaLoading, setMediaLoading] = useState(false);
  const [mediaSortBy, setMediaSortBy] = useState("filename");
  const [mediaOrder, setMediaOrder] = useState("asc");

  // Media viewer modal states
  const [viewerIndex, setViewerIndex] = useState(null); // index in current media list
  const [viewerOpen, setViewerOpen] = useState(false);
  const [viewerPeople, setViewerPeople] = useState([]); // list of all people for tagging

  // Action modals
  const [renameOpen, setRenameOpen] = useState(false);
  const [renameValue, setRenameValue] = useState("");
  
  const [mergeOpen, setMergeOpen] = useState(false);
  const [mergeTarget, setMergeTarget] = useState("");
  
  const [createOpen, setCreateOpen] = useState(false);
  const [createValue, setCreateValue] = useState("");

  const [notification, setNotification] = useState(null);

  // Refs for infinite scroll detection
  const containerRef = useRef(null);

  // Show notification helpers
  const showToast = (message, type = "success") => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 4000);
  };

  // --- Load Initial People ---
  const loadPeople = async (reset = false) => {
    if (peopleLoading) return;
    setPeopleLoading(true);
    const skipVal = reset ? 0 : peopleSkip;
    try {
      const data = await api.getPeople({
        skip: skipVal,
        limit: 30,
        sortBy: peopleSortBy,
        order: peopleOrder,
        search: searchQuery
      });
      if (reset) {
        setPeople(data.items);
      } else {
        setPeople(prev => [...prev, ...data.items]);
      }
      setTotalPeople(data.total);
      setPeopleSkip(skipVal + data.items.length);
    } catch (err) {
      showToast("Failed to load people list: " + err.message, "error");
    } finally {
      setPeopleLoading(false);
    }
  };

  // Reload people when filters/sorting/search changes
  useEffect(() => {
    if (view === "home") {
      loadPeople(true);
    }
  }, [searchQuery, peopleSortBy, peopleOrder, view]);

  // --- Load Gallery Media ---
  const loadGallery = async (reset = false) => {
    if (!selectedPerson || mediaLoading) return;
    setMediaLoading(true);
    const skipVal = reset ? 0 : mediaSkip;
    try {
      const data = await api.getPersonMedia(selectedPerson.id, {
        skip: skipVal,
        limit: 50,
        sortBy: mediaSortBy,
        order: mediaOrder
      });
      if (reset) {
        setMedia(data.items);
      } else {
        setMedia(prev => [...prev, ...data.items]);
      }
      setTotalMedia(data.total);
      setMediaSkip(skipVal + data.items.length);
    } catch (err) {
      showToast("Failed to load gallery: " + err.message, "error");
    } finally {
      setMediaLoading(false);
    }
  };

  // Reload gallery when options change
  useEffect(() => {
    if (view === "gallery" && selectedPerson) {
      loadGallery(true);
    }
  }, [selectedPerson, mediaSortBy, mediaOrder]);

  // Load all people list for reassignment viewer once on startup
  useEffect(() => {
    api.getPeople({ skip: 0, limit: 1000 }).then(data => {
      // Exclude special directories
      setViewerPeople(data.items.filter(p => p.id !== "_unknown" && p.id !== "_multiple"));
    }).catch(() => {});
  }, []);

  // --- Infinite Scroll Listener ---
  const handleScroll = (e) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    if (scrollHeight - scrollTop - clientHeight < 150) {
      if (view === "home" && people.length < totalPeople) {
        loadPeople(false);
      } else if (view === "gallery" && media.length < totalMedia) {
        loadGallery(false);
      }
    }
  };

  // Keyboard navigation inside Media Viewer
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!viewerOpen || viewerIndex === null) return;
      if (e.key === "ArrowLeft") {
        navigateViewer(-1);
      } else if (e.key === "ArrowRight") {
        navigateViewer(1);
      } else if (e.key === "Escape") {
        setViewerOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [viewerOpen, viewerIndex, media]);

  const navigateViewer = (direction) => {
    if (viewerIndex === null) return;
    const newIdx = viewerIndex + direction;
    if (newIdx >= 0 && newIdx < media.length) {
      setViewerIndex(newIdx);
    }
  };

  // --- Core Action Handlers ---

  const handleCreatePerson = async (e) => {
    e.preventDefault();
    if (!createValue.trim()) return;
    try {
      const data = await api.createPerson(createValue);
      if (data.status === "success") {
        showToast(`Person "${createValue}" created successfully.`);
        setCreateOpen(false);
        setCreateValue("");
        loadPeople(true);
      } else {
        showToast(data.message, "error");
      }
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  const handleRenamePerson = async (e) => {
    e.preventDefault();
    if (!renameValue.trim() || !selectedPerson) return;
    try {
      const data = await api.renamePerson(selectedPerson.id, renameValue);
      if (data.status === "success") {
        showToast(`Person renamed to "${renameValue}".`);
        setSelectedPerson(prev => ({ ...prev, display_name: renameValue }));
        setRenameOpen(false);
        setRenameValue("");
        loadPeople(true);
      } else {
        showToast(data.message, "error");
      }
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  const handleMergePerson = async (e) => {
    e.preventDefault();
    if (!mergeTarget || !selectedPerson) return;
    try {
      const data = await api.mergePerson(mergeTarget, selectedPerson.id);
      if (data.status === "success") {
        showToast(`Merged successfully.`);
        setMergeOpen(false);
        setView("home");
        setSelectedPerson(null);
        loadPeople(true);
      } else {
        showToast(data.message, "error");
      }
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  const handleReassignMedia = async (mediaId, targetPersonId) => {
    try {
      const data = await api.reassignMedia(mediaId, targetPersonId);
      if (data.status === "success") {
        showToast("Media reassigned successfully.");
        // Instantly remove item from current gallery so it disappears
        setMedia(prev => prev.filter(item => item.id !== mediaId));
        setTotalMedia(prev => Math.max(0, prev - 1));
        
        // If the viewer is open, automatically move to next or close
        if (viewerOpen) {
          if (media.length <= 1) {
            setViewerOpen(false);
            setViewerIndex(null);
          } else {
            // Stay at same index (which is now the next item)
            if (viewerIndex >= media.length - 1) {
              setViewerIndex(media.length - 2);
            }
          }
        }
      } else {
        showToast(data.message, "error");
      }
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  const currentViewerMedia = viewerIndex !== null ? media[viewerIndex] : null;

  return (
    <div 
      ref={containerRef}
      onScroll={handleScroll}
      className="min-h-screen h-screen overflow-y-auto flex flex-col bg-slate-950 text-slate-100 selection:bg-violet-600 selection:text-white"
    >
      {/* Toast Notification */}
      {notification && (
        <div className={`fixed top-5 right-5 z-50 px-4 py-3 rounded-lg shadow-lg backdrop-blur-md border animate-fade-in flex items-center gap-2 ${
          notification.type === "error" 
            ? "bg-rose-950/80 border-rose-800 text-rose-200" 
            : "bg-emerald-950/80 border-emerald-800 text-emerald-200"
        }`}>
          <div className="w-2 h-2 rounded-full bg-current animate-ping" />
          <span className="text-sm font-medium">{notification.message}</span>
        </div>
      )}

      {/* Header */}
      <header className="sticky top-0 z-30 bg-slate-950/70 backdrop-blur-md border-b border-slate-900 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => setView("home")}>
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-900/30">
            <Grid className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-violet-200 to-indigo-200 bg-clip-text text-transparent">FaceSort</h1>
            <p className="text-xs text-slate-500 font-medium">Local Face Organizer</p>
          </div>
        </div>

        {view === "home" && (
          <div className="flex items-center gap-3">
            <button 
              onClick={() => setCreateOpen(true)}
              className="flex items-center gap-2 px-3 py-2 text-xs font-semibold bg-slate-900 border border-slate-800 hover:border-slate-700 hover:bg-slate-800 text-slate-200 rounded-lg transition-all active:scale-95"
            >
              <Plus className="w-4 h-4 text-violet-400" />
              <span>New Person</span>
            </button>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8">
        
        {/* --- VIEW: HOME PAGE --- */}
        {view === "home" && (
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
              <div className="flex items-center gap-3">
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
                  onClick={() => setPeopleOrder(prev => prev === "asc" ? "desc" : "asc")}
                  className="px-3 py-2 text-xs font-semibold bg-slate-950 border border-slate-900 text-slate-300 hover:border-slate-800 rounded-xl transition-all active:scale-95"
                >
                  {peopleOrder.toUpperCase()}
                </button>
              </div>
            </div>

            {/* People Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-6">
              {people.map((person) => {
                const isSpecial = person.id.startsWith("_");
                return (
                  <div
                    key={person.id}
                    onClick={() => {
                      setSelectedPerson(person);
                      setView("gallery");
                      setMediaSkip(0);
                      setMedia([]);
                    }}
                    className="group relative bg-slate-900/30 hover:bg-slate-900/60 border border-slate-900 hover:border-slate-800/70 rounded-2xl p-4 flex flex-col items-center text-center cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-violet-950/10"
                  >
                    {/* Circle Cover Photo */}
                    <div className="relative w-24 h-24 rounded-full overflow-hidden mb-4 border-2 border-slate-800 group-hover:border-violet-600 transition-colors shadow-inner bg-slate-950 flex items-center justify-center">
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
                          e.target.style.display = 'none';
                        }}
                      />
                    </div>

                    {/* Name */}
                    <h3 className="font-semibold text-sm text-slate-200 truncate w-full group-hover:text-violet-400 transition-colors">
                      {person.display_name}
                    </h3>

                    {/* Counts */}
                    <p className="text-xs text-slate-500 mt-1 font-medium">
                      {person.media_count} item{person.media_count !== 1 && "s"}
                    </p>

                    {/* Tiny badges */}
                    {!isSpecial && (
                      <div className="flex gap-2 mt-2 text-[10px] text-slate-600 font-semibold">
                        <span>{person.image_count} img</span>
                        <span>•</span>
                        <span>{person.video_count} vid</span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Empty State */}
            {people.length === 0 && !peopleLoading && (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <User className="w-16 h-16 text-slate-800 mb-4" />
                <h3 className="text-lg font-bold text-slate-400">No people found</h3>
                <p className="text-sm text-slate-600 max-w-sm mt-1">Try refining your search query or run extraction on folder.</p>
              </div>
            )}

            {/* Infinite Scroll Spinner */}
            {peopleLoading && (
              <div className="flex items-center justify-center py-8">
                <div className="w-6 h-6 border-2 border-slate-800 border-t-violet-600 rounded-full animate-spin" />
              </div>
            )}

          </div>
        )}

        {/* --- VIEW: PERSON GALLERY --- */}
        {view === "gallery" && selectedPerson && (
          <div className="flex flex-col gap-6">
            
            {/* Gallery Top Toolbar */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-900 pb-6">
              <div className="flex items-center gap-3">
                <button 
                  onClick={() => setView("home")}
                  className="p-2 bg-slate-900 hover:bg-slate-800 text-slate-300 rounded-xl transition-colors outline-none"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <div>
                  <div className="flex items-center gap-2.5">
                    <h2 className="text-2xl font-bold text-slate-100">{selectedPerson.display_name}</h2>
                    <span className="text-xs px-2 py-0.5 bg-slate-900 text-slate-400 rounded-full font-medium">
                      {totalMedia} files
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 font-medium mt-0.5">ID: {selectedPerson.id}</p>
                </div>
              </div>

              {!selectedPerson.id.startsWith("_") && (
                <div className="flex items-center gap-3">
                  {/* Rename */}
                  <button 
                    onClick={() => {
                      setRenameValue(selectedPerson.display_name);
                      setRenameOpen(true);
                    }}
                    className="flex items-center gap-2 px-3 py-2 text-xs font-semibold bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-200 rounded-xl transition-all active:scale-95"
                  >
                    <Edit3 className="w-4 h-4 text-violet-400" />
                    <span>Rename</span>
                  </button>

                  {/* Merge */}
                  <button 
                    onClick={() => {
                      setMergeTarget("");
                      setMergeOpen(true);
                    }}
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
                onClick={() => setMediaOrder(prev => prev === "asc" ? "desc" : "asc")}
                className="px-3 py-1.5 text-xs font-semibold bg-slate-950 border border-slate-900 text-slate-300 rounded-lg transition-all active:scale-95"
              >
                {mediaOrder.toUpperCase()}
              </button>
            </div>

            {/* Media Grid */}
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-7 gap-4">
              {media.map((item, index) => {
                const isVideo = item.type === "video";
                return (
                  <div
                    key={item.id}
                    onClick={() => {
                      setViewerIndex(index);
                      setViewerOpen(true);
                    }}
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
                          if (confirm(`Remove this media from ${selectedPerson.display_name}?`)) {
                            handleReassignMedia(item.id, null);
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
              })}
            </div>

            {/* Empty State */}
            {media.length === 0 && !mediaLoading && (
              <div className="flex flex-col items-center justify-center py-24 text-center">
                <Folder className="w-16 h-16 text-slate-800 mb-4" />
                <h3 className="text-lg font-bold text-slate-400">Empty gallery</h3>
                <p className="text-sm text-slate-600 max-w-sm mt-1">This person directory has no assigned media files.</p>
              </div>
            )}

            {/* Infinite Scroll Spinner */}
            {mediaLoading && (
              <div className="flex items-center justify-center py-8">
                <div className="w-6 h-6 border-2 border-slate-800 border-t-violet-600 rounded-full animate-spin" />
              </div>
            )}

          </div>
        )}

      </main>

      {/* --- MODAL: CREATE PERSON --- */}
      {createOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
          <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" onClick={() => setCreateOpen(false)} />
          <div className="relative bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl animate-scale-in">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <FolderPlus className="w-5 h-5 text-violet-400" />
                <span>Create New Person</span>
              </h3>
              <button onClick={() => setCreateOpen(false)} className="p-1 text-slate-500 hover:text-slate-300 transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreatePerson} className="flex flex-col gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">Person Display Name</label>
                <input 
                  type="text"
                  placeholder="e.g. John Doe"
                  value={createValue}
                  onChange={(e) => setCreateValue(e.target.value)}
                  autoFocus
                  className="w-full bg-slate-950 border border-slate-800 focus:border-violet-600 pl-3.5 pr-4 py-2 text-sm text-slate-200 placeholder-slate-700 rounded-xl transition-all outline-none"
                />
              </div>
              <div className="flex items-center justify-end gap-3 mt-2">
                <button 
                  type="button" 
                  onClick={() => setCreateOpen(false)}
                  className="px-4 py-2 text-xs font-semibold bg-slate-950 hover:bg-slate-900 border border-slate-800 text-slate-300 rounded-xl transition-colors"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  className="px-4 py-2 text-xs font-semibold bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white rounded-xl transition-colors"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- MODAL: RENAME PERSON --- */}
      {renameOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
          <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" onClick={() => setRenameOpen(false)} />
          <div className="relative bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl animate-scale-in">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <Edit3 className="w-5 h-5 text-violet-400" />
                <span>Rename Person</span>
              </h3>
              <button onClick={() => setRenameOpen(false)} className="p-1 text-slate-500 hover:text-slate-300 transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleRenamePerson} className="flex flex-col gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">New Display Name</label>
                <input 
                  type="text"
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  autoFocus
                  className="w-full bg-slate-950 border border-slate-800 focus:border-violet-600 pl-3.5 pr-4 py-2 text-sm text-slate-200 placeholder-slate-700 rounded-xl transition-all outline-none"
                />
              </div>
              <div className="flex items-center justify-end gap-3 mt-2">
                <button 
                  type="button" 
                  onClick={() => setRenameOpen(false)}
                  className="px-4 py-2 text-xs font-semibold bg-slate-950 hover:bg-slate-900 border border-slate-800 text-slate-300 rounded-xl transition-colors"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  className="px-4 py-2 text-xs font-semibold bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white rounded-xl transition-colors"
                >
                  Rename
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- MODAL: MERGE PERSON --- */}
      {mergeOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
          <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" onClick={() => setMergeOpen(false)} />
          <div className="relative bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl animate-scale-in">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <Merge className="w-5 h-5 text-indigo-400" />
                <span>Merge Person</span>
              </h3>
              <button onClick={() => setMergeOpen(false)} className="p-1 text-slate-500 hover:text-slate-300 transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleMergePerson} className="flex flex-col gap-4">
              <div>
                <p className="text-xs text-slate-400 leading-relaxed mb-4">
                  Merge all faces of <strong className="text-slate-200 font-semibold">{selectedPerson.display_name}</strong> into another person. 
                  The source person will be removed, and their folder will be merged instantly.
                </p>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">Select Target Person</label>
                <select
                  value={mergeTarget}
                  onChange={(e) => setMergeTarget(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-violet-600 px-3.5 py-2.5 text-sm text-slate-300 rounded-xl outline-none cursor-pointer"
                >
                  <option value="">-- Choose Target Person --</option>
                  {viewerPeople
                    .filter(p => p.id !== selectedPerson.id)
                    .map(p => (
                      <option key={p.id} value={p.id}>{p.display_name} ({p.media_count} items)</option>
                    ))
                  }
                </select>
              </div>
              <div className="flex items-center justify-end gap-3 mt-2">
                <button 
                  type="button" 
                  onClick={() => setMergeOpen(false)}
                  className="px-4 py-2 text-xs font-semibold bg-slate-950 hover:bg-slate-900 border border-slate-800 text-slate-300 rounded-xl transition-colors"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  disabled={!mergeTarget}
                  className="px-4 py-2 text-xs font-semibold bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white rounded-xl transition-colors disabled:opacity-50"
                >
                  Merge
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- FULLSCREEN MEDIA VIEWER --- */}
      {viewerOpen && currentViewerMedia && (
        <div className="fixed inset-0 z-40 bg-slate-950/95 backdrop-blur-md flex flex-col md:flex-row animate-fade-in">
          
          {/* Main media container */}
          <div className="relative flex-1 flex items-center justify-center p-4 min-h-[60svh] md:min-h-0">
            {/* Close button */}
            <button 
              onClick={() => setViewerOpen(false)} 
              className="absolute top-5 left-5 z-50 p-2.5 bg-slate-900/60 border border-slate-800 text-slate-300 hover:text-white rounded-xl backdrop-blur-md outline-none active:scale-95"
            >
              <X className="w-5 h-5" />
            </button>

            {/* Prev button */}
            {viewerIndex > 0 && (
              <button 
                onClick={() => navigateViewer(-1)} 
                className="absolute left-5 p-3 bg-slate-900/60 border border-slate-800 text-slate-300 hover:text-white rounded-2xl backdrop-blur-md outline-none active:scale-95 z-30"
              >
                <ChevronLeft className="w-6 h-6" />
              </button>
            )}

            {/* Next button */}
            {viewerIndex < media.length - 1 && (
              <button 
                onClick={() => navigateViewer(1)} 
                className="absolute right-5 p-3 bg-slate-900/60 border border-slate-800 text-slate-300 hover:text-white rounded-2xl backdrop-blur-md outline-none active:scale-95 z-30"
              >
                <ChevronRight className="w-6 h-6" />
              </button>
            )}

            {/* Fullscreen media rendering */}
            <div className="max-w-full max-h-[80vh] md:max-h-full flex items-center justify-center">
              {currentViewerMedia.type === "video" ? (
                <video 
                  key={currentViewerMedia.id}
                  src={currentViewerMedia.media_url} 
                  controls 
                  autoPlay
                  className="max-w-full max-h-[75vh] md:max-h-[85vh] rounded-xl border border-slate-900 shadow-2xl"
                />
              ) : (
                <img 
                  src={currentViewerMedia.media_url} 
                  alt={currentViewerMedia.filename}
                  className="max-w-full max-h-[75vh] md:max-h-[85vh] object-contain rounded-xl border border-slate-900 shadow-2xl select-none"
                />
              )}
            </div>
          </div>

          {/* Info & Editing Sidebar */}
          <div className="w-full md:w-80 bg-slate-900/40 border-t md:border-t-0 md:border-l border-slate-900 flex flex-col p-6 overflow-y-auto">
            {/* Header info */}
            <div className="mb-6 flex items-start gap-3">
              <Info className="w-5 h-5 text-violet-400 mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="text-sm font-semibold text-slate-200 break-all">{currentViewerMedia.filename}</h4>
                <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mt-1">{currentViewerMedia.type}</p>
                {currentViewerMedia.created && (
                  <p className="text-xs text-slate-500 font-medium mt-0.5">Date: {currentViewerMedia.created}</p>
                )}
              </div>
            </div>

            <div className="border-t border-slate-900/80 pt-6 flex-1 flex flex-col gap-4">
              {/* Current assignment display */}
              <div>
                <span className="block text-[10px] uppercase font-bold text-slate-500 tracking-wider mb-2">Assigned Person</span>
                <div className="px-4 py-3 bg-slate-950/60 border border-slate-900 rounded-xl flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <User className="w-4 h-4 text-violet-400" />
                    <span className="text-sm font-semibold text-slate-200">
                      {selectedPerson ? selectedPerson.display_name : "Unknown"}
                    </span>
                  </div>
                  <button 
                    onClick={() => {
                      if (confirm("Remove this face assignment?")) {
                        handleReassignMedia(currentViewerMedia.id, null);
                      }
                    }}
                    className="text-xs font-semibold text-rose-400 hover:text-rose-300 hover:bg-rose-950/20 px-2.5 py-1 rounded-lg transition-all"
                  >
                    Remove
                  </button>
                </div>
              </div>

              {/* Tagging / Reassign Option */}
              <div className="flex-1 flex flex-col gap-2">
                <span className="block text-[10px] uppercase font-bold text-slate-500 tracking-wider">Change/Add Assignment</span>
                
                {/* Search / Select dropdown */}
                <select
                  onChange={(e) => {
                    const val = e.target.value;
                    if (val === "__new__") {
                      // Trigger new person dialog
                      setCreateValue("");
                      setCreateOpen(true);
                    } else if (val) {
                      handleReassignMedia(currentViewerMedia.id, val);
                    }
                    e.target.value = "";
                  }}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-violet-600 px-3 py-2 text-xs text-slate-300 rounded-xl outline-none cursor-pointer"
                >
                  <option value="">-- Select Person --</option>
                  <option value="__new__" className="text-violet-400 font-bold">+ Create New Person</option>
                  {viewerPeople
                    .filter(p => !selectedPerson || p.id !== selectedPerson.id)
                    .map(p => (
                      <option key={p.id} value={p.id}>{p.display_name}</option>
                    ))
                  }
                </select>

                <p className="text-[10px] text-slate-500 font-medium leading-relaxed mt-2">
                  Selecting a person will reassign the face in this media file immediately. 
                  The file will move to their respective output folder without rescanning.
                </p>
              </div>
            </div>

            {/* Viewer sidebar footer */}
            <div className="border-t border-slate-900/80 pt-4 mt-auto flex items-center justify-between text-[11px] text-slate-500 font-medium">
              <span>{viewerIndex + 1} of {media.length} items</span>
              <button 
                onClick={() => setViewerOpen(false)}
                className="hover:text-slate-300"
              >
                Done
              </button>
            </div>

          </div>

        </div>
      )}

    </div>
  );
}

export default App;
