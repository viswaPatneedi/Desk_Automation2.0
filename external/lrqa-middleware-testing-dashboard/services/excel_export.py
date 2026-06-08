"""Excel export utility for test results data"""

import io
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def create_reboot_perf_excel(results_by_device):
    """
    Create Excel file from reboot performance results - formatted with device info header
    
    Args:
        results_by_device: Dict with structure {device_ip: {device_name, device_id, image_name, avg_boot_time, jobs: {job_id: {per_iteration: [{...}]}}}}
    
    Returns:
        BytesIO buffer with Excel file
    """
    wb = Workbook()
    wb.remove(wb.active)
    
    # Define styles
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    table_header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    table_header_font = Font(bold=True, color="FFFFFF", size=11)
    device_info_font = Font(size=10)
    label_font = Font(bold=True, size=10)
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left_align = Alignment(horizontal="left", vertical="top", wrap_text=True)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Create sheet for each device
    for device_ip, device_data in results_by_device.items():
        device_name = device_data.get('device_name', 'Unknown')
        sheet_name = f"{device_name[:30]}"
        ws = wb.create_sheet(title=sheet_name)
        
        # ===== DEVICE INFO HEADER SECTION =====
        current_row = 1
        
        # Device name and IP
        ws['A1'] = 'Device'
        ws['A1'].font = label_font
        ws['B1'] = f"{device_name} ({device_ip})"
        ws['B1'].font = device_info_font
        current_row += 1
        
        # Image/Build
        ws['A2'] = 'Image/Build'
        ws['A2'].font = label_font
        ws['B2'] = device_data.get('image_name', 'Unknown')
        ws['B2'].font = device_info_font
        current_row += 1
        
        # Execution Time
        ws['A3'] = 'Execution Time'
        ws['A3'].font = label_font
        execution_time = device_data.get('execution_time', '-')
        ws['B3'] = execution_time
        ws['B3'].font = device_info_font
        current_row += 1
        
        # Average Boot Time
        ws['A4'] = 'Average Boot Time (s)'
        ws['A4'].font = label_font
        avg_boot_time = device_data.get('avg_boot_time', '-')
        ws['B4'] = avg_boot_time
        ws['B4'].font = device_info_font
        ws['B4'].number_format = '0.00'
        current_row += 2  # Add blank row
        
        # ===== ITERATIONS TABLE SECTION =====
        table_start_row = current_row
        
        # Add table column headers
        headers = ['Iteration No', 'Boot Type', 'Reboot Time (s)', 'Crash Found', 'Logs Collected', 'Crash Details', 'RDK Milestone Logs']
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=table_start_row, column=col_idx)
            cell.value = header
            cell.font = table_header_font
            cell.fill = table_header_fill
            cell.alignment = center_align
            cell.border = border
        
        ws.row_dimensions[table_start_row].height = 20
        
        # Add data rows
        row_idx = table_start_row + 1
        jobs = device_data.get('jobs', {})
        
        for job_id, job_data in jobs.items():
            for iteration_data in job_data.get('per_iteration', []):
                iteration = iteration_data.get('iteration')
                boot_type = iteration_data.get('boot_type', '-')
                performance_seconds = iteration_data.get('performance_seconds')
                crash_found = iteration_data.get('crash_found', False)
                crash_details = iteration_data.get('crash_details', [])
                logs_collected = iteration_data.get('logs_collected', False)
                rdk_milestone_logs = iteration_data.get('rdk_milestone_logs', [])
                
                # Iteration No
                cell = ws.cell(row=row_idx, column=1)
                cell.value = iteration
                cell.alignment = center_align
                cell.border = border
                
                # Boot Type
                cell = ws.cell(row=row_idx, column=2)
                cell.value = boot_type
                cell.alignment = center_align
                cell.border = border
                
                # Reboot Time
                cell = ws.cell(row=row_idx, column=3)
                if performance_seconds is not None:
                    cell.value = round(performance_seconds, 2)
                    cell.number_format = '0.00'
                else:
                    cell.value = '-'
                cell.alignment = center_align
                cell.border = border
                
                # Crash Found
                cell = ws.cell(row=row_idx, column=4)
                cell.value = 'YES' if crash_found else 'NO'
                cell.alignment = center_align
                cell.border = border
                if crash_found:
                    cell.font = Font(color="FF0000", bold=True)
                
                # Logs Collected
                cell = ws.cell(row=row_idx, column=5)
                cell.value = 'YES' if logs_collected else 'NO'
                cell.alignment = center_align
                cell.border = border
                
                # Crash Details
                cell = ws.cell(row=row_idx, column=6)
                if crash_details:
                    if isinstance(crash_details, list):
                        # crash_details is now a list of dicts with structure: {'description': ..., 'output': ..., 'output_lines': ..., 'line_count': ...}
                        formatted_details = []
                        for detail in crash_details:
                            if isinstance(detail, dict):
                                output = detail.get('output', '').strip()
                                if output:
                                    # Show only the actual log output, truncate to 200 chars for Excel
                                    formatted_details.append(output[:200])
                                else:
                                    # Fallback to description if no output
                                    desc = detail.get('description', 'Crash detected')
                                    formatted_details.append(desc)
                            else:
                                # Old format compatibility (string)
                                formatted_details.append(str(detail))
                        cell.value = ' | '.join(formatted_details)
                    else:
                        cell.value = str(crash_details)
                    cell.alignment = left_align
                else:
                    cell.value = '-'
                    cell.alignment = center_align
                cell.border = border
                
                # RDK Milestone Logs
                cell = ws.cell(row=row_idx, column=7)
                if rdk_milestone_logs:
                    if isinstance(rdk_milestone_logs, list):
                        cell.value = ' | '.join(str(log) for log in rdk_milestone_logs)
                    else:
                        cell.value = str(rdk_milestone_logs)
                    cell.alignment = left_align
                else:
                    cell.value = '-'
                    cell.alignment = center_align
                cell.border = border
                
                ws.row_dimensions[row_idx].height = None  # Auto height
                row_idx += 1
        
        # Auto-adjust column widths
        ws.column_dimensions['A'].width = 15
        ws.column_dimensions['B'].width = 18
        ws.column_dimensions['C'].width = 16
        ws.column_dimensions['D'].width = 14
        ws.column_dimensions['E'].width = 15
        ws.column_dimensions['F'].width = 20
        ws.column_dimensions['G'].width = 25
        
        # Add footer with timestamp
        footer_row = row_idx + 2
        ws.merge_cells(f'A{footer_row}:G{footer_row}')
        cell = ws[f'A{footer_row}']
        cell.value = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        cell.font = Font(italic=True, size=9, color="666666")
        cell.alignment = left_align
    
    # Save to buffer
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def create_tiles_excel(results_by_device):
    """
    Create Excel file from tiles detection results
    
    Args:
        results_by_device: Dict with structure {device_ip: {device_name, jobs: {job_id: {per_iteration: [{...}]}}}}
    
    Returns:
        BytesIO buffer with Excel file
    """
    wb = Workbook()
    wb.remove(wb.active)
    
    # Define styles
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    title_fill = PatternFill(start_color="70AD47", end_color="70AD47", fill_type="solid")
    title_font = Font(bold=True, color="FFFFFF", size=12)
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left_align = Alignment(horizontal="left", vertical="top", wrap_text=True)
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Create sheet for each device
    for device_ip, device_data in results_by_device.items():
        device_name = device_data.get('device_name', 'Unknown')
        sheet_name = f"{device_name[:30]}"
        ws = wb.create_sheet(title=sheet_name)
        
        # Add device header
        ws.merge_cells('A1:D1')
        cell = ws['A1']
        cell.value = f"Device: {device_name} ({device_ip})"
        cell.font = title_font
        cell.fill = title_fill
        cell.alignment = center_align
        cell.border = border
        ws.row_dimensions[1].height = 25
        
        # Add column headers
        headers = ['Iteration', 'Tiles Found', 'Input Tiles', 'Missing Tiles']
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=2, column=col_idx)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center_align
            cell.border = border
        
        ws.row_dimensions[2].height = 20
        
        # Add data rows
        row_idx = 3
        jobs = device_data.get('jobs', {})
        
        for job_id, job_data in jobs.items():
            for iteration_data in job_data.get('per_iteration', []):
                iteration = iteration_data.get('iteration')
                tiles_status = iteration_data.get('tiles_status', '-')
                found_tiles = iteration_data.get('found_tiles', [])
                missing_tiles = iteration_data.get('missing_tiles', [])
                
                # Iteration
                cell = ws.cell(row=row_idx, column=1)
                cell.value = f"ITR-{iteration}"
                cell.alignment = center_align
                cell.border = border
                
                # Tiles Found (Status)
                cell = ws.cell(row=row_idx, column=2)
                cell.value = tiles_status
                cell.alignment = center_align
                cell.border = border
                # Color code based on status
                if tiles_status and '/' in tiles_status:
                    found, total = tiles_status.split('/')
                    if found == total:
                        # Green for all found
                        cell.fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
                    else:
                        # Yellow for partial
                        cell.fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
                
                # Input Tiles
                cell = ws.cell(row=row_idx, column=3)
                if found_tiles:
                    cell.value = ', '.join(found_tiles)
                else:
                    cell.value = '-'
                cell.alignment = left_align
                cell.border = border
                ws.row_dimensions[row_idx].height = None  # Auto height
                
                # Missing Tiles
                cell = ws.cell(row=row_idx, column=4)
                if missing_tiles:
                    cell.value = ', '.join(missing_tiles)
                    cell.font = Font(color="FF0000")
                else:
                    cell.value = '-'
                cell.alignment = left_align
                cell.border = border
                
                row_idx += 1
        
        # Auto-adjust column widths
        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 14
        ws.column_dimensions['C'].width = 35
        ws.column_dimensions['D'].width = 35
        
        # Add footer with timestamp
        footer_row = row_idx + 2
        ws.merge_cells(f'A{footer_row}:D{footer_row}')
        cell = ws[f'A{footer_row}']
        cell.value = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        cell.font = Font(italic=True, size=10, color="666666")
        cell.alignment = left_align
    
    # Save to buffer
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
