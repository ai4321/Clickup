import streamlit as st
import requests

# --- API Configuration ---
# WARNING: Do not hardcode real API keys. Use st.text_input as shown below.
# The key provided in the prompt is used as a default example.
DEFAULT_API_KEY = "88049748_252aea582407f70da5caa635d8f7f39dd2d0d4c87a4337afc58ee11bdfb74fd6"
DEFAULT_LIST_IDS = "901307726539"

# --- ClickUp API Helper Functions ---

def get_list_details(list_id, api_key):
    """Fetches details for a specific list, including members."""
    url = f"https://api.clickup.com/api/v2/list/{list_id}"
    headers = {"Authorization": api_key}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching details for list {list_id}: {e}")
        return None

def get_all_tasks(list_id, api_key):
    """Fetches all tasks from a list, handling pagination."""
    all_tasks = []
    page = 0
    
    while True:
        url = f"https://api.clickup.com/api/v2/list/{list_id}/task"
        headers = {"Authorization": api_key}
        params = {
            "page": page,
            "include_closed": "true", # Get completed tasks
            "subtasks": "true"         # Include subtasks in the results
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            tasks = data.get('tasks', [])
            
            if not tasks:
                break  # No more tasks, exit loop
                
            all_tasks.extend(tasks)
            page += 1
            
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching tasks for list {list_id} (page {page}): {e}")
            break
            
    return all_tasks

def process_task_data(tasks):
    """Categorizes tasks and returns counts and lists."""
    total_tasks = len(tasks)
    
    # Filter tasks by status type
    completed_tasks = [t for t in tasks if t.get('status', {}).get('type') == 'closed']
    current_tasks = [t for t in tasks if t.get('status', {}).get('type') != 'closed']
    
    # Filter current tasks by specific status names (case-insensitive)
    todo_tasks = [
        t for t in current_tasks 
        if 'to do' in t.get('status', {}).get('status', '').lower()
    ]
    inprogress_tasks = [
        t for t in current_tasks 
        if 'in progress' in t.get('status', {}).get('status', '').lower()
    ]
    
    return {
        "total": total_tasks,
        "completed_count": len(completed_tasks),
        "current_count": len(current_tasks),
        "todo_count": len(todo_tasks),
        "inprogress_count": len(inprogress_tasks),
        "completed_tasks": completed_tasks,
        "current_tasks": current_tasks
    }

# --- Streamlit App UI ---

st.set_page_config(layout="wide", page_title="ClickUp List Dashboard")

st.title("ClickUp List Dashboard 🚀")
st.markdown("Enter your ClickUp API key and a list of List IDs to get a detailed breakdown.")

# --- Security and Inputs ---
st.error(
    "**Security Warning:** Never share your API keys. The key below is just the "
    "example you provided. Replace it with your *real* key and treat it like a password."
)

api_key = st.text_input(
    "ClickUp API Key", 
    value=DEFAULT_API_KEY, 
    type="password",
    help="Your personal ClickUp API token."
)

list_ids_input = st.text_area(
    "List IDs (one per line)", 
    value=DEFAULT_LIST_IDS,
    help="Enter one or more ClickUp List IDs, separated by new lines."
)

# Parse the list IDs from the text area
list_ids = [list_id.strip() for list_id in list_ids_input.split('\n') if list_id.strip()]

if st.button("Fetch List Data", type="primary"):
    if not api_key:
        st.warning("Please enter your API Key.")
    elif not list_ids:
        st.warning("Please enter at least one List ID.")
    else:
        with st.spinner("Fetching data from ClickUp... This may take a moment."):
            for list_id in list_ids:
                st.divider()
                
                # --- 1. Fetch List Details ---
                list_details = get_list_details(list_id, api_key)
                
                if list_details:
                    list_name = list_details.get('name', f"List ID: {list_id}")
                    
                    with st.expander(f"### {list_name}", expanded=True):
                        
                        # --- 2. Fetch Tasks ---
                        all_tasks = get_all_tasks(list_id, api_key)
                        task_data = process_task_data(all_tasks)
                        
                        # --- 3. Show Metrics (KPIs) ---
                        st.subheader("List Statistics")
                        col1, col2, col3, col4, col5 = st.columns(5)
                        col1.metric("Total Tasks", task_data['total'])
                        col2.metric("Current Tasks", task_data['current_count'])
                        col3.metric("Completed Tasks", task_data['completed_count'])
                        col4.metric("To Do", task_data['todo_count'])
                        col5.metric("In Progress", task_data['inprogress_count'])
                        
                        st.divider()
                        
                        # --- 4. Show Members and Tasks ---
                        col_members, col_tasks = st.columns([1, 2]) # Give tasks more space
                        
                        # --- Members View ---
                        with col_members:
                            st.subheader("List Members 👥")
                            members = list_details.get('members', [])
                            if members:
                                for member in members:
                                    # Use a subtle markdown format for each member
                                    st.markdown(
                                        f"- **{member.get('username', 'N/A')}** "
                                        f"(`{member.get('email', 'no-email')}`)"
                                    )
                            else:
                                st.info("No members found for this list.")
                        
                        # --- Tasks View ---
                        with col_tasks:
                            st.subheader("Task Details 📝")
                            
                            tab_current, tab_completed = st.tabs([
                                f"Current ({task_data['current_count']})", 
                                f"Completed ({task_data['completed_count']})"
                            ])
                            
                            # Current Tasks Tab
                            with tab_current:
                                if task_data['current_tasks']:
                                    for task in task_data['current_tasks']:
                                        assignees = ", ".join(
                                            a.get('username', 'Unassigned') 
                                            for a in task.get('assignees', [])
                                        )
                                        st.markdown(
                                            f"[{task.get('name')}]({task.get('url')}) "
                                            f"*(Status: **{task['status']['status']}**, "
                                            f"Assignee: {assignees})*"
                                        )
                                else:
                                    st.info("No current tasks.")
                            
                            # Completed Tasks Tab
                            with tab_completed:
                                if task_data['completed_tasks']:
                                    for task in task_data['completed_tasks']:
                                        st.markdown(
                                            f"[{task.get('name')}]({task.get('url')}) "
                                            f"*(Status: **{task['status']['status']}**)*"
                                        )
                                else:
                                    st.info("No completed tasks.")
                                    
                else:
                    st.error(f"Could not fetch data for List ID: {list_id}")
