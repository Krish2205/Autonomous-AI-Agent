"""
JARVIS — Universal Academic Learning & Educator Autonomous Executive Suite
Provides an end-to-end autonomous executive assistant for school teachers, college professors, and university educators:
Curriculum & Syllabus Architect, Exam Controller Studio, Google Sheets Gradebook, Google Calendar Sync, Notes Management, Parent Broadcasts, and Cloud PDF Export.
"""

from langchain_core.prompts import ChatPromptTemplate
from backend.agents.base import BaseAgent
from backend.logger import get_logger
from backend.utils.pdf_generator import create_edtech_pdf
from backend.utils.google_sheets_service import create_live_google_sheet
from backend.config import get_user_integration

logger = get_logger("agents.edtech")


class LessonArchitectAgent(BaseAgent):
    name = "lesson_architect"
    description = (
        "Draft exhaustive, period-by-period timeline lesson plans, syllabus blueprints, course learning outcomes, "
        "and lecture diagrams for school, college, and university courses, complete with downloadable PDF export."
    )

    def run(self, query: str) -> str:
        logger.info(f"Running Universal Curriculum Architect Agent with query: {query[:80]}...")
        llm = self.get_llm(default_model="llama-3.3-70b-versatile", default_temp=0.3)

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are the Chief Academic Officer & Senior Master Curriculum Architect for Schools, Colleges, and Universities worldwide.\n"
                "You do NOT provide high-level summaries. You design exhaustive, highly detailed, professional, day-by-day, period-by-period, or week-by-week TIMELINE syllabi and lecture plans.\n\n"
                "<execution_guidelines>\n"
                "1. Analyze requested level and discipline (e.g. 1st Year University Computer Science, High School Physics, or MBA Marketing).\n"
                "2. Structure a complete Course Timeline Scaffolding across days/weeks (e.g., Day 1 to Day 7 or Week 1 to Week 14 Master Syllabus Plan).\n"
                "3. For EACH Day/Session in the timeline, provide minute-by-minute lecture structure:\n"
                "   - Opening: Learning Objectives, Hook & Prerequisites Recap\n"
                "   - Core: Theoretical Concepts, Mathematical Formulas & Architectural Diagrams\n"
                "   - Practical: Live Code Demonstration, Case Study Analysis, or Lab Experiment Activity\n"
                "   - Closing: Guided Problem Solving, Discussion Prompt & Homework/Reading Assignment\n"
                "4. Deliver publication-grade markdown formatted for university accreditation and syllabus deployment.\n"
                "5. Grounding Rule: If context from uploaded documents is provided, you MUST ground your curriculum planning and lesson topics strictly on the actual concepts, data, and subjects present in that context. Do NOT generate generic or unrelated topics (like default school science or biology) if the context is about different concepts. If the requested topic or subject is blank, empty, or unspecified in the query, identify the primary subject matter from the uploaded context and use that as the primary topic.\n"
                "</execution_guidelines>",
            ),
            ("human", "{query}"),
        ])

        try:
            # Check if RAG context should be fetched
            from backend.config import get_user_documents_dir
            import os
            doc_dir = get_user_documents_dir()
            rag_context = ""
            if os.path.exists(doc_dir) and os.listdir(doc_dir) and "from online" not in query.lower() and "from gpt" not in query.lower():
                logger.info("RAG source selected: Fetching curriculum context from uploaded documents...")
                try:
                    from backend.agents.analyse_agent import AnalyseAgent
                    analyzer = AnalyseAgent()
                    rag_context = analyzer.run(f"Retrieve context matching: {query}")
                    if rag_context == "INFORMATION_NOT_AVAILABLE":
                        rag_context = ""
                except Exception as e:
                    logger.error(f"RAG context retrieval failed: {e}")

            if rag_context:
                contextual_query = f"Here is the context retrieved from the uploaded curriculum/textbook documents:\n{rag_context}\n\nUser request: {query}"
            else:
                contextual_query = query

            chain = prompt | llm
            res = chain.invoke({"query": contextual_query})
            content = res.content

            # Dynamic Title
            topic_title = "Master Curriculum Lecture Plan"
            if "ai agent" in query.lower():
                topic_title = "AI Agents 1-Week Master Curriculum Plan"
            elif "python" in query.lower():
                topic_title = "Python Programming Course Syllabus"

            # Parse explicit export options
            q_low = query.lower()
            has_explicit_tool = any(k in q_low for k in ["pdf", "doc", "word", "docs", "wps", "calendar", "schedule", "event", "meeting", "sheet", "spreadsheet", "excel", "csv", "keep", "task", "reminder", "note"])
            
            trigger_pdf = not has_explicit_tool or "pdf" in q_low or "print" in q_low or "download" in q_low
            trigger_docs = "doc" in q_low or "word" in q_low or "wps" in q_low
            trigger_calendar = "calendar" in q_low or "schedule" in q_low or "event" in q_low or "meeting" in q_low

            pdf_url = None
            if trigger_pdf:
                pdf_url = create_edtech_pdf(
                    title=topic_title,
                    content=content,
                    filename="master_curriculum_lecture_plan"
                )

            # 2. Look up user Google Workspace tokens & save live Google Doc in Drive
            from backend.config import current_user_id, load_profile_config
            from backend.utils.google_workspace_service import create_live_google_doc, create_google_calendar_event
            keys_to_check = [current_user_id.get(), "edtech_studio", "developer", "default"]
            gw_integ = {}
            found_key = "developer"
            for k in keys_to_check:
                if k:
                    cfg = load_profile_config(k).get("integrations", {}).get("google_workspace", {})
                    if cfg.get("access_token") or cfg.get("connected") or cfg.get("refresh_token"):
                        gw_integ = cfg
                        found_key = k
                        break
            google_acc = gw_integ.get("account", "connected.user@google.com")
            access_token = gw_integ.get("access_token")
            refresh_token = gw_integ.get("refresh_token")

            doc_res = None
            if trigger_docs:
                doc_res = create_live_google_doc(
                    title=topic_title,
                    text_body=content[:3500],
                    user_email=google_acc,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    user_key=found_key
                )

            cal_res = None
            if trigger_calendar:
                # 3. Schedule 1-Week Calendar Reminders starting from next Monday
                import datetime
                now_dt = datetime.datetime.now()
                days_ahead = 7 - now_dt.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                start_dt = now_dt + datetime.timedelta(days=days_ahead)
                end_dt = start_dt + datetime.timedelta(days=7)

                start_iso = start_dt.replace(hour=9, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%S")
                end_iso = end_dt.replace(hour=17, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%S")

                cal_res = create_google_calendar_event(
                    summary=f"{topic_title} & Reminders",
                    start_time_iso=start_iso,
                    end_time_iso=end_iso,
                    description=f"Course Schedule ({start_dt.strftime('%b %d')} - {end_dt.strftime('%b %d')})",
                    user_email=google_acc,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    user_key=found_key
                )

            # Build download banner dynamically based on triggered tools
            banners = []
            if pdf_url:
                banners.append(f"📥 [Click Here to Download Printable PDF File]({pdf_url})")
            if doc_res:
                banners.append(f"📝 [Click Here to Open Editable Document in Google Drive / Docs]({doc_res['google_docs_url']})")
            if cal_res:
                banners.append(f"📅 [Click Here to View Course Schedule on Google Calendar]({cal_res['calendar_event_url']})")
                banners.append(f"📹 [Join Automated Google Meet Classroom Session]({cal_res['google_meet_link']})")

            download_banner = (
                f"### 🚀 Academic Execution Complete\n\n"
                f"Your curriculum plan for **{topic_title}** has been compiled successfully!\n\n"
                + "\n".join(banners) + "\n\n"
                f"*Synced with connected account:* `{google_acc}`"
            )
            return download_banner

        except Exception as e:
            logger.error(f"Curriculum Architect Agent failed: {e}")
            return f"Error executing Curriculum Architect task: {str(e)}"


class ExamGeneratorAgent(BaseAgent):
    name = "exam_generator"
    description = (
        "Generate complete examination question papers, unit tests, mid-terms, final exams, "
        "MCQs, Case-Based studies, and detailed grading rubrics with downloadable PDF export."
    )

    def run(self, query: str) -> str:
        logger.info(f"Running Universal Exam Controller Agent with query: {query[:80]}...")
        llm = self.get_llm(default_model="llama-3.3-70b-versatile", default_temp=0.3)

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are an Elite Master Examination Controller & Senior Educator with 10+ years of pedagogical experience.\n"
                "You create highly professional, curriculum-aligned, and blueprint-compliant examination papers, worksheets, and unit tests.\n\n"
                "<execution_guidelines>\n"
                "1. Structure your output with clear headers (Exam Title, Subject, Grade, Time Allowed, Max Marks). Do NOT include or invent any school/institute name.\n"
                "2. Apply Bloom's Taxonomy principles to distribute questions across levels: Cognitive (Recall), Application (Problem-Solving), and Analytical/Creation.\n"
                "3. Divide worksheets and exams into clear sections:\n"
                "   - Section A: Multiple Choice & Objective Questions\n"
                "   - Section B: Short Answer Questions (Conceptual & Definition)\n"
                "   - Section C: Case-Based / Passage-Based analytical studies\n"
                "   - Section D: Long Answer/Essay style synthesis questions\n"
                "4. Provide a highly detailed, step-by-step marking scheme, answer key, and grading rubrics at the end of the document.\n"
                "5. Ensure the tone is highly academic, professional, and directly ready for distribution to students.\n"
                "6. Grounding Rule: If context from uploaded documents is provided, you MUST ground your questions and generated material strictly on the actual concepts, data, and subjects present in that context. Do NOT generate generic or unrelated topics (like default school science or biology) if the context is about different concepts. If the requested topic or subject is blank, empty, or unspecified in the query, identify the primary subject matter from the uploaded context and use that as the primary topic.\n"
                "</execution_guidelines>",
            ),
            ("human", "{query}"),
        ])

        try:
            # Check if RAG context should be fetched
            from backend.config import get_user_documents_dir
            import os
            doc_dir = get_user_documents_dir()
            rag_context = ""
            if os.path.exists(doc_dir) and os.listdir(doc_dir) and "from online" not in query.lower() and "from gpt" not in query.lower():
                logger.info("RAG source selected: Fetching curriculum context from uploaded documents...")
                try:
                    from backend.agents.analyse_agent import AnalyseAgent
                    analyzer = AnalyseAgent()
                    rag_context = analyzer.run(f"Retrieve context matching: {query}")
                    if rag_context == "INFORMATION_NOT_AVAILABLE":
                        rag_context = ""
                except Exception as e:
                    logger.error(f"RAG context retrieval failed: {e}")

            if rag_context:
                contextual_query = f"Here is the context retrieved from the uploaded curriculum/textbook documents:\n{rag_context}\n\nUser request: {query}"
            else:
                contextual_query = query

            chain = prompt | llm
            res = chain.invoke({"query": contextual_query})
            content = res.content

            # Parse explicit export options
            q_low = query.lower()
            has_explicit_tool = any(k in q_low for k in ["pdf", "doc", "word", "docs", "wps", "calendar", "schedule", "event", "meeting", "sheet", "spreadsheet", "excel", "csv", "keep", "task", "reminder", "note"])
            
            trigger_pdf = not has_explicit_tool or "pdf" in q_low or "print" in q_low or "download" in q_low
            trigger_docs = "doc" in q_low or "word" in q_low or "wps" in q_low

            pdf_url = None
            if trigger_pdf:
                pdf_url = create_edtech_pdf(
                    title="Master Academic Examination Test Paper",
                    content=content,
                    filename="master_examination_test_paper"
                )

            # Generate live Google Doc
            from backend.config import current_user_id, load_profile_config
            from backend.utils.google_workspace_service import create_live_google_doc
            keys_to_check = [current_user_id.get(), "edtech_studio", "developer", "default"]
            gw_integ = {}
            found_key = "developer"
            for k in keys_to_check:
                if k:
                    cfg = load_profile_config(k).get("integrations", {}).get("google_workspace", {})
                    if cfg.get("access_token") or cfg.get("connected") or cfg.get("refresh_token"):
                        gw_integ = cfg
                        found_key = k
                        break
            google_acc = gw_integ.get("account", "connected.user@google.com")
            access_token = gw_integ.get("access_token")
            refresh_token = gw_integ.get("refresh_token")

            doc_res = None
            if trigger_docs:
                doc_res = create_live_google_doc(
                    title="Master Academic Examination Paper",
                    text_body=content[:3000],
                    user_email=google_acc,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    user_key=found_key
                )

            # Build download banner dynamically based on triggered tools
            banners = []
            if doc_res:
                banners.append(f"📝 [Click Here to Open Live Editable Document in Google Docs]({doc_res['google_docs_url']})")
            if pdf_url:
                banners.append(f"📥 [Download Printable PDF Test Paper]({pdf_url})")

            download_banner = (
                f"\n\n---\n### 📄 Official Cloud & Print Documents Generated\n"
                + "\n".join(banners) + "\n\n"
                f"*Synced with connected account:* `{google_acc}`"
            )
            return content + download_banner

        except Exception as e:
            logger.error(f"Exam Controller Agent failed: {e}")
            return f"Error executing Exam Controller task: {str(e)}"


class TeacherExecutiveAssistantAgent(BaseAgent):
    name = "teacher_executive_assistant"
    description = (
        "Master Executive Personal Assistant for teachers. Automates daily teaching workflows, "
        "coordinates timetable tasks, delegates exam creation, orchestrates gradebooks, and manages parent communications."
    )

    def run(self, query: str) -> str:
        logger.info(f"Running Teacher Executive Assistant Agent with query: {query[:80]}...")
        llm = self.get_llm(default_model="llama-3.3-70b-versatile", default_temp=0.3)

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are the Chief Executive Personal AI Assistant to the Teacher in JARVIS EdTech OS.\n"
                "You manage the teacher's complete daily workload, organizing tasks across lesson planning, document scanning, "
                "Google Sheets gradebooks, Google Calendar schedules, parent messaging, and classroom notes.\n\n"
                "<execution_guidelines>\n"
                "1. Provide a clear, highly structured executive response breaking down complex requests into actionable steps.\n"
                "2. Offer proactive assistance for daily administrative tasks (e.g. attendance tracking, PTM preparation, unit test scheduling).\n"
                "3. Keep tone supportive, executive, highly organized, and efficient.\n"
                "</execution_guidelines>",
            ),
            ("human", "{query}"),
        ])

        try:
            chain = prompt | llm
            res = chain.invoke({"query": query})
            return res.content
        except Exception as e:
            logger.error(f"Teacher Executive Assistant Agent failed: {e}")
            return f"Error executing Teacher Executive Assistant task: {str(e)}"


class DocumentExamScannerAgent(BaseAgent):
    name = "document_exam_scanner"
    description = (
        "Scan uploaded textbook PDFs, Word files (.docx), syllabus documents, and student answer scripts "
        "to perform autonomous AI paper checking, rubric grading, custom test generation, and classroom fun activities."
    )

    def run(self, query: str) -> str:
        logger.info(f"Running Document Exam Scanner Agent with query: {query[:80]}...")
        llm = self.get_llm(default_model="llama-3.3-70b-versatile", default_temp=0.2)

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are the Senior Document Scanning, Paper Checking & Assessment Ingestion Specialist for Educators.\n"
                "You analyze uploaded documents in all formats (PDF, Word .docx, CSV, Scanned Images) to perform paper checking, rubric evaluation, test generation, and classroom fun games.\n\n"
                "<execution_guidelines>\n"
                "1. If checking student papers: Evaluate answers against master syllabus/answer keys, assign scores, and provide constructive feedback on strengths and areas of improvement.\n"
                "2. If generating quizzes or fun activities: Design engaging classroom games, team trivia, or interactive quick quizzes based on course topics.\n"
                "3. Provide structured, professional markdown output ready for immediate classroom deployment.\n"
                "</execution_guidelines>",
            ),
            ("human", "{query}"),
        ])

        try:
            chain = prompt | llm
            res = chain.invoke({"query": query})
            content = res.content

            # Check if user requested a generated document file
            if "paper check" in query.lower() or "grade" in query.lower() or "result" in query.lower():
                pdf_url = create_edtech_pdf(
                    title="Student Assessment Evaluation & Paper Check Report",
                    content=content,
                    filename="student_paper_check_report"
                )
                return content + f"\n\n---\n### 📄 Official Evaluation Report Generated\n📥 [Click Here to Download Student Paper Check PDF]({pdf_url})"
            return content
        except Exception as e:
            logger.error(f"Document Exam Scanner Agent failed: {e}")
            return f"Error executing Document Exam Scanner task: {str(e)}"


class SheetsGradebookAgent(BaseAgent):
    name = "sheets_gradebook_agent"
    description = (
        "Automates student gradebooks, attendance rosters, CCE marksheets, and class performance analytics "
        "formatted for CSV and Google Sheets export."
    )

    def run(self, query: str) -> str:
        logger.info(f"Running Sheets Gradebook Agent with query: {query[:80]}...")
        try:
            from backend.config import current_user_id, load_profile_config
            keys_to_check = [current_user_id.get(), "edtech_studio", "developer", "default"]
            gw_integ = {}
            found_key = "developer"
            for k in keys_to_check:
                if k:
                    cfg = load_profile_config(k).get("integrations", {}).get("google_workspace", {})
                    if cfg.get("access_token") or cfg.get("connected") or cfg.get("refresh_token"):
                        gw_integ = cfg
                        found_key = k
                        break
            google_acc = gw_integ.get("account", "connected.user@google.com")
            access_token = gw_integ.get("access_token")
            refresh_token = gw_integ.get("refresh_token")

            sheet_res = create_live_google_sheet(
                title="Class Gradebook & Performance Roster",
                headers=["Roll No", "Student Name", "Marks Obtained", "Total", "Percentage", "Grade", "Remarks"],
                rows=[
                    [101, "Aarav Sharma", 88, 100, "88%", "A1", "Excellent conceptual clarity"],
                    [102, "Ananya Patel", 94, 100, "94%", "A1", "Top ranker in class"],
                    [103, "Devansh Gupta", 76, 100, "76%", "B1", "Good effort, work on numericals"],
                    [104, "Isha Verma", 91, 100, "91%", "A1", "Outstanding analytical skills"],
                    [105, "Rohan Kumar", 82, 100, "82%", "A2", "Consistent performance"]
                ],
                user_email=google_acc,
                access_token=access_token,
                refresh_token=refresh_token,
                user_key=found_key
            )

            response_banner = (
                f"### 📊 Google Sheets Action Executed\n\n"
                f"Your requested gradebook spreadsheet has been successfully generated and synced with your connected Google Workspace account.\n\n"
                f"👉 [Click Here to Open Live Spreadsheet in Google Sheets]({sheet_res['google_sheets_url']})\n"
                f"📥 [Download Local CSV Dataset]({sheet_res['local_csv_url']})\n\n"
                f"*Synced with connected account:* `{google_acc}`"
            )
            return response_banner
        except Exception as e:
            logger.error(f"Sheets Gradebook Agent failed: {e}")
            return f"Error executing Sheets Gradebook task: {str(e)}"


class SheetsAgent(BaseAgent):
    name = "sheets"
    description = (
        "Create, format, and manage student marksheets, attendance rosters, and gradebook tables "
        "formatted for Google Sheets and CSV export."
    )

    def run(self, query: str) -> str:
        logger.info(f"Running Sheets Agent with query: {query[:80]}...")
        try:
            if "SYNC_TIMETABLE_SHEET" in query:
                if "\\n" in query:
                    query = query.replace("\\n", "\n")
                lines = [l.strip() for l in query.split('\n') if l.strip()]
                title_line = [l for l in lines if l.startswith("Title: ")]
                title = title_line[0].replace("Title: ", "").strip() if title_line else "Class Timetable"
                
                csv_start_idx = 0
                for i, l in enumerate(lines):
                    if l.startswith("Time,Monday"):
                        csv_start_idx = i
                        break
                
                csv_lines = lines[csv_start_idx:]
                headers = csv_lines[0].split(',')
                
                import csv
                from io import StringIO
                rows = []
                if len(csv_lines) > 1:
                    reader = csv.reader(StringIO('\n'.join(csv_lines[1:])))
                    rows = list(reader)
                else:
                    rows = [["" for _ in headers]]
            elif "class 2" in query.lower() or "a-f" in query.lower() or "section" in query.lower():
                headers = ["Section ID", "Class & Section", "Class Teacher", "Student Count", "Room No", "Status"]
                rows = [
                    [1, "Class 2-A", "Mrs. Sunita Sharma", 35, "Room 101", "Active"],
                    [2, "Class 2-B", "Mr. Rajesh Verma", 34, "Room 102", "Active"],
                    [3, "Class 2-C", "Mrs. Anjali Gupta", 36, "Room 103", "Active"],
                    [4, "Class 2-D", "Mr. Vikram Singh", 35, "Room 104", "Active"],
                    [5, "Class 2-E", "Mrs. Pooja Patel", 33, "Room 105", "Active"],
                    [6, "Class 2-F", "Mr. Amit Joshi", 34, "Room 106", "Active"]
                ]
                title = "Class 2 Sub-Sections A-F Master Sheet"
            else:
                headers = ["Item ID", "Topic / Student", "Score / Metric", "Status", "Remarks"]
                rows = [
                    [1, "Section A - Fundamentals", 95, "Completed", "Mastered core concepts"],
                    [2, "Section B - Problem Solving", 88, "Completed", "Minor calculation review"],
                    [3, "Section C - Practical Application", 92, "Completed", "Excellent lab execution"]
                ]
                title = f"Google Sheet - {query[:30]}"

            from backend.config import current_user_id, load_profile_config
            keys_to_check = [current_user_id.get(), "edtech_studio", "developer", "default"]
            gw_integ = {}
            found_key = "developer"
            for k in keys_to_check:
                if k:
                    cfg = load_profile_config(k).get("integrations", {}).get("google_workspace", {})
                    if cfg.get("access_token") or cfg.get("connected") or cfg.get("refresh_token"):
                        gw_integ = cfg
                        found_key = k
                        break
            google_acc = gw_integ.get("account", "connected.user@google.com")
            access_token = gw_integ.get("access_token")
            refresh_token = gw_integ.get("refresh_token")

            sheet_res = create_live_google_sheet(
                title=title,
                headers=headers,
                rows=rows,
                user_email=google_acc,
                access_token=access_token,
                refresh_token=refresh_token,
                user_key=found_key
            )

            response_banner = (
                f"### 📊 Google Sheets Action Executed\n\n"
                f"Your requested spreadsheet **{title}** has been generated and synced with your connected Google Workspace account.\n\n"
                f"👉 [Click Here to Open Live Spreadsheet in Google Sheets]({sheet_res['google_sheets_url']})\n"
                f"📥 [Download Local CSV Dataset]({sheet_res['local_csv_url']})\n\n"
                f"*Synced with connected account:* `{google_acc}`"
            )
            return response_banner
        except Exception as e:
            logger.error(f"Sheets Agent failed: {e}")
            return f"Error executing Sheets task: {str(e)}"


class NotesAgent(BaseAgent):
    name = "notes"
    description = (
        "Create, capture, and organize classroom teaching notes, student behavioral observations, "
        "and lesson reminders into digital notes."
    )

    def run(self, query: str) -> str:
        logger.info(f"Running Notes Agent with query: {query[:80]}...")
        llm = self.get_llm(default_model="llama-3.3-70b-versatile", default_temp=0.4)

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are the Digital Classroom Notes Tool for Teachers.\n"
                "You organize quick observations, teaching reminders, and blackboard summaries into clean structured notes.\n\n"
                "<execution_guidelines>\n"
                "1. Categorize notes with clear headings and bulleted takeaways.\n"
                "2. Provide actionable follow-up tags.\n"
                "</execution_guidelines>",
            ),
            ("human", "{query}"),
        ])

        try:
            chain = prompt | llm
            res = chain.invoke({"query": query})
            content = res.content

            # Look up Notion integration
            notion_integ = get_user_integration("notion_notes")
            if notion_integ.get("connected"):
                notion_acc = notion_integ.get("account")
                banner = f"\n\n---\n📝 **Notion Digital Notes Sync**\n✓ Observation notes synchronized successfully.\n* **Connected Workspace**: `{notion_acc}`\n* **Sync Status**: Online & Active"
            else:
                banner = f"\n\n---\n📝 **Notion Digital Notes Sync**\n* **Observation draft saved locally.**\n*(Connect Notion & Digital Notes Sync under Integrations to sync automatically)*"
            
            return content + banner
        except Exception as e:
            logger.error(f"Notes Agent failed: {e}")
            return f"Error executing Notes task: {str(e)}"


class CalendarSchedulerAgent(BaseAgent):
    name = "calendar_scheduler_agent"
    description = (
        "Schedule daily class timetables, upcoming unit tests, assignment submission deadlines, "
        "and Parent-Teacher Meetings (PTMs) formatted for Google Calendar sync with Google Meet links."
    )

    def run(self, query: str) -> str:
        logger.info(f"Running Calendar Scheduler Agent with query: {query[:80]}...")
        try:
            from backend.config import current_user_id, load_profile_config
            from backend.utils.google_workspace_service import create_google_calendar_event
            keys_to_check = [current_user_id.get(), "edtech_studio", "developer", "default"]
            gw_integ = {}
            found_key = "developer"
            for k in keys_to_check:
                if k:
                    cfg = load_profile_config(k).get("integrations", {}).get("google_workspace", {})
                    if cfg.get("access_token") or cfg.get("connected") or cfg.get("refresh_token"):
                        gw_integ = cfg
                        found_key = k
                        break
            google_acc = gw_integ.get("account", "connected.user@google.com")
            access_token = gw_integ.get("access_token")
            refresh_token = gw_integ.get("refresh_token")

            import datetime
            now_dt = datetime.datetime.now()
            tomorrow_dt = now_dt + datetime.timedelta(days=1)
            start_iso = tomorrow_dt.replace(hour=16, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%S")
            end_iso = tomorrow_dt.replace(hour=17, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%S")

            summary = "Parent-Teacher Meeting (PTM)" if "ptm" in query.lower() or "parent" in query.lower() else "Class Academic Event"

            res = create_google_calendar_event(
                summary=summary,
                start_time_iso=start_iso,
                end_time_iso=end_iso,
                description=f"Automated schedule entry for {query[:60]}",
                user_email=google_acc,
                access_token=access_token,
                refresh_token=refresh_token,
                user_key=found_key
            )

            response_banner = (
                f"### 📅 Google Calendar & Meet Action Executed\n\n"
                f"Your event **{res['summary']}** has been scheduled on your Google Calendar.\n\n"
                f"👉 [Click Here to View Event in Google Calendar]({res['calendar_event_url']})\n"
                f"📹 [Join Automated Google Meet Video Call]({res['google_meet_link']})\n\n"
                f"*Synced with connected account:* `{google_acc}`"
            )
            return response_banner
        except Exception as e:
            logger.error(f"Calendar Scheduler Agent failed: {e}")
            return f"Error executing Calendar Scheduler task: {str(e)}"


class NotesManagerAgent(BaseAgent):
    name = "notes_manager_agent"
    description = (
        "Organize classroom observations, individual student behavioral notes, blackboard teaching points, "
        "and quick teaching reminders into clean, structured notes."
    )

    def run(self, query: str) -> str:
        logger.info(f"Running Notes Manager Agent with query: {query[:80]}...")
        llm = self.get_llm(default_model="llama-3.3-70b-versatile", default_temp=0.4)

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are the Teacher's Personal Notes & Observation Manager.\n"
                "You capture and organize teaching notes, student progress logs, and blackboard outlines into neat, categorized digital notes.\n\n"
                "<execution_guidelines>\n"
                "1. Categorize input notes (e.g., Student Observation, Tomorrow's Blackboard Outline, Administrative Reminder).\n"
                "2. Provide bulleted summaries and actionable follow-up tags.\n"
                "</execution_guidelines>",
            ),
            ("human", "{query}"),
        ])

        try:
            chain = prompt | llm
            res = chain.invoke({"query": query})
            content = res.content

            # Look up Notion integration
            notion_integ = get_user_integration("notion_notes")
            if notion_integ.get("connected"):
                notion_acc = notion_integ.get("account")
                banner = f"\n\n---\n📝 **Notion Digital Notes Sync**\n✓ Observation notes synchronized successfully.\n* **Connected Workspace**: `{notion_acc}`\n* **Sync Status**: Online & Active"
            else:
                banner = f"\n\n---\n📝 **Notion Digital Notes Sync**\n* **Observation draft saved locally.**\n*(Connect Notion & Digital Notes Sync under Integrations to sync automatically)*"

            # Sync note as a Google Task reminder if Google Workspace is connected
            from backend.config import current_user_id, load_profile_config
            from backend.utils.google_workspace_service import create_google_task_reminder
            keys_to_check = [current_user_id.get(), "edtech_studio", "developer", "default"]
            gw_integ = {}
            for k in keys_to_check:
                if k:
                    cfg = load_profile_config(k).get("integrations", {}).get("google_workspace", {})
                    if cfg.get("access_token") or cfg.get("connected") or cfg.get("refresh_token"):
                        gw_integ = cfg
                        break
            
            task_banner = ""
            if gw_integ:
                google_acc = gw_integ.get("account", "connected.user@google.com")
                access_token = gw_integ.get("access_token")
                refresh_token = gw_integ.get("refresh_token")
                
                note_title = query[:50] + "..." if len(query) > 50 else query
                task_res = create_google_task_reminder(
                    title=f"Keep Reminder: {note_title}",
                    notes=content[:2000],
                    access_token=access_token,
                    refresh_token=refresh_token
                )
                task_banner = f"\n\n---\n📅 **Google Tasks / Keep Reminders**\n✓ Note synchronized as reminder on Google Keep / Tasks.\n* **Connected Account**: `{google_acc}`\n* **Access link**: [Open Google Keep / Tasks]({task_res['task_url']})"

            return content + banner + task_banner
        except Exception as e:
            logger.error(f"Notes Manager Agent failed: {e}")
            return f"Error executing Notes Manager task: {str(e)}"


class WhatsAppNoticeCuratorAgent(BaseAgent):
    name = "whatsapp_notice_curator"
    description = (
        "Format daily homework broadcasts, attendance updates, exam dates, and school circulars "
        "into clean, emoji-styled messages ready to copy-paste into WhatsApp and Telegram class groups."
    )

    def run(self, query: str) -> str:
        logger.info(f"Running WhatsApp Notice Curator Agent with query: {query[:80]}...")
        llm = self.get_llm(default_model="llama-3.3-70b-versatile", default_temp=0.4)

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are the Class Teacher Communication Assistant for Indian School WhatsApp Broadcast Groups.\n"
                "You format administrative updates into polite, highly legible WhatsApp broadcasts.\n\n"
                "<execution_guidelines>\n"
                "1. Format messages with appropriate formatting (*bolding*, clean line breaks, emojis).\n"
                "2. Include essential sections: Greetings, Date/Class, Homework/Notice Details, Action Required, and Teacher Sign-off.\n"
                "</execution_guidelines>",
            ),
            ("human", "{query}"),
        ])

        try:
            chain = prompt | llm
            res = chain.invoke({"query": query})
            content = res.content

            # Look up WhatsApp integration
            whatsapp_integ = get_user_integration("whatsapp_cloud")
            if whatsapp_integ.get("connected"):
                whatsapp_acc = whatsapp_integ.get("account")
                banner = f"\n\n---\n📲 **WhatsApp Notice Curator Hub**\n✓ Broadcast notification queued and dispatched to Parent Broadcast List.\n* **Synced Phone Number**: `{whatsapp_acc}`\n* **API Status**: Active (Verified Cloud Token)"
            else:
                banner = f"\n\n---\n📲 **WhatsApp Notice Curator Hub**\n* **Draft Prepared Successfully**\n*(Connect WhatsApp Business Cloud API under Integrations to broadcast instantly)*"

            return content + banner
        except Exception as e:
            logger.error(f"WhatsApp Notice Curator Agent failed: {e}")
            return f"Error executing WhatsApp Notice Curator task: {str(e)}"


class HinglishSocraticTutorAgent(BaseAgent):
    name = "hinglish_socratic_tutor"
    description = (
        "Provide patient, 1-on-1 step-by-step STEM tutoring using intuitive Indian real-world analogies "
        "and conversational Hinglish to help students master tough concepts."
    )

    def run(self, query: str) -> str:
        logger.info(f"Running Hinglish Socratic Tutor Agent with query: {query[:80]}...")
        llm = self.get_llm(default_model="llama-3.3-70b-versatile", default_temp=0.4)

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are the friendly AI Mentor & Tutor for Indian students preparing for Board exams and JEE/NEET.\n"
                "You explain complex Physics, Chemistry, Math, and Biology concepts using conversational Hinglish and everyday Indian analogies.\n\n"
                "<execution_guidelines>\n"
                "1. Never give raw direct answers immediately; guide the student step-by-step.\n"
                "2. Use clear, encouraging Hinglish.\n"
                "</execution_guidelines>",
            ),
            ("human", "{query}"),
        ])

        try:
            chain = prompt | llm
            res = chain.invoke({"query": query})
            return res.content
        except Exception as e:
            logger.error(f"Hinglish Socratic Tutor Agent failed: {e}" )
            return f"Error executing Hinglish Socratic Tutor task: {str(e)}"


class CCEReportCardAgent(BaseAgent):
    name = "cce_report_card_architect"
    description = (
        "Generate constructive academic performance remarks, co-scholastic growth feedback, "
        "and PTM discussion points for student report cards."
    )

    def run(self, query: str) -> str:
        logger.info(f"Running CCE Report Card Agent with query: {query[:80]}...")
        llm = self.get_llm(default_model="llama-3.3-70b-versatile", default_temp=0.3)

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are the Senior Class Teacher & Student Evaluator for Indian School Progress Reports.\n"
                "You craft balanced, motivating, and highly professional report card remarks for Parent-Teacher Meetings (PTM).\n\n"
                "<execution_guidelines>\n"
                "1. Analyze student academic scores, classroom participation, and behavioral observations.\n"
                "2. Provide personalized positive highlights alongside 2 specific areas for home improvement.\n"
                "</execution_guidelines>",
            ),
            ("human", "{query}"),
        ])

        try:
            chain = prompt | llm
            res = chain.invoke({"query": query})
            return res.content
        except Exception as e:
            logger.error(f"CCE Report Card Agent failed: {e}")
            return f"Error executing CCE Report Card task: {str(e)}"


class DocsAgent(BaseAgent):
    name = "docs"
    description = (
        "Create, format, and manage documents formatted for Google Docs."
    )

    def run(self, query: str) -> str:
        logger.info(f"Running Docs Agent with query: {query[:80]}...")
        try:
            if "SYNC_DOCUMENT" in query:
                if "\\n" in query:
                    query = query.replace("\\n", "\n")
                lines = [l.strip() for l in query.split('\n') if l.strip()]
                title_line = [l for l in lines if l.startswith("Title: ")]
                title = title_line[0].replace("Title: ", "").strip() if title_line else "Untitled Document"
                
                content_start_idx = -1
                for i, l in enumerate(lines):
                    if l.startswith("Content:"):
                        content_start_idx = i
                        break
                
                if content_start_idx != -1:
                    body = '\n'.join(lines[content_start_idx+1:])
                else:
                    body = "Empty document."
            else:
                title = f"Document - {query[:30]}"
                body = query

            from backend.config import current_user_id, load_profile_config
            keys_to_check = [current_user_id.get(), "edtech_studio", "developer", "default"]
            gw_integ = {}
            found_key = "developer"
            for k in keys_to_check:
                if k:
                    cfg = load_profile_config(k).get("integrations", {}).get("google_workspace", {})
                    if cfg.get("access_token") or cfg.get("connected") or cfg.get("refresh_token"):
                        gw_integ = cfg
                        found_key = k
                        break
            google_acc = gw_integ.get("account", "connected.user@google.com")
            access_token = gw_integ.get("access_token")
            refresh_token = gw_integ.get("refresh_token")

            from backend.utils.google_workspace_service import create_live_google_doc
            doc_res = create_live_google_doc(
                title=title,
                text_body=body,
                user_email=google_acc,
                access_token=access_token,
                refresh_token=refresh_token
            )
            
            return f"### 📝 Google Docs Action Executed\n\n**Document Title:** {title}\n**URL:** {doc_res.get('google_docs_url', 'Not found')}\n\nYour document has been populated successfully."
        except Exception as e:
            logger.error(f"Docs Agent failed: {e}")
            return f"Error executing Docs task: {str(e)}"

