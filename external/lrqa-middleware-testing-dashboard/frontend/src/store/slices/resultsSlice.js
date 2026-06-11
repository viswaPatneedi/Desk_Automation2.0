import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axiosInstance from '@services/axiosService';

export const fetchResults = createAsyncThunk(
  'results/fetchResults',
  async (params, { rejectWithValue }) => {
    try {
      const response = await axiosInstance.get('/results', { params });
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const fetchResultDetail = createAsyncThunk(
  'results/fetchDetail',
  async (id, { rejectWithValue }) => {
    try {
      const response = await axiosInstance.get(`/results/${id}`);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

const initialState = {
  items: [],
  selectedResult: null,
  isLoading: false,
  isLoadingDetail: false,
  error: null,
  filter: {
    status: 'all',
    type: 'all',
    dateRange: null,
  },
  pagination: {
    page: 1,
    limit: 20,
    total: 0,
  },
};

const resultsSlice = createSlice({
  name: 'results',
  initialState,
  reducers: {
    selectResult: (state, action) => {
      state.selectedResult = action.payload;
    },
    setFilter: (state, action) => {
      state.filter = { ...state.filter, ...action.payload };
      state.pagination.page = 1;
    },
    setPagination: (state, action) => {
      state.pagination = { ...state.pagination, ...action.payload };
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch Results
      .addCase(fetchResults.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchResults.fulfilled, (state, action) => {
        state.isLoading = false;
        state.items = action.payload.results || [];
        state.pagination.total = action.payload.total || 0;
      })
      .addCase(fetchResults.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })

      // Fetch Detail
      .addCase(fetchResultDetail.pending, (state) => {
        state.isLoadingDetail = true;
        state.error = null;
      })
      .addCase(fetchResultDetail.fulfilled, (state, action) => {
        state.isLoadingDetail = false;
        state.selectedResult = action.payload;
      })
      .addCase(fetchResultDetail.rejected, (state, action) => {
        state.isLoadingDetail = false;
        state.error = action.payload;
      });
  },
});

export const { selectResult, setFilter, setPagination, clearError } = resultsSlice.actions;
export default resultsSlice.reducer;
