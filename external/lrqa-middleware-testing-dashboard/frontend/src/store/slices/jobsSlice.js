import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axiosInstance from '@services/axiosService';

export const fetchJobs = createAsyncThunk(
  'jobs/fetchJobs',
  async (_, { rejectWithValue }) => {
    try {
      const response = await axiosInstance.get('/jobs');
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const createJob = createAsyncThunk(
  'jobs/createJob',
  async (jobData, { rejectWithValue }) => {
    try {
      const response = await axiosInstance.post('/jobs', jobData);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const updateJob = createAsyncThunk(
  'jobs/updateJob',
  async ({ id, data }, { rejectWithValue }) => {
    try {
      const response = await axiosInstance.put(`/jobs/${id}`, data);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const cancelJob = createAsyncThunk(
  'jobs/cancelJob',
  async (id, { rejectWithValue }) => {
    try {
      const response = await axiosInstance.post(`/jobs/${id}/cancel`);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

const initialState = {
  items: [],
  isLoading: false,
  error: null,
  selectedJob: null,
  filter: {
    status: 'all',
    device: 'all',
  },
};

const jobsSlice = createSlice({
  name: 'jobs',
  initialState,
  reducers: {
    selectJob: (state, action) => {
      state.selectedJob = action.payload;
    },
    setFilter: (state, action) => {
      state.filter = { ...state.filter, ...action.payload };
    },
    clearError: (state) => {
      state.error = null;
    },
    updateJobStatus: (state, action) => {
      const { id, status } = action.payload;
      const job = state.items.find(j => j.id === id);
      if (job) {
        job.status = status;
      }
      if (state.selectedJob?.id === id) {
        state.selectedJob.status = status;
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch Jobs
      .addCase(fetchJobs.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchJobs.fulfilled, (state, action) => {
        state.isLoading = false;
        state.items = action.payload;
      })
      .addCase(fetchJobs.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })

      // Create Job
      .addCase(createJob.fulfilled, (state, action) => {
        state.items.unshift(action.payload);
      })
      .addCase(createJob.rejected, (state, action) => {
        state.error = action.payload;
      })

      // Update Job
      .addCase(updateJob.fulfilled, (state, action) => {
        const index = state.items.findIndex(j => j.id === action.payload.id);
        if (index !== -1) {
          state.items[index] = action.payload;
        }
        if (state.selectedJob?.id === action.payload.id) {
          state.selectedJob = action.payload;
        }
      })

      // Cancel Job
      .addCase(cancelJob.fulfilled, (state, action) => {
        const job = state.items.find(j => j.id === action.payload.id);
        if (job) {
          job.status = 'cancelled';
        }
      });
  },
});

export const { selectJob, setFilter, clearError, updateJobStatus } = jobsSlice.actions;
export default jobsSlice.reducer;
