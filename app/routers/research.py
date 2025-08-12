import json
import os
import re
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse

# Local imports
from app.utils.supabase_client import get_supabase_client
from app.helpers.auth import get_current_user
from app.helpers.research import (
    active_research_tasks,
    cleanup_temp_file,
    generate_research_pdf,
    simple_sanitize,
)
from app.helpers.research import conduct_research
from app.models.research import (
    Report,
    ReportResponse,
    ResearchHistory,
    ResearchHistoryResponse,
    ResearchRequest,
    ResearchResponse,
)


supabase = get_supabase_client()

router = APIRouter()


@router.post("/", response_model=ResearchResponse)
async def request_research(
    research_req: ResearchRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """Start a research task on a topic"""
    # Generate a unique ID for this research
    research_id = str(uuid.uuid4())

    # Initialize the task status
    active_research_tasks[research_id] = {
        "user_id": current_user["id"],
        "topic": research_req.topic,
        "status": "in_progress",
        "start_time": datetime.now(timezone.utc).isoformat(),
    }

    # Start the research task in the background
    background_tasks.add_task(
        conduct_research,
        research_id,
        research_req.topic,
        research_req.additional_context,
        current_user["id"],
    )

    return ResearchResponse(
        research_id=research_id,
        status="in_progress",
        estimated_time=60,  # Estimate 60 seconds for research
    )


@router.get("/history", response_model=ResearchHistoryResponse)
async def get_research_history(current_user: dict = Depends(get_current_user)):
    """Get the user's research history"""
    response = (
        supabase.table("research_reports")
        .select("id, user_id, topic, created_at")
        .eq("user_id", current_user["id"])
        .eq("deleted", False)
        .order("created_at", desc=True)
        .execute()
    )

    researches = [
        ResearchHistory(
            id=item["id"],
            user_id=item["user_id"],
            topic=item["topic"],
            created_at=item["created_at"],
        )
        for item in response.data
    ]

    return ResearchHistoryResponse(researches=researches)


@router.get("/{research_id}/status")
async def get_research_status(
    research_id: str, current_user: dict = Depends(get_current_user)
):
    """Get the status of a research task"""
    if research_id not in active_research_tasks:
        # Check if it's in the database
        response = (
            supabase.table("research_reports")
            .select("*")
            .eq("id", research_id)
            .eq("user_id", current_user["id"])
            .eq("deleted", False)
            .execute()
        )

        if response.data:
            return {"status": "completed"}

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Research task not found"
        )

    task = active_research_tasks[research_id]

    # Ensure the user owns this research
    if task["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    return {"status": task["status"]}


@router.get("/{research_id}", response_model=ReportResponse)
async def get_research_report(
    research_id: str, current_user: dict = Depends(get_current_user)
):
    """Get the completed research report"""
    # Check if the research is completed
    if (
        research_id in active_research_tasks
        and active_research_tasks[research_id]["status"] != "completed"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Research is still in progress",
        )

    # Get from database
    response = (
        supabase.table("research_reports")
        .select("*")
        .eq("id", research_id)
        .eq("user_id", current_user["id"])
        .eq("deleted", False)
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Research report not found"
        )

    report_data = response.data[0]

    # Parse the JSON fields
    try:
        if isinstance(report_data["sections"], str):
            report_data["sections"] = json.loads(report_data["sections"])
        if isinstance(report_data["sources"], str):
            report_data["sources"] = json.loads(report_data["sources"])
    except:
        # If parsing fails, use the raw data
        print("Failed to parse JSON from report data")
        pass

    return ReportResponse(
        id=report_data["id"],
        topic=report_data["topic"],
        summary=report_data["summary"],
        sections=report_data["sections"],
        sources=report_data["sources"],
        created_at=report_data["created_at"],
    )


@router.get("/{research_id}/pdf")
async def get_research_pdf(
    research_id: str, current_user: dict = Depends(get_current_user)
):
    """Generate and download a PDF of the research report using ReportLab"""
    # Check if the research is completed
    if (
        research_id in active_research_tasks
        and active_research_tasks[research_id]["status"] != "completed"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Research is still in progress",
        )

    pdf_path = None

    try:
        # Get the report
        response = (
            supabase.table("research_reports")
            .select("*")
            .eq("id", research_id)
            .eq("user_id", current_user["id"])
            .eq("deleted", False)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Research report not found",
            )

        report_data = response.data[0]

        # Parse the JSON fields
        if isinstance(report_data["sections"], str):
            report_data["sections"] = json.loads(report_data["sections"])
        if isinstance(report_data["sources"], str):
            report_data["sources"] = json.loads(report_data["sources"])

        # Create a unique temporary file path
        pdf_path = f"temp_{research_id}_{uuid.uuid4().hex[:8]}.pdf"

        # Generate the Research Report PDF
        generate_research_pdf(report_data, pdf_path)

        topic = simple_sanitize(report_data.get("topic", "Research_Report"))

        # Create a background task to clean up the file after it's been sent
        background_tasks = BackgroundTasks()
        print(f"Background tasks: {background_tasks}")
        background_tasks.add_task(cleanup_temp_file, pdf_path)

        # Return the file as a response
        return FileResponse(
            path=pdf_path,
            filename=f"LibreResearch-{topic.replace(' ', '_')}.pdf",
            media_type="application/pdf",
            background=background_tasks,
        )
    except Exception as e:
        # Clean up any temporary file if it exists
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except:
                pass

        # Log the error and return a proper HTTP exception
        error_detail = f"Failed to generate PDF: {str(e)}"
        print(error_detail)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_detail
        )


@router.delete("/{research_id}")
async def delete_research_report(
    research_id: str, current_user: dict = Depends(get_current_user)
):
    try:
        response = (
            supabase.table("research_reports")
            .select("*")
            .eq("id", research_id)
            .eq("user_id", current_user["id"])
            .eq("deleted", False)
            .execute()
        )

        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Research report not found",
            )

        # Delete the report
        supabase.table("research_reports").update({"deleted": True}).eq(
            "id", research_id
        ).execute()

        return {"message": "Research report deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete research report: {str(e)}",
        )
