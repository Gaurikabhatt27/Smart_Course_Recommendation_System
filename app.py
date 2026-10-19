"""
app.py
------
Smart Course Recommendation System Using MongoDB
Course: CSE494 – Intelligent NoSQL Databases
Frontend: Streamlit Dashboard with Plotly Visualizations
Backend: MongoDB with PyMongo
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from bson import ObjectId

# Import modular backend services
from database import check_connection, get_db_name, get_connection_uri, mask_uri
import operations
import recommendations
import analytics
import performance
import validation_demo

# ==============================================================================
# PAGE CONFIGURATION & THEME STYLING
# ==============================================================================

st.set_page_config(
    page_title="Smart Course Recommendation System Using MongoDB",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern educational dashboard styling (Navy/Blue corporate theme)
st.markdown("""
<style>
    /* Main container styling */
    .main {
        background-color: #F8FAFC;
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    }
    
    /* Header & Title Accents */
    .main-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%);
        color: white;
        padding: 24px 32px;
        border-radius: 12px;
        margin-bottom: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 {
        color: white !important;
        font-size: 26px;
        font-weight: 700;
        margin-bottom: 6px;
    }
    .main-header p {
        color: #93C5FD;
        font-size: 14px;
        margin: 0;
    }

    /* Metric Cards */
    .metric-card {
        background-color: white;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: transform 0.15s ease-in-out;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 32px;
        font-weight: 700;
        color: #1E3A8A;
        margin: 4px 0;
    }
    .metric-label {
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #64748B;
    }

    /* Course & Recommendation Card */
    .course-card {
        background-color: white;
        border: 1px solid #E2E8F0;
        border-left: 5px solid #2563EB;
        border-radius: 8px;
        padding: 18px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 6px;
    }
    .badge-primary { background-color: #DBEAFE; color: #1E40AF; }
    .badge-success { background-color: #DCFCE7; color: #166534; }
    .badge-warning { background-color: #FEF3C7; color: #92400E; }
    .badge-purple  { background-color: #F3E8FF; color: #6B21A8; }

    /* Explain Box */
    .explain-box {
        background-color: #EFF6FF;
        border: 1px solid #BFDBFE;
        border-radius: 8px;
        padding: 14px;
        font-size: 13px;
        color: #1E3A8A;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# SIDEBAR NAVIGATION & CONNECTION STATUS
# ==============================================================================

with st.sidebar:
    st.image("https://img.icons8.com/clouds/200/education.png", width=110)
    st.title("Academic Portal")
    st.caption("CSE494 – Intelligent NoSQL Databases")
    st.markdown("---")

    # Connection health check
    is_connected, conn_msg, conn_info = check_connection()
    if is_connected:
        st.success(f"🟢 **MongoDB Connected** (v{conn_info.get('version', 'N/A')})")
        with st.expander("Database Info", expanded=False):
            st.write(f"**DB:** `{conn_info.get('database')}`")
            st.write(f"**URI:** `{conn_info.get('masked_uri')}`")
            st.write(f"**Collections:** {conn_info.get('collection_count')}")
    else:
        st.error("🔴 **MongoDB Disconnected**")
        st.caption(conn_msg)

    st.markdown("---")
    menu = st.radio(
        "Navigation",
        [
            "📊 Dashboard",
            "👨‍🎓 Student Management",
            "📚 Course Catalog",
            "📝 Enrollments & Progress",
            "🎯 Course Recommendations",
            "📈 Learning Analytics",
            "⚡ Database Performance",
            "🛡️ Schema Validation Demo"
        ],
        index=0
    )
    st.markdown("---")
    st.markdown(
        "<div style='font-size: 11px; color: #64748B;'>"
        "Designed for B.Tech CS Mini-Project<br>"
        "MongoDB 8.x • PyMongo • Streamlit"
        "</div>",
        unsafe_allow_html=True
    )


# Stop gracefully if DB is not reachable
if not is_connected:
    st.error("### ⚠️ Database Connection Unavailable")
    st.warning(
        f"Unable to reach MongoDB server. Please ensure MongoDB is running.\n\n"
        f"**Error Details:** {conn_msg}\n\n"
        "**Local Windows Service Check:**\n"
        "Run `Get-Service MongoDB` or start it via Windows Services Manager."
    )
    st.stop()


# ==============================================================================
# PAGE 1: DASHBOARD
# ==============================================================================
if menu == "📊 Dashboard":
    st.markdown("""
    <div class="main-header">
        <h1>Smart Course Recommendation System Using MongoDB</h1>
        <p>Live MongoDB KPI Dashboard • Real-time Aggregation Metrics & Enrollment Trends</p>
    </div>
    """, unsafe_allow_html=True)

    stats = analytics.get_overall_statistics()

    # Live Metric Cards
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Students</div>
            <div class="metric-value">{stats['total_students']}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Courses</div>
            <div class="metric-value">{stats['total_courses']}</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Enrollments</div>
            <div class="metric-value">{stats['total_enrollments']}</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Reviews</div>
            <div class="metric-value">{stats['total_reviews']}</div>
        </div>
        """, unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Rating</div>
            <div class="metric-value">{stats['avg_review_rating']:.1f} ★</div>
        </div>
        """, unsafe_allow_html=True)
    with c6:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Completion</div>
            <div class="metric-value">{stats['completion_rate']:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Dashboard Visualizations from MongoDB Aggregation
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Enrollments by Category")
        cat_data = analytics.get_category_wise_enrollments()
        if cat_data:
            df_cat = pd.DataFrame(cat_data)
            fig_cat = px.pie(
                df_cat,
                names="category",
                values="enrollment_count",
                hole=0.45,
                color_discrete_sequence=px.colors.sequential.Blues_r
            )
            fig_cat.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=320)
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.info("No enrollment data available.")

    with col_right:
        st.subheader("Top 5 Most Enrolled Courses")
        pop_data = analytics.get_most_popular_courses(limit=5)
        if pop_data:
            df_pop = pd.DataFrame(pop_data)
            fig_pop = px.bar(
                df_pop,
                x="enrollment_count",
                y="title",
                orientation="h",
                text="enrollment_count",
                color="enrollment_count",
                color_continuous_scale="Blues"
            )
            fig_pop.update_layout(
                yaxis=dict(autorange="reversed"),
                margin=dict(t=20, b=20, l=20, r=20),
                height=320,
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_pop, use_container_width=True)
        else:
            st.info("No popular courses data available.")

    # Student progress overview chart
    st.subheader("Course Completion & Learning Progress Distribution")
    prog_data = analytics.get_student_learning_progress()
    if prog_data:
        df_prog = pd.DataFrame(prog_data)
        fig_prog = px.bar(
            df_prog,
            x="title",
            y=["completed_count", "in_progress_count", "not_started_count"],
            barmode="stack",
            labels={"value": "Student Count", "title": "Course", "variable": "Enrollment Status"},
            color_discrete_map={
                "completed_count": "#10B981",
                "in_progress_count": "#3B82F6",
                "not_started_count": "#94A3B8"
            }
        )
        fig_prog.update_layout(
            xaxis_tickangle=-30,
            margin=dict(t=20, b=60, l=20, r=20),
            height=360,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_prog, use_container_width=True)


# ==============================================================================
# PAGE 2: STUDENT MANAGEMENT
# ==============================================================================
elif menu == "👨‍🎓 Student Management":
    st.markdown("""
    <div class="main-header">
        <h1>Student Profile Management</h1>
        <p>MongoDB CRUD Operations • Profile Creation, Search, Skill Updates & Safe Deletion</p>
    </div>
    """, unsafe_allow_html=True)

    tab_view, tab_add, tab_edit, tab_del = st.tabs([
        "📋 Directory & Search",
        "➕ Register Student",
        "✏️ Edit Profile",
        "🗑️ Delete Student"
    ])

    with tab_view:
        search_query = st.text_input("🔍 Search Students by Name or Email", placeholder="e.g. Aarav, priya@...")
        students_list = operations.search_students(search_query) if search_query else operations.get_all_students()

        st.caption(f"Displaying {len(students_list)} students")
        if students_list:
            for s in students_list:
                with st.container():
                    st.markdown(f"""
                    <div class="course-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <h3 style="margin: 0; color: #1E3A8A;">{s.get('name')}</h3>
                            <span class="badge badge-primary">{s.get('level')}</span>
                        </div>
                        <p style="color: #64748B; font-size: 13px; margin: 4px 0 10px 0;">
                            ✉️ {s.get('email')} &nbsp;|&nbsp; 📅 Registered: {s.get('created_at', 'N/A')}
                        </p>
                        <div>
                            <strong>Skills:</strong> {' '.join([f'<span class="badge badge-success">{sk}</span>' for sk in s.get('skills', [])])}
                        </div>
                        <div style="margin-top: 6px;">
                            <strong>Interests:</strong> {' '.join([f'<span class="badge badge-purple">{it}</span>' for it in s.get('interests', [])])}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No students found matching your criteria.")

    with tab_add:
        st.subheader("Register a New Student")
        with st.form("add_student_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                s_name = st.text_input("Full Name *", placeholder="e.g. Rahul Sharma")
                s_email = st.text_input("Email Address *", placeholder="e.g. rahul@example.com")
            with col_b:
                s_level = st.selectbox("Proficiency Level *", operations.VALID_LEVELS, index=0)
                s_skills_input = st.text_input("Skills (comma-separated)", placeholder="Python, SQL, Docker")
            s_interests_input = st.text_input("Interests (comma-separated)", placeholder="Data Science, AI, Cloud")

            submitted = st.form_submit_button("Submit Registration", use_container_width=True)
            if submitted:
                skills_arr = [s.strip() for s in s_skills_input.split(",") if s.strip()]
                interests_arr = [i.strip() for i in s_interests_input.split(",") if i.strip()]
                ok, msg, new_id = operations.create_student(s_name, s_email, skills_arr, interests_arr, s_level)
                if ok:
                    st.success(f"✅ {msg} (ID: `{new_id}`)")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

    with tab_edit:
        st.subheader("Update Student Information")
        all_students = operations.get_all_students()
        if all_students:
            student_options = {f"{s['name']} ({s['email']})": s for s in all_students}
            selected_name = st.selectbox("Select Student to Edit", list(student_options.keys()))
            selected_student = student_options[selected_name]

            with st.form("edit_student_form"):
                e_name = st.text_input("Name", value=selected_student.get("name", ""))
                e_level_idx = operations.VALID_LEVELS.index(selected_student.get("level", "Beginner"))
                e_level = st.selectbox("Level", operations.VALID_LEVELS, index=e_level_idx)
                e_skills = st.text_input("Skills (comma-separated)", value=", ".join(selected_student.get("skills", [])))
                e_interests = st.text_input("Interests (comma-separated)", value=", ".join(selected_student.get("interests", [])))

                update_btn = st.form_submit_button("Save Changes", use_container_width=True)
                if update_btn:
                    skills_list = [s.strip() for s in e_skills.split(",") if s.strip()]
                    interests_list = [i.strip() for i in e_interests.split(",") if i.strip()]
                    ok, msg = operations.update_student(
                        selected_student["_id_str"],
                        name=e_name,
                        skills=skills_list,
                        interests=interests_list,
                        level=e_level
                    )
                    if ok:
                        st.success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
        else:
            st.info("No students registered yet.")

    with tab_del:
        st.subheader("Delete Student Profile")
        all_students = operations.get_all_students()
        if all_students:
            del_options = {f"{s['name']} ({s['email']})": s for s in all_students}
            del_name = st.selectbox("Select Student to Delete", list(del_options.keys()), key="del_sel")
            del_target = del_options[del_name]

            # Display enrollment warning
            enr_count = len(operations.get_student_enrollments(del_target["_id_str"]))
            st.warning(f"⚠️ Student has **{enr_count}** active enrollments.")

            cascade_confirm = st.checkbox("Cascade delete associated enrollments and reviews", value=True)
            confirm_text = st.text_input(f"Type '{del_target['name']}' to confirm deletion")

            if st.button("Permanently Delete Student", type="primary"):
                if confirm_text.strip() == del_target["name"].strip():
                    ok, msg = operations.delete_student(del_target["_id_str"], cascade=cascade_confirm)
                    if ok:
                        st.success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")
                else:
                    st.error("Confirmation name did not match.")


# ==============================================================================
# PAGE 3: COURSE CATALOG
# ==============================================================================
elif menu == "📚 Course Catalog":
    st.markdown("""
    <div class="main-header">
        <h1>Course Catalog Management</h1>
        <p>Browse, Search, Filter by Category/Level & Manage Academic Curriculum</p>
    </div>
    """, unsafe_allow_html=True)

    tab_catalog, tab_add_c, tab_edit_c, tab_del_c = st.tabs([
        "📖 Course Catalog",
        "➕ Add New Course",
        "✏️ Edit Course",
        "🗑️ Delete Course"
    ])

    with tab_catalog:
        f1, f2, f3 = st.columns([2, 1, 1])
        with f1:
            c_search = st.text_input("🔍 Search Course Title, Skills, or Description", placeholder="e.g. Python, Docker, Neural...")
        with f2:
            cat_filter = st.selectbox("Category", ["All"] + operations.VALID_CATEGORIES)
        with f3:
            lvl_filter = st.selectbox("Level", ["All"] + operations.VALID_LEVELS)

        courses_list = operations.search_courses(c_search, category=cat_filter, level=lvl_filter)
        st.caption(f"Found {len(courses_list)} courses")

        for c in courses_list:
            with st.container():
                st.markdown(f"""
                <div class="course-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <h3 style="margin: 0; color: #1E3A8A;">{c.get('title')}</h3>
                            <div style="margin: 6px 0;">
                                <span class="badge badge-primary">{c.get('category')}</span>
                                <span class="badge badge-purple">{c.get('level')}</span>
                                <span class="badge badge-warning">⏱️ {c.get('duration_hours')} hrs</span>
                                <span class="badge badge-success">★ {c.get('rating', 0.0):.1f}</span>
                            </div>
                        </div>
                    </div>
                    <p style="color: #475569; font-size: 14px; margin: 8px 0;">{c.get('description')}</p>
                    <div>
                        <strong>Key Skills:</strong> {' '.join([f'<span class="badge badge-primary">{sk}</span>' for sk in c.get('skills', [])])}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    with tab_add_c:
        st.subheader("Add a Course to the Catalog")
        with st.form("add_course_form", clear_on_submit=True):
            ca_title = st.text_input("Course Title *", placeholder="e.g. Advanced Cloud Systems with Terraform")
            col_c1, col_c2, col_c3 = st.columns(3)
            with col_c1:
                ca_cat = st.selectbox("Category *", operations.VALID_CATEGORIES)
            with col_c2:
                ca_lvl = st.selectbox("Difficulty Level *", operations.VALID_LEVELS)
            with col_c3:
                ca_duration = st.number_input("Duration (Hours) *", min_value=0.5, max_value=120.0, value=30.0, step=1.0)

            col_c4, col_c5 = st.columns([1, 2])
            with col_c4:
                ca_rating = st.number_input("Catalog Rating (0.0 - 5.0) *", min_value=0.0, max_value=5.0, value=4.5, step=0.1)
            with col_c5:
                ca_skills = st.text_input("Skills Taught (comma-separated) *", placeholder="Terraform, AWS, DevOps")

            ca_desc = st.text_area("Course Description *", placeholder="Comprehensive syllabus summary and learning goals.")

            submitted_c = st.form_submit_button("Publish Course", use_container_width=True)
            if submitted_c:
                skills_arr = [s.strip() for s in ca_skills.split(",") if s.strip()]
                ok, msg, new_cid = operations.create_course(
                    ca_title, ca_cat, skills_arr, ca_lvl, ca_duration, ca_rating, ca_desc
                )
                if ok:
                    st.success(f"✅ {msg} (ID: `{new_cid}`)")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

    with tab_edit_c:
        st.subheader("Modify Existing Course")
        all_courses = operations.get_all_courses()
        if all_courses:
            c_dict = {f"{c['title']} ({c['category']})": c for c in all_courses}
            c_sel = st.selectbox("Select Course to Edit", list(c_dict.keys()))
            target_course = c_dict[c_sel]

            with st.form("edit_c_form"):
                ec_title = st.text_input("Title", value=target_course.get("title", ""))
                ec_cat_idx = operations.VALID_CATEGORIES.index(target_course.get("category", operations.VALID_CATEGORIES[0]))
                ec_cat = st.selectbox("Category", operations.VALID_CATEGORIES, index=ec_cat_idx)
                ec_lvl_idx = operations.VALID_LEVELS.index(target_course.get("level", operations.VALID_LEVELS[0]))
                ec_lvl = st.selectbox("Level", operations.VALID_LEVELS, index=ec_lvl_idx)
                ec_dur = st.number_input("Duration (hours)", min_value=0.5, value=float(target_course.get("duration_hours", 30.0)))
                ec_rat = st.number_input("Rating (0.0 - 5.0)", min_value=0.0, max_value=5.0, value=float(target_course.get("rating", 4.5)), step=0.1)
                ec_skills = st.text_input("Skills", value=", ".join(target_course.get("skills", [])))
                ec_desc = st.text_area("Description", value=target_course.get("description", ""))

                save_c = st.form_submit_button("Save Course Updates", use_container_width=True)
                if save_c:
                    sk_list = [s.strip() for s in ec_skills.split(",") if s.strip()]
                    ok, msg = operations.update_course(
                        target_course["_id_str"],
                        title=ec_title,
                        category=ec_cat,
                        skills=sk_list,
                        level=ec_lvl,
                        duration_hours=ec_dur,
                        rating=ec_rat,
                        description=ec_desc
                    )
                    if ok:
                        st.success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")

    with tab_del_c:
        st.subheader("Delete Course")
        all_courses = operations.get_all_courses()
        if all_courses:
            c_del_dict = {f"{c['title']} ({c['category']})": c for c in all_courses}
            c_del_sel = st.selectbox("Select Course to Remove", list(c_del_dict.keys()), key="del_c_sel")
            del_course = c_del_dict[c_del_sel]

            c_cascade = st.checkbox("Cascade delete associated student enrollments and reviews", value=True)
            if st.button("Delete Course from Catalog", type="primary"):
                ok, msg = operations.delete_course(del_course["_id_str"], cascade=c_cascade)
                if ok:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")


# ==============================================================================
# PAGE 4: ENROLLMENTS & PROGRESS
# ==============================================================================
elif menu == "📝 Enrollments & Progress":
    st.markdown("""
    <div class="main-header">
        <h1>Student Enrollments & Progress Tracking</h1>
        <p>Referential Integrity Checks • Duplicate Prevention • Dynamic Completion Status Logic</p>
    </div>
    """, unsafe_allow_html=True)

    tab_enr_list, tab_new_enr, tab_up_prog = st.tabs([
        "📋 Active Enrollments",
        "➕ Enroll Student in Course",
        "🔄 Update Learning Progress"
    ])

    with tab_enr_list:
        enrollments_data = operations.get_all_enrollments()
        st.subheader(f"Total Enrollments: {len(enrollments_data)}")

        if enrollments_data:
            df_enr = pd.DataFrame([
                {
                    "Student": e.get("student_name"),
                    "Course": e.get("course_title"),
                    "Category": e.get("course_category"),
                    "Progress": f"{e.get('progress', 0.0):.0f}%",
                    "Status": e.get("status"),
                    "Enrolled Date": e.get("enrolled_at", "N/A")
                }
                for e in enrollments_data
            ])
            st.dataframe(df_enr, use_container_width=True)
        else:
            st.info("No enrollments found.")

    with tab_new_enr:
        st.subheader("Create a New Course Enrollment")
        all_s = operations.get_all_students()
        all_c = operations.get_all_courses()

        if not all_s or not all_c:
            st.warning("Please ensure at least one student and course exist before enrolling.")
        else:
            s_map = {f"{s['name']} ({s['email']})": s["_id_str"] for s in all_s}
            c_map = {f"{c['title']} [{c['category']} - {c['level']}]": c["_id_str"] for c in all_c}

            with st.form("new_enrollment_form", clear_on_submit=True):
                sel_student_label = st.selectbox("Select Student *", list(s_map.keys()))
                sel_course_label = st.selectbox("Select Course *", list(c_map.keys()))
                init_progress = st.slider("Initial Progress (%)", 0.0, 100.0, 0.0, step=5.0)

                submit_enr = st.form_submit_button("Confirm Enrollment", use_container_width=True)
                if submit_enr:
                    student_oid = s_map[sel_student_label]
                    course_oid = c_map[sel_course_label]
                    ok, msg, enr_id = operations.enroll_student(
                        student_oid, course_oid, progress=init_progress
                    )
                    if ok:
                        st.success(f"✅ {msg} (Enrollment ID: `{enr_id}`)")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")

    with tab_up_prog:
        st.subheader("Update Student Progress")
        enrollments_data = operations.get_all_enrollments()
        if enrollments_data:
            enr_map = {
                f"{e.get('student_name')} -> {e.get('course_title')} (Currently {e.get('progress'):.0f}%, {e.get('status')})": e
                for e in enrollments_data
            }
            sel_enr_label = st.selectbox("Select Enrollment to Update", list(enr_map.keys()))
            target_enr = enr_map[sel_enr_label]

            with st.form("update_progress_form"):
                new_prog = st.slider(
                    "New Progress (%)",
                    0.0,
                    100.0,
                    float(target_enr.get("progress", 0.0)),
                    step=5.0
                )
                st.caption("ℹ️ Progress = 100% will automatically transition status to 'Completed'. Progress = 0% will set 'Not Started'.")

                prog_btn = st.form_submit_button("Save Progress Update", use_container_width=True)
                if prog_btn:
                    ok, msg = operations.update_enrollment_progress(target_enr["_id_str"], new_prog)
                    if ok:
                        st.success(f"✅ {msg}")
                        st.rerun()
                    else:
                        st.error(f"❌ {msg}")


# ==============================================================================
# PAGE 5: COURSE RECOMMENDATIONS
# ==============================================================================
elif menu == "🎯 Course Recommendations":
    st.markdown("""
    <div class="main-header">
        <h1>Explainable Course Recommendation Engine</h1>
        <p>Rule-Based Scoring • Skill & Interest Alignment • Transparent Weighting</p>
    </div>
    """, unsafe_allow_html=True)

    # Educational formula callout
    st.markdown("""
    <div class="explain-box">
        <strong>Recommendation Scoring Formula:</strong><br>
        <code>Final Score = (0.50 × Skill Match) + (0.30 × Interest Match) + (0.20 × Course Rating)</code><br>
        • All component scores normalized to 0–100.<br>
        • Automatically excludes courses the student has already enrolled in (including Completed ones).<br>
        • 100% deterministic and explainable — no black-box or fabricated AI claims.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    students = operations.get_all_students()

    if not students:
        st.warning("No students available. Please register a student first.")
    else:
        st_dict = {f"{s['name']} ({s['email']})": s for s in students}
        sel_student_label = st.selectbox("Select Target Student", list(st_dict.keys()))
        target_student = st_dict[sel_student_label]

        # Student Profile snapshot
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.write(f"**Level:** `{target_student.get('level')}`")
        with col_s2:
            st.write(f"**Skills:** {', '.join(target_student.get('skills', [])) or 'None'}")
        with col_s3:
            st.write(f"**Interests:** {', '.join(target_student.get('interests', [])) or 'None'}")

        # Show currently enrolled courses
        enrolled_list = operations.get_student_enrollments(target_student["_id_str"])
        with st.expander(f"📚 Currently Enrolled Courses ({len(enrolled_list)}) - Excluded from Recommendations"):
            if enrolled_list:
                for en in enrolled_list:
                    st.write(f"• **{en.get('course_title')}** ({en.get('course_category')}) — Progress: {en.get('progress'):.0f}% [{en.get('status')}]")
            else:
                st.caption("No existing enrollments for this student.")

        st.markdown("<br>", unsafe_allow_html=True)
        top_n = st.slider("Number of Recommendations", min_value=3, max_value=10, value=5)

        if st.button("Generate Explainable Recommendations", type="primary", use_container_width=True):
            ok, msg, recs = recommendations.get_recommendations_for_student(
                target_student["_id_str"],
                top_n=top_n,
                save_to_log=True
            )

            if not ok:
                st.error(msg)
            elif not recs:
                st.info(msg)
            else:
                st.success(f"✅ {msg}")
                for idx, r in enumerate(recs, start=1):
                    with st.container():
                        st.markdown(f"""
                        <div class="course-card">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <h3 style="margin: 0; color: #1E3A8A;">#{idx}. {r.get('title')}</h3>
                                <div style="text-align: right;">
                                    <span style="font-size: 22px; font-weight: 700; color: #2563EB;">{r.get('score'):.1f}</span>
                                    <span style="color: #64748B; font-size: 13px;"> / 100</span>
                                </div>
                            </div>
                            <div style="margin: 6px 0;">
                                <span class="badge badge-primary">{r.get('category')}</span>
                                <span class="badge badge-purple">{r.get('level')}</span>
                                <span class="badge badge-warning">⏱️ {r.get('duration_hours')} hrs</span>
                                <span class="badge badge-success">★ {r.get('rating'):.1f}</span>
                            </div>
                            <p style="color: #475569; font-size: 13px; margin: 8px 0 12px 0;">{r.get('description')}</p>
                            
                            <!-- Component Score Breakdown -->
                            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; background: #F8FAFC; padding: 10px; border-radius: 6px; border: 1px solid #E2E8F0; font-size: 12px;">
                                <div>
                                    <strong>Skill Match (50%):</strong> {r.get('skill_score'):.1f}%<br>
                                    <span style="color: #64748B;">Matched: {', '.join(r.get('matched_skills', [])) or 'None'}</span>
                                </div>
                                <div>
                                    <strong>Interest Match (30%):</strong> {r.get('interest_score'):.1f}%<br>
                                    <span style="color: #64748B;">Matched: {', '.join(r.get('matched_interests', [])) or 'None'}</span>
                                </div>
                                <div>
                                    <strong>Rating Score (20%):</strong> {r.get('rating_score'):.1f}%<br>
                                    <span style="color: #64748B;">Raw: {r.get('rating'):.1f} / 5.0</span>
                                </div>
                            </div>
                            
                            <!-- Explainability summary -->
                            <div class="explain-box" style="margin-top: 10px;">
                                💡 <strong>Why Recommended:</strong> {r.get('explanation')}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)


# ==============================================================================
# PAGE 6: LEARNING ANALYTICS
# ==============================================================================
elif menu == "📈 Learning Analytics":
    st.markdown("""
    <div class="main-header">
        <h1>Learning Analytics & Aggregation Pipelines</h1>
        <p>Live MongoDB Analytics • $lookup Joins • $group Reductions • Technical Pipeline Inspector</p>
    </div>
    """, unsafe_allow_html=True)

    tab_a, tab_b, tab_c, tab_d = st.tabs([
        "🔥 Most Popular Courses",
        "⭐ Course Ratings Analysis",
        "📊 Category Enrollments",
        "📈 Learning Progress & Completion"
    ])

    with tab_a:
        st.subheader("Analytics A: Most Popular Courses by Enrollment")
        pop_courses = analytics.get_most_popular_courses(limit=10)
        if pop_courses:
            df_pop = pd.DataFrame(pop_courses)
            fig_p = px.bar(
                df_pop,
                x="title",
                y="enrollment_count",
                color="category",
                labels={"title": "Course Title", "enrollment_count": "Total Enrollments"},
                title="Enrollment Count per Course"
            )
            fig_p.update_layout(xaxis_tickangle=-35, margin=dict(t=40, b=80))
            st.plotly_chart(fig_p, use_container_width=True)
            st.dataframe(df_pop, use_container_width=True)
        else:
            st.info("No enrollment data available.")

        with st.expander("🔍 View MongoDB Aggregation Pipeline (Analytics A)"):
            st.code(str(analytics.POPULAR_COURSES_PIPELINE), language="python")

    with tab_b:
        st.subheader("Analytics B: Average Review Rating per Course")
        ratings_data = analytics.get_average_rating_per_course()
        if ratings_data:
            df_rat = pd.DataFrame(ratings_data)
            fig_r = px.scatter(
                df_rat,
                x="review_count",
                y="avg_rating",
                size="review_count",
                color="category",
                hover_name="title",
                labels={"review_count": "Total Reviews", "avg_rating": "Average Rating (Stars)"},
                title="Average Rating vs Review Volume"
            )
            fig_r.update_layout(yaxis_range=[1, 5.2])
            st.plotly_chart(fig_r, use_container_width=True)
            st.dataframe(df_rat, use_container_width=True)
        else:
            st.info("No review data available.")

        with st.expander("🔍 View MongoDB Aggregation Pipeline (Analytics B)"):
            st.code(str(analytics.COURSE_RATINGS_PIPELINE), language="python")

    with tab_c:
        st.subheader("Analytics C: Category-wise Enrollments")
        cat_data = analytics.get_category_wise_enrollments()
        if cat_data:
            df_c = pd.DataFrame(cat_data)
            fig_c = px.pie(
                df_c,
                names="category",
                values="enrollment_count",
                hole=0.4,
                title="Category Enrollment Distribution"
            )
            st.plotly_chart(fig_c, use_container_width=True)
            st.dataframe(df_c, use_container_width=True)
        else:
            st.info("No category data available.")

        with st.expander("🔍 View MongoDB Aggregation Pipeline (Analytics C)"):
            st.code(str(analytics.CATEGORY_ENROLLMENTS_PIPELINE), language="python")

    with tab_d:
        st.subheader("Analytics D: Student Learning Progress per Course")
        prog_data = analytics.get_student_learning_progress()
        if prog_data:
            df_pr = pd.DataFrame(prog_data)
            st.dataframe(df_pr[[
                "title", "category", "total_students", "completed_count",
                "in_progress_count", "not_started_count", "avg_progress", "completion_rate"
            ]], use_container_width=True)
        else:
            st.info("No student progress data available.")

        with st.expander("🔍 View MongoDB Aggregation Pipeline (Analytics D)"):
            st.code(str(analytics.STUDENT_PROGRESS_PIPELINE), language="python")


# ==============================================================================
# PAGE 7: DATABASE PERFORMANCE & EXPLAIN()
# ==============================================================================
elif menu == "⚡ Database Performance":
    st.markdown("""
    <div class="main-header">
        <h1>Database Performance & Query Optimization</h1>
        <p>Real-Time Index Inspection • Controlled explain(executionStats) Benchmark • COLLSCAN vs IXSCAN</p>
    </div>
    """, unsafe_allow_html=True)

    tab_inspect, tab_explain = st.tabs([
        "📋 Active Index Inspector",
        "🔬 Controlled explain() Benchmark"
    ])

    with tab_inspect:
        st.subheader("MongoDB Collection Indexes")
        st.write("Inspect active indexes registered across the 4 core collections:")

        sel_coll = st.selectbox("Select Collection", ["courses", "students", "enrollments", "reviews"])
        idx_list = performance.get_collection_indexes(sel_coll)

        if idx_list:
            df_idx = pd.DataFrame([
                {
                    "Index Name": idx["name"],
                    "Keys": ", ".join([f"{k[0]}: {k[1]}" for k in idx["key"]]),
                    "Unique Constraint": "Yes" if idx["unique"] else "No"
                }
                for idx in idx_list
            ])
            st.table(df_idx)
        else:
            st.info("No indexes found.")

    with tab_explain:
        st.subheader("Controlled Query Optimization Experiment")
        st.markdown("""
        <div class="explain-box">
            <strong>Controlled Evaluation Methodology:</strong><br>
            To evaluate an index impartially, an unindexed query must run without a pre-existing index.<br>
            This benchmark creates a temporary test collection with 500 documents, runs <code>explain("executionStats")</code> 
            before creating the index (<strong>COLLSCAN</strong>), creates the index, and runs the identical query 
            (<strong>IXSCAN</strong>). The temporary collection is immediately cleaned up afterward.
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Execute Live explain() Comparison Benchmark", type="primary"):
            with st.spinner("Generating controlled dataset and executing MongoDB explain commands..."):
                benchmark_res = performance.run_controlled_explain_benchmark(num_sample_docs=500)

            unindexed = benchmark_res["unindexed"]
            indexed = benchmark_res["indexed"]
            comp = benchmark_res["comparison"]

            st.success("✅ Benchmark Completed Successfully!")

            c_un, c_idx = st.columns(2)
            with c_un:
                st.markdown(f"""
                <div class="course-card" style="border-left-color: #EF4444;">
                    <h3 style="color: #DC2626; margin: 0 0 10px 0;">Unindexed Query (Before Index)</h3>
                    <p><strong>Stage:</strong> <span class="badge" style="background:#FEE2E2; color:#991B1B;">{unindexed['stage']}</span></p>
                    <p><strong>Documents Examined:</strong> {unindexed['totalDocsExamined']}</p>
                    <p><strong>Keys Examined:</strong> {unindexed['totalKeysExamined']}</p>
                    <p><strong>Documents Returned:</strong> {unindexed['nReturned']}</p>
                    <p><strong>Execution Time:</strong> {unindexed['executionTimeMillis']} ms</p>
                </div>
                """, unsafe_allow_html=True)

            with c_idx:
                st.markdown(f"""
                <div class="course-card" style="border-left-color: #10B981;">
                    <h3 style="color: #059669; margin: 0 0 10px 0;">Indexed Query (After Index)</h3>
                    <p><strong>Stage:</strong> <span class="badge" style="background:#D1FAE5; color:#065F46;">{indexed['stage']}</span></p>
                    <p><strong>Documents Examined:</strong> {indexed['totalDocsExamined']}</p>
                    <p><strong>Keys Examined:</strong> {indexed['totalKeysExamined']}</p>
                    <p><strong>Documents Returned:</strong> {indexed['nReturned']}</p>
                    <p><strong>Execution Time:</strong> {indexed['executionTimeMillis']} ms</p>
                </div>
                """, unsafe_allow_html=True)

            st.metric(
                label="Scanned Documents Reduction",
                value=f"{comp['docs_reduction_pct']}% Reduction",
                delta=f"-{comp['docs_examined_reduction']} documents scanned"
            )

            # Viva Educational Concepts
            st.markdown("### 🎓 Academic Concepts & Viva Discussion")
            c_e1, c_e2 = st.columns(2)
            with c_e1:
                st.info(f"**COLLSCAN (Collection Scan):**\n\n{performance.INDEX_CONCEPTS_EXPLANATION['COLLSCAN']}")
                st.warning(f"**Selectivity:**\n\n{performance.INDEX_CONCEPTS_EXPLANATION['SELECTIVITY']}")
            with c_e2:
                st.success(f"**IXSCAN (Index Scan):**\n\n{performance.INDEX_CONCEPTS_EXPLANATION['IXSCAN']}")
                st.error(f"**Index Overhead:**\n\n{performance.INDEX_CONCEPTS_EXPLANATION['OVERHEAD']}")


# ==============================================================================
# PAGE 8: SCHEMA VALIDATION DEMO
# ==============================================================================
elif menu == "🛡️ Schema Validation Demo":
    st.markdown("""
    <div class="main-header">
        <h1>MongoDB JSON Schema Validation</h1>
        <p>Server-side Document Validation • Exception Handling • Strict Schema Rules</p>
    </div>
    """, unsafe_allow_html=True)

    tab_rules, tab_demo = st.tabs([
        "📜 Active Schema Rules",
        "🧪 Live Document Validation Demo"
    ])

    with tab_rules:
        st.subheader("Configured Collection Validators")
        for rule_group in validation_demo.VALIDATION_RULES_EXPLANATION:
            with st.expander(f"📁 {rule_group['collection'].capitalize()} Collection Rules", expanded=True):
                for r in rule_group["rules"]:
                    st.write(f"• {r}")

    with tab_demo:
        st.subheader("Live Exception Handling Demonstration")
        st.write(
            "This test sends a valid document followed by an intentionally malformed document "
            "to demonstrate MongoDB server-side validation error catching."
        )

        test_entity = st.selectbox("Select Test Scenario", ["Students", "Courses", "Enrollments"])

        if st.button("Run Schema Validation Test", type="primary"):
            if test_entity == "Students":
                result = validation_demo.run_student_validation_demo()
            elif test_entity == "Courses":
                result = validation_demo.run_course_validation_demo()
            else:
                result = validation_demo.run_enrollment_validation_demo()

            # Display Valid Result
            st.success(f"**Step 1: Valid Insert** -> {result['valid_test']['message']}")

            # Display Invalid Result
            inv = result["invalid_test"]
            if inv["caught_expected_error"]:
                st.error(f"**Step 2: Invalid Insert Caught** -> `{inv['error_type']}`")
                st.info(f"💡 **Why Rejected:** {inv['explanation']}")
                with st.expander("View Raw PyMongo Error Details"):
                    st.code(inv["error_details"], language="json")
            else:
                st.warning(inv["explanation"])
