import { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Routes, Route, Navigate } from 'react-router-dom';
import { initializeApp } from '@store/slices/appSlice';
import { initializeWebSocket } from '@services/websocketService';
import PrivateRoute from '@components/auth/PrivateRoute';
import MainLayout from '@components/layouts/MainLayout';
import AuthLayout from '@components/layouts/AuthLayout';
import ErrorBoundary from '@components/common/ErrorBoundary';
import ModalContainer from '@components/modals/ModalContainer';
import { useNotification } from '@hooks/useNotification';

// Pages
import LoginPage from '@pages/auth/LoginPage';
import DashboardPage from '@pages/DashboardPage';
import DevicesPage from '@pages/devices/DevicesPage';
import JobsPage from '@pages/jobs/JobsPage';
import ResultsPage from '@pages/results/ResultsPage';
import SettingsPage from '@pages/settings/SettingsPage';
import NotFoundPage from '@pages/NotFoundPage';

export default function App() {
  const dispatch = useDispatch();
  const { isInitialized, isLoading } = useSelector(state => state.app);
  const { isAuthenticated } = useSelector(state => state.auth);
  const { Notification } = useNotification();

  // Initialize app on mount
  useEffect(() => {
    const initApp = async () => {
      try {
        // Dispatch app initialization
        dispatch(initializeApp());

        // Initialize WebSocket connection
        if (isAuthenticated) {
          initializeWebSocket();
        }
      } catch (error) {
        console.error('Failed to initialize app:', error);
      }
    };

    initApp();
  }, [dispatch, isAuthenticated]);

  if (isLoading || !isInitialized) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <div className="mb-4 animate-spin">
            <svg
              className="w-12 h-12 text-blue-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
          </div>
          <p className="text-gray-600">Initializing LRQA v2.0...</p>
        </div>
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <div className="app">
        <Routes>
          {/* Public Routes */}
          <Route path="/auth" element={<AuthLayout />}>
            <Route path="login" element={<LoginPage />} />
            <Route index element={<Navigate to="login" replace />} />
          </Route>

          {/* Protected Routes */}
          <Route
            path="/"
            element={
              <PrivateRoute>
                <MainLayout />
              </PrivateRoute>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="devices" element={<DevicesPage />} />
            <Route path="jobs" element={<JobsPage />} />
            <Route path="results" element={<ResultsPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>

          {/* 404 Route */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>

        {/* Global Modal Container */}
        <ModalContainer />

        {/* Notification System */}
        <Notification />
      </div>
    </ErrorBoundary>
  );
}
