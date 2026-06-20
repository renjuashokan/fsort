import { useState, useEffect, useCallback, useRef } from "react";
import { api, MEDIA_PAGE_SIZE } from "../api/facesortApi";
import { showToast } from "../utils/notifications";

export function useGallery(selectedPerson, view) {
  const [media, setMedia] = useState([]);
  const [totalMedia, setTotalMedia] = useState(0);
  const [mediaSkip, setMediaSkip] = useState(0);
  const [mediaLoading, setMediaLoading] = useState(false);
  const [mediaSortBy, setMediaSortBy] = useState("filename");
  const [mediaOrder, setMediaOrder] = useState("asc");

  // Ref-based guard prevents concurrent fetches from creating a new loadGallery
  // reference (via mediaLoading state) which would re-trigger the useEffect below.
  const mediaLoadingRef = useRef(false);

  const loadGallery = useCallback(
    async (reset = false) => {
      if (!selectedPerson || mediaLoadingRef.current) return;
      mediaLoadingRef.current = true;
      setMediaLoading(true);
      const skipVal = reset ? 0 : mediaSkip;
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
    // mediaLoading removed from deps — using ref guard instead to avoid
    // re-creating loadGallery on every fetch, which would re-trigger the effect.
    [selectedPerson, mediaSkip, mediaSortBy, mediaOrder]
  );

  // Reload gallery when options change or selected person changes
  useEffect(() => {
    let active = true;
    const fetchGallery = async () => {
      if (view === "gallery" && selectedPerson) {
        await Promise.resolve();
        if (!active) return;
        loadGallery(true);
      }
    };
    fetchGallery();
    return () => {
      active = false;
    };
  }, [selectedPerson, view, loadGallery]);

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
