import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axiosInstance from '@services/axiosService';

const AUTH_TOKEN_KEY = import.meta.env.VITE_AUTH_TOKEN_KEY || 'lrqa_auth_token';

// Load initial state from localStorage
const loadAuthState = () => {
  try {
    const token = localStorage.getItem(AUTH_TOKEN_KEY);
    const user = localStorage.getItem('lrqa_user');
    return {
      isAuthenticated: !!token,
      token,
      user: user ? JSON.parse(user) : null,
    };
  } catch {
    return {
      isAuthenticated: false,
      token: null,
      user: null,
    };
  }
};

export const login = createAsyncThunk(
  'auth/login',
  async ({ email, password }, { rejectWithValue }) => {
    try {
      const response = await axiosInstance.post('/auth/login', { email, password });
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const logout = createAsyncThunk(
  'auth/logout',
  async (_, { rejectWithValue }) => {
    try {
      await axiosInstance.post('/auth/logout');
      return null;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

export const verifyToken = createAsyncThunk(
  'auth/verify',
  async (_, { rejectWithValue }) => {
    try {
      const response = await axiosInstance.get('/auth/verify');
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

const initialState = {
  ...loadAuthState(),
  isLoading: false,
  error: null,
  isVerifying: true,
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    setUser: (state, action) => {
      state.user = action.payload;
      localStorage.setItem('lrqa_user', JSON.stringify(action.payload));
    },
  },
  extraReducers: (builder) => {
    builder
      // Login
      .addCase(login.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        state.isLoading = false;
        state.isAuthenticated = true;
        state.token = action.payload.token;
        state.user = action.payload.user;
        localStorage.setItem(AUTH_TOKEN_KEY, action.payload.token);
        localStorage.setItem('lrqa_user', JSON.stringify(action.payload.user));
        axiosInstance.defaults.headers.common['Authorization'] = `Bearer ${action.payload.token}`;
      })
      .addCase(login.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload?.message || 'Login failed';
      })

      // Logout
      .addCase(logout.fulfilled, (state) => {
        state.isAuthenticated = false;
        state.token = null;
        state.user = null;
        state.error = null;
        localStorage.removeItem(AUTH_TOKEN_KEY);
        localStorage.removeItem('lrqa_user');
        delete axiosInstance.defaults.headers.common['Authorization'];
      })

      // Verify Token
      .addCase(verifyToken.pending, (state) => {
        state.isVerifying = true;
      })
      .addCase(verifyToken.fulfilled, (state, action) => {
        state.isVerifying = false;
        state.isAuthenticated = true;
        state.user = action.payload.user;
        localStorage.setItem('lrqa_user', JSON.stringify(action.payload.user));
      })
      .addCase(verifyToken.rejected, (state) => {
        state.isVerifying = false;
        state.isAuthenticated = false;
        state.token = null;
        state.user = null;
        localStorage.removeItem(AUTH_TOKEN_KEY);
        localStorage.removeItem('lrqa_user');
      });
  },
});

export const { clearError, setUser } = authSlice.actions;
export default authSlice.reducer;
