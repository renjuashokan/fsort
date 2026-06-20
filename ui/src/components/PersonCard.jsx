import { Folder, User } from "lucide-react";

export default function PersonCard({ person, onClick }) {
  const isSpecial = person.id.startsWith("_");

  return (
    <div
      onClick={onClick}
      className="group relative bg-slate-900/30 hover:bg-slate-900/60 border border-slate-900 hover:border-slate-800/70 rounded-2xl p-3 sm:p-4 flex flex-col items-center text-center cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-violet-950/10"
    >
      {/* Circle Cover Photo */}
      <div className="relative w-20 h-20 sm:w-24 sm:h-24 rounded-full overflow-hidden mb-3 sm:mb-4 border-2 border-slate-800 group-hover:border-violet-600 transition-colors shadow-inner bg-slate-950 flex items-center justify-center">
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
        <div className="flex gap-2 mt-2 text-[10px] text-slate-600 font-semibold">
          <span>{person.image_count} img</span>
          <span>•</span>
          <span>{person.video_count} vid</span>
        </div>
      )}
    </div>
  );
}
