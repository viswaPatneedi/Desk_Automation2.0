import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axiosInstance from '@services/axiosService';

export const initializeApp = createAsyncThunk(
  'app/initialize',
  async (_, { rejectWithValue }) => {
    try {
      // Fetch app configuration from backend
      const response = await axiosInstance.get('/config');
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

const initialState = {
  isInitialized: false,
  isLoading: true,
  error: null,
  config: {
    appName: 'LRQA v2.0',
    version: '2.0.0',
    environment: process.env.VITE_ENVIRONMENT || 'development',
  },
};

const appSlice = createSlice({
  name: 'app',
  initialState,
  reducers: {
    setConfig: (state, action) => {
      state.config = { ...state.config, ...action.payload };
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(initializeApp.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(initializeApp.fulfilled, (state, action) => {
        state.isInitialized = true;
        state.isLoading = false;
        state.config = { ...state.config, ...action.payload };
      })
      .addCase(initializeApp.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
        // Still consider app initialized even if config fetch fails
        state.isInitialized = true;
      });
  },
});

export const { setConfig } = appSlice.actions;
export default appSlice.reducer;
