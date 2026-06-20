import { useState, useEffect, useCallback, useRef } from "react";
import { api, MEDIA_PAGE_SIZE } from "../api/facesortApi";
import { showToast } from "../utils/notifications";

export function useGallery(selectedPerson, view) {
  const [media, setMedia] = useState([]);
  const [totalMedia, setTotalMedia] = useState(0);
  const [mediaSkip, setMediaSkipState] = useState(0);
  const [mediaLoading, setMediaLoading] = useState(false);
  const [mediaSortBy, setMediaSortBy] = useState("filename");
  const [mediaOrder, setMediaOrder] = useState("asc");

  // Ref mirrors for values read inside loadGallery.
  // Using refs avoids adding them to loadGallery's dep array, which would
  // recreate the function on every page load and re-trigger the useEffect
  // (causing it to call loadGallery(true) / reset on every successful fetch).
  const mediaLoadingRef = useRef(false);
  const mediaSkipRef = useRef(0);

  // Keep ref in sync with state
  const setMediaSkip = (val) => {
    mediaSkipRef.current = typeof val === "function" ? val(mediaSkipRef.current) : val;
    setMediaSkipState(mediaSkipRef.current);
  };

  const loadGallery = useCallback(
    async (reset = false) => {
      if (!selectedPerson || mediaLoadingRef.current) return;
      mediaLoadingRef.current = true;
      setMediaLoading(true);
      const skipVal = reset ? 0 : mediaSkipRef.current;
      try {
        const data = await api.getPersonMedia(selectedPerson.id, {
          skip: skipVal,
          limit: MEDIA_PAGE_SIZE,
          sortBy: mediaSortBy,
          order: mediaOrder,
        });
        if (reset) {
          setMedia(data.items);
        } else {
          setMedia((prev) => [...prev, ...data.items]);
        }
        setTotalMedia(data.total);
        setMediaSkip(skipVal + data.items.length);
      } catch (err) {
        showToast("Failed to load gallery: " + err.message, "error");
      } finally {
        mediaLoadingRef.current = false;
        setMediaLoading(false);
      }
    },
    // mediaSkip and mediaLoading intentionally omitted — both are read via refs
    // to prevent loadGallery from being recreated after every page load, which
    // would re-trigger the useEffect and call loadGallery(true) in a loop.
    [selectedPerson, mediaSortBy, mediaOrder]
  );

  // Reload gallery when the person, sort field, or sort order changes
  useEffect(() => {
    if (view === "gallery" && selectedPerson) {
      mediaSkipRef.current = 0; // reset ref before the call
      loadGallery(true);
    }
  }, [selectedPerson, view, mediaSortBy, mediaOrder, loadGallery]);

  return {
    media,
    setMedia,
    totalMedia,
    setTotalMedia,
    mediaSkip,
    setMediaSkip,
    mediaLoading,
    mediaSortBy,
    setMediaSortBy,
    mediaOrder,
    setMediaOrder,
    loadGallery,
  };
}
