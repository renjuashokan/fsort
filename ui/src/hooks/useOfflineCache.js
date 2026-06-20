import { useState, useRef, useCallback } from "react";
import { api } from "../api/facesortApi";

/**
 * In-memory offline cache for a person's media.
 *
 * Fetches all media files as Blobs and serves them via blob:// URLs so the
 * gallery stays fully viewable without a server connection.  The cache lives
 * only in JS heap — it vanishes on page reload and can be manually cleared.
 *
 * Shape per person:
 *   blobStore.current = Map<personId, Map<mediaId, { mediaUrl, thumbUrl }>>
 */
export function useOfflineCache() {
  // Per-person cache status: "idle" | "downloading" | "cached"
  const [cacheStatus, setCacheStatus] = useState({});
  // Per-person download progress: { done: number, total: number }
  const [cacheProgress, setCacheProgress] = useState({});

  // Blob URL store — NOT in React state to avoid re-renders on every blob fetch
  const blobStore = useRef(new Map());

  // ---------------------------------------------------------------------------
  // Internal helpers
  // ---------------------------------------------------------------------------

  const setStatus = (personId, status) =>
    setCacheStatus((prev) => ({ ...prev, [personId]: status }));

  const setProgress = (personId, done, total) =>
    setCacheProgress((prev) => ({ ...prev, [personId]: { done, total } }));

  /** Fetch a URL as a Blob, return an object URL.  Returns null on failure. */
  const fetchBlob = async (url) => {
    try {
      const res = await fetch(url);
      if (!res.ok) return null;
      const blob = await res.blob();
      return URL.createObjectURL(blob);
    } catch {
      return null;
    }
  };

  /** Revoke all blob URLs for one person and remove their entry from the store. */
  const revokePersonBlobs = (personId) => {
    const personMap = blobStore.current.get(personId);
    if (!personMap) return;
    for (const { mediaUrl, thumbUrl } of personMap.values()) {
      if (mediaUrl?.startsWith("blob:")) URL.revokeObjectURL(mediaUrl);
      if (thumbUrl?.startsWith("blob:")) URL.revokeObjectURL(thumbUrl);
    }
    blobStore.current.delete(personId);
  };

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  /**
   * Download all media for a person into memory.
   * Fetches all pages from the API, then downloads each file + thumbnail
   * in parallel batches of BATCH_SIZE.
   */
  const downloadPersonCache = useCallback(async (person, { onMediaLoaded } = {}) => {
    const personId = person.id;
    if (cacheStatus[personId] === "downloading") return;

    // Clear any previous cache for this person first
    revokePersonBlobs(personId);
    blobStore.current.set(personId, new Map());

    setStatus(personId, "downloading");
    setProgress(personId, 0, 0);

    try {
      // ── Step 1: collect all media items across all pages ──────────────────
      const FETCH_LIMIT = 200;
      let allItems = [];
      let skip = 0;
      let total = Infinity;

      while (skip < total) {
        const data = await api.getPersonMedia(personId, {
          skip,
          limit: FETCH_LIMIT,
          sortBy: "filename",
          order: "asc",
        });
        allItems = [...allItems, ...data.items];
        total = data.total;
        skip += data.items.length;
        if (data.items.length === 0) break; // safety
      }

      // Notify caller with the complete item list so gallery state can be
      // hydrated immediately — before blobs finish downloading.
      onMediaLoaded?.(allItems, total);

      setProgress(personId, 0, allItems.length);

      // ── Step 2: download blobs in parallel batches ─────────────────────────
      const BATCH_SIZE = 8;
      const personMap = blobStore.current.get(personId);
      let done = 0;

      for (let i = 0; i < allItems.length; i += BATCH_SIZE) {
        const batch = allItems.slice(i, i + BATCH_SIZE);
        await Promise.all(
          batch.map(async (item) => {
            const [mediaUrl, thumbUrl] = await Promise.all([
              fetchBlob(item.media_url),
              fetchBlob(item.thumbnail_url),
            ]);
            personMap.set(item.id, {
              mediaUrl: mediaUrl ?? item.media_url,
              thumbUrl: thumbUrl ?? item.thumbnail_url,
            });
            done++;
            setProgress(personId, done, allItems.length);
          })
        );
      }

      setStatus(personId, "cached");
    } catch (err) {
      console.error("Offline cache download failed:", err);
      revokePersonBlobs(personId);
      setStatus(personId, "idle");
      setProgress(personId, 0, 0);
    }
  }, [cacheStatus]);

  /**
   * Revoke all blob URLs for a person and reset their cache to idle.
   */
  const clearPersonCache = useCallback((personId) => {
    revokePersonBlobs(personId);
    setStatus(personId, "idle");
    setProgress(personId, 0, 0);
  }, []);

  /**
   * Given a media item, return its URLs — blob:// if cached, originals otherwise.
   */
  const resolveMediaItem = useCallback((personId, item) => {
    const personMap = blobStore.current.get(personId);
    if (!personMap) return item;
    const cached = personMap.get(item.id);
    if (!cached) return item;
    return {
      ...item,
      media_url: cached.mediaUrl,
      thumbnail_url: cached.thumbUrl,
      // Preserved so MediaViewer can fall back to server URL if blob
      // video playback fails (e.g. iOS Safari blob:// video restriction).
      original_media_url: item.media_url,
    };
  }, []);

  return {
    cacheStatus,
    cacheProgress,
    downloadPersonCache,
    clearPersonCache,
    resolveMediaItem,
  };
}
