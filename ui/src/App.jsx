import { useState, useRef } from "react";
import "./App.css";
import { showToast } from "./utils/notifications";

// API
import { api } from "./api/facesortApi";

// Hooks
import { usePeople } from "./hooks/usePeople";
import { useGallery } from "./hooks/useGallery";
import { useOfflineCache } from "./hooks/useOfflineCache";

// Components
import Header from "./components/Header";
import Toast from "./components/Toast";
import MediaViewer from "./components/MediaViewer";

// Pages
import HomePage from "./pages/HomePage";
import GalleryPage from "./pages/GalleryPage";

// Modals
import CreatePersonModal from "./modals/CreatePersonModal";
import RenamePersonModal from "./modals/RenamePersonModal";
import MergePersonModal from "./modals/MergePersonModal";

export default function App() {
  // Navigation & view states
  const [view, setView] = useState("home"); // "home" | "gallery"
  const [selectedPerson, setSelectedPerson] = useState(null);

  // Custom states
  const peopleState = usePeople();
  const galleryState = useGallery(selectedPerson, view);
  const offlineCache = useOfflineCache();

  // Media viewer modal states
  const [viewerIndex, setViewerIndex] = useState(null);
  const [viewerOpen, setViewerOpen] = useState(false);
  // Holds semantic search results when viewer is opened from a search result
  const [semanticViewerMedia, setSemanticViewerMedia] = useState(null);

  // Action modals open states
  const [renameOpen, setRenameOpen] = useState(false);
  const [mergeOpen, setMergeOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [isReassigning, setIsReassigning] = useState(false);
  // Incrementing this causes MediaViewer to re-fetch people for the current media
  const [viewerPeopleRefreshKey, setViewerPeopleRefreshKey] = useState(0);

  // Refs
  const containerRef = useRef(null);

  const scrollToTop = () => {
    containerRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  };

  const goHome = () => {
    setView("home");
    peopleState.loadPeople(peopleState.peoplePage);
    scrollToTop();
  };

  const handleScroll = (e) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    if (scrollHeight - scrollTop - clientHeight < 150) {
      if (view === "gallery" && galleryState.media.length < galleryState.totalMedia) {
        galleryState.loadGallery(false);
      }
    }
  };

  const handleSelectPerson = (person) => {
    setSelectedPerson(person);
    setView("gallery");
    galleryState.setMediaSkip(0);
    galleryState.setMedia([]);
  };

  const handleViewPersonFromViewer = (person) => {
    setViewerOpen(false);
    setViewerIndex(null);
    setSemanticViewerMedia(null);
    handleSelectPerson(person);
    scrollToTop();
  };

  const handleReassignMedia = async (mediaId, targetPersonId) => {
    setIsReassigning(true);
    try {
      const data = await api.reassignMedia(mediaId, targetPersonId);
      if (data.status === "success") {
        showToast("Reassigned successfully!");
        setViewerPeopleRefreshKey((k) => k + 1);
        if (viewerOpen) {
          galleryState.setMedia((prevMedia) => {
            const nextMedia = prevMedia.filter((item) => item.id !== mediaId);
            if (nextMedia.length === 0) {
              setViewerOpen(false);
              setViewerIndex(null);
            } else {
              setViewerIndex((prevIdx) => {
                if (prevIdx === null) return null;
                if (prevIdx >= nextMedia.length) return nextMedia.length - 1;
                return prevIdx;
              });
            }
            return nextMedia;
          });
        } else {
          galleryState.setMedia((prev) => prev.filter((item) => item.id !== mediaId));
        }
        galleryState.setTotalMedia((prev) => Math.max(0, prev - 1));
        peopleState.loadPeople(peopleState.peoplePage);
        peopleState.loadViewerPeople();
      } else {
        showToast(data.detail || data.message || "Reassign failed", "error");
      }
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setIsReassigning(false);
    }
  };

  // Open viewer with semantic results (read-only, no reassign)
  const handleViewSemanticResult = (results, idx) => {
    setSemanticViewerMedia(results);
    setViewerIndex(idx);
    setViewerOpen(true);
  };

  // Viewer uses semantic results when triggered from search, gallery media otherwise
  const activeViewerMedia =
    semanticViewerMedia ? semanticViewerMedia : galleryState.media;

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="min-h-screen h-screen overflow-y-auto flex flex-col bg-slate-950 text-slate-100 selection:bg-violet-600 selection:text-white"
    >
      <Toast />

      <Header
        view={view}
        onGoHome={goHome}
        onCreatePerson={() => setCreateOpen(true)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-3 sm:px-6 py-6 sm:py-8">
        {view === "home" && (
          <HomePage
            peopleState={peopleState}
            onSelectPerson={handleSelectPerson}
            onScrollToTop={scrollToTop}
            offlineCache={offlineCache}
            onViewSemanticResult={handleViewSemanticResult}
          />
        )}

        {view === "gallery" && selectedPerson && (
          <GalleryPage
            selectedPerson={selectedPerson}
            galleryState={galleryState}
            offlineCache={offlineCache}
            onGoHome={goHome}
            onRenameOpen={() => setRenameOpen(true)}
            onMergeOpen={() => setMergeOpen(true)}
            onViewMedia={(index) => {
              setSemanticViewerMedia(null);
              setViewerIndex(index);
              setViewerOpen(true);
            }}
            onRemoveMedia={(mediaId) => handleReassignMedia(mediaId, null)}
            onViewSemanticResult={handleViewSemanticResult}
          />
        )}
      </main>

      <CreatePersonModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onSuccess={() => {
          peopleState.loadPeople(1);
          peopleState.loadViewerPeople();
        }}
      />

      <RenamePersonModal
        key={selectedPerson?.id || "rename"}
        open={renameOpen}
        onClose={() => setRenameOpen(false)}
        selectedPerson={selectedPerson}
        onSuccess={(newName) => {
          setSelectedPerson((prev) => ({ ...prev, display_name: newName }));
          peopleState.loadPeople(peopleState.peoplePage);
          peopleState.loadViewerPeople();
        }}
      />

      <MergePersonModal
        open={mergeOpen}
        onClose={() => setMergeOpen(false)}
        selectedPerson={selectedPerson}
        viewerPeople={peopleState.viewerPeople}
        onSuccess={() => {
          setView("home");
          setSelectedPerson(null);
          peopleState.loadPeople(peopleState.peoplePage);
          peopleState.loadViewerPeople();
        }}
      />

      {viewerOpen && (
        <MediaViewer
          media={activeViewerMedia}
          viewerIndex={viewerIndex}
          onClose={() => {
            setViewerOpen(false);
            setViewerIndex(null);
            setSemanticViewerMedia(null);
          }}
          onNavigate={(idx) => setViewerIndex(idx)}
          selectedPerson={semanticViewerMedia ? null : selectedPerson}
          viewerPeople={semanticViewerMedia ? [] : peopleState.viewerPeople}
          onReassign={semanticViewerMedia ? () => {} : handleReassignMedia}
          onCreateNewPerson={() => setCreateOpen(true)}
          onViewPerson={handleViewPersonFromViewer}
          isReassigning={isReassigning}
          peopleRefreshKey={viewerPeopleRefreshKey}
          totalMedia={semanticViewerMedia ? null : galleryState.totalMedia}
          onRequestMore={
            semanticViewerMedia
              ? undefined
              : () => {
                  if (galleryState.media.length < galleryState.totalMedia) {
                    galleryState.loadGallery(false);
                  }
                }
          }
        />
      )}
    </div>
  );
}
