from datetime import date

from django.contrib.auth.models import User
from django.urls import reverse
from django.test import TestCase

from .models import Task


class TodoAppTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="mohan",
            password="strong-pass-123",
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_user_can_register(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password1": "ComplexPass123",
                "password2": "ComplexPass123",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_user_can_create_task(self):
        self.client.login(username="mohan", password="strong-pass-123")
        response = self.client.post(
            reverse("add_task"),
            {
                "title": "Finish project",
                "description": "Complete the Django to-do app",
                "deadline": "2026-04-01",
                "priority": Task.PRIORITY_HIGH,
                "status": Task.STATUS_TODO,
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("dashboard"))
        task = Task.objects.get(title="Finish project")
        self.assertEqual(task.user, self.user)
        self.assertEqual(task.description, "Complete the Django to-do app")
        self.assertEqual(str(task.deadline), "2026-04-01")
        self.assertEqual(task.position, 1)

    def test_user_can_update_complete_and_delete_own_task(self):
        task = Task.objects.create(user=self.user, title="Initial")
        self.client.login(username="mohan", password="strong-pass-123")

        self.client.post(
            reverse("update_task", args=[task.pk]),
            {
                "title": "Updated",
                "description": "Edited description",
                "deadline": "2026-05-01",
                "priority": Task.PRIORITY_MEDIUM,
                "status": Task.STATUS_IN_PROGRESS,
            },
        )
        task.refresh_from_db()
        self.assertEqual(task.title, "Updated")
        self.assertEqual(task.status, Task.STATUS_IN_PROGRESS)

        self.client.post(reverse("mark_complete", args=[task.pk]))
        task.refresh_from_db()
        self.assertEqual(task.status, Task.STATUS_DONE)

        self.client.post(reverse("delete_task", args=[task.pk]))
        self.assertFalse(Task.objects.filter(pk=task.pk).exists())

    def test_filter_only_shows_matching_tasks(self):
        Task.objects.create(
            user=self.user,
            title="Pending task",
            status=Task.STATUS_TODO,
            priority=Task.PRIORITY_LOW,
            deadline=date(2026, 4, 1),
        )
        Task.objects.create(
            user=self.user,
            title="Completed task",
            status=Task.STATUS_DONE,
            priority=Task.PRIORITY_HIGH,
            deadline=date(2026, 4, 2),
        )
        self.client.login(username="mohan", password="strong-pass-123")

        response = self.client.get(
            reverse("dashboard"),
            {"status": Task.STATUS_DONE, "priority": Task.PRIORITY_HIGH},
        )

        tasks = list(response.context["tasks"])
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].title, "Completed task")

    def test_user_cannot_access_other_users_task(self):
        other_user = User.objects.create_user(username="other", password="test-pass-123")
        task = Task.objects.create(user=other_user, title="Private task")
        self.client.login(username="mohan", password="strong-pass-123")

        response = self.client.get(reverse("update_task", args=[task.pk]))

        self.assertEqual(response.status_code, 404)

    def test_user_can_move_task_across_board(self):
        task = Task.objects.create(
            user=self.user,
            title="Board issue",
            status=Task.STATUS_TODO,
            priority=Task.PRIORITY_MEDIUM,
            position=1,
        )
        self.client.login(username="mohan", password="strong-pass-123")

        self.client.post(reverse("move_task", args=[task.pk, "right"]))
        task.refresh_from_db()
        self.assertEqual(task.status, Task.STATUS_IN_PROGRESS)
        self.assertEqual(task.position, 1)

    def test_user_can_reorder_tasks_within_and_across_columns(self):
        first = Task.objects.create(
            user=self.user,
            title="First",
            status=Task.STATUS_TODO,
            position=1,
        )
        second = Task.objects.create(
            user=self.user,
            title="Second",
            status=Task.STATUS_TODO,
            position=2,
        )
        review = Task.objects.create(
            user=self.user,
            title="Review",
            status=Task.STATUS_REVIEW,
            position=1,
        )
        self.client.login(username="mohan", password="strong-pass-123")

        response = self.client.post(
            reverse("reorder_task", args=[second.pk]),
            {
                "status": Task.STATUS_REVIEW,
                "ordered_task_ids[]": [review.pk, second.pk],
            },
        )

        self.assertEqual(response.status_code, 200)
        first.refresh_from_db()
        second.refresh_from_db()
        review.refresh_from_db()
        self.assertEqual(first.position, 1)
        self.assertEqual(second.status, Task.STATUS_REVIEW)
        self.assertEqual(second.position, 2)
        self.assertEqual(review.position, 1)
