import streamlit as st
import requests
from datetime import datetime
from collections import defaultdict
import pandas as pd

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
CLICKUP_API_TOKEN = "88049748_252aea582407f70da5caa635d8f7f39dd2d0d4c87a4337afc58ee11bdfb74fd6"
HEADERS = {
    "Authorization": CLICKUP_API_TOKEN,
    "Content-Type": "application/json"
}
BASE_URL = "https://api.clickup.com/api/v2"

# List IDs to fetch (can be expanded)
LIST_IDS = [
    "901307726539",
    # Add more list IDs here as needed
]

@st.cache_data(ttl=300)
def get_list_info(list_id):
    """Fetch list information"""
    try:
        response = requests.get(f"{BASE_URL}/list/{list_id}", headers=HEADERS)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching list {list_id}: {str(e)}")
        return None

@st.cache_data(ttl=300)
def get_tasks(list_id):
    """Fetch all tasks from a list"""
    try:
        all_tasks = []
        page = 0
        while True:
            response = requests.get(
                f"{BASE_URL}/list/{list_id}/task",
                headers=HEADERS,
                params={"page": page, "archived": False, "subtasks": True}
            )
            response.raise_for_status()
            data = response.json()
            tasks = data.get("tasks", [])
            if not tasks:
                break
            all_tasks.extend(tasks)
            page += 1
            if len(tasks) < 100:  # ClickUp returns max 100 per page
                break
        return all_tasks
    except Exception as e:
        st.error(f"Error fetching tasks for list {list_id}: {str(e)}")
        return []

def categorize_tasks(tasks):
    """Categorize tasks by status"""
    categories = {
        "to_do": [],
        "in_progress": [],
        "completed": [],
        "closed": []
    }
    
    for task in tasks:
        status = task.get("status", {}).get("status", "").lower()
        
        if "complete" in status or "done" in status:
            categories["completed"].append(task)
        elif "closed" in status:
            categories["closed"].append(task)
        elif "progress" in status or "in progress" in status or "active" in status:
            categories["in_progress"].append(task)
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
            return datetime.fromtimestamp(int(timestamp) / 1000).strftime("%Y-%m-%d %H:%M")
        except:
            return "N/A"
    return "N/A"

def display_task_card(task, show_details=True):
    """Display a task card with details"""
    status = task.get("status", {}).get("status", "Unknown")
    priority = task.get("priority")
    
    priority_emoji = {
        1: "🔴 Urgent",
        2: "🟠 High",
        3: "🟡 Normal",
        4: "🔵 Low"
    }.get(priority, "⚪ None")
    
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown(f"**{task.get('name', 'Untitled')}**")
            if show_details and task.get("description"):
                with st.expander("Description"):
                    st.write(task.get("description"))
        
        with col2:
            st.markdown(f"<span class='status-badge status-{status.lower().replace(' ', '-')}'>{status}</span>", unsafe_allow_html=True)
        
        with col3:
            st.caption(priority_emoji)
        
        if show_details:
            st.caption(f"📅 Created: {format_date(task.get('date_created'))}")
            if task.get("due_date"):
                st.caption(f"⏰ Due: {format_date(task.get('due_date'))}")
            
            assignees = task.get("assignees", [])
            if assignees:
                assignee_names = ", ".join([a.get("username", "Unknown") for a in assignees])
                st.caption(f"👤 {assignee_names}")
        
        st.divider()

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
    
    view_mode = st.radio(
        "📋 View Mode",
        ["Overview", "Tasks Detail", "Team Members", "Analytics"]
    )

# Fetch data for all lists
all_lists_data = {}
for list_id in LIST_IDS:
    list_info = get_list_info(list_id)
    if list_info:
        tasks = get_tasks(list_id)
        all_lists_data[list_id] = {
            "info": list_info,
            "tasks": tasks,
            "categories": categorize_tasks(tasks),
            "assignees": get_task_assignees(tasks)
        }

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
        
        tab1, tab2, tab3, tab4 = st.tabs(["📝 To Do", "🔄 In Progress", "✅ Completed", "🔒 Closed"])
        
        with tab1:
            st.subheader(f"To Do Tasks ({len(categories['to_do'])})")
            if categories["to_do"]:
                for task in categories["to_do"]:
                    display_task_card(task)
            else:
                st.info("No tasks in this category")
        
        with tab2:
            st.subheader(f"In Progress Tasks ({len(categories['in_progress'])})")
            if categories["in_progress"]:
                for task in categories["in_progress"]:
                    display_task_card(task)
            else:
                st.info("No tasks in this category")
        
        with tab3:
            st.subheader(f"Completed Tasks ({len(categories['completed'])})")
            if categories["completed"]:
                for task in categories["completed"]:
                    display_task_card(task)
            else:
                st.info("No tasks in this category")
        
        with tab4:
            st.subheader(f"Closed Tasks ({len(categories['closed'])})")
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
                workload_data.append({
                    "Member": user_data["name"],
                    "Total Tasks": len(user_data["tasks"]),
                    "Completed": len(categorize_tasks(user_data["tasks"])["completed"])
                })
            
            workload_df = pd.DataFrame(workload_data)
            st.dataframe(workload_df, use_container_width=True)
        
        st.divider()

# Footer
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
