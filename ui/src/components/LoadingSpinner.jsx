export default function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-8">
      <div className="w-6 h-6 border-2 border-slate-800 border-t-violet-600 rounded-full animate-spin" />
    </div>
  );
}
