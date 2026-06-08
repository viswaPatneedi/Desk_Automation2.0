# Excel Export Feature Guide

## Overview
The Excel export functionality has been successfully implemented for both the **Reboot Performance Results** page and the **Tiles Detection Results** page. Users can now download filtered result data into Excel spreadsheets with the same column titles and formatting.

## Features Implemented

### 1. **Reboot Performance Results Export**
- **Location**: `/reboot-perf-results` page
- **Button**: Green "Export" button in the filter section
- **File Generated**: `reboot_perf_results_YYYYMMDD_HHMMSS.xlsx`
- **Excel Columns**:
  - Iteration
  - Reboot Time (s) - with 2 decimal places
  - Crash Found - displays "YES" or "NO"
  - Crash Details - multiline crash information
  - Logs Collected - displays "Collected" or "Not Collected"

**Features**:
- One sheet per device
- Color-coded headers (dark blue background)
- Device name and IP displayed as title
- Auto-adjusted column widths
- Timestamp footer with generation time
- Supports filtering by jobs and devices before export

### 2. **Tiles Detection Results Export**
- **Location**: `/tiles-results` page
- **Button**: Green "Export" button next to the Apply Filter button
- **File Generated**: `tiles_detection_results_YYYYMMDD_HHMMSS.xlsx`
- **Excel Columns**:
  - Iteration
  - Tiles Found - displays status (e.g., "8/8")
  - Input Tiles - comma-separated list of found tiles
  - Missing Tiles - comma-separated list of missing tiles (shown in red if any)

**Features**:
- One sheet per device
- Color-coded status badges:
  - Green: All tiles found (e.g., "8/8")
  - Yellow: Partial tiles found (e.g., "7/8")
- Device name and IP displayed as title
- Auto-adjusted column widths for long tile names
- Timestamp footer with generation time
- Supports filtering by jobs and devices before export

## How to Use

### From Reboot Performance Results Page:

1. Navigate to `/reboot-perf-results`
2. (Optional) Select specific jobs and/or devices using the dropdown filters
3. Click "Apply Filter" to apply your selections
4. Click the green "Export" button to download the Excel file
5. The file will be automatically downloaded as `reboot_perf_results_YYYYMMDD_HHMMSS.xlsx`

### From Tiles Detection Results Page:

1. Navigate to `/tiles-results`
2. (Optional) Select a specific job and/or device from the dropdown selectors
3. Click "Apply Filter" to apply your selections
4. Click the green "Export" button to download the Excel file
5. The file will be automatically downloaded as `tiles_detection_results_YYYYMMDD_HHMMSS.xlsx`

## Technical Implementation

### Files Created:
- **`services/excel_export.py`** - Core Excel generation module with two main functions:
  - `create_reboot_perf_excel(results_by_device)` - Generates reboot performance Excel
  - `create_tiles_excel(results_by_device)` - Generates tiles detection Excel

### Files Modified:
1. **`app.py`** (2 new routes):
   - `@app.route('/download/reboot-perf-results')` - Download endpoint for reboot perf
   - `@app.route('/download/tiles-results')` - Download endpoint for tiles

2. **`controllers/results_controller.py`** (2 new methods):
   - `download_reboot_perf_excel()` - Handles reboot performance download
   - `download_tiles_excel()` - Handles tiles detection download

3. **`templates/reboot_perf_results.html`**:
   - Added green "Export" button in filter section
   - Added `downloadExcel()` JavaScript function
   - Function extracts selected filters and calls the download endpoint

4. **`templates/tiles_results.html`**:
   - Added green "Export" button next to Apply Filter
   - Added `downloadExcel()` JavaScript function
   - Function extracts selected filters and calls the download endpoint

### Query Parameters:
The export endpoints support filtering via query parameters:
- `job_ids` - Comma-separated job IDs to include in export
- `device_ips` - Comma-separated device IPs to include in export

Example:
```
/download/reboot-perf-results?job_ids=job1,job2&device_ips=10.0.0.100,10.0.0.101
/download/tiles-results?job_ids=job3&device_ips=10.0.0.100
```

## Excel File Structure

### Reboot Performance Excel:
- **Sheet per Device**: Each device gets its own worksheet named after the device
- **Header Row**: Device name and IP in merged cells (blue background)
- **Column Headers**: Formatted with dark blue background and white text
- **Data Rows**: One row per iteration with all performance metrics
- **Footer**: Generation timestamp in UTC

### Tiles Detection Excel:
- **Sheet per Device**: Each device gets its own worksheet named after the device
- **Header Row**: Device name and IP in merged cells (green background)
- **Column Headers**: Formatted with dark blue background and white text
- **Data Rows**: One row per iteration with tiles status and tile lists
- **Status Coloring**: Green cells for "all found", Yellow for "partial"
- **Footer**: Generation timestamp in UTC

## Dependencies
- `openpyxl==3.1.5` - Already included in requirements.txt
- Flask's `send_file()` function for file serving

## Browser Compatibility
- All modern browsers (Chrome, Firefox, Safari, Edge)
- Files are downloaded with proper MIME type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Automatic filename based on current timestamp

## Notes
- All timestamps in Excel files are in UTC
- Export respects current filter selections
- If no filters are applied, all data is exported
- Export functionality requires user login (protected by @login_required)
- Cell widths are automatically adjusted based on content
- Numbers are formatted with appropriate decimal places
- Large datasets export efficiently (tested with 100+ iterations)

## Testing
The implementation has been tested with:
- Sample data structure validation
- Excel file generation (verified file size and content)
- Multiple devices and jobs
- Filtering by device and job
- All data types (strings, numbers, lists, booleans)

## Future Enhancements
Potential improvements for future versions:
- Add CSV export option
- Add PDF export with charts/graphs
- Add colored rows based on performance metrics
- Add summary statistics sheets
- Add inline charts in Excel
- Email export functionality
