from io import BytesIO
import pandas as pd

def normalize_url(url):
    if not isinstance(url, str):
        return ""
    url = url.replace("https://", "").replace("http://", "").replace("www.", "")
    if url.endswith("/"):
        url = url[:-1]
    return url.strip()

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

def to_excel_multi(sheets_dict):
    output = BytesIO()
    has_sheets = False
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in sheets_dict.items():
            if df is not None and not df.empty:
                df.to_excel(writer, index=False, sheet_name=sheet_name)
                has_sheets = True
        
        if not has_sheets:
            pd.DataFrame({"Informacja": ["Brak danych (puste tabele)"]}).to_excel(writer, index=False, sheet_name="Brak Danych")
                
        # Access the workbook to apply formatting
        workbook = writer.book
        
        # Define some basic styles
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
        
        for sheet_name in workbook.sheetnames:
            worksheet = workbook[sheet_name]
            
            # Format header row
            for cell in worksheet[1]:
                cell.font = header_font
                cell.fill = header_fill
                
            # Auto-adjust columns width based on data
            for col_idx, col in enumerate(worksheet.columns, 1):
                max_length = 0
                column = get_column_letter(col_idx)
                for cell in col:
                    try:
                        if cell.value:
                            max_length = max(max_length, len(str(cell.value)))
                    except:
                        pass
                # Set a little padding, max width 60, min width 10
                adjusted_width = max(10, min(max_length + 2, 60))
                worksheet.column_dimensions[column].width = adjusted_width

    return output.getvalue()
