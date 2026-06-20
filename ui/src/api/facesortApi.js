export const PEOPLE_PAGE_SIZE = 30;
export const MEDIA_PAGE_SIZE = 50;

export const api = {
  getPeople: async ({ skip = 0, limit = PEOPLE_PAGE_SIZE, sortBy = "name", order = "asc", search = "", min_media_count = 0 }) => {
    const params = new URLSearchParams({
      skip: String(skip),
      limit: String(limit),
      sort_by: sortBy,
      order: order,
      min_media_count: String(min_media_count),
    });
    if (search) params.append("search", search);
    const res = await fetch(`/api/people?${params.toString()}`);
    return res.json();
  },

  getPerson: async (id) => {
    const res = await fetch(`/api/person/${id}`);
    if (!res.ok) throw new Error("Person not found");
    return res.json();
  },

  getPersonMedia: async (id, { skip = 0, limit = MEDIA_PAGE_SIZE, sortBy = "filename", order = "asc" }) => {
    const params = new URLSearchParams({
      skip: String(skip),
      limit: String(limit),
      sort_by: sortBy,
      order: order,
    });
    const res = await fetch(`/api/person/${id}/media?${params.toString()}`);
    return res.json();
  },

  renamePerson: async (id, newName) => {
    const res = await fetch("/api/person/rename", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ person: id, new_name: newName }),
    });
    return res.json();
  },

  mergePerson: async (targetId, sourceId) => {
    const res = await fetch("/api/person/merge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target: targetId, source: sourceId }),
    });
    return res.json();
  },

  reassignMedia: async (mediaId, personId) => {
    const res = await fetch("/api/media/reassign", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ media_id: mediaId, person_id: personId }),
    });
    return res.json();
  },

  createPerson: async (name) => {
    const res = await fetch("/api/person/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    return res.json();
  },

  search: async (query) => {
    const res = await fetch(`/api/search?query=${encodeURIComponent(query)}`);
    return res.json();
  }
};
