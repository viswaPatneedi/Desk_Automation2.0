import { configureStore } from '@reduxjs/toolkit';
import appReducer from './slices/appSlice';
import authReducer from './slices/authSlice';
import modalReducer from './slices/modalSlice';
import devicesReducer from './slices/devicesSlice';
import jobsReducer from './slices/jobsSlice';
import resultsReducer from './slices/resultsSlice';

export default configureStore({
  reducer: {
    app: appReducer,
    auth: authReducer,
    modals: modalReducer,
    devices: devicesReducer,
    jobs: jobsReducer,
    results: resultsReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['app/initialize/fulfilled'],
        ignoredPaths: ['app.config'],
      },
    }),
});
