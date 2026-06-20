import { useState } from "react";
import { Merge, X } from "lucide-react";
import { api } from "../api/facesortApi";
import { showToast } from "../utils/notifications";

export default function MergePersonModal({
  open,
  onClose,
  selectedPerson,
  viewerPeople,
  onSuccess,
}) {
  const [mergeTarget, setMergeTarget] = useState("");

  if (!open || !selectedPerson) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!mergeTarget) return;
    try {
      const data = await api.mergePerson(mergeTarget, selectedPerson.id);
      if (data.status === "success") {
        showToast("Merged successfully.");
        setMergeTarget("");
        onSuccess();
        onClose();
      } else {
        showToast(data.message, "error");
      }
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div
        className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className="relative bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl animate-scale-in">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <Merge className="w-5 h-5 text-indigo-400" />
            <span>Merge Person</span>
          </h3>
          <button
            onClick={onClose}
            className="p-1 text-slate-500 hover:text-slate-300 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <p className="text-xs text-slate-400 leading-relaxed mb-4">
              Merge all faces of{" "}
              <strong className="text-slate-200 font-semibold">
                {selectedPerson.display_name}
              </strong>{" "}
              into another person. The source person will be removed, and their
              folder will be merged instantly.
            </p>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5">
              Select Target Person
            </label>
            <select
              value={mergeTarget}
              onChange={(e) => setMergeTarget(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 focus:border-violet-600 px-3.5 py-2.5 text-sm text-slate-300 rounded-xl outline-none cursor-pointer"
            >
              <option value="">-- Choose Target Person --</option>
              {viewerPeople
                .filter((p) => p.id !== selectedPerson.id)
                .map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.display_name} ({p.media_count} items)
                  </option>
                ))}
            </select>
          </div>
          <div className="flex items-center justify-end gap-3 mt-2">
            <button
              type="button"
              onClick={onClose}
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
  );
}
