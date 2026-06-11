import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axiosInstance from '@services/axiosService';

export const fetchDevices = createAsyncThunk(
  'devices/fetchDevices',
  async (_, { rejectWithValue }) => {
    try {
      const response = await axiosInstance.get('/devices');
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const addDevice = createAsyncThunk(
  'devices/addDevice',
  async (deviceData, { rejectWithValue }) => {
    try {
      const response = await axiosInstance.post('/devices', deviceData);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const updateDevice = createAsyncThunk(
  'devices/updateDevice',
  async ({ id, data }, { rejectWithValue }) => {
    try {
      const response = await axiosInstance.put(`/devices/${id}`, data);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const deleteDevice = createAsyncThunk(
  'devices/deleteDevice',
  async (id, { rejectWithValue }) => {
    try {
      await axiosInstance.delete(`/devices/${id}`);
      return id;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

const initialState = {
  items: [],
  isLoading: false,
  error: null,
  selectedDevice: null,
};

const devicesSlice = createSlice({
  name: 'devices',
  initialState,
  reducers: {
    selectDevice: (state, action) => {
      state.selectedDevice = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch Devices
      .addCase(fetchDevices.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchDevices.fulfilled, (state, action) => {
        state.isLoading = false;
        state.items = action.payload;
      })
      .addCase(fetchDevices.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })

      // Add Device
      .addCase(addDevice.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(addDevice.fulfilled, (state, action) => {
        state.isLoading = false;
        state.items.push(action.payload);
      })
      .addCase(addDevice.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })

      // Update Device
      .addCase(updateDevice.fulfilled, (state, action) => {
        const index = state.items.findIndex(d => d.id === action.payload.id);
        if (index !== -1) {
          state.items[index] = action.payload;
        }
        if (state.selectedDevice?.id === action.payload.id) {
          state.selectedDevice = action.payload;
        }
      })
      .addCase(updateDevice.rejected, (state, action) => {
        state.error = action.payload;
      })

      // Delete Device
      .addCase(deleteDevice.fulfilled, (state, action) => {
        state.items = state.items.filter(d => d.id !== action.payload);
        if (state.selectedDevice?.id === action.payload) {
          state.selectedDevice = null;
        }
      })
      .addCase(deleteDevice.rejected, (state, action) => {
        state.error = action.payload;
      });
  },
});

export const { selectDevice, clearError } = devicesSlice.actions;
export default devicesSlice.reducer;
