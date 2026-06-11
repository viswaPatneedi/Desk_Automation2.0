import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  stack: [], // Stack of open modals
  modals: {}, // Modal data by type
};

const modalSlice = createSlice({
  name: 'modals',
  initialState,
  reducers: {
    openModal: (state, action) => {
      const { type, id, data } = action.payload;
      const modalId = id || `${type}-${Date.now()}`;
      
      state.stack.push(modalId);
      state.modals[modalId] = {
        type,
        id: modalId,
        data,
        isOpen: true,
        timestamp: Date.now(),
      };
    },
    closeModal: (state, action) => {
      const modalId = action.payload;
      
      state.stack = state.stack.filter(id => id !== modalId);
      delete state.modals[modalId];
    },
    closeAllModals: (state) => {
      state.stack = [];
      state.modals = {};
    },
    closeTopModal: (state) => {
      if (state.stack.length > 0) {
        const topModalId = state.stack.pop();
        delete state.modals[topModalId];
      }
    },
    updateModal: (state, action) => {
      const { id, data } = action.payload;
      if (state.modals[id]) {
        state.modals[id].data = { ...state.modals[id].data, ...data };
      }
    },
    setModalData: (state, action) => {
      const { id, data } = action.payload;
      if (state.modals[id]) {
        state.modals[id].data = data;
      }
    },
  },
});

export const {
  openModal,
  closeModal,
  closeAllModals,
  closeTopModal,
  updateModal,
  setModalData,
} = modalSlice.actions;

export const selectModalStack = (state) => state.modals.stack;
export const selectModals = (state) => state.modals.modals;
export const selectTopModal = (state) => {
  const { stack, modals } = state.modals;
  if (stack.length === 0) return null;
  return modals[stack[stack.length - 1]];
};
export const selectModalById = (modalId) => (state) => state.modals.modals[modalId];

export default modalSlice.reducer;
