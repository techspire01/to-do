from datetime import date

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import RegisterForm, TaskForm
from .models import Task


BOARD_COLUMNS = [
    (Task.STATUS_BACKLOG, "Backlog"),
    (Task.STATUS_TODO, "To Do"),
    (Task.STATUS_IN_PROGRESS, "In Progress"),
    (Task.STATUS_REVIEW, "Review"),
    (Task.STATUS_DONE, "Done"),
]

PRIORITY_BADGES = {
    Task.PRIORITY_LOW: "bg-success-subtle text-success-emphasis",
    Task.PRIORITY_MEDIUM: "bg-warning-subtle text-warning-emphasis",
    Task.PRIORITY_HIGH: "bg-danger-subtle text-danger-emphasis",
    Task.PRIORITY_URGENT: "bg-dark text-white",
}


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Your account was created successfully.")
        return redirect("dashboard")

    return render(request, "registration/register.html", {"form": form})


@login_required
def dashboard(request):
    status = request.GET.get("status", "").strip()
    priority = request.GET.get("priority", "").strip()
    query = request.GET.get("q", "").strip()

    tasks = Task.objects.filter(user=request.user)

    valid_statuses = {choice[0] for choice in Task.STATUS_CHOICES}
    valid_priorities = {choice[0] for choice in Task.PRIORITY_CHOICES}

    if status in valid_statuses:
        tasks = tasks.filter(status=status)

    if priority in valid_priorities:
        tasks = tasks.filter(priority=priority)

    if query:
        tasks = tasks.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )

    paginator = Paginator(tasks, 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    task_list = list(page_obj.object_list)
    for task in task_list:
        task.priority_badge = PRIORITY_BADGES.get(task.priority, "bg-secondary-subtle")

    board_columns = []
    for column_key, column_label in BOARD_COLUMNS:
        column_tasks = [task for task in task_list if task.status == column_key]
        board_columns.append(
            {
                "key": column_key,
                "label": column_label,
                "tasks": column_tasks,
                "count": len(column_tasks),
            }
        )

    context = {
        "page_obj": page_obj,
        "tasks": task_list,
        "board_columns": board_columns,
        "selected_status": status,
        "selected_priority": priority,
        "search_query": query,
        "today": date.today(),
        "status_choices": Task.STATUS_CHOICES,
        "priority_choices": Task.PRIORITY_CHOICES,
    }
    return render(request, "todo_app/dashboard.html", context)


@login_required
def add_task(request):
    form = TaskForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        task = form.save(commit=False)
        task.user = request.user
        task.save()
        messages.success(request, "Task created successfully.")
        return redirect("dashboard")

    return render(
        request,
        "todo_app/task_form.html",
        {"form": form, "page_title": "Add Task", "submit_label": "Create Task"},
    )


def _get_user_task(user, pk):
    return get_object_or_404(Task, pk=pk, user=user)


@login_required
def update_task(request, pk):
    task = _get_user_task(request.user, pk)
    form = TaskForm(request.POST or None, instance=task)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Task updated successfully.")
        return redirect("dashboard")

    return render(
        request,
        "todo_app/task_form.html",
        {
            "form": form,
            "task": task,
            "page_title": "Update Task",
            "submit_label": "Save Changes",
        },
    )


@login_required
def delete_task(request, pk):
    task = _get_user_task(request.user, pk)
    if request.method == "POST":
        task.delete()
        messages.success(request, "Task deleted successfully.")
        return redirect("dashboard")

    return render(request, "todo_app/task_confirm_delete.html", {"task": task})


@login_required
def mark_complete(request, pk):
    if request.method != "POST":
        return redirect("dashboard")

    task = _get_user_task(request.user, pk)
    task.status = (
        Task.STATUS_TODO
        if task.status == Task.STATUS_DONE
        else Task.STATUS_DONE
    )
    task.save(update_fields=["status"])
    messages.success(request, "Task status updated successfully.")
    return redirect("dashboard")


@login_required
def move_task(request, pk, direction):
    if request.method != "POST":
        return redirect("dashboard")

    task = _get_user_task(request.user, pk)
    sequence = [column[0] for column in BOARD_COLUMNS]
    current_index = sequence.index(task.status)

    if direction == "left" and current_index > 0:
        task.status = sequence[current_index - 1]
    elif direction == "right" and current_index < len(sequence) - 1:
        task.status = sequence[current_index + 1]

    task.save(update_fields=["status"])
    return redirect("dashboard")
