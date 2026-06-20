import { Grid, Plus } from "lucide-react";

export default function Header({ view, onGoHome, onCreatePerson }) {
  return (
    <header className="sticky top-0 z-30 bg-slate-950/70 backdrop-blur-md border-b border-slate-900 px-4 sm:px-6 py-4 flex items-center justify-between">
      <div className="flex items-center gap-3 cursor-pointer" onClick={onGoHome}>
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-violet-900/30">
          <Grid className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-violet-200 to-indigo-200 bg-clip-text text-transparent">
            FaceSort
          </h1>
          <p className="text-xs text-slate-500 font-medium">Local Face Organizer</p>
        </div>
      </div>

      {view === "home" && (
        <div className="flex items-center gap-3">
          <button
            onClick={onCreatePerson}
            className="flex items-center gap-2 px-3 py-2 text-xs font-semibold bg-slate-900 border border-slate-800 hover:border-slate-700 hover:bg-slate-800 text-slate-200 rounded-lg transition-all active:scale-95"
          >
            <Plus className="w-4 h-4 text-violet-400" />
            <span className="hidden sm:inline">New Person</span>
          </button>
        </div>
      )}
    </header>
  );
}
