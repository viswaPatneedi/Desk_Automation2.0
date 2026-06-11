# Phase 3: Modal UI Conversion - Implementation Plan

**Status**: Starting Phase 3 🚀  
**Date**: 2026-06-08  
**Objective**: Convert Flask templates to React-based modal UI system

---

## Phase 3 Overview

**Goal**: Transform the existing Flask Jinja2 templates into a modern React-based modal dialog system with real-time WebSocket updates.

**Key Deliverables**:
1. ✅ React component framework setup
2. ✅ Modal dialog system (20+ modal types)
3. ✅ WebSocket real-time communication
4. ✅ State management (Redux/Context API)
5. ✅ Responsive UI components
6. ✅ Authentication flow migration

---

## Architecture: Modal UI System

### Modal Types to Implement (from existing templates)

```
Device Management Modals:
  ├─ device_add_modal.jsx              (Add new device)
  ├─ device_edit_modal.jsx             (Edit device details)
  ├─ device_delete_modal.jsx           (Confirm device deletion)
  ├─ device_viewer_modal.jsx           (View device details/status)
  └─ lock_status_indicator_modal.jsx   (Device lock status)

Job Management Modals:
  ├─ job_create_modal.jsx              (Create new job)
  ├─ job_details_modal.jsx             (View job details)
  ├─ job_status_modal.jsx              (Monitor job status)
  └─ job_cancel_modal.jsx              (Cancel job confirmation)

Execution Results Modals:
  ├─ results_view_modal.jsx            (View execution results)
  ├─ results_filter_modal.jsx          (Filter & search results)
  ├─ reboot_perf_results_modal.jsx     (Performance test results)
  ├─ soft_hard_boot_results_modal.jsx  (Boot test results)
  ├─ system_command_results_modal.jsx  (Command execution results)
  ├─ tiles_results_modal.jsx           (Tile results view)
  └─ deepsleep_results_modal.jsx       (Deep sleep test results)

Comparison Modals:
  └─ reboot_perf_compare_modal.jsx     (Performance comparison)

Configuration Modals:
  ├─ log_patterns_modal.jsx            (Log pattern configuration)
  ├─ system_commands_modal.jsx         (System commands config)
  └─ saved_sequences_modal.jsx         (Sequence management)

Authentication Modals:
  ├─ login_modal.jsx                   (User login)
  ├─ register_modal.jsx                (User registration)
  ├─ forgot_password_modal.jsx         (Reset password flow)
  ├─ verify_code_modal.jsx             (Email verification)
  └─ reset_password_modal.jsx          (Password reset)
```

### Directory Structure

```
frontend/
├─ public/
│  ├─ index.html
│  └─ favicon.ico
├─ src/
│  ├─ components/
│  │  ├─ modals/
│  │  │  ├─ ModalBase.jsx             (Base modal wrapper)
│  │  │  ├─ ModalContainer.jsx        (Modal orchestrator)
│  │  │  ├─ device/
│  │  │  │  ├─ DeviceAddModal.jsx
│  │  │  │  ├─ DeviceEditModal.jsx
│  │  │  │  └─ DeviceDeleteModal.jsx
│  │  │  ├─ job/
│  │  │  │  ├─ JobCreateModal.jsx
│  │  │  │  ├─ JobDetailsModal.jsx
│  │  │  │  └─ JobStatusModal.jsx
│  │  │  ├─ results/
│  │  │  │  ├─ ResultsViewModal.jsx
│  │  │  │  ├─ RebootPerfResultsModal.jsx
│  │  │  │  └─ ResultsFilterModal.jsx
│  │  │  ├─ auth/
│  │  │  │  ├─ LoginModal.jsx
│  │  │  │  ├─ RegisterModal.jsx
│  │  │  │  └─ VerifyCodeModal.jsx
│  │  │  └─ config/
│  │  │     ├─ LogPatternsModal.jsx
│  │  │     └─ SystemCommandsModal.jsx
│  │  ├─ common/
│  │  │  ├─ Button.jsx
│  │  │  ├─ Input.jsx
│  │  │  ├─ Select.jsx
│  │  │  ├─ Table.jsx
│  │  │  ├─ Card.jsx
│  │  │  ├─ Alert.jsx
│  │  │  └─ Spinner.jsx
│  │  └─ layout/
│  │     ├─ Header.jsx
│  │     ├─ Sidebar.jsx
│  │     └─ MainLayout.jsx
│  ├─ pages/
│  │  ├─ Dashboard.jsx                (Main dashboard)
│  │  ├─ Devices.jsx                  (Device management page)
│  │  ├─ Jobs.jsx                     (Job management page)
│  │  ├─ Results.jsx                  (Results page)
│  │  └─ NotFound.jsx                 (404 page)
│  ├─ services/
│  │  ├─ api.js                       (REST API calls)
│  │  ├─ websocket.js                 (WebSocket client)
│  │  ├─ auth.js                      (Authentication service)
│  │  └─ deviceService.js             (Device operations)
│  ├─ store/
│  │  ├─ store.js                     (Redux store setup)
│  │  ├─ slices/
│  │  │  ├─ authSlice.js              (Auth state)
│  │  │  ├─ deviceSlice.js            (Devices state)
│  │  │  ├─ jobSlice.js               (Jobs state)
│  │  │  ├─ resultsSlice.js           (Results state)
│  │  │  └─ uiSlice.js                (UI state - modals)
│  │  └─ hooks.js                     (Custom Redux hooks)
│  ├─ utils/
│  │  ├─ constants.js                 (App constants)
│  │  ├─ helpers.js                   (Utility functions)
│  │  ├─ validators.js                (Form validation)
│  │  └─ formatters.js                (Data formatting)
│  ├─ styles/
│  │  ├─ index.css                    (Global styles)
│  │  ├─ modals.css                   (Modal styles)
│  │  ├─ components.css               (Component styles)
│  │  └─ theme.css                    (Theme variables)
│  ├─ App.jsx                         (Main app component)
│  ├─ index.jsx                       (React entry point)
│  └─ index.css
├─ package.json
├─ vite.config.js
└─ .env.local
```

---

## Implementation Phases

### Phase 3.1: React Foundation (Week 1)
- [ ] Setup Vite + React project
- [ ] Install dependencies (Redux, WebSocket, Tailwind/MUI)
- [ ] Create base component library
- [ ] Implement authentication flow
- [ ] Setup state management

### Phase 3.2: Modal System (Week 2)
- [ ] Create ModalBase component
- [ ] Implement ModalContainer orchestrator
- [ ] Build 25+ modal components
- [ ] Create modal reducer/actions
- [ ] Add modal animations

### Phase 3.3: WebSocket Integration (Week 3)
- [ ] Implement WebSocket client
- [ ] Create real-time listeners
- [ ] Add event handlers for:
  - Job status updates
  - Device status changes
  - Execution progress
  - Agent status updates
- [ ] Implement reconnection logic
- [ ] Add error handling

### Phase 3.4: Integration (Week 4)
- [ ] Connect React frontend to Flask backend
- [ ] Migrate authentication
- [ ] Test all modal flows
- [ ] Performance optimization
- [ ] Deployment setup

---

## Technology Stack

```
Frontend Framework:
  • React 18+ (component library)
  • Vite 4+ (build tool)
  • Tailwind CSS (styling)
  • Redux Toolkit (state management)
  • React Query (data fetching)

Real-time:
  • Socket.io (WebSocket library)
  • Socket.io-client (client side)

Forms & Validation:
  • React Hook Form (form handling)
  • Yup or Zod (validation)

Utilities:
  • Axios (HTTP client)
  • Date-fns (date formatting)
  • Clsx (className utility)

Dev Tools:
  • ESLint (code linting)
  • Prettier (code formatting)
  • Vitest (testing)
```

---

## WebSocket Event Schema

### Client → Server Events
```
// Job Management
emit('job:create', {job_data})
emit('job:cancel', {job_id})
emit('job:retry', {job_id})

// Device Management
emit('device:add', {device_data})
emit('device:update', {device_id, updates})
emit('device:delete', {device_id})

// Status Monitoring
emit('subscribe:job', {job_id})
emit('subscribe:device', {device_id})
emit('unsubscribe', {resource_id})
```

### Server → Client Events
```
// Real-time Updates
on('job:status_changed', {job_id, status, progress})
on('device:status_changed', {device_id, status})
on('execution:progress', {job_id, step, current, total})
on('agent:status_update', {agent_name, status, metrics})

// Notifications
on('notification:, {type, message, severity})
on('error:occurred', {code, message})
```

---

## Modal Opening Patterns

### Pattern 1: Global Modal Dispatcher
```javascript
// Anywhere in the app
dispatch(openModal({
  type: 'DEVICE_ADD',
  payload: { device_data: {} }
}));

// Redux handles:
// - Which modal to show
// - Animation in/out
// - Payload passed to component
// - Backdrop overlay
```

### Pattern 2: URL-based Modal
```javascript
// /app/devices?modal=edit&id=123
// ModalContainer watches URL and opens appropriate modal
```

### Pattern 3: Programmatic
```javascript
// Direct component usage
<DeviceAddModal 
  isOpen={isOpen} 
  onClose={handleClose}
  onSave={handleSave}
/>
```

---

## State Management Strategy

### Redux Slices
```javascript
// uiSlice: Modal state
{
  modals: {
    isOpen: boolean,
    type: string,
    payload: object,
    history: []
  }
}

// deviceSlice: Device state
{
  devices: [],
  selectedDevice: null,
  loading: boolean,
  error: null
}

// jobSlice: Job state
{
  jobs: [],
  selectedJob: null,
  filters: { status, dateRange },
  loading: boolean
}

// authSlice: Auth state
{
  user: { id, name, email, role },
  token: string,
  isAuthenticated: boolean,
  loading: boolean
}
```

---

## Success Metrics

- [ ] All 25+ modals implemented & tested
- [ ] WebSocket real-time updates working
- [ ] UI responsiveness across devices
- [ ] Zero data loss on page refresh
- [ ] Sub-500ms modal open animation
- [ ] 95%+ test coverage
- [ ] Accessibility (A11y) compliant
- [ ] Backward compatible with Flask API

---

## Next Immediate Steps

1. **Setup React Project** - Initialize Vite + React
2. **Create Modal Infrastructure** - Base components & orchestrator
3. **Build Authentication Flow** - Login/register modals
4. **Setup WebSocket** - Real-time communication
5. **Convert Modals** - Start with device management

---

**Estimated Duration**: 4 weeks  
**Team Size**: 1-2 developers  
**Priority**: High (Critical for v2.0 UX)

---

**Status**: Planning Complete - Ready to Start Implementation 🚀
