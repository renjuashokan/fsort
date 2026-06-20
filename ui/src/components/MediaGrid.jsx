import { Folder } from "lucide-react";
import MediaCard from "./MediaCard";
import LoadingSpinner from "./LoadingSpinner";

export default function MediaGrid({
  media,
  loading,
  personName,
  onViewMedia,
  onRemoveMedia,
}) {
  if (loading && media.length === 0) {
    return <LoadingSpinner />;
  }

  if (media.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <Folder className="w-16 h-16 text-slate-800 mb-4" />
        <h3 className="text-lg font-bold text-slate-400">Empty gallery</h3>
        <p className="text-sm text-slate-600 max-w-sm mt-1">
          This person directory has no assigned media files.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-7 gap-2 sm:gap-4">
      {media.map((item, index) => (
        <MediaCard
          key={item.id}
          item={item}
          personName={personName}
          onClick={() => onViewMedia(index)}
          onRemove={onRemoveMedia}
        />
      ))}
    </div>
  );
}
