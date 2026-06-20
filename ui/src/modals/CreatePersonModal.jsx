import { useState } from "react";
import { FolderPlus, X } from "lucide-react";
import { api } from "../api/facesortApi";
import { showToast } from "../utils/notifications";

export default function CreatePersonModal({ open, onClose, onSuccess }) {
  const [createValue, setCreateValue] = useState("");

  if (!open) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!createValue.trim()) return;
    try {
      const data = await api.createPerson(createValue);
      if (data.status === "success") {
        showToast(`Person "${createValue}" created successfully.`);
        setCreateValue("");
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
            <FolderPlus className="w-5 h-5 text-violet-400" />
            <span>Create New Person</span>
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
            <label className="block text-xs font-semibold text-slate-400 mb-1.5">
              Person Display Name
            </label>
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
              onClick={onClose}
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
  );
}
