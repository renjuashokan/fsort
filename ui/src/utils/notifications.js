export const toastEvents = {
  listeners: new Set(),
  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  },
  show(message, type = "success") {
    this.listeners.forEach((listener) => listener({ message, type }));
  },
};

export const showToast = (message, type = "success") => {
  toastEvents.show(message, type);
};
