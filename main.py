from datetime import datetime
import time
import threading
from tkinter import *
import tkinter as tk
import cx_Oracle
from functools import partial
from tkcalendar import Calendar, DateEntry
from plyer import notification

lib_dir = r"C:\Kit\Oracle\instantclient-basic-windows.x64-19.12.0.0.0dbru\instantclient_19_12"

cx_Oracle.init_oracle_client(lib_dir=lib_dir)

BACKGROUND_COLOR = "#212121"
BTN_COLOR = "#0c0c0c"
UNKNOWN = "UNKNOWN"
start_date = UNKNOWN
start_hour = UNKNOWN
end_hour = UNKNOWN
end_date = UNKNOWN
db_username = UNKNOWN
db_password = UNKNOWN
connection = None
today = datetime.today()
all_tasks = {}
stop_threads = False

# Method that sends commands to db, choice=0 is for inserting, choice=1 is for retrieving
def send_db_info(choice,message):
    try:
        with open('database_cred.txt', 'r') as file:
            db_cred = file.read()
        connection = cx_Oracle.connect(db_cred)
        cursor = connection.cursor()
        # Sending...    
        if choice == 0:
            cursor.execute(message)
            connection.commit()
        # Retrieving...
        elif choice == 1:
            cursor.execute(message)
            answer = cursor.fetchone()
            return answer
        elif choice == 2:
            cursor.execute(message)
            answer = cursor.fetchall()
            return answer
    except cx_Oracle.Error as error:
        print(error)
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

# Retrieving all the task a user has and placing them in a dictionary
def accessing_tasks():
    global all_tasks
    id = send_db_info(2, f"select id from tasks where username = '{db_username}' order by id asc")
    item_list = []
    for i in id:
        for index in i:
            # Nume_task, Descriere task, Username, Times, Dates
            info = send_db_info(2, f"select * from tasks where username = '{db_username}' and id = '{index}'")
            for list in info:
                for item in list:
                    # Placing all the data from db in a list
                    item_list.append(item)
            title, desc, times, dates = item_list[0], item_list[1], item_list[3], item_list[4]
            tasks_list = [title, desc, times, dates]
            item_list.clear()

        all_tasks[index] = (tasks_list)

# Veryfing times method
# TODO : Add the abort and delete functions to the tasks (add a new column in db = aborted ?)
# TODO : Abort and delete
def check_time():
    global stop_threads
    while True:
        today = datetime.today()
        time_now = str(today)[11:-10]
        # Picking each task
        for i in all_tasks:
            temp = all_tasks[i]
            # Getting task's starting-ending hours
            times = temp[2]
            # temp = 00:00-00:00
            starting = times[:-6]
            # When there are 30 mins left until the task begins, display message
            half_early_mins = int(starting[3:])
            hour = int(starting[:-3])
            # -30 mins
            for j in range(30):
                if half_early_mins == 0:
                    half_early_mins = 59
                    hour = hour - 1
                    if hour == - 1:
                        hour = 23
                half_early_mins = half_early_mins - 1
            early_hour = hour
            if hour < 10:
                early_hour = f"0{hour}"
            half_early = f"{early_hour}:{half_early_mins}"
            title = all_tasks[i]
            title = title[0]
            # Showing desktop notify
            if half_early == time_now:
                notification.notify(
                    title=f'{title}',
                    message=f'{title} starting in 30 minutes!',
                    app_icon=None,
                    timeout=4,  
                )
                print(f"{title} is starting in 30!!!")

        time.sleep(10)
        if stop_threads:
            break
t1 = threading.Thread(target=check_time, name="t1")


# Creating register window
def register_login(choice):
    global db_username, db_password
    if choice == "Login":
        rg_flds_v = ["Userame", "Password"]
        field_v = ["", ""]
        offset = 50
        pady = 0
    elif choice == "Register":
        rg_flds_v = ["Userame", "Password", "Confirm Password"]
        field_v = ["", "", ""]
        offset = 20
        pady = 20
    else:
        print("Wrong argument passed, returning...")
        return

    # Retrieves username and passowrds from input fields
    def get_info():
        global db_username, db_password
        user = field_v[0].get()
        passwrd = field_v[1].get()
        # If register, we send the user and pass to the db
        if choice == "Register":
            conf = field_v[2].get()
            if passwrd != conf:
                print("Passwords don't match")
            else:
                db_username = user
                db_password = passwrd
                print(passwrd)
                send_db_info(0 ,f"insert into users values ('{db_username}', '{db_password}')")
                rg_wnd.destroy()
        # If login, we check if user in db, then we check pass to see if matches
        elif choice == "Login":
            password = send_db_info(1, f"select Password from users where Username='{user}'")
            if passwrd == password[0]:
                db_username = user
                print(f"Acces granted. Hello {db_username}!")
                rg_wnd.destroy()
            else:
                print("Wrong username or password. Try again...")
        accessing_tasks()
        t1.start()

    # Creating register/login window
    rg_wnd = tk.Toplevel(root)
    rg_wnd.config(bg=BACKGROUND_COLOR)
    rg_wnd.title("Register Account")
    rg_wnd.geometry("500x500")

    rg_flds_frm = tk.Frame(rg_wnd, bg=BACKGROUND_COLOR)
    rg_flds_frm.rowconfigure([0,1,2], minsize= 100)
    rg_flds_frm.columnconfigure(0, minsize=450)

    # Creating input fields from rg_flds_v
    for i in range(len(rg_flds_v)):
        field = tk.Entry(rg_flds_frm, bg=BTN_COLOR, fg="white", font=("",20))
        field.insert(0, rg_flds_v[i])
        field.grid(row=i, column=0, pady=20, sticky="nsew")
        field_v[i] = field
    rg_flds_frm.pack(pady=offset)

    # Login/Register Button (gets the user and passowrds)
    rg_btn = tk.Button(rg_wnd, bg=BTN_COLOR, fg="white", text=choice, font=("", 20), height=2, width=10, activebackground="green", bd=0, command=get_info)
    rg_btn.pack(pady=pady)


# Method for adding tasks
def add_task(user):
    
    # In case we are not logged in, the method returns
    if db_username == UNKNOWN:
        print("Not logged in")
        return

    # Getting the star and end date from the window
    def get_date_time(choice):
        global start_date, end_date
        if choice == "from":
            start_date = cal.get_date()
            from_date_lbl["text"] = start_date
            print(start_date)   
        elif choice == "to":
            end_date = cal.get_date()
            to_date_lbl["text"] = end_date
            print(end_date)  

    # Submit the task to the db
    def submit_info():

        # Checking the last index so we can imprement
        condition = send_db_info(2, f"select id from tasks where username = '{db_username}' order by id asc")
        if not condition:
            index = 1
        else:
            for i in condition:
                for j in i:
                    index = j + 1

        # Get all the info from the 'Add_Task'   
        start_hour, start_minute = from_hour.get(), from_minute.get()
        end_hour, end_minute = to_hour.get(), to_minute.get()
        starting = f"{start_hour}:{start_minute}"
        ending = f"{end_hour}:{end_minute}"
        hours = f"{starting}-{ending}"
        dates = f"{start_date}-{end_date}"
        title = task_title.get()
        description = task_desc.get(1.0, tk.END)
        send_db_info(0, f"insert into tasks values ('{title}', '{description}', '{db_username}', '{hours}', '{dates}', {index})")
        print("Info sent succesfully..")
        # print(starting, ending, title, description)
        #(task_name, task_desc, username, hours, dates)

    # Creating the 'add task' window
    cal_wnd = Toplevel(root)
    cal_wnd.config(bg=BACKGROUND_COLOR)
    cal_wnd.geometry("900x700")
    cal_wnd.resizable(False, False)
    cal_wnd.title("Add title")
    cal_set_date = tk.Frame(cal_wnd, bg=BACKGROUND_COLOR)
    cal_set_date.columnconfigure(0, minsize=400)
    cal_set_date.columnconfigure(1, minsize=500)
    cal_set_date.rowconfigure(0, minsize=400)
    # Retrieving today's day, month and year
    today_day = int(str(today)[8:-16])
    today_month = int(str(today)[5:-19])
    today_year = int(str(today)[:-22])
    # Creating the calendar
    cal = Calendar(cal_set_date, selectmode='day', year=today_year, month=today_month, day=today_day, bg=BTN_COLOR, fg="white")
    cal.grid(row=0, column=0, sticky="nsew")

    to_startend_frm = tk.Frame(cal_set_date, bg=BACKGROUND_COLOR)
    to_startend_frm.rowconfigure([0,1,2], minsize=90)
    to_startend_frm.columnconfigure([0,1], minsize=200)

    # From start to end hours
    from_hour_frm=tk.Frame(to_startend_frm, bg=BACKGROUND_COLOR)
    from_hour=tk.Entry(from_hour_frm, font=("", 25), bg=BTN_COLOR, fg="white", width=3)
    dots_lbl=tk.Label(from_hour_frm, font=("", 25), bg=BACKGROUND_COLOR, fg="white", text=":")
    from_minute=tk.Entry(from_hour_frm, font=("", 25), bg=BTN_COLOR, fg="white", width=3)
    from_hour.insert(0, "00")
    from_minute.insert(0, "00")
    from_hour.grid(row=0, column=0, sticky="nsew")
    dots_lbl.grid(row=0, column=1, sticky="nsew")
    from_minute.grid(row=0, column=2, sticky="nsew")

    to_hour_frm=tk.Frame(to_startend_frm, bg=BACKGROUND_COLOR)
    to_hour=tk.Entry(to_hour_frm, font=("", 25), bg=BTN_COLOR, fg="white", width=3)
    dots_lbl2=tk.Label(to_hour_frm, font=("", 25), bg=BACKGROUND_COLOR, fg="white", text=":")
    to_minute=tk.Entry(to_hour_frm, font=("", 25), bg=BTN_COLOR, fg="white", width=3)
    to_hour.insert(0, "00")
    to_minute.insert(0, "00")
    to_hour.grid(row=0, column=0, sticky="nsew")
    dots_lbl2.grid(row=0, column=1, sticky="nsew")
    to_minute.grid(row=0, column=2, sticky="nsew")

    from_hour_frm.grid(row=0, column=0, sticky="nsew", padx=(30, 10), pady=10)
    to_hour_frm.grid(row=0, column=1, sticky="nsew", padx=30, pady=10)

    # From start to end date buttons and labels
    #Labels
    from_date_lbl = tk.Label(to_startend_frm, font=("",20), text="--.--.----")
    to_date_lbl = tk.Label(to_startend_frm, font=("",20), text="--.--.----")
    from_date_lbl.grid(row=1, column=0, sticky="nsew", padx=10, pady=30)
    to_date_lbl.grid(row=1, column=1, sticky="nsew", padx=10, pady=30)
    #Buttons
    from_date = tk.Button(to_startend_frm, font=("", 13), text="From", command=partial(get_date_time, "from"))
    to_date = tk.Button(to_startend_frm, font=("", 13), text="To", command=partial(get_date_time, "to"))
    from_date.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
    to_date.grid(row=2, column=1, sticky="nsew", padx=20, pady=10)
    to_startend_frm.grid(row=0, column=1, sticky="nsew", padx=35, pady=50)

    # Title and Description entries
    task_info_frm = tk.Frame(cal_wnd, bg=BACKGROUND_COLOR)
    task_info_frm.rowconfigure(0, minsize = 100)
    task_info_frm.columnconfigure([0,1], minsize = 70)

    task_title_frm = tk.Frame(task_info_frm, bg=BACKGROUND_COLOR)
    task_title_lbl=tk.Label(task_title_frm, bg=BACKGROUND_COLOR, fg="white", font=("", 20), text="Title :")
    task_title=tk.Entry(task_title_frm, bg=BTN_COLOR, fg="white", font=("", 20))
    submit_btn=tk.Button(task_title_frm, bg=BTN_COLOR, fg="white", bd=0, text="Submit Task", font=("", 20), command=submit_info)
    task_title_lbl.grid(row=0, column=0)
    task_title.grid(row=1, column=0)
    submit_btn.grid(row=2, column=0, pady=20)
    task_desc=tk.Text(task_info_frm, bg=BTN_COLOR, fg="white", height=15, width=50)
    task_desc.insert(tk.END, "Task description...")
    task_title_frm.grid(row=0, column=0, sticky="ew", padx=(0,50))
    task_desc.grid(row=0, column=1, sticky="nsew", pady=(30, 0))
    cal_set_date.pack()
    task_info_frm.pack()

page = 0
view_fields = [0, 0, 0]
view_lines = [0, 0, 0]
view_btns = [0]
view_flag = False

def view_tasks():
    global db_username, view_fields, view_flag,  view_lines, view_btns, page
    view_fields, view_lines, view_btns,  page =  [0, 0, 0], [0, 0, 0], 0,  -3

    view_task_wnd = tk.Toplevel(root)
    view_task_wnd.geometry("900x670")
    view_task_wnd.title("Viewing All Tasks")
    view_task_wnd.config(bg = BACKGROUND_COLOR)

    def next_page(choice):
        global view_fields, view_flag, view_lines, view_btns, page
        # Destroying all the frames and lines from last page


        # TODO : Soft-delete
        def delete_task(frame, index):
            send_db_info(0, f"delete from tasks where id='{index}' and username = '{db_username}'")
            id1 = send_db_info(2, f"select id from tasks where username = '{db_username}' order by id asc")
            print (f"id1 : {id1}")
            
            # Creating a list 'id_list' with all the 'id' from the db 
            ids_list = []
            for j in id1:
                for k in j:
                    ids_list.append(k)

            # Checking if the last index is one less than the next one, if not, that is the missing index
            missing_index = UNKNOWN
            for i in range(1,len(ids_list)):
                if ids_list[i] != ids_list[i-1] + 1:
                    missing_index = ids_list[i-1] + 1
                    print(f"Missing index is : {missing_index}")
                # If 'id' = 1 is not found, than we immediately assign it
                elif ids_list[0] != 1:
                    missing_index = 1
                    print(f"Missing index = 1")
                    
            # We update every index starting from the 'missing_index' to be 1 less, so every 'id' is sorted
            aux = missing_index
            for i in range(missing_index, len(ids_list) + 1):
                print(f"Updating {aux + 1} to {aux}")
                send_db_info(0, f"update tasks set id = '{aux}' where id = '{aux + 1}' and username = '{db_username}'")
                aux += 1 

            # Destroying the actual frame 
            frame.destroy()

        # Destroying the buttons and frames from the window
        try:
            for i in range(3):
                view_btns.destroy()
                view_fields[i].destroy()
                view_lines[i].destroy()
        except:
            print("Nope")

        # Resetting the lists
        view_fields = [0, 0, 0]
        view_lines = [0, 0, 0]
        iteration_index = 0
        # Retrieving all the ID's from the db
        id = send_db_info(2, f"select id from tasks where username = '{db_username}' order by id asc")
        item_list = []

        # Indexes
        if choice == "Next":
            page+=3
        elif choice == "Previous":
            print(f"Page before decrement : {page}")
            if page != 0:
                page-=3
            else:
                page = 0

        for i in id:
            # We only want 3 tasks on a page, so we iterate 3 times
            if iteration_index < 3:
                for index in i:

                    # We take the first 3 tasks from index 'page' increased 3 times, and we store them in 'tasks_list'
                    tasks_lists = []
                    for i in range(1,4):
                        tasks_lists.append(send_db_info(2, f"select * from tasks where username = '{db_username}' and id = '{page+i}'"))
                        view_flag = True

                    # Taking the corresponding task, according to 'iteration_index', and appending every value to 'item_list'
                    item_list.clear()
                    now_task = tasks_lists[iteration_index]
                    for item in now_task:
                        for sub_item in item:
                            # Placing all the data from db in 'item_list'
                            item_list.append(sub_item)    

                try:
                    title, times, dates = item_list[0], item_list[3], item_list[4]
                except:
                    break
                if view_flag:
                    frame = tk.Frame(view_task_wnd, bg = BACKGROUND_COLOR)

                    # Placing title, time and date, buttons all in one window
                    title_lbl = tk.Label(frame, bg=BACKGROUND_COLOR, fg="white", font=("", 20), text=title)
                    end_lbl = tk.Label(frame, bg=BACKGROUND_COLOR, fg="white", font=("", 13), text=f"Hours : {times},  Dates : {dates}")
                    buttons_frm = tk.Frame(frame, bg=BACKGROUND_COLOR)
                    buttons_frm.columnconfigure([0,1,2], minsize=60)
                    buttons_frm.rowconfigure(0, minsize=60)
                    inspect_btn = tk.Button(buttons_frm, bg=BTN_COLOR, fg="white", font=("", 10), text="Inspect", bd=0)
                    abort_btn = tk.Button(buttons_frm, bg=BTN_COLOR, fg="white", font=("", 10), text="Abort", bd=0)

                    delete_btn = tk.Button(buttons_frm, bg=BTN_COLOR, fg="white", font=("", 10), text="Delete", bd=0, command=partial(delete_task, frame, page + iteration_index + 1))
                    inspect_btn.grid(row=0, column=0, padx=3, sticky="nsew")
                    abort_btn.grid(row=0, column=1, padx=3, sticky="nsew")
                    delete_btn.grid(row=0, column=2, padx=3, sticky="nsew")

                    title_lbl.grid(row=0, column=0, padx=30, sticky="nsew")
                    end_lbl.grid(row=0, column=1, padx=70, sticky="nsew")
                    buttons_frm.grid(row=0, column=2, padx=20, sticky="nsew")
                    frame.pack(pady=30)
                    line = tk.Frame(view_task_wnd, height=1, width=770, bg="white")
                    line.pack(pady=30)
                    item_list.clear()

                    # Adding every frame and white line into the list
                    view_fields[iteration_index] = frame
                    view_lines[iteration_index] = line

            view_flag = False
            iteration_index = iteration_index + 1
                
        # Creating the next and previous button
        pages_btns = tk.Frame(view_task_wnd, bg=BACKGROUND_COLOR)
        prvs_btn = tk.Button(pages_btns, bg=BTN_COLOR, fg="white", text="Previous", font=("", 15), command=partial(next_page, "Previous"))
        next_btn = tk.Button(pages_btns, bg=BTN_COLOR, fg="white", text="Next", font=("", 15), command=partial(next_page, "Next"))
        prvs_btn.grid(row=0, column=0, padx=(100,20))
        next_btn.grid(row=0, column=1, padx=400)
        view_btns = pages_btns
        pages_btns.pack(padx=50)

    next_page("Next")


# Method for destroying root wnd and ending thread
def close_root():
    global stop_threads
    stop_threads = True
    t1.join()
    root.destroy()
    # t1.()


root = tk.Tk()
root.resizable(False, False)
root.title("Taskify")
root.geometry("500x500")
root.config(bg=BACKGROUND_COLOR)
root.protocol("WM_DELETE_WINDOW", close_root)

# Creating main menu buttons
buttons_v = ["Login", "Register", "Add Task", "View All Tasks"]
cmnds_v = [partial(register_login,"Login"), partial(register_login,"Register"),partial(add_task, "UNKNOWN") , view_tasks]

btns_frm = tk.Frame(root, bg="#212121")
btns_frm.rowconfigure([0,1,2,3], minsize=110)
btns_frm.columnconfigure(0, minsize=400)

for i in range(len(buttons_v)):
    button = tk.Button(btns_frm, text=buttons_v[i], font=("", 20), bg=BTN_COLOR, fg="white", highlightthickness = 0, bd = 0, command=cmnds_v[i])
    button.grid(row=i, column=0, pady=20, sticky="nsew")


btns_frm.pack(pady=25)

root.mainloop()


