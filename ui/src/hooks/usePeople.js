import { useState, useEffect, useRef, useCallback } from "react";
import { api, PEOPLE_PAGE_SIZE } from "../api/facesortApi";
import { showToast } from "../utils/notifications";

export function usePeople() {
  const [people, setPeople] = useState([]);
  const [totalPeople, setTotalPeople] = useState(0);
  const [peoplePage, setPeoplePage] = useState(1);
  const [peopleLoading, setPeopleLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [peopleSortBy, setPeopleSortBy] = useState("name");
  const [peopleOrder, setPeopleOrder] = useState("asc");

  // Reassignment & Merge viewer lists
  const [viewerPeople, setViewerPeople] = useState([]);

  const peopleLoadingRef = useRef(false);

  const loadPeople = useCallback(
    async (
      page = 1,
      overrideSortBy = peopleSortBy,
      overrideOrder = peopleOrder,
      overrideSearch = searchQuery
    ) => {
      if (peopleLoadingRef.current) return;
      peopleLoadingRef.current = true;
      setPeopleLoading(true);
      const skip = (page - 1) * PEOPLE_PAGE_SIZE;
      try {
        const data = await api.getPeople({
          skip,
          limit: PEOPLE_PAGE_SIZE,
          sortBy: overrideSortBy,
          order: overrideOrder,
          search: overrideSearch,
          min_media_count: 1,
        });
        setPeople(data.items);
        setTotalPeople(data.total);
        setPeoplePage(page);
      } catch (err) {
        showToast("Failed to load people list: " + err.message, "error");
      } finally {
        peopleLoadingRef.current = false;
        setPeopleLoading(false);
      }
    },
    [peopleSortBy, peopleOrder, searchQuery]
  );

  const loadViewerPeople = useCallback(async () => {
    try {
      const data = await api.getPeople({ skip: 0, limit: 1000 });
      setViewerPeople(
        data.items.filter((p) => p.id !== "_unknown" && p.id !== "_multiple")
      );
    } catch {
      // ignore
    }
  }, []);

  // Initial load on mount and when filters/search changes
  useEffect(() => {
    let active = true;
    const fetchOnMountAndFilters = async () => {
      await Promise.resolve();
      if (!active) return;
      loadPeople(1, peopleSortBy, peopleOrder, searchQuery);
    };
    fetchOnMountAndFilters();
    return () => {
      active = false;
    };
  }, [searchQuery, peopleSortBy, peopleOrder, loadPeople]);

  // Load viewer people list once on startup
  useEffect(() => {
    let active = true;
    const fetchViewerPeople = async () => {
      await Promise.resolve();
      if (!active) return;
      loadViewerPeople();
    };
    fetchViewerPeople();
    return () => {
      active = false;
    };
  }, [loadViewerPeople]);

  return {
    people,
    setPeople,
    totalPeople,
    setTotalPeople,
    peoplePage,
    setPeoplePage,
    peopleLoading,
    searchQuery,
    setSearchQuery,
    peopleSortBy,
    setPeopleSortBy,
    peopleOrder,
    setPeopleOrder,
    viewerPeople,
    loadPeople,
    loadViewerPeople,
  };
}
