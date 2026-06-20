import { useState, useEffect } from "react";
import { toastEvents } from "../utils/notifications";

export default function Toast() {
  const [notification, setNotification] = useState(null);

  useEffect(() => {
    const unsubscribe = toastEvents.subscribe(({ message, type }) => {
      setNotification({ message, type });
      const timer = setTimeout(() => setNotification(null), 4000);
      return () => clearTimeout(timer);
    });
    return unsubscribe;
  }, []);

  if (!notification) return null;

  return (
    <div
      className={`fixed top-5 right-5 z-50 px-4 py-3 rounded-lg shadow-lg backdrop-blur-md border animate-fade-in flex items-center gap-2 ${
        notification.type === "error"
          ? "bg-rose-950/80 border-rose-800 text-rose-200"
          : "bg-emerald-950/80 border-emerald-800 text-emerald-200"
      }`}
    >
      <div className="w-2 h-2 rounded-full bg-current animate-ping" />
      <span className="text-sm font-medium">{notification.message}</span>
    </div>
  );
}
