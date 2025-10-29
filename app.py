import streamlit as st
import requests
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
import json
import os

# Page configuration
st.set_page_config(
    page_title="ClickUp Dashboard",
    page_icon="📊",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 10px 0;
    }
    .status-badge {
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 12px;
        display: inline-block;
        margin: 2px;
    }
    .status-todo { background-color: #e3e8ef; color: #293647; }
    .status-in-progress { background-color: #fef3c7; color: #92400e; }
    .status-completed { background-color: #d1fae5; color: #065f46; }
    .status-closed { background-color: #e5e7eb; color: #374151; }
    .member-card {
        background: #f8fafc;
        border-left: 4px solid #3b82f6;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .list-header {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        padding: 20px;
        border-radius: 12px;
        color: white;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# ClickUp API Configuration
CLICKUP_API_TOKEN =os.getenv("CLICKUP_API_TOKEN")
HEADERS = {
    "Authorization": CLICKUP_API_TOKEN
}
BASE_URL = "https://api.clickup.com/api/v2"

# List IDs to fetch (can be expanded)
LIST_IDS = [
    "901307726539",
    # Add more list IDs here as needed
]

@st.cache_data(ttl=300, show_spinner=False)
def get_list_info(list_id):
    """Fetch list information"""
    try:
        url = f"{BASE_URL}/list/{list_id}"
        response = requests.get(url, headers=HEADERS)
        
        if response.status_code != 200:
            st.error(f"API Error for list {list_id}: {response.status_code} - {response.text}")
            return None
            
        return response.json()
    except Exception as e:
        st.error(f"Exception fetching list {list_id}: {str(e)}")
        return None

@st.cache_data(ttl=300, show_spinner=False)
def get_all_tasks(list_id):
    """Fetch ALL tasks including completed ones from a list"""
    try:
        all_tasks = []
        
        url = f"{BASE_URL}/list/{list_id}/task"
        params = {
            "archived": "false",
            "include_closed": "true",
            "subtasks": "true"
        }
        
        response = requests.get(url, headers=HEADERS, params=params)
        
        if response.status_code != 200:
            st.error(f"API Error fetching tasks for list {list_id}: {response.status_code}")
            st.error(f"Response: {response.text}")
            return []
        
        data = response.json()
        tasks = data.get("tasks", [])
        all_tasks.extend(tasks)
        
        return all_tasks
        
    except Exception as e:
        st.error(f"Exception fetching tasks for list {list_id}: {str(e)}")
        return []

def filter_tasks_by_date(tasks, start_date, end_date):
    """Filter tasks based on date range"""
    filtered_tasks = []
    
    start_timestamp = int(start_date.timestamp() * 1000)
    end_timestamp = int(end_date.timestamp() * 1000) + (24 * 60 * 60 * 1000 - 1)  # End of day
    
    for task in tasks:
        date_closed = task.get("date_closed")
        date_done = task.get("date_done")
        
        # Check if task was completed in the date range
        if date_closed:
            task_timestamp = int(date_closed)
            if start_timestamp <= task_timestamp <= end_timestamp:
                filtered_tasks.append(task)
        elif date_done:
            task_timestamp = int(date_done)
            if start_timestamp <= task_timestamp <= end_timestamp:
                filtered_tasks.append(task)
    
    return filtered_tasks

def categorize_tasks(tasks):
    """Categorize tasks by status"""
    categories = {
        "to_do": [],
        "in_progress": [],
        "completed": [],
        "closed": []
    }
    
    for task in tasks:
        status_obj = task.get("status", {})
        status_name = status_obj.get("status", "").lower()
        status_type = status_obj.get("type", "").lower()
        
        if task.get("date_closed"):
            categories["closed"].append(task)
        elif status_type == "done" or status_type == "closed":
            categories["completed"].append(task)
        elif "progress" in status_name or "active" in status_name or status_type == "active":
            categories["in_progress"].append(task)
        elif "open" in status_type or "to do" in status_name or status_name == "to do":
            categories["to_do"].append(task)
        else:
            categories["to_do"].append(task)
    
    return categories

def get_task_assignees(tasks):
    """Extract unique assignees from tasks"""
    assignees_dict = {}
    
    for task in tasks:
        for assignee in task.get("assignees", []):
            user_id = assignee.get("id")
            if user_id and user_id not in assignees_dict:
                assignees_dict[user_id] = {
                    "name": assignee.get("username", "Unknown"),
                    "email": assignee.get("email", "N/A"),
                    "color": assignee.get("color", "#7B68EE"),
                    "tasks": []
                }
            if user_id:
                assignees_dict[user_id]["tasks"].append(task)
    
    return assignees_dict

def format_date(timestamp):
    """Format timestamp to readable date"""
    if timestamp:
        try:
            ts = int(timestamp) if isinstance(timestamp, (int, float)) else int(timestamp)
            return datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M")
        except:
            return "N/A"
    return "N/A"

def get_priority_display(priority):
    """Get priority emoji and text"""
    if priority is None:
        return "⚪ None"
    
    if isinstance(priority, dict):
        priority = priority.get('priority') or priority.get('id')
    
    if priority is None:
        return "⚪ None"
    
    priority_map = {
        1: "🔴 Urgent",
        2: "🟠 High", 
        3: "🟡 Normal",
        4: "🔵 Low"
    }
    
    try:
        priority_num = int(priority)
        return priority_map.get(priority_num, "⚪ None")
    except (ValueError, TypeError):
        return "⚪ None"

def display_task_card(task, show_details=True):
    """Display a task card with details"""
    status_obj = task.get("status", {})
    status = status_obj.get("status", "Unknown")
    priority = task.get("priority")
    
    priority_display = get_priority_display(priority)
    
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            task_url = task.get("url", "#")
            task_name = task.get("name", "Untitled")
            st.markdown(f"**[{task_name}]({task_url})**")
            
            if show_details and task.get("description"):
                with st.expander("📝 Description"):
                    st.write(task.get("description"))
        
        with col2:
            status_class = status.lower().replace(' ', '-')
            st.markdown(f"<span class='status-badge status-{status_class}'>{status}</span>", unsafe_allow_html=True)
        
        with col3:
            st.caption(priority_display)
        
        if show_details:
            col_a, col_b = st.columns(2)
            with col_a:
                st.caption(f"📅 Created: {format_date(task.get('date_created'))}")
            with col_b:
                if task.get("due_date"):
                    st.caption(f"⏰ Due: {format_date(task.get('due_date'))}")
                if task.get("date_closed"):
                    st.caption(f"✅ Closed: {format_date(task.get('date_closed'))}")
            
            assignees = task.get("assignees", [])
            if assignees:
                assignee_names = ", ".join([a.get("username", "Unknown") for a in assignees])
                st.caption(f"👤 {assignee_names}")
        
        st.divider()

def display_team_member_analytics(user_data, tasks_in_period, list_name):
    """Display detailed analytics for a team member"""
    st.markdown(f"""
    <div class='member-card'>
        <h3>👤 {user_data['name']}</h3>
        <p><strong>Email:</strong> {user_data['email']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Overall stats
    col1, col2, col3, col4 = st.columns(4)
    
    user_categories = categorize_tasks(user_data['tasks'])
    completed_in_period = [t for t in tasks_in_period if any(a.get('id') == list(get_task_assignees([t]).keys())[0] for a in t.get('assignees', []) if get_task_assignees([t]))]
    
    # Filter completed tasks for this user in the selected period
    user_completed_in_period = []
    for task in tasks_in_period:
        for assignee in task.get("assignees", []):
            if assignee.get("id") in get_task_assignees(user_data['tasks']).keys():
                user_completed_in_period.append(task)
                break
    
    with col1:
        st.metric("Total Tasks", len(user_data['tasks']))
    with col2:
        st.metric("To Do", len(user_categories["to_do"]))
    with col3:
        st.metric("In Progress", len(user_categories["in_progress"]))
    with col4:
        st.metric("Completed (All)", len(user_categories["completed"]) + len(user_categories["closed"]))
    
    # Period-specific metrics
    if user_completed_in_period:
        st.success(f"✅ Completed {len(user_completed_in_period)} tasks in selected period")
        
        with st.expander(f"View {len(user_completed_in_period)} Completed Tasks"):
            for task in user_completed_in_period:
                display_task_card(task, show_details=True)
    else:
        st.info("No tasks completed in selected period")
    
    # Task breakdown
    st.markdown("**All Tasks by Status:**")
    for task in user_data['tasks'][:5]:  # Show first 5
        display_task_card(task, show_details=False)
    
    if len(user_data['tasks']) > 5:
        with st.expander(f"View all {len(user_data['tasks'])} tasks"):
            for task in user_data['tasks'][5:]:
                display_task_card(task, show_details=False)

# Main App
st.title("📊 ClickUp Dashboard")
st.markdown("### Comprehensive Task & Team Analytics")

# Sidebar for filters
with st.sidebar:
    st.header("⚙️ Settings")
    
    st.info(f"Monitoring {len(LIST_IDS)} list(s)")
    
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    
    # Date range filter
    st.subheader("📅 Date Range Filter")
    st.caption("Filter completed tasks by completion date")
    
    date_filter_option = st.selectbox(
        "Quick Select",
        ["Last 7 Days", "Last 30 Days", "Last 90 Days", "This Month", "Last Month", "Custom Range"]
    )
    
    today = datetime.now()
    
    if date_filter_option == "Last 7 Days":
        start_date = today - timedelta(days=7)
        end_date = today
    elif date_filter_option == "Last 30 Days":
        start_date = today - timedelta(days=30)
        end_date = today
    elif date_filter_option == "Last 90 Days":
        start_date = today - timedelta(days=90)
        end_date = today
    elif date_filter_option == "This Month":
        start_date = today.replace(day=1)
        end_date = today
    elif date_filter_option == "Last Month":
        first_day_this_month = today.replace(day=1)
        end_date = first_day_this_month - timedelta(days=1)
        start_date = end_date.replace(day=1)
    else:  # Custom Range
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", today - timedelta(days=30))
        with col2:
            end_date = st.date_input("End Date", today)
        start_date = datetime.combine(start_date, datetime.min.time())
        end_date = datetime.combine(end_date, datetime.min.time())
    
    st.caption(f"From: {start_date.strftime('%Y-%m-%d')}")
    st.caption(f"To: {end_date.strftime('%Y-%m-%d')}")

# Show loading message
with st.spinner("Loading ClickUp data..."):
    all_lists_data = {}
    
    for list_id in LIST_IDS:
        with st.spinner(f"Fetching list {list_id}..."):
            list_info = get_list_info(list_id)
            
            if list_info:
                tasks = get_all_tasks(list_id)
                
                all_lists_data[list_id] = {
                    "info": list_info,
                    "tasks": tasks,
                    "categories": categorize_tasks(tasks),
                    "assignees": get_task_assignees(tasks),
                    "completed_in_period": filter_tasks_by_date(
                        [t for t in tasks if t.get("date_closed") or t.get("date_done")],
                        start_date,
                        end_date
                    )
                }

if not all_lists_data:
    st.error("❌ Could not fetch any list data. Please check your API token and list IDs.")
    st.stop()

# Display each list separately with unique views
for idx, (list_id, data) in enumerate(all_lists_data.items()):
    list_info = data["info"]
    categories = data["categories"]
    tasks = data["tasks"]
    assignees = data["assignees"]
    completed_in_period = data["completed_in_period"]
    
    # Unique header for each list
    list_color = ["#6366f1", "#8b5cf6", "#ec4899", "#f59e0b", "#10b981"][idx % 5]
    
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, {list_color} 0%, {list_color}dd 100%); 
                padding: 25px; border-radius: 12px; color: white; margin: 30px 0 20px 0;'>
        <h2 style='margin: 0;'>📁 {list_info.get('name', 'Unnamed List')}</h2>
        <p style='margin: 5px 0 0 0; opacity: 0.9;'>List ID: {list_id}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overview & Period Analytics",
        "📝 All Tasks by Status", 
        "👥 Team Performance",
        "📈 Advanced Analytics"
    ])
    
    with tab1:
        # Overall metrics
        st.subheader("📊 Overall Statistics")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        total_tasks = len(tasks)
        
        with col1:
            st.metric("Total Tasks", total_tasks)
        with col2:
            st.metric("📝 To Do", len(categories["to_do"]))
        with col3:
            st.metric("🔄 In Progress", len(categories["in_progress"]))
        with col4:
            st.metric("✅ Completed", len(categories["completed"]))
        with col5:
            st.metric("🔒 Closed", len(categories["closed"]))
        
        # Progress bar
        if total_tasks > 0:
            completion_rate = (len(categories["completed"]) + len(categories["closed"])) / total_tasks * 100
            st.progress(completion_rate / 100)
            st.caption(f"Overall Completion Rate: {completion_rate:.1f}%")
        
        st.divider()
        
        # Period-specific analytics
        st.subheader(f"📅 Completed Tasks in Selected Period")
        st.caption(f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.metric(
                "Tasks Completed in Period",
                len(completed_in_period),
                delta=f"{len(completed_in_period)} tasks"
            )
            
            # Breakdown by team member for period
            st.markdown("**Breakdown by Team Member:**")
            member_completion = {}
            for task in completed_in_period:
                for assignee in task.get("assignees", []):
                    name = assignee.get("username", "Unassigned")
                    member_completion[name] = member_completion.get(name, 0) + 1
            
            if member_completion:
                for name, count in sorted(member_completion.items(), key=lambda x: x[1], reverse=True):
                    st.markdown(f"- **{name}**: {count} tasks")
            else:
                st.info("No tasks completed in this period")
        
        with col2:
            if completed_in_period:
                st.markdown("**Recently Completed Tasks:**")
                for task in completed_in_period[:10]:  # Show first 10
                    display_task_card(task, show_details=True)
                
                if len(completed_in_period) > 10:
                    with st.expander(f"View all {len(completed_in_period)} completed tasks"):
                        for task in completed_in_period[10:]:
                            display_task_card(task, show_details=True)
    
    with tab2:
        st.subheader("All Tasks Organized by Status")
        
        status_tab1, status_tab2, status_tab3, status_tab4 = st.tabs([
            f"📝 To Do ({len(categories['to_do'])})", 
            f"🔄 In Progress ({len(categories['in_progress'])})", 
            f"✅ Completed ({len(categories['completed'])})", 
            f"🔒 Closed ({len(categories['closed'])})"
        ])
        
        with status_tab1:
            if categories["to_do"]:
                for task in categories["to_do"]:
                    display_task_card(task)
            else:
                st.info("No tasks in this category")
        
        with status_tab2:
            if categories["in_progress"]:
                for task in categories["in_progress"]:
                    display_task_card(task)
            else:
                st.info("No tasks in this category")
        
        with status_tab3:
            if categories["completed"]:
                for task in categories["completed"]:
                    display_task_card(task)
            else:
                st.info("No tasks in this category")
        
        with status_tab4:
            if categories["closed"]:
                for task in categories["closed"]:
                    display_task_card(task)
            else:
                st.info("No tasks in this category")
    
    with tab3:
        st.subheader(f"👥 Team Performance Analysis")
        st.caption(f"Showing work completed between {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}")
        
        if assignees:
            # Sort team members by number of tasks completed in period
            members_with_completion = []
            for user_id, user_data in assignees.items():
                user_completed = [t for t in completed_in_period 
                                 if any(a.get('id') == user_id for a in t.get('assignees', []))]
                members_with_completion.append((user_id, user_data, len(user_completed)))
            
            members_with_completion.sort(key=lambda x: x[2], reverse=True)
            
            for user_id, user_data, completion_count in members_with_completion:
                user_completed_tasks = [t for t in completed_in_period 
                                       if any(a.get('id') == user_id for a in t.get('assignees', []))]
                
                with st.expander(f"👤 {user_data['name']} - {completion_count} tasks completed in period", expanded=False):
                    display_team_member_analytics(user_data, user_completed_tasks, list_info.get('name'))
        else:
            st.info("No team members assigned to tasks in this list")
    
    with tab4:
        st.subheader("📈 Advanced Analytics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Task Distribution**")
            status_df = pd.DataFrame({
                "Status": ["To Do", "In Progress", "Completed", "Closed"],
                "Count": [
                    len(categories["to_do"]),
                    len(categories["in_progress"]),
                    len(categories["completed"]),
                    len(categories["closed"])
                ]
            })
            st.bar_chart(status_df.set_index("Status"))
        
        with col2:
            st.markdown("**Priority Distribution**")
            priority_count = defaultdict(int)
            for task in tasks:
                priority = task.get("priority")
                
                if isinstance(priority, dict):
                    priority = priority.get('priority') or priority.get('id')
                
                priority_name = {
                    1: "Urgent",
                    2: "High",
                    3: "Normal",
                    4: "Low",
                    None: "None"
                }.get(priority, "None")
                priority_count[priority_name] += 1
            
            priority_df = pd.DataFrame({
                "Priority": list(priority_count.keys()),
                "Count": list(priority_count.values())
            })
            st.bar_chart(priority_df.set_index("Priority"))
        
        # Team workload comparison
        st.markdown("**Team Workload Comparison**")
        if assignees:
            workload_data = []
            for user_id, user_data in assignees.items():
                user_cats = categorize_tasks(user_data["tasks"])
                user_completed = [t for t in completed_in_period 
                                 if any(a.get('id') == user_id for a in t.get('assignees', []))]
                
                workload_data.append({
                    "Member": user_data["name"],
                    "Total Tasks": len(user_data["tasks"]),
                    "To Do": len(user_cats["to_do"]),
                    "In Progress": len(user_cats["in_progress"]),
                    "Completed (Overall)": len(user_cats["completed"]) + len(user_cats["closed"]),
                    f"Completed (Period)": len(user_completed)
                })
            
            workload_df = pd.DataFrame(workload_data)
            st.dataframe(workload_df, use_container_width=True, hide_index=True)
        else:
            st.info("No assigned team members")
    
    st.markdown("---")

# Footer
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.caption("💡 Tip: Use the date range filter in the sidebar to analyze work completed in specific periods")
