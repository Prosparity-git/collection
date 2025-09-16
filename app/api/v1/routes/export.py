from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.deps import get_db
from app.crud.export import get_collection_export_data
from app.schemas.export import ExportCollectionDataRequest
import pandas as pd
import io
from typing import Optional

router = APIRouter()

@router.get("/collection-data")
async def export_collection_data(
    demand_month: int = Query(..., description="Demand month (1-12)"),
    demand_year: int = Query(..., description="Demand year"),
    format: str = Query("excel", description="Export format (excel)"),
    db: Session = Depends(get_db)
):
    """
    Export collection data to Excel format
    """
    try:
        # Get data from database
        data = get_collection_export_data(db, demand_month, demand_year)
        
        if not data:
            raise HTTPException(status_code=404, detail="No data found for the specified month and year")
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Create Excel file in memory
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Collection Data', index=False)
            
            # Get the workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Collection Data']
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        # Create filename
        filename = f"collection_data_{demand_month}_{demand_year}.xlsx"
        
        # Return file as streaming response
        return StreamingResponse(
            io.BytesIO(output.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
