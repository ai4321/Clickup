import streamlit as st
import requests
from datetime import datetime
from collections import defaultdict
import pandas as pd
import json

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
    </style>
""", unsafe_allow_html=True)

# ClickUp API Configuration
CLICKUP_API_TOKEN = "88049748_252aea582407f70da5caa635d8f7f39dd2d0d4c87a4337a"
HEADERS = {
    "Authorization": CLICKUP_API_TOKEN
}
BASE_URL = "https://api.clickup.com/api/v2"

# List IDs to fetch (can be expanded)
LIST_IDS = [
    "901307726539",
    # Add more list IDs here as needed
]

def debug_api_call(url, method="GET", params=None):
    """Debug helper to show API calls"""
    st.sidebar.write(f"🔍 {method}: {url}")
    if params:
        st.sidebar.write(f"Params: {params}")

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
        
        # Get open tasks
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

def categorize_tasks(tasks):
    """Categorize tasks by status - now properly handles ClickUp status types"""
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
        
        # Check if task is closed by date_closed field
        if task.get("date_closed"):
            categories["closed"].append(task)
        # Use status type for better categorization
        elif status_type == "done" or status_type == "closed":
            categories["completed"].append(task)
        elif "progress" in status_name or "active" in status_name or status_type == "active":
            categories["in_progress"].append(task)
        elif "open" in status_type or "to do" in status_name or status_name == "to do":
            categories["to_do"].append(task)
        else:
            # Default to to_do if unclear
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
            # ClickUp uses milliseconds
            ts = int(timestamp) if isinstance(timestamp, (int, float)) else int(timestamp)
            return datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M")
        except:
            return "N/A"
    return "N/A"

def get_priority_display(priority):
    """Get priority emoji and text"""
    if priority is None:
        return "⚪ None"
    
    # Handle if priority is a dict (get the 'priority' key or 'id' key)
    if isinstance(priority, dict):
        priority = priority.get('priority') or priority.get('id')
    
    # If still None or not a number, return None
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

# Main App
st.title("📊 ClickUp Dashboard")
st.markdown("### Comprehensive Task & Team Analytics")

# Sidebar for filters and debug
with st.sidebar:
    st.header("⚙️ Settings")
    
    show_debug = st.checkbox("🐛 Show Debug Info", value=False)
    
    st.info(f"Monitoring {len(LIST_IDS)} list(s)")
    
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    
    view_mode = st.radio(
        "📋 View Mode",
        ["Overview", "Tasks Detail", "Team Members", "Analytics"]
    )
    
    if show_debug:
        st.divider()
        st.subheader("Debug Info")

# Show loading message
with st.spinner("Loading ClickUp data..."):
    # Fetch data for all lists
    all_lists_data = {}
    
    for list_id in LIST_IDS:
        with st.spinner(f"Fetching list {list_id}..."):
            list_info = get_list_info(list_id)
            
            if list_info:
                tasks = get_all_tasks(list_id)
                
                if show_debug:
                    with st.sidebar:
                        st.write(f"List: {list_info.get('name', list_id)}")
                        st.write(f"Total tasks fetched: {len(tasks)}")
                        if tasks:
                            st.write("Sample task statuses:")
                            for t in tasks[:3]:
                                st.write(f"- {t.get('name')}: {t.get('status', {}).get('status')} (type: {t.get('status', {}).get('type')})")
                
                all_lists_data[list_id] = {
                    "info": list_info,
                    "tasks": tasks,
                    "categories": categorize_tasks(tasks),
                    "assignees": get_task_assignees(tasks)
                }

if not all_lists_data:
    st.error("❌ Could not fetch any list data. Please check your API token and list IDs.")
    st.stop()

# Display based on view mode
if view_mode == "Overview":
    for list_id, data in all_lists_data.items():
        list_info = data["info"]
        categories = data["categories"]
        
        st.header(f"📁 {list_info.get('name', 'Unnamed List')}")
        
        # Metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        total_tasks = len(data["tasks"])
        
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
            st.caption(f"Completion Rate: {completion_rate:.1f}%")
        
        # Team size
        st.caption(f"👥 Team Members: {len(data['assignees'])}")
        
        st.divider()

elif view_mode == "Tasks Detail":
    for list_id, data in all_lists_data.items():
        list_info = data["info"]
        categories = data["categories"]
        
        st.header(f"📁 {list_info.get('name', 'Unnamed List')}")
        
        tab1, tab2, tab3, tab4 = st.tabs([
            f"📝 To Do ({len(categories['to_do'])})", 
            f"🔄 In Progress ({len(categories['in_progress'])})", 
            f"✅ Completed ({len(categories['completed'])})", 
            f"🔒 Closed ({len(categories['closed'])})"
        ])
        
        with tab1:
            if categories["to_do"]:
                for task in categories["to_do"]:
                    display_task_card(task)
            else:
                st.info("No tasks in this category")
        
        with tab2:
            if categories["in_progress"]:
                for task in categories["in_progress"]:
                    display_task_card(task)
            else:
                st.info("No tasks in this category")
        
        with tab3:
            if categories["completed"]:
                for task in categories["completed"]:
                    display_task_card(task)
            else:
                st.info("No tasks in this category")
        
        with tab4:
            if categories["closed"]:
                for task in categories["closed"]:
                    display_task_card(task)
            else:
                st.info("No tasks in this category")
        
        st.divider()

elif view_mode == "Team Members":
    for list_id, data in all_lists_data.items():
        list_info = data["info"]
        assignees = data["assignees"]
        
        st.header(f"📁 {list_info.get('name', 'Unnamed List')}")
        st.subheader(f"👥 Team Members ({len(assignees)})")
        
        if assignees:
            for user_id, user_data in assignees.items():
                with st.expander(f"👤 {user_data['name']} ({len(user_data['tasks'])} tasks)"):
                    st.write(f"**Email:** {user_data['email']}")
                    
                    # Categorize user's tasks
                    user_categories = categorize_tasks(user_data['tasks'])
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("To Do", len(user_categories["to_do"]))
                    with col2:
                        st.metric("In Progress", len(user_categories["in_progress"]))
                    with col3:
                        st.metric("Completed", len(user_categories["completed"]))
                    with col4:
                        st.metric("Closed", len(user_categories["closed"]))
                    
                    st.markdown("**Tasks:**")
                    for task in user_data['tasks']:
                        display_task_card(task, show_details=False)
        else:
            st.info("No team members assigned to tasks in this list")
        
        st.divider()

elif view_mode == "Analytics":
    for list_id, data in all_lists_data.items():
        list_info = data["info"]
        tasks = data["tasks"]
        categories = data["categories"]
        
        st.header(f"📁 {list_info.get('name', 'Unnamed List')}")
        
        # Task distribution
        st.subheader("📊 Task Distribution")
        col1, col2 = st.columns(2)
        
        with col1:
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
            # Priority distribution
            priority_count = defaultdict(int)
            for task in tasks:
                priority = task.get("priority")
                
                # Handle priority being a dict
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
        
        # Team workload
        st.subheader("👥 Team Workload")
        assignees = data["assignees"]
        if assignees:
            workload_data = []
            for user_id, user_data in assignees.items():
                user_cats = categorize_tasks(user_data["tasks"])
                workload_data.append({
                    "Member": user_data["name"],
                    "Total Tasks": len(user_data["tasks"]),
                    "To Do": len(user_cats["to_do"]),
                    "In Progress": len(user_cats["in_progress"]),
                    "Completed": len(user_cats["completed"]),
                    "Closed": len(user_cats["closed"])
                })
            
            workload_df = pd.DataFrame(workload_data)
            st.dataframe(workload_df, use_container_width=True)
        else:
            st.info("No assigned team members")
        
        st.divider()

# Footer
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.caption("💡 Tip: Enable 'Show Debug Info' in the sidebar to troubleshoot issues")
